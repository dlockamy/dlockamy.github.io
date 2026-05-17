---
layout: post
title: "The weekend Spec-Up went to production"
date: 2026-05-17
categories: [general]
tags: [spec-up, infrastructure, cloudflare, jenkins, terraform, devops]
excerpt: "Three days. Spec-Up went from a Docker-shipped prototype to live at spec-up.com with end-to-end TLS — and an eight-round Jenkins outage taught me about three-layer variable substitution along the way."
author: Douglas Lockamy
ai_assisted: true
---

Friday morning the `spec-up.com` domain was a Cloudflare DNS record pointing at nothing in particular. Sunday afternoon the production stack is live — API on a dedicated AWS EC2 fronted by Cloudflare, Flutter app and marketing landing on Cloudflare Pages, end-to-end TLS via a Cloudflare Origin Certificate, the EC2's security group locked down to Cloudflare's edge CIDR ranges so even if someone learns the elastic IP they can't bypass the CDN. The path got there with a few side quests. Worth a journal entry.

## The shipping arc

The plan from the project board was straightforward: bootstrap a Terraform state backend, run the first prod CD, point Cloudflare DNS at the origin, verify the surfaces, harden the TLS path. Each step took longer than expected for reasons that aren't individually interesting — AWS account had no default VPC, ECR repositories pre-existed outside Terraform state, IAM inline policies hit the 2048-byte cap, AL2023's repos don't ship the upstream Docker Compose plugin, the AMI filter `most_recent = true` picked the *minimal* variant by accident (which omits the SSM Agent), and Terraform's default `user_data` behaviour is *stop-modify-attribute-start* rather than full replacement — meaning edits to the boot-time shell script silently no-op on the running instance because cloud-init only runs once.

Each problem surfaced exactly one apply at a time. Each got a small fix and a comment explaining the gotcha. By Sunday morning the API endpoint was answering on HTTPS at `api.spec-up.com`.

## TLS to the origin

The Cloudflare default for new zones is *Flexible* SSL — encrypted edge for the user, plaintext between Cloudflare and the origin. That's fine for getting started but it leaves the CDN-to-AWS hop exposed on the open internet. Sunday afternoon was bumping that to *Full (strict)*:

1. Generate a Cloudflare Origin Certificate in the dashboard — free, fifteen-year validity, signed by Cloudflare's private CA. Trusted by Cloudflare's edge, not by public browsers, which is exactly what's wanted for an origin nobody hits directly.
2. Stash the cert and key in AWS Secrets Manager alongside the rest of the project's secrets.
3. Update the EC2's user-data to pull both at first boot, write them to `/etc/ssl/spec-up/`, and serve nginx with a `listen 443 ssl http2` block.
4. Switch the Cloudflare SSL mode to Full (strict).
5. Drop the `:80` ingress from the security group entirely — in strict mode Cloudflare only talks `:443` to origin.
6. Restrict `:443` ingress to Cloudflare's published CIDR ranges, fetched live via Terraform's `http` data source so the rule auto-updates when Cloudflare changes their edge ranges.

End-to-end encrypted, origin un-bypassable. About an hour of work once the cert was generated.

## A small UX detour

While the infra was settling, the Flutter app needed two things. First, the prototype banner referenced the collaborator who had been reviewing the design direction — that ticket is closed and the URL is heading somewhere a stranger might land, so I dropped the personal reference. Second, the navy/blue brand palette from the marketing landing page wasn't being used in the app itself — the chrome was all kraft amber. Lifted the landing's color tokens into the Flutter theme so the top bar, sidebar, and logo now match. Continuity from landing → app is a small thing but it matters when a prospect clicks through.

Added a quick login gate too — the prototype's UI is too rough to leave open to the internet. `shared_preferences` for persistence, a static demo credential, a `go_router` redirect on every unauthenticated route. The threat model is "keep crawlers and casual visitors out," not "defend against a determined attacker" — anyone with the JS bundle can read the credentials. Real auth is Okta, soon. The whole gate lives in one file so swapping it for an OIDC client is a single-file change.

I also implemented the collaborator's confirmed twelve-section information architecture as a collapsible sidebar — eighty-plus navigation entries grouped under Workspace, Commercial, Product & Materials, Design & Engineering, Planning & Production, Inventory & Warehouse, Shipping & Logistics, Procurement & Vendors, Maintenance, Finance, People, and Admin. Sections collapse by default; the one containing the active route auto-expands; a small amber dot appears on a collapsed section header when the active view lives behind it. Twenty minutes of UX polish but it transformed the prototype from "wall of links" to "navigable application."

## A smoke test suite

Once the surfaces were live, the next concern was *staying* live. Wrote a shell-script smoke suite — seventeen assertions across three groups. Public surfaces: apex landing, app subdomain, and api subdomain all return 200 from Cloudflare with the expected content markers. Subscribe flow: CORS preflight from the landing origin, real POST with the Origin header set, response shape check, and DynamoDB persistence verification — using a unique `test+smoke-<unix>@example.com` row per run, cleaned up at the end. Security posture: direct `:80` and `:443` connection attempts to the EIP from a non-Cloudflare source must time out, confirming the security-group lockdown is enforced.

Wired into the CD pipeline as a post-deploy stage so every prod deploy validates itself before reporting green. Also exposed as a standalone job via `Jenkinsfile.test` — the same suite runs nightly as a drift check and can be triggered manually after incidents.

## A Jenkins reorganization

The other major weekend project was reorganizing the Jenkins controller for Sol. The flat list of top-level org folders (one per GitHub organization, scanning for a single Jenkinsfile per repo) was getting hard to navigate as the project count grew. Restructured into nested per-org folders, each containing three sibling org-folder children for different Jenkinsfile variants:

```
additiveprime/
  ci/   — auto-discovers repos with Jenkinsfile         (build per push)
  cd/   — auto-discovers repos with Jenkinsfile.cd      (deploy)
  test/ — auto-discovers repos with Jenkinsfile.test    (smoke / drift)
```

Same shape for each of nine GitHub orgs, plus a curated `spec-up/` folder containing three single-repo multibranch pipelines since Spec-Up is one repo inside `lockamy-studios` rather than its own org. Adding a new `Jenkinsfile.test` to any repo in any org makes a new pipeline auto-appear on the next scan — no manual job configuration. The whole thing is generated from a single Groovy `job-dsl` loop with a config list of orgs, so adding a tenth org is one line.

## The eight-round outage

The Jenkins reorg landed in production via the standard `sol-infrastructure` pipeline — and immediately broke the controller. Five hours and eight rebuild rounds later it was back up. Each round surfaced a different class of bug.

1. **okhttp plugin classloader** missing `okhttp3.Authenticator` — stale plugin JARs persisted in the JENKINS_HOME volume across image rebuilds because Jenkins's stock entrypoint only copies plugins from `/usr/share/jenkins/ref/` to the volume if the destination file is missing.
2. **`terraform apply` failed** with `vars map does not contain key org` — Terraform's `templatefile()` was greedily interpreting Groovy GString interpolations like `${org.folder}` as template variables.
3. **Same error** on `${var}` — in a comment I'd just written explaining the rule. The comment itself contained the literal syntax.
4. **Same error again** on `${entity.folder}` — in *another* comment that had been rewritten to explain the rename of the closure parameter.
5. **`name must not contain trailing slash: /`** — initially misdiagnosed as Groovy `org`-as-Java-package-prefix shadowing. The actual cause turned out to be Jenkins's Configuration-as-Code plugin: JCasC has its own `${...}` substitution layer (for secret references) that runs *before* Groovy ever sees the script. It was eating every `${entity.foo}` and `${variant.foo}` and replacing them with empty strings — so `"${entity.folder}/${variant.type}"` became `"" + "/" + ""` = `"/"`. The fix was a caret prefix to escape past the JCasC layer and reach Groovy.
6. **Dockerfile `chmod` exit-1** — the Jenkins base image ends with `USER jenkins`, so my `RUN chmod` was unprivileged.
7. **`exec: "/usr/local/bin/tini"` not found** — different Jenkins base images put tini in different places. Dropped the tini wrapper entirely; the refresh script `exec`s into the original entrypoint immediately so the original PID-1 semantics are preserved.
8. **`okhttp3.internal.tls.CertificateChainCleaner` not found** — a different stale plugin marker file in the volume. The refresh script I'd added in round 1 only overwrote same-named files; leftover `.jpi.pinned` markers from a previous build were confusing the classloader.

By the end I knew more about three-layer variable substitution chains than I expected to. **Terraform `templatefile()` → JCasC `SecretSourceResolver` → Groovy GString interpolation** — all three layers use the same `${...}` syntax, each one greedily consumes what it sees unless explicitly escaped past, and the right escape depends on which layer the variable belongs to. Documented the full rule in a banner at the top of the JCasC YAML template so the next operator hits it once and immediately knows why.

## What the experience pushed onto the followup list

Three tickets filed against Sol as a direct result of the outage:

- **A pre-commit lint** that scans every `*.tpl` passed to `templatefile()` for unescaped `${...}` patterns and cross-references them against the actual vars map. Three of the eight outage rounds would have failed lint instantly.
- **A Sol PR validator** pipeline that runs `terraform plan` plus `docker build --no-cache` plus a `docker run` boot-smoke for any service module touched by a PR. Would have caught at least five of the eight rounds at PR time instead of production. Filed with the full outage timeline as evidence; it's now exhibit A for why the validator is worth building.
- **A `make render` target** per module that locally emits the rendered `templatefile()` output for visual inspection before push. Shortens the "did I escape it right" feedback loop from *push + apply + reboot Jenkins* to *save + `make render` + diff*.

## Three days, one product live

Net result of the weekend:

- `spec-up.com`, `app.spec-up.com`, `api.spec-up.com` live with end-to-end TLS
- Origin security group locked to Cloudflare's edge ranges, no direct-to-IP path remaining
- A seventeen-assertion smoke suite running on every deploy and nightly
- A login gate on the prototype pending the real Okta migration
- The Flutter app aligned with the marketing brand palette and the collaborator-confirmed information architecture
- The Jenkins controller reorganised with auto-discovered CI/CD/test pipelines per org
- Three followup tickets filed to prevent the next eight-round outage from happening at all

A long weekend. Worth it.
