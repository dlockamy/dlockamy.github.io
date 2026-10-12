---
layout: post
title: "What Local AI Can and Can't Do"
date: 2026-10-11
categories: [ai]
tags: [ai, local-llm, privacy, homelab, rust, testing]
excerpt: "I spent a week testing which jobs a small AI model on my own machine can do, and which still need Claude. Everyday tasks stay home. Hard debugging doesn't."
author: Douglas Lockamy
ai_assisted: true
syndicate: [linkedin, bluesky, mastodon]
---

![Six requests flow as glowing teal lines into a warmly lit house with a padlock on it, while a dim cloud sits unconnected in the top corner.](/images/local-ai-stays-home.jpg)

I want my household's AI to run on my own hardware, and only call a cloud model when it has to. So I spent a week finding out what that actually costs.

**Everyday jobs work fine at home.** On 50 household-style tasks (triage, lookups, reminders), a 12B model on my graphics card got 49 right. A tiny 3B model got 43.

**Hard debugging doesn't.** I gave 13 local models a 3D rendering bug with a known fix and checked each answer by running it. None found the exact fix. The best got the direction right and the amount wrong. Claude Opus nailed it three times out of three.

**Settings can change the result.** A model a Reddit thread recommended (I tested Ollama's default build, not the thread's exact one) found the bug's mechanism 4 times out of 5 at a low temperature, then 0 out of 5 at its own default. Most other models barely moved, so this isn't a general rule, just a reason to test your own settings.

**A router gets most of the benefit.** I replayed 76 tasks through different policies. The 12B model alone scored 95%. Letting it hand the failures to Claude scored 97%, and only 2 of the 76 went to the cloud. Keeping the household data local cost nothing I could measure at 12B, and about 8 points at 3B.

![Three charts of the test results. Everyday tasks, correct out of 50: Llama 3.2 3B 43, Qwen 3.6 35B 48, Gemma 4 12B 49, Claude 49 to 50. Hard debugging: Claude Opus found the exact fix in 3 of 3 runs, no local model did, the best local model (Gemma 4 26B) had the right direction but the wrong amount in 5 of 5, and Qwen 3.8 27B went from 4 right-direction runs at low temperature to 5 wrong runs at its own defaults. Routing, 76 mixed tasks: with a 3B local model, 71% alone, 84% with Claude as a fallback (10 tasks to Claude) and 91% sending everything but household data to Claude (26 tasks); with a 12B local model, 95%, 97% (2 tasks) and 99% (26 tasks).](/images/tests-at-a-glance.png)

The part I care about most is the rule that nothing leaves the house by default. Content carries a label saying whose it is, and a provider only sees it if a rule allows it. I tested that by trying to break it, then ran the real thing: a private note went to a local model and the cloud provider was never called.

**What I haven't tested.** The Anthropic and Gemini connections have only run against mocks, because I haven't used a real key yet. The 76 tasks are a small sample, run once each, and I wrote the task classifier while looking at them, so treat the percentages as a direction, not a benchmark.

The image above was made on the same machine by a local image model.
