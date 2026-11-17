---
layout: post
title: "BenixOS Is Running on Four of My Machines. It Isn't Allowed to Do Anything Yet."
date: 2026-11-17
categories: [slashbuilder, ai]
tags: [slashbuilder, benixos, venue, kits, hearth, homelab, security, ai-assisted-development, series]
excerpt: "A progress update on BenixOS, the distributed OS this series has been building toward: a cluster went live across four machines in my lab, four rounds of review found real problems, and a public book now describes what exists and what doesn't."
image: /images/benixos-running-on-four-machines.png
syndicate: false
author: Douglas Lockamy
ai_assisted: true
---

This series has been about parts. [Part 2](/posts/2026/10/26/what-a-kit-is/)
was the Kits, [Part 3](/posts/2026/11/02/hearth-the-plan-9-half/) was the
protocol that connects them. This post is about the thing they're parts *of*,
and it's the first one where I get to say what is actually running.

That thing is called **BenixOS**. It's a distributed operating system: one
namespace, one identity and one way of deciding where work runs, across every
machine a person or household owns. It's built from Kits, its machines speak
Hearth to each other, and a machine joins by meeting a small contract. It is
not a Linux distribution, and it doesn't replace Docker. If you read
[Part 1](/posts/2026/10/19/where-an-os-idea-started/), this is the large OS
project I kept pushing off.

On 11 November I decided to stop splitting my time between BenixOS and
Quickring, the consumer product built on Hearth, and to do only BenixOS for now.
The goal I set is deliberately plain: **you bring a stock Linux machine and
Docker, you run `docker compose up`, and you have a BenixOS node.** There is no
image to flash.

## Five days

| When | What happened |
|---|---|
| 11 Nov | The decision above: BenixOS only, and it has to start from compose on stock Linux. |
| 14 Nov | I asked for one thing by the end of the weekend: every machine in my lab runs it, and they share resources as one cluster. |
| 14 to 16 Nov | AI agents built it in parallel tracks. Fresh AI reviewers attacked it four times. |
| 15 to 16 Nov | A public book describing the design went live. |
| 16 Nov | The cluster went live on four machines, and version 0.1.0 was tagged. |

## Where the pieces stand

| Piece | What it does | State |
|---|---|---|
| Hearth | How machines talk to each other | Public spec; a subset is implemented |
| Kits | Reusable building blocks, one domain each | Early; no Kit has a stable API yet |
| Venue | The registry and planner that decides where work can run | Alpha |
| The executor | Runs containers on one machine, only if a local policy allows it | Works; this week's focus |
| The book | A public description of all of it | Live |

The cluster is the Venue row, growing from one machine to several.

## The cluster

One machine holds the registry: a list of the machines in the cluster and what
each can offer. Every machine, including that one, runs an executor. The
executor is the only process allowed to talk to Docker on its machine, and it
will only start a container if its local policy says so. The default policy
says no to everything.

The worker machines connect outward to the registry through a tunnel where each
end checks the other's certificate, so the registry has one inbound port and
the workers have none.

I have more machines than that. The rest include Windows and macOS machines, a
hypervisor host, the CI controller and an Android device, and none of them can
run an executor yet. "Every machine" turned out to mean every Linux box that
can safely carry one, which is four.

Here is what I checked on the real machines, not a simulation:

| Check | Result |
|---|---|
| The 133-check test suite, on the registry machine's own Docker | Passed |
| A workload requested at the registry, run on another machine through the tunnel | Ran, answered, and was removed on release |
| Five workloads asking for 1.5 CPUs each, across three machines | Spread 2, 2 and 1; a sixth was refused as not fitting |
| A node declaring 2 CPUs, given quarter-CPU workloads | Took eight; the ninth was refused |
| A call with no token, and a node's token trying to place work | Refused, both times |
| Cutting one node's tunnel | Registry marked it not ready in about a minute; its workload ran to the end of its lease, stopped just after, and did not come back when the tunnel did |

Under load, placing a workload took 50 to 95 milliseconds at the median. The
planner packs machines rather than spreading across them, and a per-user limit
of 20 live reservations stopped my ramp before the machines did.

My verdict from the load test: it's ready for a modest, stateless load. It is
not ready for real services. Nothing is allowed by policy, workloads get no
storage, and nothing renews a lease automatically yet.

## Why it isn't allowed to do anything

Between the build and going live, fresh AI reviewers went over the code four
times. Each started from the code, not the builders' notes, and wrote tests to
break it. Every round found something real:

- **Round 1** rejected a patch outright: a node's routine status report broke
  the lease renewal of whoever held the workload.
- **Round 2** found that a freshly enrolled node that had never reported in
  could still be handed work, and that a check for a revoked credential could be
  fooled by a planted line in a log.
- **Round 3** said the cluster was not safe yet for a machine hosting real
  services.
- **Round 4** reviewed the final fixes. Nothing gets past the tunnel without a
  certificate and a token, and its advice was to keep it running.

Round 4 added a condition I want to be plain about. The cluster is safe today
because every node's policy permits nothing. Once I allow a real workload, it
isn't safe as deployed.

The reason is a high-severity finding about my own lab. On three of the four
machines, the CI agents share the machine's Docker daemon with the executor, so
a CI job could read the node's credentials and act as that node. I have to fix
that before anything real runs: a separate daemon for the executor, or no CI
access to Docker on those machines.

## What went wrong

- **The builders hit usage limits twice.** The weekend lost about a day to the
  two stops.
- **A hung test ran away.** When I came back, one had been holding 18 GB of RAM
  and 61 CPU-hours on a build machine. Every test now runs under a timeout and
  a memory cap.
- **CI rejected the first three tries at 0.1.0.** Its lint checks found problems
  in shell scripts that had never been through them before.
- **CI can't build the images.** It needs to clone a private Kit repository, and
  my organization's setting disables the deploy keys that would allow it. The
  cluster runs images I built locally from the tagged release. Nothing is
  published to a registry, and the twelve Venue Kit patches it depends on sit on
  a branch that isn't merged anywhere.
- **My CI agents can't move onto the cluster.** They compete with it for the
  same machines, so I asked. Of 57 pipelines, 30 drive Docker and 11 build
  embedded Linux images with huge caches. The executor forbids Docker access,
  mounts and privileges by design. The rules did their job, and they mean the
  first real workload will be something simpler than my build system.

## The book

I also wrote it down. [The BenixOS Book](https://book.benixos.com/) is a public
description of the design and of what exists. Every chapter opens with a State
box saying what is built, partial, drafted or only planned, and where the book
and a repository disagree, the repository is right.

Its status page lists what isn't built: signed grants, workload storage, a
conformance suite for Hearth, and a stable API on any Kit. One correction is
pending. The status page and two chapters were written on 15 November and still
call the multi-node work simulated only. The fix is written and waiting on my
review.

## What's next

I want one real thing running on it that I use every day, because that is the
quickest way to find what's wrong. My candidate is a replacement for the notes
app I'm writing this in, built from BenixOS's own pieces. That's a plan, and
nothing exists yet.

Before any real workload is allowed, three things have to happen: the shared
Docker problem gets fixed, the policy needs real image digests, and the images
need to build in CI. Most of the cluster code is still private. The public parts
are the book and the
[Hearth spec](https://github.com/slash-builder/hearth), and either is a good
place to start poking holes.

Drafted with AI assistance.
