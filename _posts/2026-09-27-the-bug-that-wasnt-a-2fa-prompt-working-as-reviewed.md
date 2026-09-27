---
layout: post
title: "The bug that wasn't: a 2FA prompt working as reviewed, and the knob I turned instead"
date: 2026-09-27
categories: [security, devops]
tags: [keycloak, oidc, terraform, jenkins, grafana, 2fa, mfa, aws-ssm, security, verification]
excerpt: "Jenkins was making me do password plus a one-time code every few minutes. A well-evidenced write-up traced it to a missing step in the Keycloak login flow and recommended adding it back. The diagnosis was correct and the fix was wrong: the missing step is deliberate, and a dated security-review comment sitting above the resource says why. The actual lever was a different knob entirely — one that controls how often the check fires rather than whether it can be skipped. Including the part of the bill that did get worse, which the commit message I wrote doesn't quite say."
author: Douglas Lockamy
ai_assisted: true
---

The complaint was mine and it was specific: *any time I hit Jenkins's main
page I have to log back in — username, password, and a one-time code.*
Every few minutes, all night. Not a session that expired once. A tollbooth.

That produced a same-day write-up with real evidence in it, tracing the
behavior to a specific Terraform resource and recommending a specific fix.
The evidence was good. The diagnosis was correct. The fix would have
reversed a security control that somebody had already thought harder about
than I was about to.

This is a post about the twenty minutes between "I have the fix" and
"actually, hold on," because that gap is the only thing that kept a
reviewed control from being quietly deleted by a maintenance change.

## The diagnosis, which was right

Jenkins and Grafana on my network authenticate through Keycloak, in a
realm shared with the consumer-facing side of the product. Both admin
clients bind a custom browser flow rather than the realm default:

```hcl
authentication_flow_binding_overrides {
  browser_id = keycloak_authentication_flow.operators_sol_step_up_browser.id
}
```

And that flow, in its entirety, is two executions:

```hcl
authenticator = "auth-username-password-form"   # REQUIRED, priority 10
authenticator = "auth-otp-form"                 # REQUIRED, priority 20
```

That's all of it. Which is notable, because a stock Keycloak browser flow
*begins* with a **Cookie** execution (`auth-cookie`) — the step that
notices you already hold a valid SSO session for the realm and lets you
straight through without prompting for anything. Keycloak does not
silently insert one into a custom top-level flow you build from an empty
flow resource. If it isn't declared, it isn't there.

No Cookie step means no session reuse means every single invocation of
that flow is a full interactive password-and-OTP challenge, regardless of
how recently you logged in elsewhere in the same realm. That is exactly
the symptom I was reporting. The write-up was right about the mechanism,
and the recommended fix followed cleanly: add an `auth-cookie` execution
as the first step, `ALTERNATIVE`, and standard behavior resumes.

It's a two-line Terraform change. It plans clean. It would have worked
perfectly.

## The comment above the resource

The thing that saved this was that the write-up flagged its own weak spot.
It didn't present the missing Cookie step as a bug; it listed, under what
it hadn't confirmed, whether the omission was "an oversight vs. a
deliberate (if user-hostile) choice" — and told whoever picked it up next
to read the surrounding comments in the file before assuming either.

I read them. It's deliberate.

Immediately above the flow's own resource definition sits a dated
security-review comment — a specific reviewed item, from a specific
review wave — stating outright that this flow has no cookie or SSO
shortcut *by omission, on purpose*, so that a password-plus-OTP challenge
is required on every login to these admin clients regardless of an
existing realm session. The comment even names what it's emulating: the
Keycloak-native equivalent of `prompt=login` / `max_age=0`.

And the reason is not aesthetic. Consumer logins and operator logins were
about to share one realm SSO session — the flow was written the same day
the operator clients were first staged into that realm, four days ahead of
the merge actually going live. Without it, a stolen consumer session
cookie or a captured consumer password walks into Grafana, Jenkins, and
the container-update watcher's admin surface with no second factor
required. The flow stands in for a separate operator signing key that
hasn't been built yet. It is load-bearing *because* of a convenience that,
at the moment it was written, hadn't shipped yet either — hardening put in
before the door it protects was even open.

So the proposed fix wasn't a fix. It was a two-line patch reopening
exactly the attack path the control exists to close, and in a diff it
looks identical to a fix — an obviously-missing standard step, restored.
That's the whole hazard. Nothing about the shape of the change tells you
which of those two things it is. Only the comment does.

## Confirming it rather than believing it

I didn't want to take the comment's word for it either, for the same
reason I shouldn't have taken the write-up's word for it. Prose in a repo
is a claim about the system, not the system. So, two checks:

**One: the live state.** Pulled the real remote Terraform state for the
identity stack and read the actual `keycloak_authentication_execution`
resources. Exactly two, matching the file, no drift. Nobody had added a
Cookie step in the console and let the code fall behind — the reviewed
design is what's actually running.

**Two: the blast radius of the symptom.** Grafana binds the *same* flow
with the same settings. If the cause is the flow, Grafana must behave the
same way; if only Jenkins does this, the cause is something
Jenkins-plugin-specific and the flow is a red herring. Structurally it has
to hit both, which is consistent with a flow-level control and
inconsistent with a Jenkins quirk.

The diagnosis survived verification. The recommendation didn't.

## The knob I should have been looking at

Here's what I'd conflated, and it took separating two sentences to see it:

- **Whether the check can be silently skipped.** That's the Cookie step.
  That's the control.
- **How often the check fires.** That's `access_token_lifespan`. That's a
  number.

Those are different knobs. I'd been treating the friction as a property of
the control, when the control only says *you cannot skip this*. How often
you're made to do it is set somewhere else entirely — a per-client
override sitting about a hundred lines above the flow, pinning the admin
clients to 300 seconds against the realm's consumer-tuned 15-minute
default.

Five minutes. With no silent-refresh escape hatch behind it, a five-minute
access token means a full interactive password-and-OTP login up to twelve
times an hour while you're actively working. Which is precisely what I'd
been experiencing, and it's not a malfunction — it's two deliberate
decisions multiplying into something neither of them intended on its own.

So: 300 to 1800 on all three admin clients. Thirty minutes instead of
five, six times less friction, and the Cookie step stays absent. A stolen
consumer session still cannot reach any of those admin surfaces without
completing password and OTP. It just gets asked to try less often than I
do.

## The part of the bill I'm going to say out loud

My own commit message says "OR-3's actual security property is unchanged."
That's true and it isn't the whole invoice, so let me put the rest of it
here rather than leave it in a footnote nobody reads.

The 300 wasn't arbitrary. Its own comment explains it: Grafana validates
JWTs locally against JWKS with no introspection call, so a revoked
operator's already-issued access token keeps working until it expires on
its own. There is no revoke button that reaches it. The lifespan *is* the
revocation window.

I just moved that window from five minutes to thirty.

The no-silent-skip property is genuinely untouched — that's real, and
it's the property the review was protecting. But a second property, how
fast a revoked operator actually loses access, got six times worse, and
"same security property, less friction" is too tidy a sentence for what
happened. What happened is I traded one property I could afford to lose
thirty minutes of for one I was losing an hour of productivity to, made
that trade knowingly, and wrote it into the code next to the number so the
next person sees the cost and not just the value.

That's a different thing from a free win, and I'd rather label it
correctly.

## Applying it, which is its own small story

Keycloak's admin console is hard-blocked on the public listener — a
fixed-response rule evaluated before any host routing, no exceptions. The
reasoning is sound and worth repeating: this network has no static egress
IP, and behind proxied DNS the load balancer never sees a real client IP
anyway, so an IP allowlist was a dead end no matter how it was written.
Fail closed instead. Nobody reaches `/admin/*` from the internet, ever.

Which means a Terraform provider that talks to the Keycloak admin API
can't reach it from my desk. Real admin access is an AWS SSM Session
Manager port-forward straight into the running container — that's the
documented path, and it's the only one.

So: open the tunnel, point the provider at localhost, and run a plan
scoped to just those three clients. The plan showed three changes, each
one `access_token_lifespan: 300 -> 1800`, and nothing else — which is the
entire reason to scope it, on a stack where an unscoped plan against live
identity infrastructure has produced genuine surprises in the same week.
Applied. Then verified twice, because state and reality are different
claims: the Terraform state, and a direct read back out of the Keycloak
admin API.

## What I'm not calling done

There's a question underneath all of this that I still can't answer.

Silent token refresh — the refresh-token grant — is a direct call to the
token endpoint. It does not go through the browser flow at all, Cookie
step or no Cookie step. So if refresh is healthy, the interactive
challenge should only fire about once per token lifespan. If it's actually
firing far more often than that, then the real defect is in the Jenkins
OIDC plugin's refresh handling and has nothing to do with the step-up flow
I spent the day reading.

I described the symptom as "every few minutes" from memory, under
annoyance, which is not a measurement. I don't know whether it was firing
at the designed cadence or well above it.

The nice accident is that raising the number turned that unknown into a
test. At 300 seconds, "designed cadence" and "broken refresh" produce
roughly the same lived experience and I can't tell them apart. At 1800,
they don't: if I still get challenged every five minutes, refresh is
broken and I'll know within one working session, with no further
investigation needed. The change I made for comfort is also the
instrument.

---

The honest shape of this one: a good bug report, correct in every detail
it asserted, pointed at a fix that would have downgraded security — and
the only reason it didn't was that the report named its own unverified
assumption instead of rounding it off, and the control had a comment
explaining itself sitting three lines above the resource.

Both of those are cheap. Writing down what you haven't checked costs a
sentence. Explaining *why* a thing is missing, at the place where its
absence is implemented, costs a paragraph. Neither would show up in any
review of the change I almost made, because the change was fine. It was
the change's premise that was wrong, and premises don't appear in diffs.

The version of me that skipped both would have shipped a two-line patch,
closed the ticket, enjoyed a markedly smoother login experience, and
never found out what it cost.
