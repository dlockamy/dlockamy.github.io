---
layout: post
title: "One click, thirty red builds, and a release that shipped two-week-old bytes"
date: 2026-08-23
categories: [quickring, devops]
tags: [quickring, dart, flutter, docker, jenkins, ci-cd, jellyfin]
excerpt: "The goal today was a one-click Jellyfin install in Quickring. Getting there meant first admitting that CI had been red for about thirty builds, that the release pipeline had been shipping two-week-old bytes under a fresh version number, and that the feature I'd already worked on three times had never actually been one-click at all."
author: Douglas Lockamy
ai_assisted: true
---

The thing I set out to finish today was small and legible: let someone
add Jellyfin to their Quickring gateway in one click. Pick it from the
catalog, tap install, wait, done. No terminal, no compose file, no
typing an IP address into a box and hoping.

It shipped. But it only shipped because two layers of infrastructure
underneath it got fixed first, and that ordering isn't incidental — it's
the whole story. I couldn't trust a green test suite until CI was
actually running, and I couldn't trust a release until the release
pipeline stopped lying about what was in it. The feature was the last
act, not the first.

## Act one: thirty red builds, stacked like sediment

Courier's `main` had been red for something like thirty consecutive
builds. Not "flaky," not "the mac agent is offline" — genuinely,
consistently failing, for long enough that people had stopped reading
the notification.

The root cause turned out to be three failures stacked on top of each
other, and they had to be peeled off in order, because each one was
hiding the next.

**First, `dart format`.** A couple of files didn't match what CI's
formatter wanted. Easy. Except my first fix was wrong — I formatted
against the wrong `dart_style` config, which produced output that was
locally clean and remotely still red. That took a second PR to correct,
which is embarrassing in exactly the way that's worth writing down: the
first attempt *looked* like it worked, right up until CI disagreed.

**Second, an import path that had been broken for weeks.** With
formatting finally passing, the pipeline got far enough to run
`flutter analyze` — and immediately failed on a wrong relative import in
`lib/src/testing/e1_test_helpers.dart`. That import had been broken
since QR-141/147. It had been sitting there, silently, for weeks.

The reason nobody caught it is the interesting part. The format stage
runs before the analyze stage and short-circuits the pipeline on
failure. So for as long as formatting was broken, `flutter analyze`
never ran *at all*. The build was red for a reason that was true but
shallow, and the moment I fixed the shallow reason, a deeper one that
had been there far longer surfaced instantly. Red builds don't queue
failures politely; they mask them.

**Third, ninety-one more analyzer issues** once that import was fixed
and analyze could finally see the whole tree.

Worth calling out explicitly, because it caught me: this repo's
`flutter analyze` runs *without* `--no-fatal-infos`. That means it fails
the build on any diagnostic at all — info-level lints included, not just
errors. That's a defensible choice and I'm not changing it. But it does
mean "ninety-one issues" is not ninety-one bugs; it's ninety-one things
the analyzer had an opinion about, all of which are now build-breaking,
none of which anyone had seen because of the two failures above.

Cleared all three, and the build went green for the first time in a
long while. Which is when I made the mistake of trusting the next thing
in the chain.

## Act two: the release that shipped two-week-old bytes

With CI green, I cut `v0.1.36`. Two separate bugs in the release
pipeline turned up in the process, and neither of them announces
itself.

**Bug one: re-running the pipeline against an already-drafted version.**
The release job creates a draft GitHub Release. If you run it again for
a version that already has a draft sitting there, you don't get an
update — you get a *second* release for the same version. Worse, at the
moment that duplicate gets published, the git tag it's associated with
silently becomes `untagged-<hash>` instead of the version tag you
wanted. You end up with a published release that is not attached to the
tag it claims to be. Nothing errors. Nothing warns.

**Bug two: `gh release upload --clobber` reporting success without
actually replacing the asset bytes.** This is the one that stings. The
command exits zero. The Jenkins log says the upload succeeded. The
release page shows the asset with a fresh timestamp. Everything you
would normally look at says it worked.

I only caught it because I downloaded the actual "v0.1.36" artifact and
opened it. The `version.json` inside said **v0.1.29** — a build from
August 10th, roughly two weeks stale. The release was correctly named,
correctly dated, correctly reported, and full of the wrong software.

There's a lesson in there that I keep having to relearn: the Jenkins log
is a claim about the artifact, not the artifact. Checking the log tells
you the pipeline believes it succeeded. Checking the artifact tells you
whether it did.

I root-caused both, and then made a deliberate call not to fix them
today. They're in my backlog, and I want to be precise about what that
means: **they are not Jira tickets yet.** They're written down, they are
not tracked, and if I don't come back to them that's on me. The
workaround for today was to stop fighting the poisoned draft and cut a
fresh, version-bumped release instead — which is a workaround, not a
fix, and I'd rather label it that way than pretend the pipeline is
healthy.

## Act three: the one-click install that was never one click

Now the actual feature. And the first thing I had to accept is that
three prior rounds of work on this had left it *looking* finished
without being finished. The install flow existed. It ran. It did not do
what it said.

Two specific causes, neither previously caught:

- The catalog manifest for Jellyfin still said `provision: false`. So
  even a perfect client would have been told, correctly, not to
  provision anything.
- Courier's install screen had never called the real provisioning RPC.
  Not once. All it had ever done was write a local systemd unit pointed
  at an address the user typed in by hand. Which is a fine feature — it
  just isn't the feature, and the button said otherwise.

Then, while scoping the fix, a third one surfaced a layer down: the
gateway's `/services/resolve` only ever provisioned the *glue bridge*
container. It never provisioned the third-party service container
itself. So the thing that was supposed to stand up Jellyfin had, by
design, never been the thing that stood up Jellyfin.

And fixing *that* ran straight into real Docker networking. Once the
gateway was provisioning both containers, they couldn't reach each
other — the ports involved were bound to host loopback only, which
works fine from the host and not at all from a sibling container. The
answer was a shared user-defined Docker network so the two containers
resolve each other by name. Unglamorous, and the kind of thing that no
amount of application-layer correctness gets you around.

Three PRs, in dependency order, each tested independently before the
next one went in:

1. **`quickring/gateway` #29** — provision the service container, not
   just the glue. 147/147 tests passing, including a live Docker test
   that pulls Jellyfin, starts it, and asserts cross-container name
   resolution actually works. Not mocked. The whole point was that the
   mock is what had been lying.
2. **`quickring/service-catalog` #8** — flip the Jellyfin manifest to
   gateway-provisioned, start-only install, and delete the now-dead
   user-typed address field so nobody can reintroduce the old path.
3. **`quickring/courier` #62** — the install screen finally calls
   install, then resolve, then polls the job until it completes.
   380/380 tests.

That last suite is worth a note. I'd dispatched the Courier work to an
agent whose sandbox couldn't run the Flutter test suite at all. So I ran
it locally myself before merging, and it immediately turned up two real
bugs the agent had no way to see: a widget-finder ambiguity in the
tests, and a duplicate-notification bug in the actual install flow. Both
fixed before merge. An agent that can't run the tests isn't producing
tested code, no matter how confident the summary sounds — and the fix
for that is boring and mechanical, which is: run them.

`v0.1.37` went out carrying all three.

## The one I'm not calling done

A freshly-provisioned Jellyfin has no admin account. It comes up, it
runs, Quickring can see it and start and stop it — and its own setup
wizard is still sitting there unanswered.

That means the API-level glue features, library browsing chief among
them, still need a human to walk through Jellyfin's own first-run setup
and paste an API key back into Quickring. The install is one click. The
*integration* is one click plus a detour through somebody else's
onboarding flow.

I did not attempt to fix that today, and I want to be clear that it
wasn't an oversight. Auto-bootstrapping an admin account inside a third
party's application is a genuinely different and harder problem than
starting a container — it means driving another project's setup flow
programmatically, against an API surface that's explicitly designed to
be driven by a person, and owning that forever as they change it. It's
real scope. It's known, it's documented, and it's not done.

---

The honest shape of today: one feature shipped, and the majority of the
work had nothing to do with the feature. Two of the three acts were
just restoring the ability to tell whether anything works — a CI
pipeline that had been failing for so long it had stopped communicating
anything, and a release pipeline that was reporting success while
handing out two-week-old bytes.

I don't think that's a detour. A green build I don't trust and a release
I can't verify are worse than a red build, because a red build at least
tells you the truth. The feature only shipped cleanly because the boring
stuff underneath it broke first, loudly enough that I finally had to
look.
