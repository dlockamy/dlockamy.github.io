---
layout: post
title: "Hello World (Is this thing on)"
date: 2026-10-07
categories: [general]
tags: [social-media, automation, ai, github-actions, homelab, 3d-printing]
excerpt: "I've meant to document my homelab and 3D printing experiments on social media for years and never had the time. This post tests whether AI can fix my empty profiles. If you're reading it on Bluesky, Mastodon or LinkedIn, it worked."
author: Douglas Lockamy
ai_assisted: true
syndicate: [linkedin, bluesky, mastodon]
---

I've kept social media accounts around for most platforms for ages, always with the best of intentions to post, update and document my endless homelab and 3D printing experiments. I'm just always too heads down to take the time to write anything up, so the accounts sit empty.

Part of those experiments is finding useful jobs for AI. So let's see if it can finally fix my empty social media presence.

This post is the test. It opts in to being shared with one line of front matter. When I publish it, a GitHub Action waits for this page to go live, then shares the title, a short excerpt and a link to Bluesky, Mastodon and LinkedIn. If you found it on one of those, the pipeline works.

The credentials are kept separate from my real logins. Bluesky takes an app password and Mastodon takes an access token from a small app I registered. LinkedIn is the awkward one: a small app there gets a token that lasts 60 days and cannot be refreshed automatically, so I have to re-authorise it by hand every couple of months. The Action checks it weekly and opens an issue before it lapses. The [setup notes](https://github.com/dlockamy/dlockamy.github.io/blob/master/.github/SYNDICATION.md) are public if you want to see how it hangs together.

What to expect from here is the same as before: build logs on Jenkins and CI/CD, Terraform, Rust, the homelab, and lately CAD and 3D printing. There is no schedule. Most of these posts are drafted with AI help and labelled that way, this one included. The AI drafts, and I decide what goes out.

If something looks off, like a broken link card, a duplicate, or a post that shows up on one platform and not another, that is exactly what this test is for.
