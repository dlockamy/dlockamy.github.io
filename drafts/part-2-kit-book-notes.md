# Part 2 ("What a Kit Is"): Kit Book revision notes

Working notes for `_posts/2026-10-26-what-a-kit-is.md` on branch
`draft/part-2-kit-book`. Excluded from the Jekyll build (`_config.yml`,
`exclude: drafts/`), so this file is never served. Written 2026-10-24.

Markers: **verified** = checked against the file, a recount, a test run or a
live request on 2026-10-24. **reported** = stated by a source file or by the
builder's own notes and not re-run here. **carried** = an account from DJ's
2026-10-19 draft (`32861b6`), kept as written and not re-checked.

Source shorthand:

- `AK` = `slash-builder/application-kit`, branch `public/release-prep`
  (`f88d406`), `README.md`
- `KB` = `slash-builder/kit-book` at `main` (`e94ff81`)
- `MAT` = vault `wiki/ideas/application-kit-blog-material-2026-10-24.md`
  (section 3, claim check)
- `REG` = vault `wiki/ideas/kit-registry-inconsistencies-2026-10-24.md`
- `P1` = `_posts/2026-10-19-where-an-os-idea-started.md`
- `D0` = the previous draft, `draft/part-2-what-a-kit-is` at `32861b6`

## A. Claim check

| # | Claim in the post | Source | Marker |
|---|---|---|---|
| 1 | Part 1 said the idea I never got over from BeOS was the Kit | `P1`, BeOS section | verified |
| 2 | A Kit named after a field of technology drew a request its rules forbade; it was renamed for what it owns | `D0`; vault `wiki/ideas/slashbuilder-kits-series-part-2-outline-2026-10-19.md` (the "AI Kit" rename) | carried |
| 3 | Every Kit has a written out-of-scope list; one line settled most placement arguments | `D0`; Kit Book cards carry "will not do" lines (`REG`, Mold Kit item) | carried |
| 4 | Stable interface, changed deliberately with a version | `D0` (a design rule, not a measurement) | carried |
| 5 | Products compose Kits and never fork them; gaps are filed against the Kit | `D0`; Kit model lock 2026-05-30 (blog repo `README.md`, Plans section) | carried |
| 6 | The more mature Kits have invariants backed by tests; not every Kit does | `D0`; `REG` (an entry's "invariants") | carried |
| 7 | Kits hold bytes, carry messages, know who someone is | `KB` `book/30-kits/README.md` taglines (storage, message, identity) | verified |
| 8 | The BeOS Kit I wanted first was the Application Kit (one of the BeOS Kits) | `P1` lists the Application Kit; `MAT` section 2 | verified |
| 9 | The name is provisional, echoes BeOS, not checked against existing product names | `AK` Status note | verified |
| 10 | Every app re-solved files, settings, test mode, who else is running, quitting | `AK` "The idea in one screen" | verified |
| 11 | The contract was written first, as a spec | `AK` ("One spec, `spec/APP-CONTEXT.md`, is the contract"); `MAT` section 2 | reported |
| 12 | Built twice, Dart and Rust, against one set of shared test cases | `AK` "What is in the box"; `MAT` row 1 | verified |
| 13 | Dart passed straight away; the same builder wrote the code and the tests | `MAT` section 2 and row 2 | reported |
| 14 | Rust passed the same tests yet disagreed on about a dozen things the tests never asked | `AK` ("about a dozen behaviours the first one had silently decided differently"); `MAT` row 2 (16 listed in `FINDINGS-rust.md`) | reported |
| 15 | Closing them took twenty more cases, for 61 in all | `MAT` row 2 (41 to 61); `AK` (61 fixtures). Recount: `spec/conformance/context_cases.json` 25 + `manifest_cases.json` 36 = 61. (The two `snapshot_*` files hold 36 more cases added later for the adopt API; the post's "61" is the shared Dart and Rust fixture set the README names.) | verified (count); reported (41 start) |
| 16 | Both implementations pass every one | Re-run 2026-10-24 on an archive of `f88d406`: Dart `test/conformance_test.dart` "+61: All tests passed"; Rust `tests/conformance.rs` 2 passed, 0 failed (the two tests iterate the case files) | verified |
| 17 | Six apps: calculator, minesweeper, notepad, stopwatch, a queue of pretend jobs, a launcher | `KB` `README.md`; `apps/` (render-queue is the queue) | verified |
| 18 | Each app's `main.dart` is 5 to 11 lines | `wc -l apps/*/lib/main.dart` in `KB`: 5, 5, 5, 10, 11, 9 | verified |
| 19 | Helper code: 727, then 330, then 777 after coordination, then 164 | `KB` `book/20-guides/demo-apps.md` lines 290 to 311; `AK` "Results at a glance". 164 recomputed (`wc -l` of the six apps' `lib/kit_gaps/*.dart`) | verified (164); reported (727, 330, 777) |
| 20 | The jump to 777 came from three apps writing the same helpers | `MAT` row 3 (three files byte-identical, checked with `diff`); `demo-apps.md` line 311 | reported |
| 21 | The Kit finds other copies and carries messages without reading them | `AK` ("It never reads a payload") | verified |
| 22 | Each app writes five small methods | `AK` hook example (`channel`, `hello`, `admit`, `onPeer`, `onMessage`) | verified |
| 23 | Plenty for the stopwatch and the handoff, only just enough for live play | `AK` ("enough for a signal and a handoff, and only just enough for live play") | reported (builder's judgement) |
| 24 | For the notepad, a thin shell around about 700 lines of app code | `AK` ("a 22-line shell around about 700 lines of app code") | reported |
| 25 | Grow next: acknowledgements, large transfers, catching up a late arrival | `AK` (no acknowledgement, large transfer, replay); `MAT` row 7 | reported (the "next" is an opinion) |
| 26 | A seventh app: Flutter UI over a Rust core, using the Application Kit's Rust side and the Kit that holds bytes | `KB` `apps/notes_rust/README.md` (Application Kit `adopt` API, Storage Kit) | verified |
| 27 | In a test on macOS, a one-byte edit of a 10 MiB note synced to a second copy moved 0.46% | `KB` `apps/notes_rust/README.md`, Measurements: "one byte changed: 48,395 bytes (0.46%)", `integration_test`, macOS debug, 2026-10-24 | reported (not re-run) |
| 28 | Not verified: other machines, a real network, a Linux window, release builds | `AK` Limits; `KB` `apps/notes_rust/README.md` Limits | verified (that they are listed as not verified) |
| 29 | Differently briefed AI reviewers (data modeler, security engineer) find different problems | `D0` | carried |
| 30 | Mutation testing has found real bugs in code I'd have called finished | `D0` | carried |
| 31 | Generating a card for every Kit showed registry entries disagreeing with their repositories: one claims a language its repo lacks; others marked design have skeleton code with tests | `REG`, "Status that disagrees with the repository" (Manifest Kit; Platform, Device, Score, App Store). No Kit is named in the post | verified (by `REG`, from repository trees) |
| 32 | The cards are generated, so fixing the registry fixes them | `REG` header; `KB` `book/30-kits/README.md` ("generated from the registry") | verified |
| 33 | The Kit Book is a documentation site in the spirit of the Be Book | `KB` `README.md` "About the book"; `Makefile` (`SITE_DOMAIN ?= kits.slashbuilder.com`) | verified (content); **site not live** (see B) |
| 34 | A status card for every registry Kit, 19, public or not | `KB` `book/30-kits/README.md` ("19 Kits", generated from registry `389c4a5`) | verified |
| 35 | The cards say which are real code and which are design documents, as the registry records them | `KB` `book/30-kits/README.md` ("Has real code today", status sections) | verified |
| 36 | The Application Kit's reference pages are in the book; no other Kit has any yet | `KB` `README.md` Status note | verified |
| 37 | Demo apps and a Makefile that sets up, tests and builds them | `KB` `README.md`; `Makefile` (`setup`, `test-fast`, `apps`) | verified |
| 38 | The Application Kit's repository has a Limits section | `AK` "Limits" | verified (content); **repo private** (see B) |
| 39 | The Hearth specification was already public | `curl` 200 and `gh repo view slash-builder/hearth` = PUBLIC, 2026-10-24; linked from `D0` | verified |
| 40 | "They've started opening"; "What's real today" | DJ's direction of 2026-10-25 | **not true on 2026-10-24**: true only once B passes |

Removed from the old draft on purpose: the "planner" anecdote (it describes
another Kit's internals), "I'm not going to rank them in public until...",
"specifics come once opened", and "documentation that disagrees with itself
about how many Kits there are" (replaced by row 31).

## B. GO-LIVE checklist

State on 2026-10-24: `kits.slashbuilder.com` does not resolve (curl code 000);
`github.com/slash-builder/kit-book` and `github.com/slash-builder/application-kit`
both return 404 (both PRIVATE per `gh`); `github.com/slash-builder/hearth`
returns 200.

Each item must pass on publish day. If an item fails, use section C.

1. **The Kit Book site serves.** Expect `200`:

   ```sh
   curl -sS -o /dev/null -w '%{http_code}\n' https://kits.slashbuilder.com/
   curl -sS https://kits.slashbuilder.com/ | grep -o '<title>[^<]*</title>'   # expect The Kit Book
   curl -sS -o /dev/null -w '%{ssl_verify_result}\n' https://kits.slashbuilder.com/   # expect 0 (valid certificate)
   ```

2. **The Kit Book repository is public.** Expect `200` and `PUBLIC`:

   ```sh
   curl -sS -o /dev/null -w '%{http_code}\n' https://github.com/slash-builder/kit-book
   gh repo view slash-builder/kit-book --json visibility -q .visibility
   ```

3. **The Application Kit repository is public, under that name, with the
   public release on its default branch.** Expect `200`, `PUBLIC`,
   `application-kit`, `# Application Kit`, and a `## Limits` line:

   ```sh
   curl -sS -o /dev/null -w '%{http_code}\n' https://github.com/slash-builder/application-kit
   gh repo view slash-builder/application-kit --json visibility,name -q '.visibility + " " + .name'
   curl -sS https://raw.githubusercontent.com/slash-builder/application-kit/HEAD/README.md | head -1
   curl -sS https://raw.githubusercontent.com/slash-builder/application-kit/HEAD/README.md | grep -n '^## Limits'
   ```

   A redirect (301) from a renamed repository is not a pass: update the post.

4. **Hearth still serves.** Expect `200`:

   ```sh
   curl -sS -o /dev/null -w '%{http_code}\n' https://github.com/slash-builder/hearth
   ```

5. **The numbers still match the Kit Book** (it is regenerated from the
   registry). Expect `19 Kits`; if it changed, edit "19 of them":

   ```sh
   curl -sS https://raw.githubusercontent.com/slash-builder/kit-book/HEAD/book/30-kits/README.md | grep -o '^[0-9]* Kits:.*'
   ```

6. **The post's own links and image**, after a local build with
   `--unpublished` (see `CONTEXT.md`, build check):
   `_site/posts/2026/10/19/where-an-os-idea-started/index.html` and
   `_site/images/what-a-kit-is.png` exist, and the rendered page has been
   looked at (screenshot).
7. **Remove the two `<!-- GO-LIVE: ... -->` comments** (kramdown passes HTML
   comments into the page source) and the alternate-titles comment in the front
   matter.
8. **Remove `published: false`.** Decide `syndicate: true` separately (not set
   on purpose).
9. **DJ accepts what the linked pages say.** The post never names Venue, but
   the Kit Book `README.md`, its catalog, and the Application Kit `README.md`
   all name Venue as a provisional resource broker, and the catalog lists every
   registry Kit (including banked and pending ones). Linking makes those public
   too. Also decide `SITE_INDEXABLE` in the Kit Book `Makefile` (it is `0`,
   noindex, today).
10. **After publishing**, expect `200`:

    ```sh
    curl -sS -o /dev/null -w '%{http_code}\n' https://dlockamy.com/posts/2026/10/26/what-a-kit-is/
    ```

## C. Sentences that depend on DJ's pending decisions

**If the Kit is renamed.** "Application Kit" appears in the post seven times;
`grep -n "Application Kit" _posts/2026-10-26-what-a-kit-is.md` finds them all.
Also rewrite: "The Kit I wanted first from BeOS was the Application Kit" (the
BeOS link only holds if the new name still echoes it) and "The name is
provisional, because it echoes BeOS and I haven't checked it against existing
product names." If the name is ruled final, replace that sentence with: "The
name is settled, and yes, it's borrowed from BeOS."

**If the Kit Book is not public at publish time.** Delete the "Read the Kit
Book" line and the Kit Book bullet. If the repo is public but the site is not,
keep the bullet, change "a documentation site" to "a documentation repository",
and point the line at `https://github.com/slash-builder/kit-book`.

**If the Application Kit repo is not public at publish time.** Delete the "Read
the Application Kit" line and the repository bullet.

**If neither is public.** Also change the intro's "They've started opening, so
this version also shows one Kit in practice." to "They're about to open, so this
version also shows one Kit in practice.", retitle the section "The Kits are
about to open", replace "What's real today:" with "What's coming first:", and
drop "and the Kits starting to open" from the excerpt.

**Which other Kits are public.** "A few more Kits may follow. I'll name them
when they're ready." If DJ decides to open named Kits the same day, replace it
with one sentence naming them, each only if its repository returns 200.

**If the registry is fixed before publishing.** End the registry paragraph with
"Those entries have since been fixed, and the cards with them." instead of "The
cards are generated, so fixing the registry fixes them.", and drop ", as the
registry records them" from the Kit Book bullet.

## D. Social posts

All three end with the post URL, which is the one link guaranteed live once the
post is published. (Swap in `https://kits.slashbuilder.com` only if checklist
item 1 passes and DJ prefers it.)

**LinkedIn** (about 140 words)

> Part 2 of my series on the SlashBuilder Kits is up: what a Kit is.
>
> Five rules. A Kit is named for the thing it owns. It says what it will not do.
> It has a stable interface. Products compose Kits and never fork them. The more
> mature ones have invariants, each backed by a test.
>
> Then one Kit in practice: the Application Kit (the name is provisional). I
> wrote the contract first and had it built twice, in Dart and Rust, against one
> set of shared test cases. The second build found about a dozen things the
> first had decided silently. Six small apps went on top, and the helper code
> they wrote for themselves went 727, 330, 777, then 164 lines: the wrong way
> before the right way.
>
> What isn't verified yet is in the post too.
>
> https://dlockamy.com/posts/2026/10/26/what-a-kit-is/

**Bluesky** (287 characters with the link; limit 300)

> SlashBuilder Kits, Part 2: what a Kit is, and one built twice. The Application Kit got a written contract, then Dart and Rust builds against 61 shared test cases. The Rust one found about a dozen things the Dart one decided silently.
>
> https://dlockamy.com/posts/2026/10/26/what-a-kit-is/

**Mastodon** (469 characters with the link; limit 500)

> Part 2 of the SlashBuilder Kits series: what a Kit is.
>
> Five rules, then one Kit in practice. The Application Kit (provisional name) was specced first and built twice, in Dart and Rust, against 61 shared test cases. Six small apps on top. The helper code they wrote for themselves went 727, 330, 777, then 164 lines.
>
> Not verified yet: other machines, a real network, release builds.
>
> #BeOS #RustLang #Dart #Flutter
>
> https://dlockamy.com/posts/2026/10/26/what-a-kit-is/
