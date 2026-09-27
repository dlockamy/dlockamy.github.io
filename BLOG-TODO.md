# Blog TODO — queued posts

Captured 2026-07-25, updated 2026-09-27. All three items originally waited
on "the debug-and-deploy session actually running" before being written —
that gate has cleared for all three now, and for #2 the story changed shape
entirely since the note below was written. Status per item, below.

`_posts/2026-07-25-what-ive-been-building-july.md` covers all three at
summary depth already, so none of this is unpublished info — these are the
"now go deeper" follow-ups, now overdue on all three.

**2026-09-27 drop: two posts written, both dated 2026-09-27.** Item 2 is
done (see its status below). The second post
(`_posts/2026-09-27-the-bug-that-wasnt-a-2fa-prompt-working-as-reviewed.md`)
was not in this queue — it's the Keycloak operator step-up flow /
`access_token_lifespan` story from the same day, split out because it's a
diagnosis-correction post rather than an operational-debt one. Items 1 and 3
deliberately held back rather than shipped in the same drop.

## 1. Sol → Sirius: what actually happened when the naming convention met a real split

**Status (2026-09-27): ready to write.** Sirius is fully live — real ECS
services (Quickring's hub/API, Spec-Up's API, and, new since this note was
first drafted, the studio's shared Keycloak identity backend), a real ALB,
real RDS. Worth folding in as a beat: Sirius didn't stay a two-product
platform the way the original split assumed — Identity landed on it too,
for the same "customer-facing, not Sol's home network" reason as the
original two.

**Angle:** sequel to `2026-05-13-solar-system-homelab-naming.md`. That post
proposed the convention; this one is "did it survive contact with a real
architecture decision."

**Known beats to hit once it's deployed:**
- Why Sol's own "invisible when healthy" principle is *why* Sirius couldn't
  live there — not a hosting detail, a design constraint.
- The repo-split mechanics: what moved to `sirius/infra` (VPC, ALB core,
  ACM, ECS cluster, shared IAM) vs. what stayed product-owned (target
  groups, task defs, task roles) — and *why* that boundary, since it also
  answers "what triggers a redeploy" without a cross-repo webhook.
- The near-miss: an early pass would have relocated a VPC that's already
  live, holding the real EC2 instance — a `terraform state` mistake caught
  before it shipped. This is the strongest single beat in the whole post;
  don't bury it.
- Once deployed: what actually differed from the plan. There's always
  something — record it honestly, that's the whole value of writing this
  after rather than before.

## 2. Zero-trust-lite for a home lab — built, killed three weeks later, and the landmine it left behind

**Status (2026-09-27): WRITTEN — shipped as
`_posts/2026-09-27-a-stale-comment-a-dead-include-and-every-vhost-on-the-box-down-at-once.md`.**
Written as the full arc, framed around the landing-page staleness pass that
triggered the apply, with the oauth2-proxy build/kill compressed into one
act rather than being the subject. The exclusion-list material from the
original how-to angle survives as a paragraph (Nexus's CLI surface is still
on JumpCloud LDAP for the identical reason it was on the oauth2-proxy
exclusion list) — so item 3's "same fix, same shape" cross-link beat is
still available and is now half-set-up.

<details>
<summary>Previous status (2026-09-27, before it was written)</summary>

**The whole story changed shape. This is a better, truer post than the one
originally queued — write it as the full arc, not the how-to below (kept
struck through for the record of what was planned).**

</details>

**Real arc, in order:**
1. Built oauth2-proxy as a reverse-proxy gate in front of Jenkins/Grafana/
   the landing page — Google OAuth SSO, the exclusion-list problem (Nexus's
   package clients, Docker registry vhosts, Jenkins's `/github-webhook/`
   and the MCP server's `/mcp-server/` path all can't complete a browser
   redirect) really did happen, roughly as planned below.
2. Killed it entirely ~6 weeks later (2026-09-07/08) — each admin surface
   grew its own Keycloak OIDC login instead, so the shared perimeter gate
   became redundant overhead rather than a real control. Replaced by
   per-service auth, no perimeter gate at all.
3. The removal deleted the `/opt/sol/nginx/snippets` volume mount from
   `sol-nginx`'s own container definition — but one vhost config
   (`beta-admin.softsurve.com.conf`, predating the teardown, owned by a
   module that's never actually finished deploying) still `include`d the
   now-gone snippet file. Nobody noticed, because nginx only checks config
   validity when it actually restarts, and `sol-nginx` hadn't been
   recreated since the teardown.
4. It sat armed for **weeks**. The landmine went off 2026-09-27, on a
   completely unrelated landing-page content deploy — `sol-nginx`
   crash-looped, taking down *every* `*.softsurve.com` vhost at once
   (Jenkins, Grafana, Nexus, the site itself). Root-caused live over SSH,
   fixed by applying a repair the codebase had already designed and
   reviewed but never actually shipped (a `deny all` fail-closed in place
   of the dead include).

**This is the real hook**: not "here's how to set up oauth2-proxy," but
"here's what a security control costs you after you decommission it if
nothing enforces that every consumer of it gets cleaned up with it." The
hazard doc that *predicted this exact failure*, almost to the letter,
already existed in the repo and just never got acted on — worth quoting
directly.

<details>
<summary>Original how-to angle (struck through, kept for the record)</summary>

**Angle:** practical how-to, same lane as the JCasC/Secrets-Manager/Nexus
posts — name the tool, the exact config, the gotcha.

**Known beats to hit once it's deployed:**
- Why the answer wasn't "just finish Tailscale" — SOF-5 has been "planned"
  since May; this shipped in the time it would have taken to keep waiting.
- The nginx `auth_request` mechanism itself — worth an actual config
  snippet once it's live and verified working, not just described.
- The exclusion list is the real content: Nexus's package-manager clients
  (Cargo/Dart/Maven), the Docker registry vhosts, and Jenkins's
  `/github-webhook/` path all had to stay ungated because none of them can
  complete a browser OAuth redirect.
- Whatever the real Google Cloud OAuth-client setup friction turns out to
  be (redirect URI, Workspace-internal consent screen) — write it from the
  actual experience, not the plan.

</details>

## 3. Turning Jenkins into an MCP server

**Status (2026-09-27): ready to write, two months overdue.** Confirmed
still live — `https://jenkins.softsurve.com/mcp-server/{mcp,sse,stateless}`,
deployed 2026-07-25, unchanged since. Long enough in production to actually
answer the post's own "what did this unblock" beat below with a real
example instead of a placeholder.

**Angle:** timely (MCP is a live topic), concrete plugin walkthrough with a
twist.

**Known beats to hit once it's deployed:**
- The correction story is the hook: asked to "add it to JCasC," turned out
  the plugin has no JCasC schema at all — Java system properties only. Good
  "the obvious answer was wrong" opener.
- The identity question — which Jenkins user/token an MCP client
  authenticates as — was deliberately left open rather than defaulted to
  the break-glass service account. Report what was actually decided.
- The twist: building this in the same batch as post #2 above meant hitting
  the identical "machine client can't do a browser OAuth redirect" problem
  twice in one sitting, for `/mcp-server/` this time instead of
  `/github-webhook/`. Same fix, same shape — worth naming the pattern
  explicitly once both posts exist, maybe with a cross-link.
- Once actually used for a while: what's it *for*, concretely? What did
  querying Jenkins via an AI client actually unblock, if anything real
  happened with it.
