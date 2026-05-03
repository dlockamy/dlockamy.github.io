---
layout: post
title: "Your Binary Assets Deserve Version Control Too"
date: 2026-05-03 00:00:00 -0400
categories: [devops, tools, open-source]
tags: [binary-assets, versioning, rust, bitchain, cicd]
excerpt: "Introducing bitchain: a lightweight CLI for versioning the files your tools forgot about"
author: Douglas Lockamy
ai_generated: true
---

*Introducing bitchain: a lightweight CLI for versioning the files your tools forgot about*

---

## The Problem Nobody Talks About

Your code is versioned. Every change tracked, every release tagged, every rollback a one-liner. It's one of the most reliable parts of modern software development.

Now open your project's asset folder.

Those textures, 3D models, audio files, and compiled shaders? That library of hero images, marketing banners, and video assets for your website? Odds are they live somewhere outside your version control — maybe a shared drive, maybe an S3 bucket someone set up two years ago, maybe a Slack thread where the "final_final_v3" file got dropped. Nobody remembers which version shipped with v2.1. Nobody's sure if the QA environment has the right set of assets. And when something looks wrong in production, there's no `git log` to reach for.

This is the binary asset problem, and it's more common than anyone admits.

---

## Why Git Doesn't Save You Here

Git is exceptional at what it was built for: tracking changes in text files. Source code, configs, markdown — Git handles these beautifully because it can compare files line by line, store only what changed, and merge contributions from multiple people.

Binary files break every one of those assumptions.

A 50MB texture doesn't have lines. When a single pixel changes, Git can't compute a delta — it has to store the whole file again. Commit enough asset updates and your repository balloons to gigabytes before the project is even close to shipping. Clone times stretch. CI pipelines crawl. Developers start skipping pulls because they don't want to sit through a 2GB download just to test a UI change.

The usual workaround is Git LFS, which replaces binary files with small text pointers and stores the real data on a separate server. It helps, but it's still a Git extension — it requires your whole team to be comfortable with Git, your CI/CD toolchain to support it, and someone to keep an eye on storage and bandwidth limits that most platforms charge for separately. It's a reasonable patch, not a real solution.

---

## The Tools Built for This Are Expensive

The solutions purpose-built for large binary asset management — Perforce, Unity Version Control — are genuinely good at the job. They're also enterprise products with enterprise price tags and complexity. For an indie studio, a web agency, or an open source project that just wants assets versioned the same way its code is, they're not a realistic option.

So most teams end up in one of two bad places: assets jammed into Git (and suffering for it), or assets living entirely out-of-band in cloud storage with no versioning, no history, and no reliable way to reproduce a past release.

---

## What's Actually Needed

The pattern that works for code is straightforward: break files into addressable units, store them somewhere durable, and keep a manifest that maps a specific version of your project to a specific set of those units. Tag the manifest, and you can reconstruct any release exactly — no guesswork, no "which S3 folder was that?"

That's exactly how Git works internally. And it's exactly what was missing for binary assets — until now.

**bitchain** brings that same content-addressed approach to any file, any size, stored anywhere you already have infrastructure. S3 bucket you're already paying for? Use it. HTTP server? Works. Local disk for testing? Covered. The manifest is plain JSON, small enough to live in your Git repository, and precise enough to reconstruct an entire collection of binary assets down to the byte.

---

## How bitchain Works

The idea behind bitchain is simple, and it's the same idea that makes Git reliable: instead of tracking files by name or location, track them by their content.

When you run `bitchain ingest` on a file or directory, it does three things. It splits every file into fixed-size blocks (1MB by default). It computes a SHA-256 hash for each block — a fingerprint that is unique to that exact sequence of bytes. And it uploads those blocks to wherever you tell it: an S3 bucket, an HTTP server, or a local directory. When it's done, it writes a single JSON manifest — the `.bitchain.json` file — that records exactly which blocks make up each file, and where to find them.

That manifest is the version. It's small enough to commit to your Git repository alongside your code. Tag it with `v1.2.0` and you've permanently linked that release to a precise, reproducible set of binary assets. No ambiguity, no "I think that was the right folder."

Reconstructing files is just as straightforward. Running `bitchain rebuild` reads the manifest, fetches each block from its URI, verifies the SHA-256 hash, and reassembles the original files exactly. If a block is available from multiple locations — say, both S3 and a CDN — bitchain tries each one in order and uses the first that responds. Your assets are as resilient as you make your storage.

---

## A Concrete Example: Versioning a Game's Asset Pack

Say you're shipping a game update and the art team has delivered a new set of character textures and UI sprites — a directory of `.png` and `.fbx` files totaling about 800MB. Here's what that workflow looks like with bitchain.

**Ingest the assets:**

```bash
bitchain ingest --input ./assets/v1.2.0 \
                --uri-base s3://my-game-studio/releases \
                --output assets-v1.2.0.bitchain.json
```

bitchain splits every file into blocks, uploads them to your S3 bucket, and writes `assets-v1.2.0.bitchain.json`. That file is a few kilobytes of JSON — light enough to commit directly to your code repository.

**Commit the manifest with your release:**

```bash
git add assets-v1.2.0.bitchain.json
git commit -m "Add asset manifest for v1.2.0"
git tag v1.2.0
git push origin v1.2.0
```

Your QA environment, your CI pipeline, your release branch — they all now have a precise reference to the exact set of assets that belongs with this version of the game. Any engineer or automated system can reconstruct them on demand.

**Rebuild on any machine:**

```bash
bitchain rebuild --bitchain assets-v1.2.0.bitchain.json \
                 --output-dir ./assets/restored
```

Every block is fetched, hash-verified, and reassembled. If a block doesn't match its expected SHA-256, the rebuild fails loudly — no silent corruption, no "this texture looks slightly off and we don't know why."

---

## The Manifest Up Close

The `.bitchain.json` file is worth a quick look, because it's the key to everything bitchain does. Here's a simplified example:

```json
{
  "version": "1.0",
  "files": [
    {
      "path": "characters/hero_texture.png",
      "blocks": [
        {
          "hash": "a3f1c8...",
          "uris": [
            "s3://my-game-studio/releases/characters/hero_texture.png/a3f1c8...",
            "https://cdn.example.com/blocks/a3f1c8..."
          ]
        }
      ]
    }
  ]
}
```

A few things worth noting. The `path` field preserves the original file structure, so rebuilding restores your directory layout exactly as it was ingested. Each block lists multiple URIs — so you can back the same assets with both S3 and a CDN, and bitchain will fall back automatically if one is unavailable. And the whole thing is just JSON, which means it's diffable, readable, and easy to validate in CI with `bitchain validate`.

This is what "version your assets like code" looks like in practice. The manifest lives in Git. The blocks live in your storage. And the two together give you something neither could provide alone: a precise, auditable, reconstructible history of your binary assets.

---

## Versioning Assets Like Code: The CI/CD Angle

The key insight is that the `.bitchain.json` manifest is just a file. And because it's just a file — plain text, human-readable, small enough to live in your repository — it participates in your existing Git workflow without any special integration or toolchain changes. Your branches, your tags, your pull requests, your CI checks: they all apply to the manifest the same way they apply to your code.

That means you can treat an asset release exactly like a code release.

---

## A Release Pipeline for Binary Assets

Here's what that looks like end to end, using a website content release as the example — a batch of new hero images, product photography, and video assets handed off by the design team. The same pattern applies equally to game asset packs, marketing materials, or any other collection of binaries that needs to follow a predictable path from creation to production.

**Step 1 — Ingest on a feature branch**

When the design team delivers the new content drop, a developer ingests it on a feature branch:

```bash
git checkout -b content/homepage-refresh-q2

bitchain ingest --input ./delivered/homepage-assets \
                --uri-base s3://my-web-agency/staging \
                --output homepage-refresh.bitchain.json

git add homepage-refresh.bitchain.json
git commit -m "Ingest homepage refresh assets for Q2"
git push origin content/homepage-refresh-q2
```

The blocks are now in staging storage. The manifest is in version control. The PR is open for review.

**Step 2 — Validate in CI**

Your CI pipeline can validate the manifest structure automatically on every push:

```bash
bitchain validate homepage-refresh.bitchain.json
```

This catches malformed manifests, missing fields, or schema violations before they ever reach QA. It's a ten-second check that eliminates an entire class of "the image didn't load correctly" bugs that are otherwise maddening to diagnose in a staging environment.

**Step 3 — QA rebuilds from the manifest**

When the branch is ready for review, the staging environment rebuilds the assets directly from the manifest:

```bash
bitchain rebuild --bitchain homepage-refresh.bitchain.json \
                 --output-dir ./public/assets/current
```

QA is now reviewing against the exact files that were ingested — not a copy someone dragged into a shared drive, not whatever happened to be sitting in the staging bucket. If a reviewer spots a layout issue caused by an unexpected image dimension, you know with certainty which version of every asset was present when it occurred.

**Step 4 — Tag and promote to production**

Once the content is approved, the manifest gets merged and tagged alongside the code release:

```bash
git checkout main
git merge content/homepage-refresh-q2
git tag v4.1.0
git push origin v4.1.0
```

That tag now points to both the code and the content manifest. Anyone — a developer, a deployment pipeline, or a teammate revisiting this release six months later — can check out `v4.1.0` and run `bitchain rebuild` to get the exact set of assets that shipped with that version of the site. No archaeology required.

---

## What This Changes

The biggest shift isn't technical — it's operational. When assets follow the same branch-review-tag-release pattern as code, a few things get much easier:

**Rollbacks become real.** If `v4.2.0` ships with a broken hero image, rolling back isn't "find the old files in the staging bucket and hope the folder names make sense." It's `git checkout v4.1.0` followed by `bitchain rebuild`. The assets are as recoverable as the code.

**Environments stay in sync.** Development, staging, QA, and production each rebuild from a manifest. There's no drift, no "works on my machine," no guessing whether the right asset version made it into the right environment.

**Audits are straightforward.** Because every manifest is committed to Git, you have a complete history of which assets were part of which release, who merged them, and when. The kind of audit trail that's painful to reconstruct after the fact comes for free.

---

## Getting Started with bitchain

bitchain is open source under the Apache 2.0 license and available on GitHub at [github.com/dlockamy/bitchain](https://github.com/dlockamy/bitchain). It's built in Rust, so you'll need the Rust toolchain installed to build from source — if you don't have it, [rustup.rs](https://rustup.rs) gets you there in one command.

**Build from source:**

```bash
git clone https://github.com/dlockamy/bitchain.git
cd bitchain
cargo build --release
```

The compiled binary lands in `./target/release/bitchain`. Add it to your PATH and you're ready to go.

---

## Your First Ingest

The fastest way to see bitchain in action is a local ingest — no S3, no credentials, just a directory of files and a manifest on disk.

Pick any folder of binary files on your machine: a set of textures, a folder of images, a collection of audio files. Then run:

```bash
bitchain ingest --input ./my-assets \
                --output-dir ./blocks \
                --output my-assets.bitchain.json
```

In a few seconds you'll have two things: a `./blocks` directory containing the hashed block files, and `my-assets.bitchain.json` — the manifest that describes exactly how to put them back together. Open the manifest and take a look. The structure is intentionally readable.

To verify the round-trip, rebuild from the manifest into a new directory:

```bash
bitchain rebuild --bitchain my-assets.bitchain.json \
                 --output-dir ./restored
```

Compare `./my-assets` and `./restored` — they'll be identical, byte for byte.

---

## Adding S3 Storage

When you're ready to move blocks off local disk and into shared storage, swap in an `--uri-base` pointing at your S3 bucket. Run `bitchain --setup-config` first to store your AWS credentials:

```bash
bitchain --setup-config
```

The CLI will prompt for your AWS Access Key ID, Secret Access Key, region, and an optional session token. Credentials are saved to `~/.bitchain/config`. Then ingest as before, with your bucket as the destination:

```bash
bitchain ingest --input ./my-assets \
                --uri-base s3://your-bucket/your-prefix \
                --output my-assets.bitchain.json
```

Blocks are uploaded to S3 and the manifest URIs point there automatically. From this point, any machine with access to that bucket — your CI runner, a QA environment, a teammate's workstation — can rebuild the full asset set from the manifest alone.

---

## A Few Useful Flags to Know

Before you go, a handful of flags that will save you time:

`--dry-run` simulates an ingest without writing any files or uploading any blocks. Useful for checking that your inputs and URI base are correct before committing to a large upload:

```bash
bitchain ingest --input ./my-assets \
                --uri-base s3://your-bucket/your-prefix \
                --dry-run
```

`--block-size` lets you tune the block size in bytes if the 1MB default doesn't suit your asset profile. Larger blocks mean fewer URIs per file; smaller blocks give finer-grained deduplication:

```bash
bitchain ingest --input ./my-assets \
                --block-size 4194304 \
                --output my-assets.bitchain.json
```

`bitchain show` prints any manifest to stdout — handy for a quick inspection without opening the file manually:

```bash
bitchain show my-assets.bitchain.json
```

---

## What's Next

bitchain is a foundation. The manifest format is stable and versioned, the Apache 2.0 license means you can build on it freely, and because blocks are stored at plain URIs, the storage layer is entirely under your control.

If you're managing game assets, website content, or any collection of binary files that deserves the same rigorous versioning your code already gets — give it a try. File issues, open PRs, and follow the project at [github.com/dlockamy/bitchain](https://github.com/dlockamy/bitchain).

Your assets have earned it.

---

## About the Author

Douglas Lockamy is a Senior DevOps Engineer with nearly 20 years in the software industry, more than a decade of which has been spent in the DevOps trenches — building pipelines, taming infrastructure, and finding better ways to ship software reliably. bitchain grew out of a real frustration: watching teams nail their code release process while their binary assets remained a chaotic afterthought. He builds in the open and welcomes issues, PRs, and conversation.

[GitHub](https://github.com/dlockamy) · [LinkedIn](https://www.linkedin.com/in/douglas-lockamy-49097b33/)
