---
layout: post
title: "Hearth: The Plan 9 Half"
date: 2026-11-02
categories: [slashbuilder, ai]
tags: [slashbuilder, hearth, plan9, 9p, protocol, ai-assisted-development, series]
excerpt: "Part 3: Hearth, a small open protocol that borrows 9P's discipline and applies it to a household instead of a data center."
image: /images/hearth-the-plan-9-half.png
syndicate: true
social:
  linkedin: |-
    I'm not claiming a new idea. I'm claiming the old one still works.

    Part 3 of my series on the platform I'm building with AI is about Hearth, a small open protocol that borrows the discipline of Plan 9's 9P and applies it to a household instead of a data center.

    The post covers what Hearth takes from 9P, the two things it adds, and where it still falls short, including how much of the encryption is actually built. The spec is public, so you can check every claim against it.

    Drafted with AI assistance.
  bluesky: |-
    Plan 9's 9P showed that one small protocol could speak to everything, local or remote. Hearth borrows that discipline for a household: 24 message types in version 1, a goal of staying under 30, and every request answered exactly once.

    Part 3 of the series. Drafted with AI assistance.
  mastodon: |-
    Hearth: The Plan 9 Half (Part 3 of the series)

    Hearth is a small open protocol that borrows 9P's discipline and applies it to a household instead of a data center. 24 message types in version 1, every request answered exactly once, and files kept off the hub. What it takes from 9P, what it adds, and where it still falls short.

    Drafted with AI assistance.

    #Plan9 #9P #OpenProtocol #FOSS
author: Douglas Lockamy
ai_assisted: true
---

In [Part 1](/posts/2026/10/19/where-an-os-idea-started/) I said the idea came
from two places. BeOS gave me the Kit: a system made of parts with clear edges,
which [Part 2](/posts/2026/10/26/what-a-kit-is/) was about. This post is the
other half. Plan 9 gave me a way to think about machines talking to each other,
and the thing I built from it is called **Hearth**.

Unlike most of what I've written about this project so far, Hearth is
specific, because the specification is already public. You can read it, and
you can check what I say here against it:
[github.com/slash-builder/hearth](https://github.com/slash-builder/hearth).

## What it is

Hearth is an open protocol for distributed personal resources. The short
version in its own README is "9P-inspired — Plan 9's addressing model, reapplied
to a household instead of a data center. Capability-grants instead of accounts;
a thin wire contract instead of a platform."

It sells nothing. It's stewarded by SlashBuilder, the open-source side of the
studio, and a consumer product called Quickring is built on top of it. That
separation is deliberate: the protocol is meant to be implementable by someone
who has never heard of me.

## What I took from 9P

I did not copy 9P's encoding. Hearth uses protobuf, not 9P's hand-rolled binary
format. What I took is the discipline, and the spec says so in as many words:

- **A small, fixed set of message types.** In version 1 there are 24 envelope
  variants: nine request/response pairs, one error, and five server pushes. The
  goal is to stay under 30 for the life of the protocol. The number matters less
  than the habit. Every new message type has to earn its place, and the usual
  answer is that it should have been a new *step* of an existing interaction
  instead.
- **Every request gets exactly one answer.** A request carries a tag, and its
  answer carries the same tag.
- **Errors are first-class.** Any request can be answered with an error carrying
  its tag.
- **It's versioned from message one.** Version negotiation happens before any
  other traffic.

If you've read the 9P papers, none of that will surprise you. That's the point.
I'm not claiming a new idea. I'm claiming the old one still works.

Two things are Hearth's, not 9P's, and a 9P reader should hear it from me first.
9P is strictly request and response: the server only ever answers. Hearth adds
**server pushes** (a delivery, a presence change, a pairing result), and they
carry tag 0 so they can never be mistaken for an answer. Requests, answers and
pushes are the whole grammar. There is no fourth kind of message.

The second is the handle. Multi-step conversations, like pairing a new device,
use **a handle the server hands out** and carry it across the steps, rather than
inventing a new message type per step. That borrows the shape of 9P's `walk`,
but in real 9P the client picks the handle (the fid). In Hearth the server does.

## The two layers

The standard has two layers, defined in one specification, with encryption
details in a companion document. The **base layer** is the envelope, tag
correlation, the request/response/push grammar, errors and addressing. The
**fabric layer** is everything that's only true because the message crossed a
network: sessions, publish and subscribe, device pairing, presence, catching up
after being offline, and end-to-end encryption.

The reason for the split is a property I care about: a message should be the
same message whether it's going to another process on the same machine or to a
device across the country. Crossing the boundary changes the transport and
nothing else. What gets sent is never translated on the way.

## How it travels

The network leg is a WebSocket carrying one protobuf envelope per binary frame,
with a 1 MiB cap per message. Anything bigger, like a file, deliberately never
goes through the hub, the server every device connects to. The spec plans for
files to move peer-to-peer or as references into content-addressed storage, in
a later version. A hub that only relays small messages has much less to carry,
and much less to lose.

## Where it falls short

Part 1 said I'd be specific about what broke. These are the rough edges, and
you can check each one in the repository.

- **It still carries the old name.** As of late October 2026, the spec is titled
  "Quickring Wire Protocol," the schema package is `quickring.v1`, and the
  WebSocket subprotocol string says the same. A coordinated rename is tracked.
  The rename changes the identifiers that carry the version, so it is a
  breaking change, and it hasn't happened yet.
- **The documents lag the code in places.** The encryption design document was
  written before any of it was implemented, and it kept saying so for nearly
  three weeks after the first of it shipped. Its status note has since been
  corrected against running code, and it says plainly that the other sections
  have not been re-audited. Better a spec that admits that than one that looks
  finished.
- **Encryption is only partly built.** By the repository's own status notes,
  two levels of client-side encryption are implemented in the reference code:
  sealing a household's content key to each device on its roster, and
  encrypting message content under that shared key. Sealing arbitrary data to
  a single device, per-resource keys, and re-keying after a device is removed
  are still only written down. In the reference app, chat messages are
  encrypted this way and the app will not send without a key, but that key is
  provisioned by hand and kept in ordinary app preferences. Some things encryption will never hide: the hub always sees who
  published to which topic, when, and how much. The spec says that belongs in
  public copy, not a footnote, so it's here.
- **Some of it is still a design.** The spec lists what's deliberately not in
  version 1, including file transfer, federation between hubs and team topics.
  Each one has a later version number next to it.

## Why it belongs in this series

In Part 1 I called Hearth the protocol that ties the Kits together, and last
week I said the Kits need a way to talk to each other and to other machines.
Both are true from the Kits' side. From Hearth's side, the dependency only runs
one way: Hearth doesn't need the Kits. The Kit that carries messages between
processes on one machine speaks Hearth's envelope, so a message leaving the
machine is already in the shape the hub expects, and only the transport
changes. The Kit conforms to Hearth, not the other way round, and the protocol
is meant to work just as well for software that has never heard of a Kit.

At some point I want to come back to the AI side of this and look at what
building this way has actually cost, and what it's bought. Until then, the spec
is the best place to poke holes in any of the above.
