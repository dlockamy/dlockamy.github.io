---
layout: post
title: "A stale comment, a dead include, and every vhost on the box down at once"
date: 2026-09-27
categories: [devops, security]
tags: [nginx, terraform, docker, jenkins, keycloak, oauth2-proxy, homelab, incident, technical-debt]
excerpt: "The job was copy-editing: read my infrastructure's own landing page and fix anything that isn't true any more. Two of the stale claims turned out to be load-bearing — a health check that never accepted the status code its own comment insisted it accepted, and a sentence describing a perimeter auth layer I tore down three weeks ago. Then deploying the corrected words recreated a container and took down every vhost on the host at once. The landmine was left behind by that same teardown, and a comment in the repo had predicted it three days earlier, in detail, naming the exact command I ran."
author: Douglas Lockamy
ai_assisted: true
---

The task I picked up was about as low-stakes as infrastructure work gets:
read `softsurve.com`'s landing page — the status board for my home
network, Sol — and fix anything on it that had stopped being true. Copy
editing. Words on a page nobody but me reads.

It ended with `sol-nginx` in a crash loop and every single vhost on the
host down at once: Jenkins, Grafana, Nexus, the Docker registry, the
container-update watcher, and the landing page itself. I caused that, with
a deploy whose entire payload was corrected prose.

The interesting part isn't the outage. It's that two of the stale
sentences I was there to fix were stale for the *same reason* the box went
down, and something in the repo had already written the incident report
three days before it happened.

## Act one: the health check that never did what its comment said

The page probes a handful of services and shows a dot per service. One of
those services is Sirius — the AWS-side platform that carries the
customer-facing workloads, as opposed to Sol, which is the house.

Sirius's dot had been red. Sirius was fine.

The probe hits Sirius's ALB through a proxied path. Until a real hostname
is cut over to it, that ALB answers every `Host` header with its fixed
404 default — which is a perfectly good liveness signal, because you have
to be reachable to 404 at somebody. And the comment above the entry said
exactly that, in plain language: the 404 still proves the platform is up,
same *"any real HTTP response counts"* logic the checker already applies
to the 401/403 case.

The checker did not apply that logic. Here is the whole of it:

```js
const ok = (res.status >= 200 && res.status < 300)
  || res.status === 401 || res.status === 403;
```

2xx, 401, 403. That's the list. 404 was never on it. The comment
described an intention; the expression described the behavior; they
disagreed, and the expression won, the way it always does. Sirius had been
reading as offline for as long as that probe had existed, and I'd been
looking straight past it because the comment told me it was handled.

The fix I *didn't* make was adding 404 to the shared condition. A 404 from
Nexus's real health endpoint means Nexus is broken, not coy. So the fix is
a per-service allowlist and one service opting in:

```js
{ id: 'sirius', url: '/-/health/sirius', extraOk: [404] },
```

Narrow, and narrow on purpose. The general version of this fix would have
made every service on the board slightly worse at telling me the truth in
exchange for making one service correct.

## Act two: a sentence about an auth layer that doesn't exist

The second stale claim was a card on the same page saying Google
Workspace provided "Google OAuth SSO for internal tools," and a readout
line reading `perimeter auth: oauth2-proxy · google workspace sso`.

Both were true when they were written. Neither is true now, and the
history matters because it's the rest of this post.

Back in July I put oauth2-proxy in front of Sol's browser-facing
vhosts — one `auth_request` gate, Google Workspace as the identity
provider, and an exclusion list for everything that structurally cannot
complete a browser redirect. That exclusion list was the real content of
the project: Nexus's package clients (Cargo, Dart, Maven), the Docker
registry vhosts, Jenkins's `/github-webhook/`, and the Jenkins MCP
server's own path all had to stay ungated, because none of them is a
browser and none of them can follow a 302 to a consent screen.

Six weeks later I killed the whole thing. Not because it failed — because
each admin surface had meanwhile grown its own Keycloak OIDC login, which
is strictly better: the service knows who you are instead of inferring
that somebody upstream checked. Once Grafana and Jenkins each had that, a
shared perimeter gate stopped being a control and became a second thing
to maintain that could only ever agree or be wrong. Decommissioned
2026-09-07, torn down 2026-09-08. Sol now has no perimeter auth at all,
by design, and the readout line says so:

```
perimeter auth   none — service-owned oidc (keycloak, quickring realm)
```

Nexus is the one holdout, still on JumpCloud LDAP — deliberately kept off
the Keycloak migration for precisely the reason it was on the oauth2-proxy
exclusion list. It's a CLI and registry surface. The same constraint keeps
producing the same answer.

So I fixed the sentences, and the commit also pulled three dead
`sol/oauth2-proxy/*` entries out of the secret-provisioning script's
managed list — with a note that the underlying values stay in Secrets
Manager, unmanaged and unrotated, on purpose, in case a perimeter gate
ever comes back. That's a deliberate loose end, labeled as one.

Then I deployed.

## Act three: the words went out and the host went down

Sol deploys per-service through Jenkins. I triggered it over the Jenkins
API — `SERVICE=nginx ACTION=apply` — which is the right job for a change
to a vhost template.

That apply recreated the `sol-nginx` container. It had to: the September
8th teardown had removed the `/opt/sol/nginx/snippets` volume mount from
nginx's own container definition in Terraform, and `sol-nginx` had not
been recreated since. A container replacement had been sitting in that
plan, undeployed, for nineteen days. My content change was just the thing
that finally ran the apply.

The new container came up without the snippets mount. One vhost config —
`beta-admin.softsurve.com.conf`, for an internal admin UI, rendered by a
module that predates the teardown — still contained this line:

```nginx
include /etc/nginx/snippets/oauth2-auth.conf;
```

That file no longer existed inside the container. nginx failed its own
config test, refused to start, and crash-looped. And because every vhost
on the host lives inside that one nginx, one broken `include` in one
config file took down all of them simultaneously — including Jenkins,
which is how I deploy things.

That's the part worth sitting with. The blast radius of a missing file in
an admin UI's vhost was the entire host, and the deploy tool was inside
it. Recovery couldn't be another pipeline run. It was SSH and Terraform by
hand.

The mechanism is completely unremarkable once you say it out loud: **nginx
only validates its configuration when it starts.** A vhost that references
a deleted file is not "broken" in any way the running system can tell you
about. It is a config file that is already wrong and simply hasn't been
read yet. It stays invisible for exactly as long as nobody recreates the
container, and then it is the most visible thing on the network.

## Act four: the incident report was written three days early

Here's what I found when I went looking for why that include was still
there.

It was already known. On September 24th — three days before any of
this — someone went through the modules the oauth2-proxy teardown had
missed, found this exact vhost, and wrote it up *in the vhost template
itself*. Not a ticket. A comment, sitting in the file, above the affected
`location` block. Abbreviated, because the real one is longer:

> ⚠ Removed from the CODE, not from the running host — verified live
> 2026-09-24. `sol-nginx` has not been recreated since 2026-09-08, so it
> still carries the old mount and
> `/etc/nginx/snippets/oauth2-auth.conf` is still present inside it.
> `nginx -t` therefore still passes today.
>
> And it is armed to get much worse. Every Sol service's nginx step runs
> `docker exec sol-nginx nginx -t` across the WHOLE conf.d directory. The
> next `SERVICE=nginx ACTION=apply` recreates `sol-nginx` WITHOUT the
> snippets mount; the include then resolves to a missing file, `nginx -t`
> fails, and nginx takes down EVERY vhost on io — grafana, jenkins,
> nexus, wud, softsurve.com, spec-up-dev, ws-dev, build — not just
> studio-admin. Apply THIS module before nginx is next applied.

It names the trigger. It names the command. It names the blast radius, as
a list, and the list is correct. It tells you the ordering constraint that
would have avoided the whole thing. Three days later I ran that exact
command and got that exact outcome.

The repair was written too, in the same pass. The dead include was
replaced with a `deny all` — a deliberate fail-closed, not a cleanup,
because that admin UI is the one service that never got its own Keycloak
login, so simply deleting the include would have quietly opened the signup
queues and the invite action to anything on the LAN. A downgrade dressed
up as tidying. The comment says that too, and says what reopening it
properly requires.

So: the defect was found, root-caused, written up with an accurate
prediction, and fixed in the code. And it still went off. Why?

Because none of that put a single byte on the host. The module carrying
the repair had never successfully deployed — that same commit had to give
`studio_admin_image` a default just to make the module *plannable* in CI
at all, because Sol's root pipeline passes only three variables to every
service and a required variable with no default fails at plan. For a
while, this wasn't merely unapplied. It was unappliable. And once that was
cleared, all that remained was for someone to run the apply, in the right
order, before touching nginx. Nobody did. Me included, three days later,
with the warning in the file I was one directory away from.

The fix for the outage was, in the end, applying the repair that had been
sitting in the repo the whole time.

I keep relearning one version of this lesson in different costumes. A
while back it was a release pipeline reporting a successful upload while
handing out two-week-old bytes — the log is a claim about the artifact,
not the artifact. This is the same shape with the tenses swapped: **a fix
merged into the repo is a claim about the host, not the host.** The
correct diff, reviewed, with an excellent commit message, changes nothing
at all until something runs it.

## Act five: the same pass, on my own site

Having established that stale prose is load-bearing, I ran the identical
review on this site's own data files. Four things:

- A GitHub org listed as an active project. It was dissolved on
  2026-08-23; its repos moved elsewhere over a month ago, and two project
  cards still linked to the dead org's URLs.
- A project with its own card that no longer exists standalone — absorbed
  into another one in August. Folded a one-line mention into the surviving
  project rather than deleting the history outright.
- Three things marked `IN_DEV` that are genuinely live in production,
  including one running real user logins.
- And the same wrong sentence about Google Workspace SSO at the reverse
  proxy that I'd just finished deleting from the other site, sitting right
  there in Sol's description.

Nothing here caused an outage. It's the same defect class all the way
down, though: prose that was accurate when written, silently detached from
what it describes, still asserting itself confidently. Code fails a build
when it lies. Comments and copy just keep saying the old thing in a
steady voice until you deploy them into something that checks.

---

The honest shape of the day: I set out to make a status page tell the
truth, and discovered the page's own instrumentation had been lying about
one service the entire time, that two sentences on it were wrong because
of a teardown three weeks old, and that the same teardown had left a live
round in a vhost the teardown's own commit never enumerated. Then I fired
it, with a prose change, using a pipeline that was itself downstream of
the thing that broke.

If there's a takeaway beyond "apply your fixes," it's about what a
decommission actually is. Deleting oauth2-proxy was clean. Its container
is gone, its Terraform is gone, its secrets are unmanaged on purpose. What
wasn't clean is that nothing in the system knew which configs *consumed*
it. Four vhosts included that snippet; the teardown commit enumerated
three. A removal is not finished when the thing is gone. It's finished
when every consumer of the thing is gone, and the only reason the
remaining one felt fine for nineteen days is that nginx hadn't been asked
to read its own config yet.

The deploy that finds your landmine is never the deploy you were worried
about. It's a content change, on a Sunday, to a page nobody reads.
