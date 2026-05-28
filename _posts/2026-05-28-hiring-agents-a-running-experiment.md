---
layout: post
title: "Hiring agents: a running experiment in staffing a one-person shop"
date: 2026-05-28
categories: [general]
tags: [ai-agents, devops, automation, workflow, experiment, lockamy-studios]
excerpt: "I've started treating my AI agents like employees — job titles, job descriptions, onboarding docs. It's deliberate language for a running experiment: can org-design discipline make agents more useful than prompts do? Here's the setup, and where it breaks."
author: Douglas Lockamy
ai_assisted: true
---

I've started referring to my agents as employees.

Not because I think they're people — they aren't — but because the language is
doing real work. The moment I started writing an agent the way I'd write a job
description instead of a prompt, the agents got more useful. This post is the
running log of that experiment: what "hiring" an agent actually looks like, what
it's unblocked, and where the framing falls apart.

Call it a running experiment, because that's what it is. I'm not selling a
methodology. I'm reporting from inside one.

## The problem: one person, too many hats

I run a solo operation across more surface area than one person should:
`dlockamy` (this site, the engineering work), Lockamy Studios (products, the
Digital Zen design system), and ClusterZer0 (the Bitchain binary-versioning
suite, SlashBuilder). Different audiences, different voices, different stacks.
The expensive part isn't any one task — it's the context switch. Every time I
sit down to write a release post or a landing page or a pipeline, I spend the
first twenty minutes reloading *which project's conventions apply* into my own
head, and then into whatever AI I'm working with.

I'd already half-solved this on the technical side. Every repo has a
`CONTEXT.md` — stack, decisions, open questions, current state — that gets
loaded at the start of a session so I'm not re-explaining the project every
time. The agent pattern generalizes from there. If a context file is the
onboarding doc, the next obvious move is to write the *role*.

## Hiring = writing the job description

An "employee," in this experiment, is a markdown file with a job description.

The newest hire is a publicist. The role definition reads exactly like one
you'd post to a job board: a mandate ("build reach, reputation, pipeline, and
revenue — technical credibility is the proof, not the goal"), a scope (which
brands it owns, and a hard line around the ones it doesn't touch), a voice
guide, operating principles, and an escalation rule — *show drafts, don't
auto-publish*. It has a defined toolset, the same way you'd scope what systems a
new hire gets access to on day one.

Writing it that way forced decisions I'd been skipping. "Make me some social
posts" produces mush. A job description forces you to answer: what is this
person *for*, what do they own, what do they explicitly not own, and what's the
one thing they should never do without checking with me first. Those are the
same questions that make a real hire successful. Turns out they make an agent
successful too — and for the same reason: ambiguity is where the work goes
wrong.

The meta part: this very post's brand guidelines — the dlockamy voice, the rule
that every post ends with a next step instead of a dead end — came out of that
publicist definition. I'm using the employee I wrote to help write the post
announcing that I wrote it. That's either elegant or a hall of mirrors. Running
experiment.

## What the framing changes

Three things shifted once I stopped writing prompts and started writing roles:

**Scope boundaries got explicit.** A prompt is open-ended by default; a job
description has edges. The publicist has a written hard line: an archived brand
it must never pull content from, design systems it must keep separate. Edges are
what keep an agent from confidently doing the wrong job well.

**Onboarding became a deliverable, not an afterthought.** Agents don't remember
yesterday. Every session is a new hire's first day. The `CONTEXT.md` /
role-definition split is just the difference between "here's who you are" and
"here's what's true about this project right now." Both have to be written down
because nothing carries over on its own.

**Escalation rules made delegation safe.** The single most valuable line in any
of these definitions is the one that says *stop and ask*. "Don't auto-publish."
"Flag anything legally sensitive." That's what lets me hand off real work
instead of babysitting it.

## Where it breaks

This is an experiment, so here's the honest column.

The employee metaphor leaks. Agents have no continuity, no judgment outside
their definition, and no stake in the outcome. Lean on the language too hard and
you start trusting a tool like a colleague, which is exactly the failure mode to
watch for. They also drift: a loosely scoped agent will wander, and a *broadly*
mandated one — I gave the publicist an aggressively commercial brief — needs
tighter guardrails, not fewer, or it optimizes for the wrong thing in a
convincing voice.

And there's a real cost to the org-chart approach: maintenance. Every role is a
file that goes stale. A "team" of agents is a small documentation surface you
now own. The experiment is only worth it if the leverage beats the upkeep — and
I don't have a clean answer on that yet. Ask me in a quarter.

## Why I'm running it anyway

Because the alternative for a one-person shop is doing every job yourself or
hiring people you can't yet afford. Treating agents as employees — with
descriptions, onboarding, scope, and escalation — is the cheapest org-design
experiment I've ever run, and the early read is that the *discipline* of writing
the role is half the value, independent of the agent. Writing down what a job is
for tends to clarify the job.

I'll keep logging this as it goes — what I hire next, what I have to fire, what
the maintenance actually costs.

---

If you want to see the pattern itself, the `CONTEXT.md` approach lives across my
repos on [GitHub](https://github.com/dlockamy), and I wrote up the repo-context
half of it [here](/blog/). If you're running your own version of this
experiment, I'd like to compare notes — [find me on
LinkedIn](https://www.linkedin.com/in/douglas-lockamy-49097b33/).
