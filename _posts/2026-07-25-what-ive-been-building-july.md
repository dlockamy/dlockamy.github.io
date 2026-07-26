---
layout: post
title: "What I've been building: July 2026"
date: 2026-07-25
categories: [general]
tags: [lockamy-studios, devops, infrastructure, quickring]
excerpt: "Quickring found its unifying thesis and shipped a working v0. Spec-Up's production home is about to change shape. And the home lab got a sibling network — because it turns out the naming convention was ready for it."
author: Douglas Lockamy
ai_assisted: true
---

The May post ended with "the infrastructure being live unblocks everything
else." Fair prediction. Here's what it unblocked.

## Quickring shipped a real v0

Quickring went from "the studio's flagship product" to "the studio's
unifying thesis" — the fabric underneath Household Computing, not just one
more product alongside the others. That reframe came with a real protocol
name (Hearth) and, more importantly, real code.

v0 is done: a Rust/axum hub with WebSocket session lifecycle, Redis pub/sub
fanout built cross-instance-ready from day one, a Dart SDK, and a debug pane
that proves two devices on one account can actually exchange a message
through the hub. It's informally live in prod right now, co-tenanted on the
same box as Spec-Up. Formalizing that co-tenancy — real infra, not a shared
EC2 instance two products happen to be squatting on — is the next section.

The marketing site (`quickring.me`) shipped too — static, Digital Zen, the
studio's actual front door now.

## Spec-Up's production story is about to change shape

Spec-Up going to production in one weekend (the [May
post](/posts/2026/05/17/the-weekend-spec-up-went-to-production/)) got it
live. It didn't get it *scalable* — one `t3.small`, one AZ, no load
balancer, deploys that drop in-flight requests. That was fine for a single
product. It stopped being fine the moment Quickring's hub needed to
co-tenant the same box for real.

The migration plan moving both onto a shared ECS cluster is written and
reviewed — and, this is the part worth saying out loud, was rescued from
Claude Code's ephemeral scratch directory after living there, uncommitted,
for weeks, cited by name in two other projects' context as *the*
authoritative plan for infrastructure that hadn't shipped yet. That near-miss
is exactly what pushed me to fix how an agent's own notes get kept — the full
story is in the [next section](#the-agents-memory-got-a-real-home). Nothing's
applied yet. That's tomorrow's problem, on purpose — infrastructure changes
this size don't get rushed just because the plan is finally safe.

## The home lab got a sibling

Sol — the private, VPN-only home network from May — stayed exactly what it
was: internal, boring on purpose, never touching production traffic. But
"boring on purpose" is precisely why the shared PROD platform couldn't live
there, or inside either product's own repo. It needed its own home.

Enter Sirius. Same fractal naming logic as Sol (a star, not a name squeezed
under an existing one), same Terraform module conventions, deliberately the
opposite temperament — Sol is invisible when healthy, Sirius is the
brightest star in the sky on purpose, because that's what a customer-facing
platform is supposed to be. Splitting the shared ECS infrastructure out of
a product repo and into its own dedicated platform repo caught a real
mistake mid-migration: an early pass would have relocated a VPC that's
*already live*, holding today's real EC2 instance — which would have made
one repo's next apply try to destroy it while the other tried to recreate
it. Caught before it shipped, not after. Sirius gets a fresh, independent
network instead.

## Auth for the home lab, without waiting on a VPN

Sol's own services — Nexus, Jenkins, Grafana — have always had their own
logins, but nothing gated *reaching* those login pages. Tailscale has been
"planned" since May and is still planned. Rather than block on it, the
perimeter got a proper gate: oauth2-proxy in front of the reverse proxy,
Google Workspace as the identity provider.

The interesting part was the exclusion list, not the gate itself. Cargo,
Dart, Maven, and Docker CLI clients hit Nexus during every CI build — none
of them can complete an OAuth browser redirect, so gating that vhost outright
would have quietly broken every pipeline. Same problem, smaller scope, for
GitHub's webhook POSTs to Jenkins. The fix is one `location` block per
exception, placed so nginx's longest-prefix match picks it over the general
gated route — machine traffic keeps working, everything a human looks at
gets a real login.

## Jenkins can talk to an AI agent directly now

Small addition, worth mentioning because of the timing: Jenkins picked up
the MCP Server plugin, so an AI client can query build state and job status
directly instead of me relaying it. It shipped in the same batch as the auth
gate above, which meant catching the same class of problem twice in one
sitting — an MCP client authenticates with an API token, not a browser
session, so it needed the identical exclusion treatment as the webhook path.
Consistent failure modes are at least easy to spot the second time.

## The agent's memory got a real home

Separate post, but it belongs in this list: the AI agents I've been running
this whole stack with finally have persistent, cross-session memory instead
of starting from zero every conversation. [Wrote that one up
properly](/posts/2026/07/25/obsidian-vault-as-agent-memory/) — the short
version is a real Obsidian vault, git submodules an agent can actually read,
and the incident above about the migration plan is exactly what made "just
remember it" stop being good enough.

---

Foundation work in May, shape-of-the-system work in July. The next stretch
is applying what's designed rather than designing what's next — Sirius goes
live, the auth gate goes live, and Spec-Up + Quickring's hub actually land
on the platform built for them. I'll report back once "planned" turns into
"running."
