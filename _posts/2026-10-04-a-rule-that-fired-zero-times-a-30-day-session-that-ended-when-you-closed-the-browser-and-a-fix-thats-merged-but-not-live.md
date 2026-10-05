---
layout: post
title: "A rule that fired zero times, a 30-day session that ended when you closed the browser, and a fix that's merged but not live"
date: 2026-10-04
categories: [devops, security]
tags: [keycloak, aws, eventbridge, lambda, ecs, oidc, jenkins, cloudflare-pages, ollama, local-llm, verification, homelab]
excerpt: "Keycloak was down for five days and seventeen hours this week, and the rule I'd built so that couldn't happen again fired zero times. Its pattern was right; the event never arrived. A session problem I blamed on a time limit was a refresh race. An analysis that said customers already get 30-day sessions was wrong in practice. A portal fix got merged into a deploy pipeline that hadn't deployed anything since September 8. A Jenkins restart showed three machines whose running state had drifted from their config. And twelve answers from four local models all blamed the same correct line of code. Each was found by reading the real thing instead of the description of it, and several aren't finished."
author: Douglas Lockamy
ai_assisted: true
---

Keycloak was down for five days and seventeen hours this week, and the
thing I had built specifically so that couldn't happen again fired zero
times.

The more useful part is that the same shape kept turning up all week. A
check, a claim or a "fixed" was wrong or had never run, and what caught it
was reading the real thing: a log, the running config, a slicer's first
layer. The descriptions all said fine.

Some of the wrong claims were mine, some came from the agent doing the
digging, and two were in my own notes from the previous two weeks, written
with complete confidence. I'll say which was which.

## The safety net that never fired

Keycloak's database password is an RDS-managed secret that rotates itself
every seven days, deliberately, so no database password is ever stored by
hand. But ECS resolves a secret once, at container start, and nothing
restarts a long-running task when the secret changes. The first time this
bit me it took every realm down for eight days in mid-September. I didn't
write that one up.

The fix I wrote down then was the obvious one: Secrets Manager emits a
`RotationSucceeded` event through CloudTrail, an EventBridge rule routes it
to a small Lambda, and the Lambda forces a new ECS deployment. If the
pattern didn't match the first real rotation, the plan said, widen it.

On the 26th, my notes recorded the Lambda as "proactively invoked directly
and proven working end-to-end ahead of the next real rotation." Invoking it
by hand proved the Lambda can redeploy Keycloak. It proved nothing about
whether anything would ever invoke it.

The secret rotated at 01:22 EDT on Monday the 28th, about eighteen and a
half hours before its listed date, so before anyone was looking. Thirteen
minutes later came the first Postgres authentication failure, and from then
on every Keycloak request that touched the database returned a 500. Jenkins
and Grafana logins were down the whole time. The discovery document and
signing keys kept answering 200 from cached state, exactly as they had the
first time, so anything shallow said Keycloak was healthy. Nothing alerted.
It was found at 18:43 on Saturday, in the middle of a machine rebuild that
needed a Jenkins login, and fixed at 18:47 by forcing the
redeploy by hand. Four minutes of fixing after five and a half days of not
knowing.

Then I looked at the rule. It had fired **zero times**. The pattern was
right. CloudTrail had recorded the real rotation event,
`aws events test-event-pattern` returns true against it, and the secret ID
matches. The rule's trigger metric is simply empty. EventBridge never
received the event. I don't know why yet, and I'm not going to guess in
public.

That rules out two things I'd have got wrong. **Widening the pattern, my
own fallback, would not have helped**, because the pattern was never the
problem. And **the alarm I had couldn't have caught it.** It watched the
Lambda's errors, and a rule that never fires produces no errors. An alarm
on failure stays quiet when the failure is that nothing happened.

The replacement doesn't wait for the event. A scheduled Lambda runs every 15
minutes and reads state. If the secret changed after the running task was
created, it forces a redeploy. Loop guards skip it during a deployment,
within ten minutes of the last one, or on a timestamp from the future. It
has two alarms: one on errors, and one on *silence* (fewer than one
invocation in three hours, with missing data counted as breaching), because
silence is the failure that actually happened. Overnight it ran four times
an hour with zero errors.

What that does **not** prove: the new Lambda has never redeployed anything.
Its permissions passed the IAM policy simulator, which is a claim about
permissions, not the path. The next rotation is listed for tomorrow evening;
given how early the last one came, the window to watch opens around 01:20 tomorrow morning. And the
container still has no health check on a database-touching endpoint, the
follow-up the first outage named and the second one happened without.

The lesson, as I wrote it into the incident note: a safety net that depends
on an event arriving needs a second one that reads state directly. "The code
path works when I invoke it by hand" is not "the trigger works."

## "Customers log in constantly" was not a time limit

Same weekend, a different worry, and this one was mine: stretch the
Keycloak time limit, because customers can't be logging in constantly just
to cycle a timed-out session.

It wasn't a time limit. Keycloak's log showed one Jenkins session dying at
20:58 UTC with `Maximum allowed refresh token reuse exceeded`. The realm
rotates refresh tokens and allows zero reuse: each refresh issues a new
token and kills the old one, so a replayed token is detectable. That's
fail-closed on purpose. But when two requests refresh the same expired token
at once, the second presents a token that's already spent. Keycloak reads
that as a replay and ends the whole session. Keycloak then logged 1,306 more failed refresh attempts against a session that no longer existed. The configured
session lifetime was 30 days the entire time.

[Last week](/posts/2026/09/27/the-bug-that-wasnt-a-2fa-prompt-working-as-reviewed/)
I raised the operator token lifespan from five minutes to thirty and said
the change doubled as a test of whether refresh was healthy. This doesn't
fully answer that. It does show one way a session dies that has nothing to
do with any timer, and a longer token only makes that race rarer.

The fix I chose was to allow one reuse. The cost is stated: a stolen refresh
token can be replayed one extra time before Keycloak notices. It's written
into the Terraform comment next to the number.

Then came the customer side, where the first analysis I got back was wrong.
The agent said customers were fine, because the realm gives them 30-day
sessions. That's true in the config and false in practice. The account
portal keeps a 15-minute access token in `sessionStorage` and deliberately
does no silent refresh: a 401 "means the session is gone," so it clears
state and sends you back to sign in. And the realm had `remember_me` off, so
Keycloak's SSO cookie was a browser-session cookie. Every fifteen minutes
the portal sent you back through sign-in. With the browser still open,
Keycloak could wave you through. After you closed it, the 30-day session
still existed on the server and nothing on your side could reach it. My
instinct was right for customers, for a different reason than the one I
had.

A smaller wrong check sat inside that one. An early probe concluded the
login page had no Remember me checkbox, but it sent a bad PKCE challenge
that bounced to an error page, and the real page is rendered by script
anyway. The conclusion happened to be true; the actual evidence was the
Terraform plan showing `remember_me = false`. Right answer, wrong reason,
which next time gives the wrong answer. (The cookie's lifetime is still
inferred from that setting, not measured in a browser.)

**Applied and verified:** one refresh-token reuse, and `remember_me` on. The
apply was gated on a plan showing exactly one resource changing exactly
those two attributes. A re-plan shows no drift, and the real sign-in page
now shows the checkbox. It's opt-in and unticked by default, so it helps the
people who tick it.

**Merged:** a portal change that renews quietly. On an expired token or a
401, it redirects to Keycloak with `prompt=none`, which answers from the SSO
session without a login screen, and returns to the same page. No refresh
token is stored in the browser. Headless Chrome tests against the live
Keycloak passed 10 of 10 for the no-session path: one renewal per 401, no
loop, a clean fall-through to the normal sign-in page, and the return path
restricted to the portal's own pages.

Those tests caught a real bug before merge. The dashboard's parallel API
calls all get a 401 together, and one started the renewal while another
signed out and wiped the PKCE verifier mid-redirect. Same race shape as the
Keycloak one, in my own code, the same day. It's now handled once.

**Not tested:** the success path, where a renewal comes back from a live
session. That needs a real account. The only test account predates the
current identity setup and doesn't sign in on this realm, and the test
stopped after one attempt rather than risk locking it out.

## Merged is not deployed

Merging the portal change kicked off its CD build, and the Cloudflare Pages
deploy failed. The same failure was on the previous build, from September
26. The last successful deploy was **September 8**. So the live portal is
the September 8 build. It doesn't have the quiet renewal, and it doesn't
have the account-management screens merged on the 26th either, which have been merged since then.

Cloudflare is rejecting the Pages API token. Then it started answering "too many authentication failures" and rate-limiting my home IP, probably because of the failing builds plus the agent's own follow-up checks (I can't separate the two).
So the agent stopped calling, and it didn't reach for a broader Cloudflare
token close at hand, because that isn't the credential scoped for this job.
Correct, and slightly annoying.

**Not fixed**: it waits on me creating a new, correctly scoped token. So the
Keycloak section above comes to one change live and verified, and one
merged, tested on half its paths, and not deployed.

## A restart tells you what has been broken for days

`earth`, a Linux workstation that doubles as a CI node, was rebuilt this
week after a failed disk resize took its home folder with it. The rebuild
moved its Jenkins work directory, and a PR to match was merged. I attached
the agent by hand, it picked up builds, and everything looked fine.

Reading the controller's running config, rather than the PR, showed `earth`
still pointed at a work directory that no longer existed. The PR had been
merged and never applied, along with three other node changes merged since
the last apply.

Applying it restarts the Jenkins controller for about a minute, and the
restart did three things:

- **`earth` now matches its config.** Good.
- **A staged macOS node dropped and couldn't relaunch.** The CI account's SSH
  access on that machine was a time-boxed grant, and it had lapsed. The node
  had only stayed connected because its connection predated the restart.
  Nothing targets its labels, so no builds were affected. It stays offline
  until that account gets permanent, non-admin SSH there.
- **The older Mac's failure turned out to be one line.** It had been offline
  for days. Its launch log showed SSH authenticating fine, then `Failed to
  mkdir /Volumes/container_data`: its external drive had moved to the new
  Mac. After one config change, a plan read before the apply, and the apply,
  it's back online with two executors, because it has 37 GiB free of 228 GB.
  No macOS build has run on it since, so whether builds fit is untested.

Three machines had live state that disagreed with their config, and in every
case the live state was the one that looked fine. A restart is when the
config gets the final word.

The second apply had to wait on me, by design: a Jenkins API token here
lives and dies with my Keycloak login, so revoking me revokes my automation
too. The fix for an expired session is to log in, not to find a door that
doesn't check.

## Local models, as reviewers

Could the local models on `earth` (an RTX 3060, 12 GB, Ollama) take
routine work off the agent? Two tests, both with known answers.

**Code review: 0 of 12.** The target was a small preview renderer whose bug I'd had fixed earlier in the week. Its rotation tipped the model away from
the camera instead of towards it, so a raised boss rendered as a recess. I
gave the original code and that symptom to `llama3.2:3b`,
`qwen2.5-coder:7b`, `qwen2.5:7b` and `qwen2.5:14b`, three seeds each. All
twelve answers blamed the same line: the Y flip into image coordinates,
which is correct and necessary. Removing it would mirror the picture, not
fix it. Every answer was fluent and confident, and going from 3B to 14B
changed nothing. Trusting them would have "fixed" the code by breaking it
a different way.

**Index summaries: useful, with a reviewer.** Forty notes in my vault needed
a one-line index entry. The best model, `qwen2.5:7b`, was usable as written
on 26 of 40, with 3 wrong. The 3B model copied the prompt's worked example,
a sentence about Cloudflare, into three answers about notes that have
nothing to do with Cloudflare: verbatim twice, spliced once. The automatic
check for numbers and names absent from the source raised 18 flags. Two
were real, and it missed the spliced copy. The real errors were semantic: a
wrong verb, a missing negation, a sub-point promoted to the headline.
Grading was by hand, so treat the counts as plus or minus a few, and the
lines that went into the index were written by hand from the best drafts.

So I'll use local models for summaries a human can check in seconds, and
not as reviewers, where checking the answer means redoing the analysis.
Two things weren't tried: anything above 14B (about the ceiling for a 12 GB
card) and any reasoning-tuned model.

## Also this week

- **Drawing-to-rig.** The [setup
  overview](/posts/2026/10/02/setting-up-freecad-gimp-and-claude-to-design-3d-models/)
  and parts
  [11](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/11-from-a-drawing-to-a-model.md)
  and [12](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/12-check-the-rig.md)
  of the [tutorial](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/README.md)
  in the public [`claude-cad-workbench`](https://github.com/dlockamy/claude-cad-workbench)
  repo cover this; only the new part here. The push-up pop mascot
  that stood on a 38 mm first layer now has a print variant with a flat 36
  mm base: its first layer is 2,944 mm of path, and supports add about 17%
  filament instead of about 60%. On the humanoid, the joint-influence check built after the mascot's dead spine and chest joints failed its very first run: both hand joints owned zero vertices. **Neither model has been
  printed.**
- **Auditing a ticket's premise.** The ticket behind BenixOS's move off kirkstone says the uplift also unblocks a Smithay-based compositor, and I ruled for scarthgap. On its own, it doesn't: scarthgap's stock Rust is 1.75.0, and
  Smithay 0.7.0 declares 1.80.1. Wrynose ships 1.94.1, and `meta-rust-bin`
  solves it on any branch, including today's. Nothing was built, so every
  layer having the branches upstream is all that's established. Which way
  through is still my call.
- **A CI deadlock that's still there.** Six kit pipelines hold one
  `linux-build` executor and then ask for a second, for an arm64 cross leg
  that doesn't reuse the node. Capacity went from four executors to nine
  this week, which moves the threshold and leaves the shape alone. The count
  comes from a regex scan, so six is a floor.
- **`earth`'s rebuild** took 13-plus hours to get its agent back. The lost home folder included a loose file of credentials, which prompted an idea for a household secrets store.
  Filed as an idea; nothing built.
- **The Dial Panel's OS**
  ([public repo](https://github.com/slash-builder/hw-2015-dial-panel)) will
  be built by patching the released Raspberry Pi OS (Trixie), not by
  rebuilding one. That's merged; no image has been built from it yet.
  Optional ambient sensors and an optional flush wall mount were approved as
  designs, not built. The repo is still BETA.

## Not done, as of tonight

- The first rotation under the new Lambda is due in the early hours of
  tomorrow. Why EventBridge never got the event is unknown, and Keycloak
  still has no real health check.
- The portal's quiet renewal is merged, not deployed, and its success path
  is untested. The deploy is waiting on a new token.
- One macOS node is offline. The other is online and hasn't run a build.
- Neither 3D model has been printed.

---

The honest shape of this week: a safety net proven by hand that never
triggered, a time limit that was a race, a 30-day session that ended with
the browser, a fix merged into a pipeline that hadn't deployed in nearly
four weeks, three machines that were fine until something restarted them,
and twelve confident answers about the wrong line.

No status page, green build or note saying "done" found any of it. Tripping
over it found the outage. Everything else came from reading the real thing:
the event history, the session log, the running config, the deploy result,
the first layer.

If you've had an EventBridge rule match its pattern in a test and never
receive the real event, I'd like to hear what it turned out to be:
[find me on LinkedIn](https://www.linkedin.com/in/douglas-lockamy-49097b33/).
