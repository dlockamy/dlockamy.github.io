---
layout: post
title: "BenixOS Is Running on Four of My Machines. It Isn't Allowed to Do Anything Yet."
date: 2026-11-17
categories: [slashbuilder, ai]
tags: [slashbuilder, benixos, venue, kits, hearth, homelab, security, ai-assisted-development, series]
excerpt: "I asked four ordinary machines in my lab to act like one computer. Each step showed a piece of what BenixOS is, how far it has come, and where it's going, including the parts that broke."
image: /images/benixos-running-on-four-machines.png
syndicate: false
author: Douglas Lockamy
ai_assisted: true
---

The last two parts covered the pieces:
[the Kits](/posts/2026/10/26/what-a-kit-is/) and
[Hearth](/posts/2026/11/02/hearth-the-plan-9-half/), the protocol that connects
them. This one is about what they're for.

The easiest way to explain it is to show you what I did this week. I took four
ordinary Linux machines in my lab and asked them to act like one computer. Every
step showed a piece of what **BenixOS** is, how far along it is, and where I want
it to go.

First, the short definition. BenixOS is a distributed operating system for the
machines a person or household owns: one way to know what you have, one way to
decide where work runs, and one set of rules about what's allowed. It's built from
Kits, and its machines talk over Hearth. It's the large OS project I kept pushing
off.

It is not a new Linux distribution, and it doesn't replace Docker. The first goal
is simple: **you bring a stock Linux machine and Docker, run `docker
compose up`, and you have a BenixOS node.** Nothing to flash.

## Step one: a shared address book

First, the machines needed to know about each other. One machine holds a registry,
a shared address book of the machines in the cluster and what each can spare.
This is Venue, the part of BenixOS that decides where work can run.

The other machines dial out to it through a tunnel where each end checks the
other's certificate, so the registry has one open door and the workers have none.
The 133-check test suite passed on the registry machine's own Docker.

I have more machines than four, but the rest include Windows and macOS machines,
a hypervisor host, the CI controller and an Android device. None of them can run
a node yet. "Every machine" turned out to mean every Linux box that can safely
carry one.

Closing that gap is a long-term goal. BenixOS is meant to run on any host that meets a small
contract, not on one blessed kind of machine. Ubuntu is what runs today. A light
native host of my own boots headless, and macOS, Windows and phones are designs.

## Step two: ask where a job can run

With the address book up, I started handing it jobs. I'd ask for a place to run
something, and it would pick a machine.

| What I tried | What happened |
|---|---|
| Asked it to run a job on a different machine | It ran there, answered, and was cleaned up on release |
| Five jobs asking for 1.5 CPUs each, across three machines | Spread 2, 2 and 1; a sixth was refused for not fitting |
| A machine declaring 2 CPUs, given quarter-CPU jobs | It took eight and refused the ninth |

Under load, placing a job took 50 to 95 milliseconds at the median. The planner
fills one machine before starting on the next, and a limit of 20 live bookings per
user stopped my ramp before the machines did.

My verdict: it's ready for a modest, stateless load, and it isn't ready for real
services. Jobs get no storage yet. A booking runs out unless something renews it,
and nothing renews one automatically.

## Step three: let each machine say no

Deciding where a job can run is not the same as deciding that it may. BenixOS
keeps those separate on purpose. The registry decides where, and the machine
decides whether.

Every machine runs an executor: a small program that is the only thing allowed to
touch Docker there. Think of it as a doorman with a list. If a job isn't on the
list, it doesn't get in. Right now the list is empty, which is why the title says
what it says.

I checked the doorman. A request with no token was refused. A machine's own token
couldn't place work, either. The design goal is that a compromised registry can
ask for bad work but can't make a machine do it.

Today, "the machine decides" is a local list that allows nothing. The long-term
version is rules signed by the owner and checked by the machine on its own,
without asking anyone. That part is designed, not built.

## Step four: cut the cord

A household's computers shouldn't stop working because one link went down. So I
cut one machine's link to the registry.

About a minute later, the address book marked it "not ready". Its job ran until
its booking ran out, stopped just after, and did not spring back to life when the
link returned. That last part was the result I cared about most. A job that keeps
running after you've lost track of it is a worse failure than a job that stops.

That matches the design: if the registry disappears, running work finishes its
booking and nothing new starts. A local hub, so a home works without the
internet, is planned but not built.

## Step five: have it attacked

AI agents built this over a weekend, working in parallel tracks, so I didn't take
the result on faith. Before it went live, fresh AI reviewers went over the code
four times. Each started from the code, not from the builders' notes, and wrote
tests to break it. Every round found a problem:

- **Round 1** rejected a patch outright. A machine's routine status report broke
  the booking renewal of whoever held the job.
- **Round 2** found that a freshly enrolled machine that had never checked in
  could still be handed work. It also found that the check for a revoked
  credential could be fooled by a planted line in a log.
- **Round 3** said the cluster wasn't safe yet for a machine hosting real
  services.
- **Round 4** reviewed the final fixes. Nothing gets past the tunnel without a
  certificate and a token, and its advice was to keep it running.

Round 4 came with a condition. The cluster is safe today
because every machine's policy allows nothing. Once I allow a real job, it isn't
safe as deployed.

The reason is a high-severity finding about my own lab. On three of the four
machines, the CI agents share the machine's Docker with the executor, so a CI job
could read the machine's credentials and pretend to be that machine. BenixOS's
design says a machine's secrets should be out of reach of everything else running
on it. My lab didn't meet that. I have to fix it before anything real runs, either
with a separate Docker for the executor or by keeping CI away from Docker on those
machines.

## Where this is going

Each step above maps to a long-term goal. Here they are next to where things
stand today:

| The goal | Today |
|---|---|
| One view of every machine you own | One cluster of four Linux machines |
| Any machine can join, not just Linux servers | Ubuntu only; a native light host boots headless, and macOS, Windows and phones are designs |
| Each machine enforces the owner's rules itself, offline | A default-deny list; owner-signed rules are a design |
| Works without the internet | Running work survives losing the registry; a local household hub is planned |
| Things that keep state, like files and databases | Stateless only; storage will be a resource the owner grants |
| Other people can build on it | An app Kit exists in alpha; how an app is packaged and shared is a draft |

## The book, and what's next

I wrote the manual early. [The BenixOS Book](https://book.benixos.com/) is a
public description of the design and of what exists. Every chapter opens with a
State box saying what is built, partial, drafted or only planned, and where the
book and a repository disagree, the repository is right.

One correction is pending: the status page and two chapters, written on 15
November, still call the multi-node work simulated only. The fix is written and
waiting on my review.

Next, I want one real thing running on it that I use every day, because that's the
quickest way to find what's wrong. My candidate is a replacement for the notes app
I'm writing this in, built from BenixOS's own pieces. That's a plan, and nothing
exists yet. Before any real job is allowed, the shared Docker problem gets fixed
and the policy needs real image digests.

Most of the cluster code is still private. The public parts are the book and the
[Hearth spec](https://github.com/slash-builder/hearth), and either is a good place
to start poking holes.

Drafted with AI assistance.
