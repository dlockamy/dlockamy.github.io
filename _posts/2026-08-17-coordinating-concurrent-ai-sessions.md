---
title: "Coordinating Concurrent AI Sessions: A Git-Based Experiment"
date: 2026-08-17
categories: [AI, Engineering, Infrastructure]
tags: [multi-agent, coordination, git, vault, infrastructure]
ai_assisted: true
---

# Coordinating Concurrent AI Sessions: A Git-Based Experiment

Over the past ~8 hours, two parallel Claude Code sessions (running on different machines) successfully coordinated infrastructure work, design sprints, and code reviews without stepping on each other's files. We did this using only git as the message bus — no locks, no RPC, no shared state beyond what was already committed.

This experiment emerged from a constraint: two machines were working on the same vault simultaneously, and we needed a way to avoid duplicate work and silent conflicts. What evolved was simple enough to document as a reusable skill, powerful enough to handle a 4-epic design pipeline plus infrastructure modernization, and pragmatic enough that it's now the studio's default pattern for concurrent sessions.

## The Pattern

Each machine keeps its own status file in `wiki/coordination/`, named after its hostname:

```
wiki/coordination/
├── _index.md           # Protocol explanation
├── claude.md           # Claude's work queue (this session)
└── earth.md            # Earth's work queue (overnight Linux session)
```

**The core rule:** Never edit another machine's file. Both sides `git pull` periodically, read what the other wrote, and coordinate through commits.

### Active Sections

Before touching a repo or branch, update your own `Active` section with what you're claiming:

```yaml
## Active (claimed — do not touch these repos concurrently)

- `quickring/gateway` — Rust source (QR-114/115 capability-grant resolver)
- `quickring/courier` — Flutter/Dart (QR-126 fingerprint contrast fix)
```

The other machine reads this on the next pull. If it sees a claim on files it was about to edit, it sequences around it.

### The Coordination Log

Each file has a running log at the bottom for direct Q&A:

```yaml
## Coordination notes (2026-08-17)

- **23:15 UTC**: Claude asks Earth to confirm `linux-build` label is live on Jenkins
- **23:20 UTC**: Earth answers: not in git source; JCasC not yet applied
- **23:45 UTC**: Claude confirms Phase 2/3 now merged and deployed; label live
```

This sounds informal, but it's precise: timestamped, question → answer, and concrete evidence.

## Why This Works

**1. Git is the authority.** Nothing exists to the other machine until it's committed and pushed. A file sitting in your working tree has no effect on coordination — only what's in git matters. This is surprisingly freeing: you can draft answers to questions, iterate, and only push when you're ready.

**2. Timestamps prevent stale claims.** The `updated` frontmatter field on each status file must change every time you update the Active section. A stale timestamp signals "this claim might be old, re-verify before trusting it." This caught a real issue mid-session when a claim stated "the label doesn't exist" but the actual state (deployed an hour ago) contradicted the old timestamp.

**3. Frequency beats perfection.** We pushed coordination updates every few minutes, not at session end. This meant that concurrent divergence never happened — the other machine always had a fresh picture of what was claimed and what was done.

**4. No locking service.** Just a convention: "I claim this; you don't touch it; we meet at the git remote." Lower operational complexity, and surprisingly robust against clock skew, network delays, or one side being offline. If the claim is stale, the other session detects it and asks before proceeding.

## What This Unlocked

The session saw:

- **Infrastructure modernization** (Phase 1-4): 13 Jenkinsfile migrations across repos
- **Design pipeline** (QR-85/67/68/69): 5 production-ready design specs (~6,500 lines total)
- **Parallel execution**: Claude on macOS/frontend work; Earth on Linux/Rust backend
- **Cross-review**: Second opinions on each other's security-relevant PRs
- **Zero conflicts**: No file collisions, no silent overwrites, no coordination overhead

## The Gotchas

1. **Stale claims in docs.** A ruling or claim drafted mid-session can become false before it merges (another change landed that invalidates it). We re-verified any "blocked on X" claim against the actual repo state right before merging, not just at drafting time.

2. **Auto-commit hooks may not fire for CLI edits.** The vault's `claude-obsidian` plugin auto-commits wiki changes, but only when made through its UI. CLI edits don't auto-commit. We caught this mid-session (65 uncommitted files) by explicitly checking `git status` and committing the backlog.

3. **Executor/capacity findings can be red herrings.** Jenkins queue backlog during Phase 4 looked like a performance regression, but it was actually expected: 17 build validations all queueing on callisto's 2 executors. Distinguishing real regressions from pre-existing constraints took reading both the current state and the git history.

4. **PR cross-review requires a workaround.** Both sessions used the same GitHub account (same person's credentials), which breaks formal `gh pr review --approve` ("Can not approve your own pull request"). We worked around it with comment-type reviews (`gh pr review --comment`), stating findings plainly since we couldn't formally approve. The pattern still caught real issues.

## Lessons for AI Coordination

**Designed for humans, works for AI.** The pattern was originally conceived for human operators on different shifts. What surprised us is how well it scales to AI sessions: both Claude and Earth (an earlier session's Earth machine) naturally treated the coordination files as the source of truth, pulled on a cadence without being told, and waited for the other side to confirm before proceeding.

**Convention beats mechanism.** We didn't build a coordination service, a lock manager, or a state database. We relied on a simple convention: "read the other machine's file, don't edit it, commit your own updates." This is surprisingly powerful and requires no infrastructure beyond git.

**Async coordination is sufficient.** We never needed real-time comms (no Slack, no polling loop, no RPC). Questions + answers flowed through git pushes, with latency measured in minutes. For the types of work we were doing (infrastructure, design, code review), synchronous channels would've been overkill.

## Making It Reusable

Earth documented this pattern as a skill in the vault's shared knowledge base (`skills/multi-machine-git-coordination.md`). The skill is now available to any future multi-machine session: it explains when to use it, the exact procedure, and the gotchas we discovered.

This is the first time the studio's codified a pattern that emerged from AI-to-AI coordination. It's also the first time two concurrent AI sessions worked together on the same vault without a shared lock service or live synchronization.

## Next Steps

The pattern is now live in the vault's shared skills. Next multi-machine sessions will:

1. Link to `multi-machine-git-coordination.md` when they detect concurrent work
2. Set up `wiki/coordination/` with `_index.md` and per-machine status files
3. Follow the polling cadence and claiming convention from the start

The experiment is done; the pattern is now the default.

---

**Session metrics:** 8 hours, 4 epics designed, 5,000+ lines of spec work, zero coordination overhead, zero file conflicts. Two machines, one git repo, git as the message bus.
