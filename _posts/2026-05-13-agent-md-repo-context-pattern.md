---
layout: post
title: "AGENT.md: a per-repo context file for working with AI on engineering projects"
date: 2026-05-13
categories: [devops, tooling]
tags: [ai, claude, developer-tools, workflow, documentation]
excerpt: "README.md tells humans what a repo is. AGENT.md tells an AI. Here's the pattern I use to keep AI sessions focused, context-efficient, and genuinely useful across a multi-repo workspace."
author: Douglas Lockamy
ai_assisted: true
---

Every engineer working with AI tools hits the same wall eventually: the context window fills up, the AI starts hallucinating details from earlier in the conversation, and you spend more time re-explaining your project than actually building it. The session that was supposed to help you move faster becomes a liability.

The fix isn't a better prompt. It's a better file.

## The problem with long AI sessions

AI assistants have no persistent memory between conversations. Every session starts blank. That means you either:

1. Re-explain your stack, conventions, and decisions at the start of every chat
2. Keep one very long conversation going until the context is exhausted
3. Work from a context file that the AI reads at the start of each session

Option 3 is the only one that scales. But most people improvise it — pasting random bits of documentation into the chat, hoping the AI figures out the relevant parts. The result is inconsistent and hard to maintain.

## AGENT.md

The pattern I've settled on is a file called `AGENT.md` at the root of each repo. It's a structured system prompt written specifically for the AI, not for humans. It answers the questions the AI would otherwise ask:

- What is this repo and what problem does it solve?
- What's the stack and architecture?
- What are the conventions I need to follow?
- What's the current state — what's done, what's in progress, what's blocked?
- What decisions have already been made and shouldn't be relitigated?
- Where does this repo fit relative to other repos in the workspace?

The format is Markdown. The content is dense and direct. No filler, no tutorial-style explanations — just what an experienced engineer joining the project mid-flight would need to know.

Here's an abbreviated example from a Rust CLI project:

```markdown
# bitchain — Agent Context

You are working on **bitchain** — a Rust CLI for content-addressed binary
versioning. Be precise about the data model. Content-addressing is the core
invariant — a block's hash is its identity. Never suggest changes that
compromise that.

## Core data model

Block:
  hash: SHA-256 of content — the block's identity
  size: byte count

Manifest:
  id:      UUID
  name:    human-readable artifact name
  version: semver string
  blocks:  [{ hash, size, offset }]

## Stack

- Language: Rust (edition 2021)
- CLI framework: clap v4 with derive macros
- Async runtime: tokio
- S3: aws-sdk-s3 v1

## Open work

- [ ] Implement block.rs — splitting, SHA-256, upload/fetch
- [ ] Implement S3 store backend
- [ ] Wire up CLI subcommands

## Key decisions already made

- Local filesystem store for tests/dev — not S3
- Manifest IDs are UUIDs, not content hashes
- Block size: 4MB fixed, not configurable
```

To start a session: open the repo, paste the AGENT.md content into the system prompt field (or at the start of the chat), and begin. The AI has full context immediately.

## WORKSPACE.md at the root

For a multi-repo workspace, a root-level `WORKSPACE.md` acts as the index. It maps every repo to its context file and captures the shared infrastructure context that applies across all of them:

```markdown
# Lockamy Studios — Workspace Index

## Repositories

| Repo | File | What it is |
|------|------|-----------|
| `softsurve/sol` | `AGENT.md` | Sol network IaC |
| `lockamy-studios/digital-zen` | `AGENT.md` | Design system |
| `dlockamy/bitchain` | `AGENT.md` | Versioning CLI (Rust) |
| `dlockamy/refraction` | `AGENT.md` | Management API (Go) |
| `dlockamy/bitchain-studio` | `CONTEXT.md` | GUI stub — TBD |

## Shared infrastructure

- CI/CD: Jenkins at jenkins.softsurve.com
- Artifacts: Nexus at nexus.softsurve.com
- Secrets: AWS Secrets Manager, prefix `sol/`
- Jenkins credential IDs used in all Jenkinsfiles:
  - nexus-credentials
  - github-token
  - io-ssh-key
```

Load WORKSPACE.md when a task touches multiple repos. Load the specific AGENT.md when you're deep in one repo.

## AGENT.md vs CONTEXT.md

Not every repo needs a full agent. I use two file types:

**AGENT.md** — for active, complex repos. Opinionated. Tells the AI how to behave, not just what the repo is. Includes architectural invariants, things that should never be changed, and explicit instructions for the AI's tone and approach.

**CONTEXT.md** — for stub repos, legacy code, or simple sites. Lighter. Just answers "what is this, what stack, what's the current status, what's the next step."

The distinction is useful because it signals to anyone opening the repo how much thinking has gone into the context file. AGENT.md implies active maintenance. CONTEXT.md implies "good enough for now."

## Keeping context files current

The main failure mode is letting AGENT.md drift from reality. A decision gets made, the code changes, but the context file still describes the old approach. The AI confidently works from stale information.

The fix is to treat context file updates as part of the definition of done. When you make an architectural decision, update AGENT.md in the same commit. When you finish a major piece of work, check off the item in the open work list. When the stack changes, update the stack section.

It helps to ask the AI to draft the update:

> "Update the open work section to reflect that the S3 backend is implemented and tested. Also add a note that block size is now configurable via `--block-size` flag."

The AI generates the diff, you review and commit. Takes thirty seconds.

## One repo, one chat

The discipline that makes this work: one AI chat per repo, per task. Don't try to work on your infrastructure Terraform and your API implementation in the same session. The context gets muddled, the AI loses track of which conventions apply where, and you end up with a session that's too long to be useful.

Start a new chat. Load the relevant AGENT.md. Do the work. Close the chat.

This feels inefficient but it's the opposite. Each session is focused, the context stays relevant, and you don't hit the wall where the AI starts confusing details from five hours ago with what you're asking right now.

## What AGENT.md is not

It's not a README. READMEs are for humans — they explain the project from first principles, include setup instructions, have a friendly introduction. AGENT.md assumes the AI already understands the domain and the tools. It's dense on purpose.

It's not a specification. It doesn't try to document everything. It documents the things that would otherwise require the AI to ask questions or make wrong assumptions.

It's not permanent. It's a living document that tracks the current state of the project, not a historical record of every decision ever made.

## The broader pattern

What this is really doing is externalising the context that used to live only in your head and in long Slack threads. The AI needs that context written down. But so does any engineer joining the project cold. So does future-you, six months from now, when you come back to a repo you haven't touched in a while.

AGENT.md is useful even if you never use AI tooling. It's a forcing function for capturing the things that matter about a repo — the invariants, the decisions, the current state — in a place where they'll actually be read.

The full set of context files for Lockamy Studios projects is at [github.com/dlockamy](https://github.com/dlockamy), with a root WORKSPACE.md at the base of the local checkout.
