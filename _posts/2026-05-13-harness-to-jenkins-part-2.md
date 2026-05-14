---
layout: post
title: "From Harness to self-hosted Jenkins: the Jenkinsfile patterns (Part 2 of 2)"
date: 2026-05-13
categories: [devops, ci-cd]
tags: [jenkins, harness, ci-cd, self-hosted, migration, groovy, jenkinsfile]
excerpt: "The implementation side of the Harness migration: a consistent Jenkinsfile structure across 13 repos, Docker agents per language, a shared credential model, and the specific patterns for Rust, Go, Flutter, Jekyll, and Godot builds."
author: Douglas Lockamy
ai_assisted: true
---

[Part 1](/2026/05/13/harness-to-jenkins-part-1) covered why we moved from Harness to self-hosted Jenkins. This part covers what the resulting Jenkinsfiles actually look like — the consistent patterns across 13 repos, the Docker agent strategy, and the specifics for each build type.

## The consistent skeleton

Every Jenkinsfile across the workspace follows the same structure:

```groovy
pipeline {
  agent any

  environment {
    NEXUS_URL  = 'https://nexus.softsurve.com'
    REGISTRY   = 'nexus.softsurve.com'
    IMAGE_NAME = 'project-name'
  }

  stages {

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

    stage('Build & Test') { ... }
    stage('Publish') { ... }

  }

  post {
    success { echo "..." }
    failure { echo "Pipeline failed." }
    always  { cleanWs() }
  }
}
```

Three things are consistent in every pipeline:

1. **Pre-flight `[skip ci]` check** — lets any commit message suppress the build without touching branch protection rules
2. **`NEXUS_URL` environment variable** — every pipeline knows where the artifact store is
3. **`cleanWs()` in the `always` post block** — workspace is always cleaned up, no stale artifacts on the agent

## Docker agents per language

Rather than a single heavy agent image with every toolchain installed, each build stage uses the minimal official image for its language. This keeps images small and dependencies explicit.

```groovy
stage('Build') {
  agent {
    docker {
      image 'rust:slim'
      reuseNode true
    }
  }
  steps {
    sh 'cargo build --release'
  }
}
```

The `reuseNode true` flag is important — it runs the Docker container on the same node as the outer pipeline, which means the workspace directory is shared. Without it, a Docker agent gets its own fresh workspace and can't see files produced by previous stages.

### Language → image mapping

| Language | Image | Notes |
|----------|-------|-------|
| Rust | `rust:slim` | Add `pkg-config libfontconfig1-dev` for iced/GUI crates |
| Go | `golang:1.21-slim` | Clean, minimal |
| Flutter/Dart | `ghcr.io/cirruslabs/flutter:stable` | Official Flutter CI image |
| Jekyll/Ruby | `ruby:3.1-slim` | Add `build-essential` for native gems |
| Terraform | `hashicorp/terraform:1.7` | Override entrypoint: `args '--entrypoint=""'` |
| Godot | `barichello/godot-ci:3.5.3` | Community image for headless exports |

## Rust pipelines

Rust builds follow a four-stage pattern: format check → lint → test → publish.

```groovy
stage('Build & Test') {
  agent {
    docker {
      image 'rust:slim'
      reuseNode true
    }
  }
  steps {
    sh '''
      cargo fmt --check
      cargo clippy -- -D warnings
      cargo test
      cargo build --release
    '''
  }
  post {
    success {
      archiveArtifacts artifacts: 'target/release/bitchain', allowEmptyArchive: false
    }
  }
}

stage('Publish') {
  agent {
    docker { image 'rust:slim'; reuseNode true }
  }
  steps {
    withCredentials([usernamePassword(
      credentialsId: 'nexus-credentials',
      usernameVariable: 'NEXUS_USER',
      passwordVariable: 'NEXUS_PASS'
    )]) {
      sh '''
        mkdir -p ~/.cargo
        cat >> ~/.cargo/config.toml <<EOF
[registries.lockamy]
index = "${NEXUS_URL}/repository/cargo-hosted/"
EOF
        printf '[registries.lockamy]\ntoken = "%s:%s"\n' \
          "${NEXUS_USER}" "${NEXUS_PASS}" >> ~/.cargo/credentials.toml
        chmod 0600 ~/.cargo/credentials.toml
        cargo publish --registry lockamy
      '''
    }
  }
}
```

One subtlety: `cargo clippy -- -D warnings` promotes all clippy warnings to errors. Clippy warnings that accumulate across commits turn into technical debt. Treating them as errors keeps the codebase clean.

## Go pipelines

Go builds include coverage reporting, which gets archived as a build artifact:

```groovy
stage('Test') {
  agent {
    docker { image 'golang:1.21-slim'; reuseNode true }
  }
  steps {
    sh '''
      go mod download
      go vet ./...
      go test -v -coverprofile=coverage.out ./...
      go tool cover -func=coverage.out
    '''
  }
  post {
    always {
      archiveArtifacts artifacts: 'coverage.out', allowEmptyArchive: true
    }
  }
}

stage('Build') {
  agent {
    docker { image 'golang:1.21-slim'; reuseNode true }
  }
  steps {
    sh 'CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o app-binary .'
  }
}
```

The `-ldflags="-s -w"` strips debug symbols and DWARF information from the binary — typically reduces size by 30-40% with no runtime impact. Worth doing for anything that ships as a Docker image.

Go services publish as Docker images rather than to a package registry:

```groovy
stage('Docker') {
  steps {
    script {
      def shortSha = sh(
        script: 'git rev-parse --short HEAD',
        returnStdout: true
      ).trim()
      def imageTag  = "${env.REGISTRY}/${env.IMAGE_NAME}:${shortSha}"
      def latestTag = "${env.REGISTRY}/${env.IMAGE_NAME}:latest"

      withCredentials([usernamePassword(
        credentialsId: 'nexus-credentials',
        usernameVariable: 'NEXUS_USER',
        passwordVariable: 'NEXUS_PASS'
      )]) {
        sh """
          echo "${NEXUS_PASS}" | docker login ${env.REGISTRY} \
            -u "${NEXUS_USER}" --password-stdin
          docker build -t "${imageTag}" -t "${latestTag}" .
          docker push "${imageTag}"
          docker push "${latestTag}"
          docker logout ${env.REGISTRY}
        """
      }
    }
  }
}
```

Tagging with both the short SHA and `latest` means you can pin to a specific commit or pull the latest — useful for local development.

## Multi-stack pipelines (digital-zen)

The digital-zen design system repo has three stacks in parallel: Rust (iced renderer), Flutter (mobile/TV package), and Jekyll (web theme gem). Parallel stages handle this cleanly:

```groovy
stage('Build & Test') {
  parallel {

    stage('Rust') {
      agent { docker { image 'rust:slim'; reuseNode true } }
      steps {
        sh 'cd rust && cargo test --lib'
      }
    }

    stage('Flutter') {
      agent { docker { image 'ghcr.io/cirruslabs/flutter:stable'; reuseNode true } }
      steps {
        sh 'cd flutter && flutter pub get && flutter test'
      }
    }

    stage('Jekyll') {
      agent { docker { image 'ruby:3.1-slim'; reuseNode true } }
      steps {
        sh '''
          apt-get update -qq && apt-get install -y -qq build-essential
          bundle install
          bundle exec jekyll build
        '''
      }
    }

  }
}
```

The parallel block runs all three simultaneously. Total build time is bounded by the slowest stage (usually Rust) rather than the sum of all three.

The version bump stage keeps version numbers synchronised across all three stacks from a single place:

```groovy
stage('Version') {
  steps {
    script {
      def latestTag = sh(
        script: "git tag --list 'v*' --sort=-v:refname | head -1",
        returnStdout: true
      ).trim() ?: 'v0.0.0'

      def parts  = latestTag.replaceFirst('^v', '').tokenize('.')
      def newVer = "${parts[0]}.${parts[1]}.${parts[2].toInteger() + 1}"

      sh """
        sed -i 's/^version = "[0-9][0-9.]*"/version = "${newVer}"/' rust/Cargo.toml
        sed -i 's/^version: [0-9][0-9.]*/version: ${newVer}/'      flutter/pubspec.yaml
        sed -i 's/spec\\.version.*=.*/spec.version = "${newVer}"/'  *.gemspec
      """

      withCredentials([usernamePassword(credentialsId: 'github-token', ...)]) {
        sh """
          git add rust/Cargo.toml flutter/pubspec.yaml *.gemspec
          git commit -m "chore: bump version to ${newVer} [skip ci]"
          git tag v${newVer}
          git push ...
        """
      }
    }
  }
}
```

The `[skip ci]` in the version bump commit prevents the push from triggering another build run — otherwise you get an infinite loop.

## Stub repos

Not every repo has code yet. Stub repos still get Jenkinsfiles — they just don't do much:

```groovy
pipeline {
  agent any

  stages {
    stage('Pre-flight') { ... }

    stage('Build') {
      steps {
        echo 'No build target yet. Add build steps when framework is selected.'
      }
    }

    stage('Docker') {
      when { expression { fileExists('Dockerfile') } }
      steps {
        // Docker push when Dockerfile exists
      }
    }
  }

  post { always { cleanWs() } }
}
```

The `fileExists('Dockerfile')` condition gates the Docker stage — the stub pipeline is inert until someone adds a Dockerfile, at which point the pipeline automatically starts building and pushing without any Jenkinsfile changes.

## Godot (special case)

Godot builds use a headless export to produce a web build, then package it as a Docker/nginx container:

```groovy
stage('Godot Export') {
  agent {
    docker {
      image 'barichello/godot-ci:3.5.3'
      reuseNode true
    }
  }
  steps {
    sh '''
      mkdir -p builds/linux builds/web
      godot --headless --export "HTML5" builds/web/index.html || \
        echo "Web export skipped — configure export presets in Godot editor first."
    '''
  }
}

stage('Docker (web build)') {
  when {
    expression { fileExists('builds/web/index.html') }
  }
  steps {
    // package the web export as nginx image
  }
}
```

Export presets need to be configured in the Godot editor first — there's no way to create them from the CLI. The pipeline gracefully handles their absence rather than failing the build.

## The credential model

Every pipeline uses the same three credential IDs:

| ID | Type | Used for |
|----|------|---------|
| `nexus-credentials` | Username/password | All Nexus operations (publish, login) |
| `github-token` | Username/password | Push, tag, repo access |
| `io-ssh-key` | SSH private key | Terraform deployments via SSH |

These are provisioned by JCasC (covered in a [previous post](/2026/05/13/jcasc-bake-credentials-deploy-time)) and sourced from AWS Secrets Manager. A Jenkinsfile written in any repo can reference `nexus-credentials` without knowing anything about where the credentials come from or how they're managed.

## The full pipeline inventory

Thirteen repos, thirteen Jenkinsfiles, all pushing to the same private registry:

| Repo | Build type | Nexus target |
|------|-----------|-------------|
| `bitchain` | Rust | `cargo-hosted` |
| `refraction` | Go + Docker | Docker registry |
| `digital-zen` | Rust + Flutter + Jekyll | Cargo + RubyGems |
| `thunderhead` | Go + Flutter + Docker | Docker registry |
| `dlockamy.github.io` | Jekyll | RubyGems (if gemspec) |
| `thunderhead-systems.github.io` | Jekyll | Archive only |
| `thunderhead-systems/docs` | Markdown | Archive only |
| `pogo-pop` | Godot 3 | Docker (web export) |
| `pogo-facade` | Static HTML | Docker registry |
| `bitchain-studio` | Stub | Docker (future) |
| `slashbuilder` | Stub | Docker (future) |
| `i95north` | Stub | — |
| `softsurve/sol` | Terraform | Archive docs |

One platform, one credential model, one deployment target.
