#!/usr/bin/env bash
# Merge one armed PR on its publish day, then make sure the site rebuilds and the post is cross-posted.
# Run by .github/workflows/scheduled-publish.yml. Locally: DRY_RUN=1 GH_TOKEN=$(gh auth token) ./publish.sh
# DRY_RUN=1 (the default) only reads and says what it would do.
set -euo pipefail
cd "$(dirname "$0")/../.."
# shellcheck source=config.env
. .github/scheduled-publish/config.env
DRY_RUN="${DRY_RUN:-1}"
REPO="${GITHUB_REPOSITORY:-dlockamy/dlockamy.github.io}"
say() { echo "scheduled-publish: $*"; }
act() { if [ "$DRY_RUN" = 1 ]; then say "[dry run] would run: $*"; else "$@"; fi; }

info=$(gh pr view "$PR_NUMBER" --repo "$REPO" --json state,isDraft,labels,headRefName,mergeable,files)
state=$(jq -r .state <<<"$info")
if [ "$state" = MERGED ]; then say "PR #$PR_NUMBER is already merged. Nothing to do."; exit 0; fi
if [ "$state" != OPEN ]; then say "PR #$PR_NUMBER is $state, not open. Stopping."; exit 1; fi
if ! jq -e --arg l "$ARM_LABEL" '.labels[].name | select(. == $l)' <<<"$info" >/dev/null; then
  say "PR #$PR_NUMBER does not have the '$ARM_LABEL' label, so it is not armed. Nothing to do."; exit 0
fi
if [ -n "$REQUIRE_LIVE_URL" ]; then
  code=$(curl -s -o /dev/null -L -w '%{http_code}' "$REQUIRE_LIVE_URL" || true)
  if [ "$code" != 200 ]; then say "Part 3 is not live yet ($REQUIRE_LIVE_URL returned $code). Not publishing; the next scheduled run will try again."; exit 1; fi
  say "Part 3 is live ($REQUIRE_LIVE_URL returned 200)."
fi
posts=$(jq -r '.files[].path | select(startswith("_posts/"))' <<<"$info")
if [ "$(wc -l <<<"$posts" | tr -d ' ')" != 1 ] || [ -z "$posts" ]; then say "Expected exactly one file under _posts/ in the PR, found: ${posts:-none}. Stopping."; exit 1; fi
branch=$(jq -r .headRefName <<<"$info")
today=$(TZ="$PUBLISH_TZ" date +%F)
slug=$(basename "$posts" .md | cut -d- -f4-)
new="_posts/${today}-${slug}.md"
if [ "$posts" != "$new" ]; then
  say "Moving the post's date to $today: $posts -> $new"
  if [ "$DRY_RUN" != 1 ]; then
    git fetch -q origin "$branch"; git checkout -q -B "$branch" "origin/$branch"
    git mv "$posts" "$new"
    sed -i -E "0,/^date: .*/s//date: ${today}/" "$new"
    git -c user.name="scheduled-publish" -c user.email="actions@users.noreply.github.com" commit -q -am "post: date set to the publish day ($today)"
    git push -q origin "$branch"
  fi
fi
[ "$(jq -r .isDraft <<<"$info")" = true ] && act gh pr ready "$PR_NUMBER" --repo "$REPO"
act gh pr merge "$PR_NUMBER" --repo "$REPO" --squash --delete-branch
# Merges made with the Actions token do not start other workflows, so ask for the rebuild and the cross-post directly.
act gh api -X POST "repos/$REPO/pages/builds"
act gh workflow run syndicate.yml --repo "$REPO" --ref master -f post="$new" -f dry_run=false
say "Done. Post: https://dlockamy.com/posts/$(tr - / <<<"$today")/${slug}/"
