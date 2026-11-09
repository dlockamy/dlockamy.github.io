---
layout: post
title: "Is It the Repo or the Ticket?"
# Alternate titles (3 to 8 words, no comma, no "and"): "When the Ticket Is the Scope"; "Testing the Ticket Instead of the Repo".
date: 2026-11-09
categories: [devops, ai]
tags: [tickets, code-review, monorepo, multi-repo, experiments, ai-assisted-development]
excerpt: "When a ticket listed two of the three apps a change affected, AI developers left the third undone in 14 of 15 runs across separate repositories. One added line fixed it."
image: /images/repo-or-ticket.png
author: Douglas Lockamy
ai_assisted: true
syndicate: true
social:
  linkedin: |-
    In my previous study I spotted evidence that ticket structure might have as much or more to do with developer productivity than repo structure, so I did a second round of tests.

    I gave AI agents a ticket that listed two of the three apps a change would touch. They did the two on the list and left the third undone, 14 times out of 15. With no list at all, or a list that named all three, they found every app: 5 out of 5, both times.

    So the detail only helped when it was complete. The agents trusted the list and never went looking for anything that wasn't on it. Put everything in one repo and it never happened.

    It's a toy setup: three small apps sharing one library, five runs per kind of ticket. And the developers were AI, not people, so I can't say what a person would do. If you've seen people do this with a ticket checklist, I'd like to hear about it.

    Drafted with AI assistance.
  bluesky: |-
    In my last study I saw hints that ticket structure might matter as much as repo structure, so I tested again. AI agents given a ticket listing 2 of 3 apps left the third undone 14 times in 15. No list, or a full one: every app found, 5 of 5. Toy setup, AI not people. Drafted with AI assistance.
  mastodon: |-
    In my previous study I spotted evidence that ticket structure might matter as much as repo structure, so I ran a second round.

    I gave AI agents a ticket that listed two of the three apps a change would touch. They did the two on the list and left the third undone, 14 times out of 15. With no list, or a complete one, they found every app: 5 out of 5. In one repo it never happened.

    Toy setup, AI agents not people. Drafted with AI assistance.

    #DevOps #CodeReview
---

In [the monorepo post](/posts/2026/11/05/testing-the-monorepo-argument/), one
test went the way I'd feared. The ticket left out one of the apps that use a
shared library. With separate repositories, the developer never found that app,
so it never got updated. I couldn't tell how much of that was the repository
layout and how much was the ticket.

That wasn't in the plan, but I couldn't leave it alone. So I started a new
study, this one about the ticket. In separate repositories, the ticket decided
whether the change got finished. When it listed two of the three apps a change
affected, the third was left undone in 14 of 15 runs. An open-ended ticket with
no list never missed: 0 of 5.

**TL;DR:** If you stop here, take these three things.

- **Tell the developer the list may be incomplete.** If your tickets have one
  sub-task per repository, add a line like "The sub-tasks below cover the apps
  we know about. Others may also be affected." It took misses from 4 of 5 to 0
  of 5, and from 4 of 4 to 0 of 4 on a smaller model.
- **Give reviewers the repositories, not just the diff.** With only the ticket
  and the diff, reviewers caught 0 of 30 incomplete changes. With read access to
  the repositories, they caught 27.
- **Name the thing that matters.** A pasted chat thread that never stated the
  field name failed 10 of 10 runs. Stating the name in one line fixed it.

In the main test the monorepo never left an app out (0 of 163 runs). The caveat
is that the developers were AI agents on a toy system, with five runs per ticket
type, so read the smaller differences as leads. People are untested.

## How I ran it

It's the same toy system as before, with one more app: a shell and two
sub-route apps (billing and reports), all calling one shared contract library.
It comes in two versions, one repository and separate repositories. Each has CI
and CD, a package registry and real deploys, all on one machine.

The main change was a policy. The library's `validateApp` function now rejects
any app that doesn't pass an `owner`, so every app has to pass its owning team.
To find the affected apps, you ask "who calls this function?" A ticket can
answer that for you, rightly or wrongly.

After every run, a script loaded each live app and checked how it behaved. The
developer's own report never counted.

I designed the study with AI tools. They built the test harness, ran it
unattended and drafted the report. The developers and reviewers were AI agents
too. Claude Sonnet 5.5 (`claude-sonnet-5-5`) did most of the developer runs and
all of the reviews, and Claude Haiku 5.5 (`claude-haiku-5-5`) was a smaller
second model. Across nine phases that came to 396 single-developer runs, 60
two-developer runs and 300 reviews.

**Scope:** whether a change got finished, and what it took, on a toy system
with AI agents. No people and no real tickets.

## The partial list was the problem

Runs that left an app not updated and live, for the policy change:

| Ticket | Monorepo | Separate repos |
|---|---|---|
| Open-ended, no list | 0 of 5 | 0 of 5 |
| One sub-task per repo, all three apps listed | 0 of 5 | 0 of 5 |
| One sub-task per repo, one app missing (three versions) | 0 of 15 | 14 of 15 |

The three partial lists were plain, padded with an unrelated library, or
backed by acceptance checks on each listed repository. The checks didn't help;
they only covered what was named.

A complete list was as safe as no list. Structure wasn't the problem; a list
with a hole in it was.

In the main test, the monorepo never left an app out: 0 of 163 runs, whatever
the ticket said.


![Bar chart: runs left unfinished, out of 5, by ticket and layout, for a rename and a policy change. Every monorepo bar is 0. With separate repositories, the policy change shows 4 of 5 for the partial list, 5 of 5 for the padded list and 5 of 5 for the list with checks; the rename shows 2 of 5 for the list with checks. Every other bar is 0.](/images/repo-or-ticket-misses.png)

## Why: the agents did what the ticket said

In the first four phases, 33 changes in separate repositories were incomplete.
Clone events split them:

| What happened to the missing app | Changes |
|---|---|
| Cloned its repository, left it unchanged, named it in the closing summary | 12 |
| Never cloned it | 21 |

The 12 didn't get lost. Each summary notes that the missing app also calls
`validateApp`, then leaves it, citing the ticket's scope or its pin to the old
version. One, verbatim:

> "Reports also calls validateApp but is out of scope; it stays on ^1.0.0 and
> will need an owner ('insights') before it upgrades."

Two caveats. The harness kept clone events and closing summaries, not
transcripts, so "never cloned" is what the event log shows. And an AI tool did the first read of
the 12 summaries; I've read them since.


![Bar chart: for each ticket, runs that cloned the missing app's repository against runs that finished the change. Open-ended tickets, the complete list and the fixes did both in every run. Partial lists often cloned it and still did not finish; on the smaller model they never cloned it. A bottom bar splits the 33 incomplete changes into 12 that cloned it and 21 that never did.](/images/repo-or-ticket-cloned.png)

## One line fixed it

The simplest fix worked as well as any. I added one line to the partial-list
ticket:

> "The sub-tasks below cover the apps we know about. Others may also be
> affected."

Runs that left an app undone, separate repositories:

| Model | Partial list | With that line added |
|---|---|---|
| Main model (5 runs each) | 4 of 5 | 0 of 5 |
| Smaller model (4 runs each) | 4 of 4 | 0 of 4 |

"Find every app that uses `validateApp` and add a sub-task for each" worked as
well, on both models. With five runs, a 4-to-0 split is a lead, not proof.

Letting the developer ask the ticket writer questions didn't help. None of the
10 runs that could ask did.

If your tickets carry one sub-task per repository, saying the list may be
incomplete is the simplest change I found.

## Can a reviewer catch it?

I gave 60 saved changes from separate repositories, 30 of them incomplete, to
reviewer agents, each with different material:

| Reviewer was given | Incomplete changes caught (of 30) |
|---|---|
| Ticket and diff | 0 |
| Ticket and diff, plus read access to the repositories | 27 |
| Ticket and diff, plus the developer's summary | 11 |

A diff can't show what isn't in it. With separate repositories, a reviewer
often sees one repository's pull request at a time, which is roughly the first
row.

The summary row is the odd one. In 24 of the 30 incomplete cases, the
developer's summary named the missing app. Reviewers who read one approved 12
of those 24 anyway.

## Messy tickets broke it a different way

I also roughed up the open-ended ticket, the one that had never missed. Three
messy versions failed 11 of 30 runs.

| Messy ticket (both layouts) | Failed |
|---|---|
| One terse paragraph, no acceptance criteria | 1 of 10 |
| A pasted chat thread that never stated the field name | 10 of 10 |
| Clean text, with an old name for the library | 0 of 10 |

Every chat-thread run changed the library to check the wrong field. With the
name stated in one line, the same thread passed 10 of 10. The chatter was
harmless; the one implicit name wasn't.

Five of those failures were in the monorepo. With three from a test that split
the ticket into child tickets, 8 of 35 later monorepo runs failed for reasons
other than a skipped app. Hence "in the main test" above.

## What this doesn't tell you

- The developers and reviewers were AI agents. A person might ask who else is
  affected, or act on a summary that names a skipped app. People are untested.
- Both models were Claude, a larger one and a smaller one. The smaller one did
  worse with a partial list, so don't read this as true of every model.
- It's a toy system: three small apps, one shared library, one machine.
- Five runs per ticket type, four on the smaller model. 14 of 15 against 0 of 5
  isn't a close call; smaller differences are leads.
- The missing app was nearly always the same one. With the shell hidden
  instead, 2 of 5 runs missed it.
- The same AI tools built the tests and played the developers. The controls:
  scoring by script on the live apps, and predictions written before each
  phase.
- This is a first report. Nobody outside the work has read it yet.

The full write-up has every ticket version, the scoring, the wrong predictions
and the corrections: [the full report](/studies/ticket-scope/), with the [data and scripts](https://github.com/dlockamy/ticket-scope-study) alongside.

## What's next

Everything above is about AI agents. Whether people do better is still open, and
I want to answer it properly. A packet of files and a spreadsheet can't tell me
what a reviewer actually looked at or how long they spent. So I'm building a
small web tool where reviewers work through tickets and code like these, and,
with their consent, it records what they open and how long they take. The next
post in this series will explain how it works, and that's where I'll ask for
volunteers.

---

Drafted with AI assistance.
