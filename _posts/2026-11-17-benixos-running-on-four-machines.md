---
layout: post
title: "BenixOS Is Running on Four of My Machines. It Isn't Allowed to Do Anything Yet."
date: 2026-11-17
categories: [slashbuilder, ai]
tags: [slashbuilder, benixos, venue, kits, hearth, homelab, security, ai-assisted-development, series]
excerpt: "I asked for a cluster by Monday and went out for a few hours. A progress update on BenixOS: four machines working together, four rounds of review that kept finding real problems, and a public book that says what exists and what doesn't."
image: /images/benixos-running-on-four-machines.png
syndicate: false
author: Douglas Lockamy
ai_assisted: true
---

The last two parts covered the pieces:
[the Kits](/posts/2026/10/26/what-a-kit-is/) and
[Hearth](/posts/2026/11/02/hearth-the-plan-9-half/), the protocol that connects
them. This one is about the thing those pieces are for, and it's the first time
I can say what is actually running.

## So what is BenixOS?

**BenixOS** is the large OS project I kept pushing off. It's a distributed
operating system: one way to name things, one identity and one way of deciding
where work runs, across every machine a person or household owns. It's built
from Kits, its machines talk to each other over Hearth, and a machine joins by
meeting a small contract.

It is not a new Linux distribution, and it doesn't replace Docker. The goal I
set is deliberately plain: **you bring a stock Linux machine and Docker, run
`docker compose up`, and you have a BenixOS node.** Nothing to flash.

I set that goal on 11 November, the day I decided to stop splitting my time
between BenixOS and Quickring, the consumer product built on Hearth. For now, I'm
doing only BenixOS.

## The five-day version

| When | What happened |
|---|---|
| 11 Nov | The decision: BenixOS only, and it has to start from compose on stock Linux. |
| 14 Nov | I asked for something slightly ridiculous: by the end of the weekend, every machine in my lab running it and sharing resources as one cluster. Then I went out for a few hours. |
| 14 to 16 Nov | AI agents built it in parallel tracks. Four times, a fresh AI reviewer tried to break it. |
| 15 to 16 Nov | A public book describing the design went live. |
| 16 Nov | The cluster went live on four machines, and version 0.1.0 was tagged. |

## How it fits together

| Piece | In plain words | State |
|---|---|---|
| Hearth | How the machines talk | Public spec; a subset is implemented |
| Kits | Reusable building blocks, one domain each | Early; no Kit has a stable API yet |
| Venue | The part that decides where a job can run | Alpha |
| The executor | The part that actually runs it, on one machine | Works; this week's focus |
| The book | A public description of all of it | Live |

The cluster is the Venue row, growing from one machine to four.

## What "a cluster" means here

Picture a shared address book of the machines in my lab and what each can spare.
That's the registry, and it lives on one machine.

Every machine, including that one, also runs an executor: a small program that is
the only thing allowed to touch Docker there. Think of it as a doorman with a
list. If a job isn't on the list, it doesn't get in. Right now the list is empty.

The workers dial out to the registry through a tunnel where each end checks the
other's certificate. The registry has one open door and the workers have none.

I have more machines than that, but the rest include Windows and macOS machines,
a hypervisor host, the CI controller and an Android device. None of them can run
an executor yet. "Every machine" turned out to mean every Linux box that can
safely carry one, which is four.

## Does it actually work?

Yes, on the real machines, not just a simulation:

| What I tried | What happened |
|---|---|
| The 133-check test suite, on the registry machine's own Docker | Passed |
| Asked the registry to run a job on a different machine | It ran there, answered, and was cleaned up on release |
| Five jobs asking for 1.5 CPUs each, across three machines | Spread 2, 2 and 1; a sixth was politely refused for not fitting |
| A machine declaring 2 CPUs, given quarter-CPU jobs | It took eight and refused the ninth |
| A request with no token, and a machine's own token trying to place work | Refused, both times |
| Cutting one machine's link to the registry | The address book marked it "not ready" in about a minute. Its job ran until its booking ran out, stopped just after, and did not spring back to life when the link returned |

That last one is the result I cared about most. A job that keeps running after
you've lost track of it is a worse failure than a job that stops.

Under load, placing a job took 50 to 95 milliseconds at the median. The planner
fills one machine before starting on the next, and a limit of 20 live bookings per
user stopped my ramp before the machines did.

My verdict from the load test: it's ready for a modest, stateless load, and it
isn't ready for real services. Policy allows nothing, jobs get no storage, and
nothing renews a booking automatically yet.

## Why it's on a short leash

Between the build and going live, fresh AI reviewers went over the code four
times. Each started from the code, not from the builders' notes, and wrote tests
to break it. Every round found something real:

- **Round 1** rejected a patch outright. A machine's routine status report broke
  the booking renewal of whoever held the job.
- **Round 2** found that a freshly enrolled machine that had never checked in
  could still be handed work. It also found that the check for a revoked
  credential could be fooled by a planted line in a log.
- **Round 3** said the cluster wasn't safe yet for a machine hosting real
  services.
- **Round 4** reviewed the final fixes. Nothing gets past the tunnel without a
  certificate and a token, and its advice was to keep it running.

Round 4 came with a condition I want to be plain about. The cluster is safe today
because every machine's policy allows nothing. Once I allow a real job, it isn't
safe as deployed.

The reason is a high-severity finding about my own lab. On three of the four
machines, the CI agents share the machine's Docker with the executor, so a CI job
could read the machine's credentials and pretend to be that machine. I have to
fix that before anything real runs, either with a separate Docker for the executor
or by keeping CI away from Docker on those machines.

## The part where things broke

Here's the honest list.

- **The builders hit usage limits twice.** Each time they sat idle until the limit
  reset, and the weekend lost about a day to the two stops.
- **A hung test ran away.** One had been holding 18 GB of RAM and 61 CPU-hours on
  a build machine. Every test now runs under a timeout and a memory cap.
- **CI rejected the first three tries at 0.1.0.** Its lint checks found problems
  in shell scripts that had never been through them before.
- **CI can't build the images.** It needs to clone a private Kit repository, and
  my organization's setting disables the deploy keys that would allow it. So the
  cluster runs images I built locally from the tagged release. Nothing is
  published to a registry, and the twelve Venue Kit patches it depends on sit on
  a branch that isn't merged anywhere.
- **My CI agents can't move onto the cluster.** They compete with it for the same
  machines, so I asked. Of 57 pipelines, 30 drive Docker and 11 build embedded
  Linux images with huge caches. The executor forbids Docker access, mounts and
  privileges by design. The rules did their job, and they mean the first real
  job will be something simpler than my build system.

## I wrote the manual early

[The BenixOS Book](https://book.benixos.com/) is a public description of the
design and of what exists. Every chapter opens with a State box saying what is
built, partial, drafted or only planned. Where the book and a repository
disagree, the repository is right.

Its status page lists what isn't built: signed grants, workload storage, a
conformance suite for Hearth, and a stable API on any Kit. One correction is
pending. The status page and two chapters were written on 15 November and still
call the multi-node work simulated only. The fix is written and waiting on my
review.

## What's next

I want one real thing running on it that I use every day, because that's the
quickest way to find what's wrong. My candidate is a replacement for the notes
app I'm writing this in, built from BenixOS's own pieces. That's a plan, and
nothing exists yet.

Before any real job is allowed, three things have to happen: the shared Docker
problem gets fixed, the policy needs real image digests, and the images need to
build in CI.

Most of the cluster code is still private. The public parts are the book and the
[Hearth spec](https://github.com/slash-builder/hearth), and either is a good
place to start poking holes.

Drafted with AI assistance.
