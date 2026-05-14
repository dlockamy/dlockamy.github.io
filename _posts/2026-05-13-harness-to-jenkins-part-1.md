---
layout: post
title: "From Harness to self-hosted Jenkins: why we made the switch (Part 1 of 2)"
date: 2026-05-13
categories: [devops, ci-cd]
tags: [jenkins, harness, ci-cd, self-hosted, migration]
excerpt: "Harness is a capable platform. It was also the wrong tool for a small multi-repo workspace where the overhead of cloud runners, YAML pipeline definitions, and an external dependency outweighed the benefits. Here's what drove the decision and what the migration looked like."
author: Douglas Lockamy
ai_assisted: true
---

Harness landed in the Lockamy Studios repos for the right reason: it promises a modern CI/CD experience with a clean YAML format, built-in approval flows, and managed runners so you don't have to think about where builds execute. For a growing project, that sounds like exactly the right tradeoff.

It didn't stay long. After a few months, the decision was made to standardise on self-hosted Jenkins across all repos. This post covers the reasoning — the specific friction points that made Harness the wrong fit — and Part 2 covers the actual migration: what the Jenkinsfiles look like, how they're structured consistently, and what changed at the infrastructure level.

## What Harness looked like in the repos

The Harness configuration lived in two places across the codebase:

**`thunderhead-systems/thunderhead/.harness/release.yaml`** — a pipeline definition for the Thunderhead project:

```yaml
pipeline:
  name: release
  identifier: release
  projectIdentifier: thunderhead
  orgIdentifier: default
  stages:
    - stage:
        name: build
        type: CI
        spec:
          execution:
            steps:
              - step:
                  name: Build
                  type: Run
                  spec:
                    command: echo "start build"
```

**`thunderhead-systems/thunderhead/.harness/input_sets/mainpr.yaml`** — a trigger input set for the main branch:

```yaml
inputSet:
  name: main-pr
  pipeline:
    identifier: release
    properties:
      ci:
        codebase:
          build:
            type: branch
            spec:
              branch: <+trigger.branch>
```

**`lockamy-studios/digital-zen/harness-pipeline.yaml`** — a more developed pipeline for the multi-stack design system repo, covering Rust, Flutter, and Jekyll build stages with cloud runners.

That was the full extent of it. The digital-zen pipeline had real content; the Thunderhead pipeline was a stub. Nothing was in production.

## The friction points

### External dependency at the wrong layer

CI/CD is foundational infrastructure. When it has an external dependency — a cloud platform that controls the runners, the pipeline execution environment, the YAML schema — that dependency becomes load-bearing in a way that's easy to underestimate.

For a homelab and small studio context, the question isn't "is Harness good?" (it is) but "what happens when Harness has an outage, a pricing change, a schema migration, or a feature deprecation?" The answer is: your builds stop working and you don't control the fix. For a single-developer workspace, that's a bad tradeoff.

Self-hosted Jenkins has a different failure mode: if Jenkins is down, it's down on your hardware, and you can fix it. The dependency is owned.

### Cloud runners vs local build cache

Harness managed runners execute in ephemeral cloud environments. Every build starts clean, pulls dependencies from scratch, and discards the cache. For a Rust project, that means rebuilding `target/` from zero on every run — several minutes of compile time that a warm local cache would eliminate.

Self-hosted Jenkins with Docker-in-Docker has access to the local Nexus registry and a persistent layer cache. A Rust build that takes four minutes cold takes forty seconds warm. Ruby gem installs that pull from rubygems.org take thirty seconds; the same pull from the local Nexus proxy takes three.

For small teams, build time is a real quality-of-life factor. The cache matters.

### Complexity overhead for small pipelines

The Harness YAML format is expressive and powerful. It's also verbose for simple cases. A pipeline that runs three build steps and pushes an artifact requires more configuration surface area in Harness than the equivalent Jenkinsfile, once you account for stage definitions, runner specifications, input sets, and trigger configuration.

The digital-zen Harness pipeline was around 80 lines for what became a 120-line Jenkinsfile — not a huge difference — but the Harness version also had external dependencies on the Harness platform for execution context that the Jenkinsfile handles internally.

### Inconsistency across repos

The deeper issue was that Harness coverage was partial. Two repos had Harness configuration; a dozen others had nothing. Building a consistent CI/CD story across the workspace required either extending Harness to all repos (adding platform dependency everywhere) or standardising on something already present in the simpler repos.

Jenkins was already the answer for the simple repos. Extending it to replace Harness in the two complex repos was less work than extending Harness to cover everything else.

## The decision

The decision came down to a single question: **what's the simplest thing that handles all our cases?**

The cases are: Rust builds, Go builds, Flutter builds, Jekyll builds, Docker image builds, Terraform deployments, and artifact publishing to a private Nexus registry. Jenkins with Docker agents handles all of them without cloud runners, without external dependencies, and with a consistent Jenkinsfile format that works the same in every repo.

The Harness files were tombstoned:

```yaml
# harness-pipeline.yaml — REMOVED
# CI/CD standardised on Jenkins. See Jenkinsfile.
# This file is kept as a placeholder to avoid broken references.
# Safe to delete.
```

And a single Jira ticket was raised: *CI/CD: Standardise on Jenkins — remove Harness, audit all Jenkinsfiles*. Closed the same day.

## What we kept from Harness

The Harness pipeline structure influenced the Jenkinsfile design in a few ways worth noting:

**Stage parallelism.** The digital-zen Harness pipeline ran Rust, Flutter, and Jekyll in parallel stages. The Jenkinsfile preserves this:

```groovy
stage('Build & Test') {
  parallel {
    stage('Rust') { ... }
    stage('Flutter') { ... }
    stage('Jekyll') { ... }
  }
}
```

**Pre-flight skip.** Harness has a built-in skip mechanism via trigger conditions. The Jenkinsfile replicates this with a `[skip ci]` commit message check:

```groovy
stage('Pre-flight') {
  steps {
    script {
      def msg = sh(script: 'git log -1 --pretty=%B', returnStdout: true).trim()
      if (msg.contains('[skip ci]')) {
        currentBuild.result = 'NOT_BUILT'
        error('Commit contains [skip ci] — aborting.')
      }
    }
  }
}
```

**Explicit artifact targets.** The Harness pipeline was clear about what it was building and where it was publishing. The Jenkinsfiles carry this forward explicitly — every pipeline names its Nexus target in the environment block.

Part 2 covers the full Jenkinsfile structure across all repo types: what consistent patterns look like at scale, how Docker agent images are chosen per language, and the credential model that lets every pipeline use the same `nexus-credentials` ID regardless of what format it's publishing.
