---
layout: post
title: "The AI agent needed a memory, so I gave it an Obsidian vault"
date: 2026-07-25
categories: [general]
tags: [ai, claude, obsidian, knowledge-management, workflow, second-brain, lockamy-studios]
excerpt: "AGENT.md solved per-repo context. It never solved cross-session memory — every conversation still started from zero, and findings never compounded. Here's what replaced it: a real Obsidian vault, git submodules an AI agent can actually read, and the incident that proved I needed one."
author: Douglas Lockamy
ai_assisted: true
---

Back in May I wrote about `AGENT.md` — a per-repo context file that tells an AI
what a project is, instead of me re-explaining it every session. It worked. It
also had a ceiling I didn't see until I hit it: `AGENT.md` makes one repo
legible. It does nothing for the studio *as a whole* — the decisions that span
repos, the things one project quietly assumes because of a call another
project made two weeks earlier, the fact that yesterday's session learned
something today's session has no way of knowing.

Every conversation was still a new hire's first day. I'd written the
onboarding doc; I still hadn't given anyone a memory.

## The incident that made the gap undeniable

A planning session drafted a 293-line, seven-phase production migration plan
— real infrastructure work, the kind of thing you don't want to redo. It got
written to `~/.claude/plans/`, Claude Code's own scratch directory.

That directory is unversioned. It gets cleaned up. Nobody told me that's what
"scratch" means until the plan had already been living there for weeks, cited
by name in two other project's context files as *the* authoritative migration
plan — pointing at a file that could vanish on the next housekeeping pass. I
found this by accident, doing an unrelated review, and spent an afternoon
rescuing it into a real repo before it actually disappeared.

That's the moment "just remember it" stopped being an acceptable answer. An
agent's own working notes need to live somewhere with git history, same as
everything else it touches.

## What replaced it

The studio already had three shared context repos — `context/`, `agents/`,
`skills/` — checked out as git submodules. The fix wasn't a new system, it was
making those submodules the *actual working surface* instead of a folder an
AI reads once at session start and forgets:

- **Mounted at plain paths in an Obsidian vault**, not dotted ones, so
  Obsidian indexes them as a real knowledge graph — backlinks, wikilinks,
  a graph view that makes it visible when two documents are quietly talking
  about the same thing without knowing it.
- **Symlinked into the conventional `.claude/` paths** every repo expects, so
  Claude Code reads the identical source with zero duplication — one
  `agents/publicist.md`, not a copy per repo that drifts.
- **Mirrored again at the user level** (`~/.claude/`), so the same context
  applies to *every* project I open, not just the vault. Same trick as
  `AGENT.md`, one layer up: write it once, symlink it everywhere, never
  copy-paste a persona file again.

On top of the submodules sits a `wiki/` layer — raw sources ingested once,
a synthesis layer that's allowed to grow and be wrong and get corrected, a
small "hot" cache for what matters *right now*, and an append-only operation
log. The load-bearing rule is the boundary between the two: `wiki/` is
working synthesis, `context/` is authoritative studio truth, and something
only moves from the first to the second on purpose, with a link back. Skip
that boundary and you get the failure mode every "AI notes" system eventually
hits — a synthesis note quietly becomes gospel because nobody drew the line
between *what we think* and *what's locked*.

## Where it already caught something real

A vault entry claimed two Jira tickets were "retired — superseded, close on
sight," with a cautionary story attached about a prior session that built a
full prototype against one of them before catching the mistake. Reasonable-
sounding, specific, cited a real incident.

It was wrong. Checking it against live Jira turned up recent, substantive
comments on the "retired" ticket — real design decisions, made weeks after
the note claimed it was dead. The vault had drifted from reality and then
quietly presented the drift as a fact worth acting on.

A plain `AGENT.md` can't catch that. There's nothing to check it against —
one file, one repo, no accumulated record to cross-reference. The vault
caught it precisely because the claim and the live system it described were
both sitting in reach of the same session, and checking one against the
other was cheap enough to actually do.

## Where it breaks

Same honest-column rule as the agents-as-employees post: here's what this
doesn't solve.

**Submodule discipline is now load-bearing.** Forget to push a submodule
before bumping its pointer in the parent repo and you've recorded a commit
hash nobody can check out. This isn't hypothetical — it happened mid-session
this week, caught only because the next step was reviewing the diff.

**The vault can still be wrong** — see above. A knowledge graph doesn't
self-correct; it just makes correction *possible* where a scratch file
doesn't. Someone (usually me, sometimes the agent catching its own earlier
work) still has to actually check.

**It's a maintenance surface now, not just a convenience.** Three submodules,
a wiki layer, a boundary rule to enforce — that's real upkeep, the same tax
every "team of agents" experiment pays. Worth it if the alternative is losing
a seven-phase migration plan to a cleanup job. Ask me again once it's had a
few more months to accumulate drift of its own.

---

The submodule + symlink pattern this grew out of is the same one from the
[`AGENT.md` post](/blog/) — this is what it looks like once you stop treating
context as something you reload and start treating it as something you keep.
Code's on [GitHub](https://github.com/dlockamy). If you're running your own
version of "give the agent a memory," I'd like to compare notes — [find me on
LinkedIn](https://www.linkedin.com/in/douglas-lockamy-49097b33/).
