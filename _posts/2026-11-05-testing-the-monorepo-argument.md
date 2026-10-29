---
layout: post
title: "Testing the Monorepo Argument"
# Alternate titles (3 to 8 words, no comma, no "and"): "Does a Monorepo Break at Scale"; "I Tried to Break a Monorepo"; "Monorepo Versus Many Repos, Measured".
date: 2026-11-05
categories: [devops, ai]
tags: [monorepo, multi-repo, ci-cd, jenkins, experiments, ai-assisted-development]
excerpt: "I bet that a monorepo turns into an anti-pattern past a certain size. So I built the same system both ways, let AI developers work in each, and measured the process. My bet was half right, and the half that was wrong is the interesting part."
author: Douglas Lockamy
ai_assisted: true
---

I've held an opinion about monorepos for years: they're great until they get big,
and then they're an anti-pattern. Five people running twelve services? One repo,
obviously. A huge company with a thousand repos and a dedicated devops team?
Don't do it. That's a bet, not a fact, and most of what's written about it is a
bet too. The best review of the literature I could find (a
[2018 multivocal review](https://arxiv.org/abs/1810.09477)) counted 21
blog-type sources and 2 academic ones, and concluded there's no consensus. The
best survey is [Google's](https://research.google/pubs/advantages-and-disadvantages-of-a-monolithic-codebase/),
and it's from one company with tooling most of us don't have.

So I decided to test it. This post is what I did, what I measured, and where my
bet turned out to be wrong.

## What I wanted to know, and what I left out

I wanted the process, not the politics. How long does a change take to go
live? How many pull requests does it need? How big are they? How many builds
does it start? What happens when two people work at once? What breaks, and who
finds out?

I left out the cost of getting to a monorepo: migration, retooling, the devops
team it takes. Those are real, but they're a different question. This one is
only about how the work flows once you're there, compared at the same level of
tooling.

I wrote down the questions, my thresholds and my prediction before I ran the
big experiments. The AI running them wrote down the opposite prediction: that
the layout alone wouldn't turn out to be the cause. That turned out to matter.

## How I tested it

I took a small public demo, [a micro-frontend system](https://github.com/dlockamy/homelab-mfe-monorepo)
with a shell, a billing component and a shared config library, and built it
two ways. One repository, or five: each app its own repo with its own CI and
CD, the shared library published to a private package registry, and a second
library that lives in its own repo in both setups, used only by billing. Same
Jenkins pipelines, same real deploys to a local S3, same code. I checked that
the deployed result was byte-for-byte identical in both.

Then I let AI developers work in them. Each run was a fresh Claude agent given
a ticket and one command that stood in for GitHub and Jira: clone, branch, open
a PR, wait for CI, merge, wait for the deploy. Every action was timestamped. A
ticket only counted as done if a script loaded the live deployed bundle and
checked what it actually rendered. Before every round I restored the whole
environment from one snapshot so runs couldn't affect each other.

The tickets came in two shapes: a well-structured one, a feature broken into
per-repo tasks, and a vague one, a product request that leaves the developer
to figure out where the work belongs. That was me testing a different idea of
mine: whether a good ticket matters more in a multi-repo world.

## What the numbers say

**A change inside one component is a wash.** Same text change in both: 64
seconds versus 70, one PR each, four builds each.

**A change that crosses a boundary is where the monorepo wins.** Add a field to
the shared config and use it: the monorepo takes one PR. The multi-repo takes
two that have to land in order, because the library has to be published before
the app can adopt it. Over four such tickets the multi-repo needed about 1.2 to
1.6 times as long and twice the builds. Its diffs were about 3.5 times as many
lines (16 against 4 to 6 per ticket), plus lockfile changes the monorepo didn't
need at all. On this tiny system that's seconds, not hours.
The pull request and build counts are the part that doesn't depend on how fast
my laptop is.

**And then it disappears, as I'd guessed.** When the shared library lives in its
own repository in both setups, the monorepo needs two PRs and eight builds too.
The advantage belongs to code that lives in the repo, not to the monorepo as
such.

**Repository size didn't hurt.** I generated repos up to 200,000 files and
50,000 commits. A fresh full clone got slow, 15 seconds against 1.4 for a tenth
of it. But an incremental fetch into an existing workspace, which is what CI
normally does, was 0.26 seconds, and a shallow, sparse clone was under one. Git
was not the bottleneck in anything I tried.

**What hurt was the pipeline, not the size.** The demo repo's CI builds every
app on every change. I grew it to 250 projects and compared. Build everything:
24 to 28 times slower than a single-repo pipeline (and when I let it run all
250 builds at once, it ran the CI machine out of memory and killed Jenkins).
Build only what the change touches: 1.1 times, at every size I tried, a flat
8 to 16 percent from the step that works out what changed.

## The idea I'm taking away: global gates

Everything that went wrong with the monorepo had one shape. I've started
calling it a **global gate**: a condition that every change must pass,
checked over the whole repo instead of over what the change touches.

Build-everything CI is one. "Trunk must be green before anyone merges" is
another. A single serialized merge queue is a third. When I broke trunk on
purpose, an unrelated team's pull request, a harmless change to a different
app, went red three times out of three under the repo's normal CI, and green
three out of three once the CI only built what was affected. The multi-repo
setup never had the problem, because the repo boundary does the scoping for
free. A monorepo has to do it on purpose.

I also built a model of many developers merging to one trunk. It said the same
thing: the crossover where the monorepo gets worse appears when the gate is
global, and mostly goes away when it's scoped. I want to be clear that's a
model, checked against my measurements only at one developer, and one
assumption (how often a merge breaks trunk) did most of the work.

## What hurt the multi-repo setup

It isn't free either, and it's a different kind of cost. A library change
reaching 100 consumers took one PR and four builds in the monorepo, and 101 PRs
and 404 builds in the multi-repo, even with the consumer PRs opened by a bot.

The quieter costs were worse. Break a library on purpose without knowing who
uses it: the monorepo flagged it in 10 seconds, before merge. The multi-repo's
library CI passed, published it, and nothing happened until a consumer tried to
adopt it, which in real life could be weeks.

And one test showed the failure I'd worried about. I added a second consumer
the ticket didn't mention and asked for a rename. The monorepo developer found
it with a search. The multi-repo developer didn't, and the live site was left
quietly one major version behind. When the ticket said "every app that uses
it," both found it.

## Is one big PR harder to review?

Fewer PRs only helps if the PRs aren't harder to read, so I tested that. I gave
34 fresh AI reviewers the same rename, once as one 101-file monorepo PR and once
as a library PR plus 100 app PRs. Some had no bug, some had a typo in one app,
and some left one app out.

Nobody raised a false alarm, and every typo was caught in both setups. The
one big PR took half the effort: 6 tool calls and 24 seconds against 11 and 49
for the 101 small PRs. My guess that a reviewer seeing only one app's PR would
miss the typo was wrong; they caught it every time.

The multi-repo weakness showed up somewhere else. With a single app, the
reviewer saw a correct library PR and no app PR, and approved it twice. A
missing PR leaves nothing to look at. With 10 or 100 apps the reviewers caught
the gap, but only because I had handed them the list of apps.

## Two developers

Two developers on independent tickets got about 1.7 to 1.8 times the
throughput, not 2, because each spent about half their time waiting on CI and
CD. Splitting one strictly sequential ticket between two gave no reliable gain in
either setup: three of the four runs were slower, and the fourth was 8 seconds
faster, which is within the noise. Where their changes overlapped, the monorepo produced merge conflicts
and the multi-repo produced more messages. Writing the handoff down mattered:
in one run a developer assumed a minor release and the other had made it a
major; the message caught it before it shipped.

## Where I was wrong

My bet was that a monorepo becomes an anti-pattern past some size. Within the
ranges I tested, that's not what happened. Size didn't hurt it. Unscoped
pipelines did. So the version of my bet that survives is narrower: *a monorepo
with global gates doesn't scale.* The multi-repo setup, for its part, has no
scale limit I could find, only a bill that grows with how often changes cross
a boundary: more PRs, more builds, silent breaks, forgotten consumers.

Which means the question for a given team isn't "how big are we." It's "how often do
our changes cross a boundary, and are our pipelines scoped to what changes?"
That's an observation about this system, not a rule about yours.

## What this doesn't tell you

- It's a toy system. Builds took seconds. Absolute numbers don't carry over;
  the PR and build counts and the shapes of the curves might.
- The developers were AI agents. No code review queue, no ownership
  arguments, no onboarding. Most agent results are a single run per cell.
- Reviewers were AI agents too, on a mechanical change with one planted bug.
  They script their checks, which a person reading 100 diffs probably won't.
  I don't know how a human team would do.
- I didn't test access control, the one structural thing multi-repo does better,
  or whether a monorepo erodes module boundaries.
- I couldn't reproduce the load of scanning a thousand repositories.
- Past 200,000 files, 250 projects, 100 consumers, I'm extrapolating.

## What went wrong in the test itself

A few things, because I'd rather you hear them from me. My first two setups were
unfair and I threw the results out. The Mac went to sleep in the middle of a
round and corrupted two runs, which I reran. A metric I was using, executor
time, turned out to measure queue waiting under load, so I dropped it. And I had to
correct my own model twice after reading its output: once for an absurd result,
and once for charging the monorepo for conflicts that the other side didn't
have to pay. The corrections are in the write-up.

I'll publish the full write-up and the scripts if there's interest. Next I want
to try a bigger fan-out, add human reviewers, and test whether a monorepo
really does let developers reach into each other's internals.
