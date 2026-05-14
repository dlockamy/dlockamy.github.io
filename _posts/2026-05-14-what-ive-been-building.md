---
layout: post
title: "What I've been building: May 2026"
date: 2026-05-14
categories: [general]
tags: [lockamy-studios, devops, infrastructure]
excerpt: "A month of foundation work — and this week it went live. The home lab is deployed, secrets are in place, and the private infrastructure stack is operational."
author: Douglas Lockamy
ai_assisted: true
---

The past few weeks have been foundation work. This week it shipped.

## The home lab is live

The Sol network private infrastructure stack is deployed. The VM host is up, AWS Secrets Manager is populated, and the core services are running. What was Terraform-staged and documented for weeks is now operational.

The stack runs on a private home network, VPN-accessible only. Self-hosted artifact registry, CI/CD server, and monitoring — all containerised, all managed as code, credentials sourced entirely from AWS Secrets Manager with nothing sensitive stored on the host or in the CI system.

## What's running

A private Nexus artifact registry handling five package formats — Docker images, Rust crates, Ruby gems, Debian packages, and Dart/pub packages. A Jenkins CI/CD server configured entirely via Configuration as Code, with all credentials baked in at deploy time rather than injected at runtime. Grafana for observability, wired to Prometheus scraping the Docker host and containers.

A single containerised nginx instance terminates all TLS for the network. The wildcard cert lives in AWS Secrets Manager and is fetched at container startup — no cert files on disk.

## CI/CD standardised

Every project repo has a Jenkinsfile and a consistent pipeline structure. The move away from a partially-adopted external CI platform to self-hosted Jenkins is complete — thirteen repos, one pipeline shape, one credential model, builds that benefit from the local artifact cache.

## Private artifact registry

Five package formats, one Nexus instance, REST API provisioning via Terraform. The Dart/pub support is the most unusual piece — native pub support landed in Nexus 3.65 and the documentation for it is thin. It works, but it requires its own port connector and a separate nginx server block that isn't obvious from the docs.

## UX prototype for a collaborator project

Built an interactive prototype for an ongoing collaboration — a management suite for a specialised industrial domain. Three screens, real interactions, shipped as a self-contained Docker container so the collaborator can run it locally without any setup. Comes with a structured review checklist and an AI agent system prompt so they have a knowledgeable product collaborator available locally with any AI.

The agent pattern generalises well. A markdown file per project capturing stack, decisions, open questions, and current state — loaded into an AI at the start of a session instead of re-explaining the project every time.

## Design system

Digital Zen v1.0 documentation complete — token system, typography, motion principles, and platform constraints for web, desktop, TV, mobile, and embedded surfaces.

## AI context management

Every project repo has a context file — either a full system prompt for active projects or a lighter reference for stubs and legacy code. A root workspace index maps all of them. One repo per chat session, context loaded at the start. It solves the problem of long sessions where the model loses track of which project's conventions apply.

---

The infrastructure being live unblocks everything else. Artifact publishing, consistent builds, observability — it's all operational now rather than staged.
