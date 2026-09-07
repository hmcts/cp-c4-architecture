#!/usr/bin/env python3
"""Delivery metrics per CPP product area.

Takes the repo -> product -> subdomain -> product area mapping from the LikeC4
model (via the repo-teams-json generator), then reports three metrics per area:

  * Cycle time          median / p85 hours from a change's first commit to its
                        merge into the team branch
  * Change failure rate  share of changes that turned out to be corrective
  * Defect escape rate   share of defects that got past the pipeline into prod

GitHub (via the `gh` CLI) is the always-on source. Azure DevOps and Jira are
used automatically when their credentials are present, and give truer numbers
for the last two metrics -- see METRIC DEFINITIONS below.

Usage:
    python3 scripts/delivery_metrics.py --days 90
    python3 scripts/delivery_metrics.py --area "Court Hearing" --format json
    python3 scripts/delivery_metrics.py --by subdomain --format csv > metrics.csv

Environment (optional):
    AZDO_ORG, AZDO_PROJECT, AZURE_DEVOPS_EXT_PAT   -> pipeline-based failure rate
    JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN           -> Jira-based escape rate
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import os
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import median

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
CACHE_DIR = Path(
    os.environ.get("DELIVERY_METRICS_CACHE", REPO_ROOT / ".metrics-cache")
)

# A merged PR is counted as a "corrective change" (the numerator of the GitHub
# change-failure-rate proxy) when its title, branch or labels look like this.
CORRECTIVE_RE = re.compile(
    r"(^|\W)(revert|rollback|roll-back|hotfix|hot-fix|incident|prod(uction)?[ -]?(fix|issue|defect))(\W|$)"
    r"|^revert\s|^fix(\(|:|/)|^bugfix|^hotfix",
    re.IGNORECASE,
)
CORRECTIVE_LABELS = {"hotfix", "revert", "rollback", "incident", "production-defect"}

# Automated / housekeeping PRs: real work, but they would distort cycle time.
NOISE_RE = re.compile(
    r"^(bump up version|update pom versions?|bump |chore\(deps\)|update dependency|merge (main|master)\b)"
    r"|renovate|dependabot|snapshot version|version bump",
    re.IGNORECASE,
)
BOT_AUTHORS = {"renovate", "renovate[bot]", "dependabot", "dependabot[bot]", "github-actions[bot]"}

# Long-lived shared branches: release branches and the team/* integration branches
# CPP cuts for a release train. A PR *from* one of these into main is the release
# going home, not a change being delivered.
SHARED_BRANCH_RE = re.compile(r"^(team|release|rel|hotfix)[/-]|^develop$|^\d+\.\d+[.x]",
                              re.IGNORECASE)
# Trunk, and only trunk. `develop` is deliberately NOT here: the one repository that
# uses it (cp-case-document-knowledge-service) also merges `develop -> main`, so it is
# an integration branch playing the team-branch role, not the trunk. Treating it as
# trunk reported those changes as having reached main when they had not.
TRUNK_BRANCHES = {"main", "master"}

# ...and the same plumbing in the other direction, which is named rather than
# structured: "Dev/main rebase", "[CADB-3] Update with main", "Merge team/CCT-2488
# to Main", "Resolve merge conflict with main".
INTEGRATION_RE = re.compile(
    r"rebase"
    r"|merge[\s_/-]*(main|master)"
    r"|(main|master)[\s_/-]*(in)?to[\s_/-]*(team|release)"
    r"|merge[\s_/-]+(from[\s_/-]+)?(main|master)"
    r"|merge[\s_/-]+team[\s_/-]"
    r"|updat(e|ing|ed)[\s_/-]+with[\s_/-]+(main|master)"
    r"|(merge|changes)[\s_/-]+.{0,30}(in)?to[\s_/-]+main\b"
    r"|resolv\w*[\s_/-]+.{0,30}conflict"
    r"|release[\s_/-]*\d",
    re.IGNORECASE,
)

# Plumbing branches that carry code between long-lived branches but whose *names*
# do not start with team/ or release/, so SHARED_BRANCH_RE misses them: a snapshot
# copy of a branch, a scratch branch cut to raise a PR against a release, a
# forward-port of a release fix back onto main, a revert. Matched on the head branch
# name only. Found by inspecting the 464 changes that merge straight to trunk.
PLUMBING_BRANCH_RE = re.compile(
    r"^(copy[-_/]|tmp[-_/]|merge[-_/]|revert[-_/]|rel\d)"
    r"|^\d{4}[-_]main"
    r"|[-_/]main[-_]merge$",
    re.IGNORECASE,
)

# CPP work-item keys, e.g. SNI-9204, CHD-2227, CRA-43. Branch names throw off
# false positives ("bump-up-version-1" -> VERSION-1), so common branch and
# domain words are excluded, and the keys are validated against Jira when
# credentials are available.
JIRA_KEY_RE = re.compile(r"\b([A-Z][A-Z0-9]{1,9})-(\d+)\b")
NOT_JIRA_PROJECTS = {
    "VERSION", "REBASE", "RELEASE", "MERGE", "MAIN", "MASTER", "PATCH", "POM", "PR",
    "CONFLICTS", "JAVA", "CVE", "TO", "ERR", "ISO", "REVERT", "FIX", "HOTFIX", "DEV",
    "TEST", "UPDATE", "BUMP", "ADD", "WIP", "SNAPSHOT", "NODE", "NPM", "UI", "API",
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
    "PLEA", "HEARING", "RESULTS", "RESULTING", "NOWS", "SCHEDULING", "MAPPER", "SUPPORT",
    "STAGING", "DEFENCE", "DCS", "LIBRA01",
}


# --------------------------------------------------------------------------
# 1. The C4 model: repo -> product -> subdomain -> product area
# --------------------------------------------------------------------------

REPO_TEAMS_JSON = REPO_ROOT / "repo-teams.json"
# The generator itself decides the area names, so a change to it invalidates
# repo-teams.json every bit as much as a change to the model does.
MODEL_CONFIG = REPO_ROOT / "likec4.config.ts"


def load_repo_teams(regenerate: bool = True) -> list[dict]:
    """Read repo-teams.json, produced by the `repo-teams-json` LikeC4 generator.

    The generator walks the real model, so it picks up both `product` and
    `shared-component` owners and any nesting depth -- do not re-derive this by
    parsing the .c4 sources.
    """
    import subprocess

    sources = list(SRC_DIR.rglob("*.c4"))
    if MODEL_CONFIG.exists():
        sources.append(MODEL_CONFIG)
    stale = (
        not REPO_TEAMS_JSON.exists()
        or max((p.stat().st_mtime for p in sources), default=0)
        > REPO_TEAMS_JSON.stat().st_mtime
    )
    if stale and regenerate:
        proc = subprocess.run(
            ["npm", "run", "--silent", "generate:repo-teams"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 and not REPO_TEAMS_JSON.exists():
            raise SystemExit(
                "Could not generate repo-teams.json. Run `npm install && "
                f"npm run generate:repo-teams` in {REPO_ROOT}.\n{proc.stderr[-500:]}"
            )
        if proc.returncode != 0:
            warn("model regeneration failed; using the existing repo-teams.json")
    elif stale:
        warn("repo-teams.json is older than the model or its generator; "
             "run npm run generate:repo-teams")

    return json.loads(REPO_TEAMS_JSON.read_text())["repos"]


def build_repo_map(records: list[dict]) -> dict[str, dict]:
    """One entry per repo. A repo linked from several components keeps the first owner."""
    repos: dict[str, dict] = {}
    for r in records:
        key = f"{r['owner']}/{r['repo']}"
        if key in repos:
            repos[key]["components"].append(r["component"])
            continue
        repos[key] = {
            "owner": r["owner"],
            "repo": r["repo"],
            "area": r["area"],
            "product": r["product"],
            "product_title": r["productTitle"],
            "subdomain": r["subdomain"],
            "subdomain_title": r["subdomainTitle"],
            "components": [r["component"]],
        }
    return repos


# --------------------------------------------------------------------------
# 2. Small helpers
# --------------------------------------------------------------------------


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * pct
    lo, hi = int(pos), min(int(pos) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def rate(numerator: int, denominator: int) -> float | None:
    return round(100.0 * numerator / denominator, 1) if denominator else None


def cache_get(key: str, ttl_hours: float):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    f = CACHE_DIR / (hashlib.sha256(key.encode()).hexdigest()[:32] + ".json")
    if f.exists():
        age = (datetime.now(timezone.utc).timestamp() - f.stat().st_mtime) / 3600
        if age < ttl_hours:
            try:
                return json.loads(f.read_text())
            except json.JSONDecodeError:
                pass
    return None


def cache_put(key: str, value) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    f = CACHE_DIR / (hashlib.sha256(key.encode()).hexdigest()[:32] + ".json")
    f.write_text(json.dumps(value))


def warn(msg: str) -> None:
    print(f"warning: {msg}", file=sys.stderr)


# --------------------------------------------------------------------------
# 3. GitHub
# --------------------------------------------------------------------------

# Merged PRs are selected with the search API's `merged:` range rather than by
# paging repository.pullRequests. That connection can only be ordered by CREATED_AT
# or UPDATED_AT, never by merge date, so any rule for stopping the scan early is
# wrong: a PR merged long ago but commented on yesterday sorts to the top and hides
# the merges below it. Search filters on the field we actually want.
PR_QUERY = """
query($q:String!, $cursor:String) {
  search(query:$q, type:ISSUE, first:50, after:$cursor) {
    issueCount
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on PullRequest {
        number title mergedAt headRefName baseRefName
        mergeCommit { oid }
        author { login }
        labels(first:20) { nodes { name } }
        changesRequested: reviews(states:CHANGES_REQUESTED, first:1) { totalCount }
        firstCommit: commits(first:1) { nodes { commit { authoredDate committedDate } } }
        lastCommit: commits(last:1) { nodes { commit { statusCheckRollup { state } } } }
      }
    }
  }
}
"""

ISSUE_QUERY = """
query($owner:String!, $name:String!, $labels:[String!], $cursor:String) {
  repository(owner:$owner, name:$name) {
    issues(first:50, labels:$labels, orderBy:{field:CREATED_AT, direction:DESC}, after:$cursor) {
      pageInfo { hasNextPage endCursor }
      nodes { number title createdAt closedAt labels(first:20) { nodes { name } } }
    }
  }
}
"""


_PACE_LOCK = threading.Lock()
_LAST_CALL = [0.0]
MIN_CALL_INTERVAL = float(os.environ.get("GH_MIN_CALL_INTERVAL", "0.7"))


def _pace() -> None:
    """Space GitHub calls out across all worker threads.

    The secondary rate limit is a rate, not a quota, and it is not visible in
    `gh api rate_limit`. Once tripped it stays tripped while you keep knocking, so
    spacing requests up front is far cheaper than backing off afterwards.
    """
    with _PACE_LOCK:
        wait = MIN_CALL_INTERVAL - (time.monotonic() - _LAST_CALL[0])
        if wait > 0:
            time.sleep(wait)
        _LAST_CALL[0] = time.monotonic()


class RateLimited(RuntimeError):
    """GitHub asked us to slow down. Retried with backoff, never silently swallowed."""


def _is_rate_limited(text: str) -> bool:
    t = (text or "").lower()
    return "rate limit" in t or "secondary rate" in t or "abuse detection" in t


def gh_graphql_retry(query: str, variables: dict, partial_ok: bool = False,
                     attempts: int = 6) -> dict:
    """gh_graphql, but wait out a rate limit rather than losing the repository.

    A rate-limited run used to surface as a per-repository error, which the caller
    counted as "no changes" -- so a throttled backfill wrote a month of zeros into
    the history and looked like a real drop in delivery. Backing off is cheaper than
    explaining that later.
    """
    delay = 45.0
    for attempt in range(attempts):
        try:
            return gh_graphql(query, variables, partial_ok=partial_ok)
        except RateLimited:
            if attempt == attempts - 1:
                raise
            wait = delay + random.uniform(0, delay * 0.3)
            warn(f"rate limited; waiting {wait:.0f}s")
            time.sleep(wait)
            delay *= 2
    raise RateLimited("exhausted retries")


def gh_graphql(query: str, variables: dict, partial_ok: bool = False) -> dict:
    """Run a GraphQL query through `gh`.

    With `partial_ok`, a query that names several things tolerates some of them
    failing: GitHub answers with `data` holding nulls alongside `errors`, and a
    batched comparison should keep the branches it could resolve rather than lose
    the whole repository to one branch that has since been deleted.
    """
    import subprocess

    _pace()
    payload = json.dumps({"query": query, "variables": variables})
    proc = subprocess.run(
        ["gh", "api", "graphql", "--input", "-"],
        input=payload,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 and _is_rate_limited(proc.stdout + proc.stderr):
        raise RateLimited(proc.stderr.strip()[:200] or "rate limited")
    body = None
    if proc.stdout.strip():
        try:
            body = json.loads(proc.stdout)
        except json.JSONDecodeError:
            body = None
    if body is None:
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip()[:400] or "gh api graphql failed")
        raise RuntimeError("gh api graphql returned no body")
    if _is_rate_limited(json.dumps(body.get("errors", ""))):
        raise RateLimited(json.dumps(body["errors"])[:200])
    if partial_ok:
        if body.get("data"):
            return body["data"]
        raise RuntimeError(json.dumps(body.get("errors", "no data"))[:400])
    if proc.returncode != 0 and not body.get("data"):
        raise RuntimeError(proc.stderr.strip()[:400] or "gh api graphql failed")
    if "errors" in body and not body.get("data", {}).get("repository"):
        raise RuntimeError(json.dumps(body["errors"])[:400])
    return body["data"]


def fetch_prs(owner: str, name: str, since: datetime, until: datetime, ttl: float) -> list[dict]:
    key = f"prs:v3:{owner}/{name}:{iso(since)}:{iso(until)}"
    cached = cache_get(key, ttl)
    if cached is not None:
        return cached

    out: list[dict] = []
    cursor = None
    last = until - timedelta(seconds=1)
    q = (f"repo:{owner}/{name} is:pr is:merged "
         f"merged:{since.strftime('%Y-%m-%dT%H:%M:%SZ')}..{last.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    while True:
        data = gh_graphql_retry(PR_QUERY, {"q": q, "cursor": cursor})
        page = (data or {}).get("search")
        if not page:
            break
        if page.get("issueCount", 0) > 1000:
            warn(f"{owner}/{name}: {page['issueCount']} merged PRs in window; "
                 "search returns at most 1000 — narrow the window")
        for pr in page["nodes"]:
            if not pr:
                continue
            merged = parse_dt(pr["mergedAt"])
            if merged is None or merged < since or merged >= until:
                continue
            first = pr["firstCommit"]["nodes"]
            checks = pr["lastCommit"]["nodes"]
            out.append(
                {
                    "number": pr["number"],
                    "title": pr["title"] or "",
                    "branch": pr["headRefName"] or "",
                    "base": pr["baseRefName"] or "",
                    "mergeSha": ((pr.get("mergeCommit") or {}).get("oid") or ""),
                    "mergedAt": pr["mergedAt"],
                    "firstCommitAt": (first[0]["commit"]["authoredDate"] if first else None),
                    "labels": [l["name"] for l in pr["labels"]["nodes"]],
                    "author": ((pr.get("author") or {}).get("login") or ""),
                    "changesRequested": pr["changesRequested"]["totalCount"],
                    "checkState": (
                        (checks[0]["commit"].get("statusCheckRollup") or {}).get("state")
                        if checks
                        else None
                    ),
                }
            )
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    cache_put(key, out)
    return out


# --------------------------------------------------------------------------
# 3b. Time to main -- the second hop
# --------------------------------------------------------------------------
#
# A change is merged onto a team branch, and that branch later reaches main. Cycle
# time measures the first hop; time to main measures both, by pairing each feature
# with the moment its team branch landed. The pairing is by branch name, because
# nothing in the API links the two pull requests: a landing names the branch it
# integrates either structurally (`team/rv-2622 -> main`) or only in its title
# ("Merge team/CCT-2488 to Main").

TEAM_IN_TEXT_RE = re.compile(r"team[\s_/-]+([A-Za-z0-9][A-Za-z0-9._-]*)", re.IGNORECASE)


def branch_key(name: str) -> str | None:
    """Normalise a shared-branch name to something both sides of the pair agree on."""
    if not name:
        return None
    n = name.strip().lower()
    for prefix in ("refs/heads/", "origin/"):
        if n.startswith(prefix):
            n = n[len(prefix):]
    m = re.match(r"^(?:team|release|rel)[/-](.+)$", n)
    if m:
        n = m.group(1)
    n = n.strip("/-_")
    return n or None


def landed_branch_keys(pr: dict) -> list[str]:
    """The shared branches a PR into main appears to be integrating, best effort."""
    keys = []
    k = branch_key(pr.get("branch", "")) if SHARED_BRANCH_RE.match(pr.get("branch", "")) else None
    if k:
        keys.append(k)
    text = f"{pr.get('title','')} {pr.get('branch','')}"
    for m in TEAM_IN_TEXT_RE.finditer(text):
        k = branch_key(m.group(1))
        # "Merge team/CCT-2488 to Main" -> cct-2488; drop the trailing "to main" words
        if k and k not in ("to", "branch", "changes", "main", "master"):
            keys.append(k)
    return list(dict.fromkeys(keys))


def fetch_main_landings(owner: str, name: str, since: datetime, until: datetime,
                        ttl: float) -> dict[str, list[datetime]]:
    """When each shared branch reached main, as {branch key: [merge times, ascending]}.

    Scanned from the start of the reporting year to today, well past the reporting
    period, because a change merged in March may not reach main until September. The
    window is anchored rather than relative so a backfill asks each repository once
    instead of once per month. `base:main` keeps it small -- a few dozen pull requests
    per repository, not thousands.
    """
    key = f"landings:{owner}/{name}:{iso(since)}:{iso(until)}"
    cached = cache_get(key, ttl)
    if cached is not None:
        return {k: [parse_dt(t) for t in v] for k, v in cached.items()}

    out: dict[str, list[datetime]] = {}
    cursor = None
    last = until - timedelta(seconds=1)
    q = (f"repo:{owner}/{name} is:pr is:merged base:main "
         f"merged:{since.strftime('%Y-%m-%dT%H:%M:%SZ')}..{last.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    while True:
        data = gh_graphql_retry(LANDING_QUERY, {"q": q, "cursor": cursor})
        page = (data or {}).get("search")
        if not page:
            break
        for pr in page["nodes"]:
            if not pr:
                continue
            merged = parse_dt(pr["mergedAt"])
            if merged is None:
                continue
            norm = {"title": pr["title"] or "", "branch": pr["headRefName"] or "",
                    "base": pr["baseRefName"] or ""}
            if not is_integration(norm):
                continue
            for k in landed_branch_keys(norm):
                out.setdefault(k, []).append(merged)
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    for v in out.values():
        v.sort()
    cache_put(key, {k: [iso(t) for t in v] for k, v in out.items()})
    return out


# Landings only need to name a branch and a date. Reusing PR_QUERY here pulled a
# commit list and a review count for every pull request into main across a four-month
# lookahead, on every repository, for nothing -- enough to exhaust the hourly GraphQL
# budget on a six-month backfill.
LANDING_QUERY = """
query($q:String!, $cursor:String) {
  search(query:$q, type:ISSUE, first:100, after:$cursor) {
    pageInfo { hasNextPage endCursor }
    nodes { ... on PullRequest { title mergedAt headRefName baseRefName } }
  }
}
"""

COMPARE_QUERY_HEAD = """
query($owner:String!, $name:String!) {
  repository(owner:$owner, name:$name) {
"""
COMPARE_FIELD = """    %(alias)s: ref(qualifiedName:"main") {
      compare(headRef:%(head)s) { aheadBy behindBy }
    }
"""


def fetch_ahead_of_main(owner: str, name: str, refs: list[str], ttl: float) -> dict[str, int]:
    """How many commits each ref holds that main does not: {ref: aheadBy}.

    A ref may be a branch name or a commit SHA -- `compare` resolves either -- so the
    same call answers "has this branch reached main?" and the sharper question "is
    *this change* on main?". `aheadBy == 0` means fully contained in main.

    Asked as one aliased query per repository rather than one request per ref, and
    partial failures are kept: a single ref that no longer resolves would otherwise
    fail the whole batch. A ref that does not come back is absent from the result,
    and the caller must treat that as "unknown", never as "merged".
    """
    refs = sorted(set(b for b in refs if b))
    if not refs:
        return {}
    key = f"aheadofmain:{owner}/{name}:" + hashlib.sha1(",".join(refs).encode()).hexdigest()
    cached = cache_get(key, ttl)
    if cached is not None:
        return cached

    out: dict[str, int] = {}
    for i in range(0, len(refs), 20):
        chunk = refs[i:i + 20]
        fields = "".join(
            COMPARE_FIELD % {"alias": f"b{j}", "head": json.dumps(b)}
            for j, b in enumerate(chunk)
        )
        query = COMPARE_QUERY_HEAD + fields + "  }\n}\n"
        try:
            data = gh_graphql_retry(query, {"owner": owner, "name": name}, partial_ok=True)
        except Exception as exc:  # noqa: BLE001 - a bad ref should not sink the repo
            warn(f"{owner}/{name}: comparison against main failed ({exc})")
            continue
        repo = (data or {}).get("repository") or {}
        for j, b in enumerate(chunk):
            node = repo.get(f"b{j}") or {}
            cmp_ = node.get("compare") or {}
            if cmp_.get("aheadBy") is not None:
                out[b] = cmp_["aheadBy"]
    cache_put(key, out)
    return out


def time_to_main(pr: dict, landings: dict[str, list[datetime]],
                 ahead: dict[str, int], now: datetime) -> tuple[float | None, str]:
    """Hours from a change's first commit until it was on main, and how sure we are.

    Whether a change reached main is settled per change, by asking whether its own
    merge commit is contained in main -- not by trusting the name of the branch it
    sat on. When it is on main, the date comes from pairing its branch to the merge
    that carried it, which is name-based and does miss some; hence the split between
    a timed answer and an undateable one.

    States, kept apart because averaging them together would lie:

      measured        on main, and we know when it got there
      on_main_undated on main, but no merge into main names its branch, so there is
                      no date -- counted, never timed
      in_flight       its merge commit is not in main. The value returned is the
                      change's age so far: a lower bound, not a completed time
      branch_gone     neither the change's merge commit nor its branch can be
                      compared -- usually squashed away or a deleted fork
      unknown         no merge commit and no base branch to reason about
    """
    first, merged = parse_dt(pr.get("firstCommitAt")), parse_dt(pr.get("mergedAt"))
    if first is None or merged is None:
        return None, "unknown"
    if pr.get("base", "") in TRUNK_BRANCHES:
        pr["mainLandedAt"] = pr["mergedAt"]
        return max(0.0, (merged - first).total_seconds() / 3600), "measured"

    # Is this change on main? Prefer its own merge commit; fall back to its branch.
    contained = None
    for ref in (pr.get("mergeSha", ""), pr.get("base", "")):
        if ref and ref in ahead:
            contained = ahead[ref] == 0
            break
    if contained is None:
        return None, "branch_gone"

    if not contained:
        return (now - first).total_seconds() / 3600, "in_flight"

    k = branch_key(pr.get("base", ""))
    if k:
        for landed in landings.get(k, []):
            if landed >= merged:
                pr["mainLandedAt"] = iso(landed)
                return (landed - first).total_seconds() / 3600, "measured"
    return None, "on_main_undated"


def fetch_bug_issues(owner: str, name: str, since: datetime, until: datetime,
                     labels: list[str], ttl: float) -> list[dict]:
    key = f"issues:{owner}/{name}:{iso(since)}:{iso(until)}:{','.join(labels)}"
    cached = cache_get(key, ttl)
    if cached is not None:
        return cached

    out: list[dict] = []
    cursor = None
    while True:
        data = gh_graphql(
            ISSUE_QUERY, {"owner": owner, "name": name, "labels": labels, "cursor": cursor}
        )
        repo = (data or {}).get("repository")
        if not repo:
            break
        page = repo["issues"]
        stop = False
        for issue in page["nodes"]:
            created = parse_dt(issue["createdAt"])
            if created and created < since:
                stop = True
                break
            if created and created >= until:
                continue
            out.append(
                {
                    "number": issue["number"],
                    "title": issue["title"],
                    "createdAt": issue["createdAt"],
                    "labels": [l["name"] for l in issue["labels"]["nodes"]],
                }
            )
        if stop or not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    cache_put(key, out)
    return out


MODEL_TRUNK = "trunk-based"
MODEL_TEAM = "team-branch"
MODEL_UNKNOWN = "unclassified"
# Named for the branching behaviour, which is what is observed, not for the
# programme label. They mostly coincide -- Modern by Default services do trunk-based
# development -- but not always: cp-case-document-knowledge-service is an MbD service
# that runs a `develop` integration branch, so it is measured in the team-branch lane.
# Calling the lane "Modern by Default" would have filed it in the wrong one.
MODEL_TITLE = {MODEL_TRUNK: "Trunk-based, no integration branch",
               MODEL_TEAM: "Via an integration branch",
               MODEL_UNKNOWN: "Too few changes to classify"}
# A repo needs this many counted changes in the window before its branching
# behaviour is taken as evidence of anything. Below it, one quiet month would
# flip a team-branch repo into the trunk-based lane and flatter the migration.
MODEL_MIN_CHANGES = 5

# Dating a ticket's arrival on main needs a merge into main that names its branch,
# and most cannot be paired. Below this many timed tickets the median is one or two
# changes wearing a percentile's clothes, so it is withheld rather than published.
MIN_QUEUE_SAMPLES = 5


def delivery_model(prs: list[dict]) -> str:
    """Which delivery flow a repository is on, read from its own merges.

    Modern by Default services do trunk-based development with short-lived feature
    branches and a GitOps route to production: they never cut a team branch, so
    their merge into main IS the first hop. Legacy-flow repositories merge into a
    `team/*` branch first. That difference is directly observable, so it is read
    from the data rather than kept in a list that would go stale as repositories
    migrate.

    This matters because the two are NOT comparable on cycle time: it measures a
    shorter journey for a team-branch repo (first commit -> team branch) than for a
    trunk-based one (first commit -> trunk). Time to trunk is the comparable clock.
    """
    counted = [pr for pr in prs
               if pr.get("mergedAt") and not is_noise(pr) and not is_integration(pr)]
    if len(counted) < MODEL_MIN_CHANGES:
        return MODEL_UNKNOWN
    if any(SHARED_BRANCH_RE.match(pr.get("base", "")) for pr in counted):
        return MODEL_TEAM
    return MODEL_TRUNK


def classify_models(repos: dict[str, dict], since: datetime, until: datetime,
                    ttl: float, workers: int) -> dict[str, str]:
    """Read each repository's delivery model over the whole reporting year.

    A single month is far too thin to classify on: most repositories merge a handful
    of changes in a month, so the minimum-evidence guard would file nearly all of
    them as unclassified, and the few that squeaked past would flip lane month to
    month. The model is a property of the repository, not of the month, so it is read
    once over January-to-now and applied to every month in the run.

    The evidence is gathered from the same month-sized queries the monthly runs use,
    so a backfill pays for them once and every later run reads them from the cache.
    """
    months = []
    cursor = datetime(since.year, 1, 1, tzinfo=timezone.utc)
    horizon = max(until, datetime.now(timezone.utc))
    while cursor < horizon:
        nxt = (cursor.replace(year=cursor.year + 1, month=1) if cursor.month == 12
               else cursor.replace(month=cursor.month + 1))
        months.append((cursor, nxt))
        cursor = nxt

    def work(key: str) -> tuple[str, str]:
        meta = repos[key]
        prs: list[dict] = []
        for a, b in months:
            try:
                prs.extend(fetch_prs(meta["owner"], meta["repo"], a, b, ttl))
            except Exception:  # noqa: BLE001 - a thin year is a weaker verdict, not a failure
                pass
        return key, delivery_model(prs)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return dict(pool.map(work, list(repos)))


def jira_keys(pr: dict) -> list[str]:
    text = f"{pr['title']} {pr['branch']}".upper()
    return sorted({
        f"{m.group(1)}-{m.group(2)}"
        for m in JIRA_KEY_RE.finditer(text)
        if m.group(1) not in NOT_JIRA_PROJECTS
    })


def is_noise(pr: dict) -> bool:
    return pr.get("author", "").lower() in BOT_AUTHORS or bool(NOISE_RE.search(pr["title"]))


def is_integration(pr: dict) -> bool:
    """A PR that carries an already-counted change onward, rather than delivering one.

    CPP's flow is: feature branch -> team branch -> main -> cut a release branch for
    SIT -> go live. A change is measured once, on its first hop, where the work
    actually happened. Two later shapes are excluded:

      * the second hop, a `team/*` branch merged into main. The features on it were
        already counted when they merged into the team branch, so counting the hop
        again would double-count them -- and its first commit is the day the team
        branch was cut, so its elapsed time is that branch's age, not anyone's work.
        A release branch merged back to main is the same shape; it is cut from main
        purely to take a build through SIT, and main carries on immediately.
      * main brought back *into* a team or release branch -- a rebase, a back-merge,
        a conflict-resolution branch. Pure plumbing in either direction.

    Left in, a handful of these dominate the cycle-time tail: in Aug 2026 ten of them
    held 76% of Case Administration's total elapsed hours, and the 19 team->main hops
    that month carried between 20 and 137 days of branch age each.

    What this does NOT measure, as a result, is time-to-main -- see the README.
    """
    head, base = pr.get("branch", ""), pr.get("base", "")
    if SHARED_BRANCH_RE.match(head) and not SHARED_BRANCH_RE.match(base):
        return True          # release/team branch merging back to main
    if PLUMBING_BRANCH_RE.search(head) and base in TRUNK_BRANCHES:
        return True          # the same hop under a name the pattern above misses
    return bool(INTEGRATION_RE.search(pr["title"]) or INTEGRATION_RE.search(head))


def is_corrective(pr: dict) -> bool:
    if CORRECTIVE_LABELS.intersection({l.lower() for l in pr["labels"]}):
        return True
    return bool(CORRECTIVE_RE.search(pr["title"]) or CORRECTIVE_RE.search(pr["branch"]))


def caught_before_merge(pr: dict) -> bool:
    """A defect the pipeline or a reviewer caught before it could escape."""
    return pr["changesRequested"] > 0 or pr["checkState"] in {"FAILURE", "ERROR"}


# --------------------------------------------------------------------------
# 4. Azure DevOps (optional) -- true change failure rate from deployments
# --------------------------------------------------------------------------


def azdo_config() -> dict | None:
    org = os.environ.get("AZDO_ORG")
    project = os.environ.get("AZDO_PROJECT")
    pat = os.environ.get("AZURE_DEVOPS_EXT_PAT") or os.environ.get("AZDO_PAT")
    if not (org and project and pat):
        return None
    token = base64.b64encode(f":{pat}".encode()).decode()
    return {"org": org, "project": project, "auth": f"Basic {token}"}


def http_json(url: str, headers: dict, method: str = "GET", body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def fetch_azdo_builds(cfg: dict, since: datetime, until: datetime,
                      pipeline_re: re.Pattern, ttl: float) -> list[dict]:
    key = f"azdo:{cfg['org']}/{cfg['project']}:{iso(since)}:{iso(until)}"
    cached = cache_get(key, ttl)
    if cached is None:
        headers = {"Authorization": cfg["auth"], "Accept": "application/json"}
        base = f"https://dev.azure.com/{cfg['org']}/{cfg['project']}/_apis/build/builds"
        params = {
            "api-version": "7.1",
            "statusFilter": "completed",
            "minTime": iso(since),
            "maxTime": iso(until),
            "queryOrder": "finishTimeDescending",
            "$top": "1000",
        }
        cached = []
        token = None
        while True:
            q = dict(params)
            if token:
                q["continuationToken"] = token
            req = urllib.request.Request(
                f"{base}?{urllib.parse.urlencode(q)}", headers=headers, method="GET"
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                token = resp.headers.get("x-ms-continuationtoken")
                page = json.loads(resp.read().decode())
            for b in page.get("value", []):
                cached.append(
                    {
                        "definition": (b.get("definition") or {}).get("name", ""),
                        "result": b.get("result"),
                        "branch": b.get("sourceBranch", ""),
                        "repo": ((b.get("repository") or {}).get("name") or "").lower(),
                        "finishTime": b.get("finishTime"),
                    }
                )
            if not token:
                break
        cache_put(key, cached)

    return [b for b in cached if pipeline_re.search(b["definition"] or "")]


def azdo_repo_key(repo_name: str) -> str:
    return repo_name.split("/")[-1].lower()


# --------------------------------------------------------------------------
# 5. Jira (optional) -- true defect escape rate
# --------------------------------------------------------------------------


def jira_config() -> dict | None:
    url = os.environ.get("JIRA_URL")
    email = os.environ.get("JIRA_EMAIL")
    token = os.environ.get("JIRA_API_TOKEN")
    if not (url and email and token):
        return None
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    return {"url": url.rstrip("/"), "auth": f"Basic {auth}"}


def jira_count(cfg: dict, jql: str, ttl: float) -> int:
    key = f"jira:{cfg['url']}:{jql}"
    cached = cache_get(key, ttl)
    if cached is not None:
        return cached["total"]
    headers = {
        "Authorization": cfg["auth"],
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    try:
        body = http_json(
            f"{cfg['url']}/rest/api/3/search/approximate-count",
            headers,
            method="POST",
            body={"jql": jql},
        )
        total = int(body.get("count", 0))
    except urllib.error.HTTPError:
        body = http_json(
            f"{cfg['url']}/rest/api/2/search?{urllib.parse.urlencode({'jql': jql, 'maxResults': 0})}",
            headers,
        )
        total = int(body.get("total", 0))
    cache_put(key, {"total": total})
    return total


def jira_project_keys(cfg: dict, ttl: float) -> set[str]:
    """Every project key the credentials can see, used to drop false positives."""
    key = f"jira-projects:{cfg['url']}"
    cached = cache_get(key, max(ttl, 24.0))
    if cached is not None:
        return set(cached)
    headers = {"Authorization": cfg["auth"], "Accept": "application/json"}
    keys: list[str] = []
    start = 0
    while True:
        body = http_json(
            f"{cfg['url']}/rest/api/3/project/search?startAt={start}&maxResults=100", headers
        )
        keys.extend(v["key"] for v in body.get("values", []))
        if body.get("isLast", True) or not body.get("values"):
            break
        start += len(body["values"])
    cache_put(key, keys)
    return set(keys)


def jira_metrics(cfg: dict, product_cfg: dict, since: datetime, until: datetime,
                 ttl: float) -> dict | None:
    """product_cfg: {"jql": "<scope clause>", "escaped": "<optional override>"}"""
    scope = product_cfg.get("jql")
    if not scope:
        return None
    window = (f'created >= "{since.strftime("%Y-%m-%d")}" '
              f'AND created < "{until.strftime("%Y-%m-%d")}"')
    bug_types = product_cfg.get("bugTypes", 'issuetype in (Bug, Defect)')
    escaped = product_cfg.get("escaped") or 'labels in (escaped-defect, production-defect) OR environment ~ "prod"'
    total_jql = f"({scope}) AND {bug_types} AND {window}"
    escaped_jql = f"{total_jql} AND ({escaped})"
    total = jira_count(cfg, total_jql, ttl)
    esc = jira_count(cfg, escaped_jql, ttl)
    return {"total": total, "escaped": esc, "rate": rate(esc, total)}


# --------------------------------------------------------------------------
# 6. Confluence release pages (optional) -- true lead time, measured backwards
# --------------------------------------------------------------------------
#
# Everything above measures forwards: a change is merged, and we ask how long it
# took to get there. That view can only see work that has already merged, and it
# stops at main -- which, in a two-hop branching model, is nowhere near the user.
#
# The release manager keeps the other half of the answer. Every weekly release has
# a "Tech Focused" page under CROWN > Release Section carrying a go-live date, a
# dated milestone timeline, and -- in Section 2 -- the explicit list of GitHub PRs
# that shipped in it. Joining those PRs back to their first commit gives DORA lead
# time for changes end to end, with a real production date rather than a proxy.
#
# The catch, and it must be stated wherever the number is published: this cohort is
# every change that SHIPPED. Work still sitting on a team branch never appears on a
# release page, so this is a lower bound -- "how long it takes when it works", not
# "how long work takes". Read it next to reached_main_pct, never instead of it.

CONFLUENCE_RELEASE_ROOT = os.environ.get("CONFLUENCE_RELEASE_ROOT", "1360003823")
TECH_PAGE_RE = re.compile(r"tech\s*focused", re.IGNORECASE)
RELEASE_NO_RE = re.compile(r"\b(\d{2})\.(\d{2})(?:\.(\d{2}))?\b")
PR_URL_RE = re.compile(
    r"github\.com/([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+?)/pull/(\d+)", re.IGNORECASE)

MONTHS = {m.lower(): i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}

# "Go-Live Date  Tuesday 01 Sep 2026" / "18th April 2026" / "Go Live : 2026-04-04"
GOLIVE_ISO_RE = re.compile(r"Go[\s-]*Live[^|\n]{0,20}?(\d{4})-(\d{2})-(\d{2})", re.IGNORECASE)
GOLIVE_DMY_RE = re.compile(
    r"Go[\s-]*Live[^|\n]{0,30}?(?:\w+day\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\s+(\d{4})",
    re.IGNORECASE)
# Timeline fallback: header cells like "Sat [11-Apr]" or "Wed 08-Apr"
CELL_DATE_RE = re.compile(r"(\d{1,2})\s*-\s*([A-Za-z]{3})")
MILESTONES = {
    "scope_frozen": re.compile(r"scope\s*froz", re.IGNORECASE),
    "merge_to_master": re.compile(r"merge\s*to\s*master", re.IGNORECASE),
    "release_testing": re.compile(r"release\s*testing", re.IGNORECASE),
    "dry_run": re.compile(r"dry\s*run", re.IGNORECASE),
    "go_live": re.compile(r"go[\s-]*live", re.IGNORECASE),
}


def confluence_config() -> dict | None:
    """Server/DC personal access token, or Cloud email + API token."""
    url = os.environ.get("CONFLUENCE_URL")
    if not url:
        return None
    pat = os.environ.get("CONFLUENCE_PERSONAL_TOKEN")
    if pat:
        return {"url": url.rstrip("/"), "auth": f"Bearer {pat}"}
    user = os.environ.get("CONFLUENCE_USERNAME")
    token = os.environ.get("CONFLUENCE_API_TOKEN")
    if user and token:
        auth = base64.b64encode(f"{user}:{token}".encode()).decode()
        return {"url": url.rstrip("/"), "auth": f"Basic {auth}"}
    return None


def confluence_api(cfg: dict, path: str, **params) -> dict:
    url = f"{cfg['url']}/rest/api/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return http_json(url, {"Authorization": cfg["auth"], "Accept": "application/json"})


def confluence_children(cfg: dict, page_id: str, ttl: float) -> list[dict]:
    key = f"conf-children:{page_id}"
    cached = cache_get(key, ttl)
    if cached is not None:
        return cached
    out, start = [], 0
    while True:
        page = confluence_api(cfg, f"content/{page_id}/child/page", limit=100, start=start)
        rows = page.get("results", [])
        out += [{"id": r["id"], "title": r["title"]} for r in rows]
        if len(rows) < 100:
            break
        start += 100
    cache_put(key, out)
    return out


def confluence_body(cfg: dict, page_id: str, ttl: float) -> str:
    """Storage-format XHTML. Cached hard: a shipped release page stops changing."""
    key = f"conf-body:{page_id}"
    cached = cache_get(key, ttl)
    if cached is not None:
        return cached["body"]
    page = confluence_api(cfg, f"content/{page_id}", expand="body.storage,version")
    body = ((page.get("body") or {}).get("storage") or {}).get("value", "")
    cache_put(key, {"body": body, "version": (page.get("version") or {}).get("number")})
    return body


TIME_TAG_RE = re.compile(r"<time[^>]*\bdatetime=\"(\d{4}-\d{2}-\d{2})\"[^>]*/?>", re.IGNORECASE)


def _strip_tags(xhtml: str) -> str:
    text = re.sub(r"<!\[CDATA\[.*?\]\]>", " ", xhtml, flags=re.DOTALL)
    text = TIME_TAG_RE.sub(r" \1 ", text)
    text = re.sub(r"</t[dh]>", " | ", text)
    text = re.sub(r"</tr>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"[ \t]+", " ", text)


def release_year(release_no: str) -> int:
    return 2000 + int(release_no.split(".")[0])


def parse_timeline(text: str, year: int) -> dict[str, date]:
    """The milestone table: header row of dates, body rows of milestone names.

    Cells are matched by column index, so a merged cell in the body row would shift
    the mapping -- which is why only rows whose cell count matches the header are
    trusted.
    """
    rows = [[c.strip() for c in line.split("|")] for line in text.split("\n")]
    for i, header in enumerate(rows):
        dates = [CELL_DATE_RE.search(c) for c in header]
        if sum(1 for d in dates if d) < 5:
            continue
        found: dict[str, date] = {}
        for body in rows[i + 1:i + 4]:
            # Merged cells make the milestone row shorter than the header. When the
            # counts agree every milestone can be trusted; when they do not, only the
            # last one can -- go-live is always the final column, so aligning from the
            # right still places it correctly while the earlier names would drift.
            exact = len(body) == len(header)
            pairs = (list(enumerate(body)) if exact else
                     [(len(header) - k, body[len(body) - k])
                      for k in range(1, min(len(header), len(body)) + 1)])
            for j, cell in pairs:
                if not (0 <= j < len(dates)) or not dates[j]:
                    continue
                day, mon = dates[j].group(1), dates[j].group(2).lower()
                if mon not in MONTHS:
                    continue
                for name, pattern in MILESTONES.items():
                    if not exact and name != "go_live":
                        continue
                    if name not in found and pattern.search(cell):
                        found[name] = date(year, MONTHS[mon], int(day))
        if found:
            return found
    return {}


def parse_release_page(page_id: str, title: str, xhtml: str) -> dict | None:
    m = RELEASE_NO_RE.search(title)
    if not m:
        return None
    release_no = ".".join(p for p in m.groups() if p)
    year = release_year(release_no)
    text = _strip_tags(xhtml)

    go_live = None
    iso_m = GOLIVE_ISO_RE.search(text)
    dmy_m = GOLIVE_DMY_RE.search(text)
    if iso_m:
        go_live = date(int(iso_m.group(1)), int(iso_m.group(2)), int(iso_m.group(3)))
    elif dmy_m and dmy_m.group(2)[:3].lower() in MONTHS:
        go_live = date(int(dmy_m.group(3)), MONTHS[dmy_m.group(2)[:3].lower()],
                       int(dmy_m.group(1)))

    timeline = parse_timeline(text, year)
    if go_live is None:
        go_live = timeline.get("go_live")
    if go_live is None:
        return None

    prs = sorted({(o.lower(), r.lower(), int(n))
                  for o, r, n in PR_URL_RE.findall(xhtml)})
    return {
        "release": release_no,
        "page_id": page_id,
        "title": title,
        "go_live": go_live.isoformat(),
        "milestones": {k: v.isoformat() for k, v in timeline.items()},
        "prs": [list(p) for p in prs],
    }


def walk_release_pages(cfg: dict, since: datetime, until: datetime,
                       ttl: float) -> list[dict]:
    """Release Section -> Current Releases + Past Releases/<year>/<month> -> pages."""
    # A page that has already gone live is immutable in every way we care about, so
    # its body is cached for a week regardless of --cache-hours; the cheap tree walk
    # still honours the run's TTL so a new release is picked up the same day.
    body_ttl = max(ttl, 24.0 * 7)
    candidates: list[dict] = []

    def gather(node_id: str, depth: int) -> None:
        for child in confluence_children(cfg, node_id, ttl):
            title = child["title"]
            # The archive holds superseded copies of pages that also live under Past
            # Releases; walking both would count every change in them twice.
            if re.search(r"release\s*archive|business\s*focused|templates?$", title,
                         re.IGNORECASE):
                continue
            if TECH_PAGE_RE.search(title):
                candidates.append(child)
            elif depth < 3:
                gather(child["id"], depth + 1)

    gather(CONFLUENCE_RELEASE_ROOT, 0)

    releases, seen = [], set()
    for page in candidates:
        if page["id"] in seen:
            continue
        seen.add(page["id"])
        try:
            parsed = parse_release_page(
                page["id"], page["title"], confluence_body(cfg, page["id"], body_ttl))
        except Exception as exc:  # noqa: BLE001 - one bad page must not sink the run
            warn(f"release page {page['id']} ({page['title'][:40]}): {exc}")
            continue
        if not parsed:
            continue
        gl = datetime.fromisoformat(parsed["go_live"]).replace(tzinfo=timezone.utc)
        if since <= gl < until:
            releases.append(parsed)
    releases.sort(key=lambda r: r["go_live"])
    by_release: dict[str, dict] = {}
    for rel in releases:
        kept = by_release.get(rel["release"])
        # Same release number twice means a duplicate page; keep the fuller one.
        if kept is None or len(rel["prs"]) > len(kept["prs"]):
            by_release[rel["release"]] = rel
    return sorted(by_release.values(), key=lambda r: r["go_live"])


SHIPPED_PR_QUERY_HEAD = "query {\n%s\n}"
SHIPPED_PR_FIELD = """  %(alias)s: repository(owner:"%(owner)s", name:"%(name)s") {
    pullRequest(number:%(number)d) {
      title mergedAt baseRefName headRefName
      commits(first:1) { nodes { commit { authoredDate } } }
    }
  }"""


def fetch_shipped_prs(refs: list[tuple[str, str, int]], ttl: float) -> dict[tuple, dict]:
    """First-commit and merge dates for the PRs named on release pages.

    Batched by alias because the alternative is one HTTP call per PR, and a six-month
    backfill names a few thousand of them. Merged PRs never change, so the cache TTL
    is deliberately long.
    """
    pr_ttl = max(ttl, 24.0 * 30)
    out: dict[tuple, dict] = {}
    pending: list[tuple[str, str, int]] = []
    for ref in refs:
        cached = cache_get(f"shipped-pr:v2:{ref[0]}/{ref[1]}#{ref[2]}", pr_ttl)
        if cached is None:
            pending.append(ref)
        elif cached.get("mergedAt"):
            out[ref] = cached

    for start in range(0, len(pending), 25):
        batch = pending[start:start + 25]
        fields = "\n".join(
            SHIPPED_PR_FIELD % {"alias": f"p{i}", "owner": o, "name": n, "number": num}
            for i, (o, n, num) in enumerate(batch))
        try:
            data = gh_graphql_retry(SHIPPED_PR_QUERY_HEAD % fields, {}, partial_ok=True)
        except Exception as exc:  # noqa: BLE001
            warn(f"shipped PR batch failed: {exc}")
            continue
        for i, ref in enumerate(batch):
            node = (data.get(f"p{i}") or {}).get("pullRequest")
            record = {}
            if node:
                commits = (node.get("commits") or {}).get("nodes") or []
                record = {
                    "title": node.get("title", ""),
                    "mergedAt": node.get("mergedAt"),
                    "base": node.get("baseRefName", ""),
                    "branch": node.get("headRefName", ""),
                    # authoredDate, NOT committedDate. The flow rebases a team branch
                    # onto main immediately before merging, which rewrites every
                    # committedDate to the rebase. Read that way a change that took
                    # four months reports a lead time of nine days -- the release wait
                    # alone -- because its clock started at the rebase. authoredDate
                    # survives a rebase, so it still names when the work was done.
                    "firstCommitAt": commits[0]["commit"]["authoredDate"] if commits else None,
                }
            cache_put(f"shipped-pr:v2:{ref[0]}/{ref[1]}#{ref[2]}", record)
            if record.get("mergedAt"):
                out[ref] = record
    return out


# A team branch is squashed into a single commit when it is merged to main, so that
# PR carries exactly one commit, authored at the moment of the merge. Its oldest
# commit is then not the origin of the work -- it is the merge itself, and any clock
# started from it measures the release wait and calls it lead time. Where the gap
# between a PR's oldest commit and its merge is smaller than this, the PR has no
# history to measure and the change's origin is unknown.
SQUASHED_HISTORY_H = 12


def release_lead_times(releases: list[dict], ttl: float) -> dict[str, list[dict]]:
    """Per-repository lead-time records, keyed the same way as the repo map."""
    refs = sorted({tuple(pr) for rel in releases for pr in rel["prs"]})
    prs = fetch_shipped_prs([(o, n, int(num)) for o, n, num in refs], ttl)
    unresolved = len(refs) - len(prs)
    if unresolved:
        # Dead links on the release pages themselves. Reported so that a shrinking
        # sample is visible rather than quietly narrowing the cohort.
        warn(f"{unresolved} of {len(refs)} PR links on release pages did not resolve")

    # A release page states a PLANNED go-live date, and when a release slips the date
    # is not always corrected. A handful of PRs merging after it is normal -- they
    # simply shipped in a later release. MOST of them merging after it means the date
    # itself is wrong, and measuring against it would invent a negative wait.
    #
    # Dropping such a release loses a whole month: June 2026 has two main releases and
    # both carry a stale date, so lead time for the month disappeared entirely. So the
    # anchor is re-dated instead, from the cadence the trustworthy releases actually
    # show -- never from a guess at what the page meant to say:
    #
    #   estimate = last merge in the release + median(go-live - last merge)
    #
    # measured over the releases in this same window whose stated date IS consistent
    # with their merges, and capped a day short of the next trustworthy release. Every
    # record so dated is marked "estimated" and counted, so a reader can see how much
    # of a figure rests on a stated date and how much on an inferred one.
    dated: list[dict] = []
    for rel in releases:
        stated = datetime.fromisoformat(rel["go_live"]).replace(hour=18, tzinfo=timezone.utc)
        merges = [parse_dt((prs.get((o, n, int(x))) or {}).get("mergedAt"))
                  for o, n, x in rel["prs"]]
        merges = [m for m in merges if m]
        stale = bool(merges) and sum(1 for m in merges if m > stated) > len(merges) / 2
        dated.append({"rel": rel, "stated": stated, "last": max(merges) if merges else None,
                      "stale": stale})

    gaps = [(d["stated"] - d["last"]).total_seconds() / 3600
            for d in dated if not d["stale"] and d["last"]]
    gap_h = median(gaps) if gaps else 24 * 7

    for k, d in enumerate(dated):
        if not d["stale"]:
            d["go_live"], d["estimated"] = d["stated"], False
            continue
        if d["last"] is None:
            d["go_live"] = None
            continue
        est = d["last"] + timedelta(hours=gap_h)
        # A release cannot go live after the next one that has a date worth trusting.
        nxt = next((x["stated"] for x in dated[k + 1:] if not x["stale"]), None)
        if nxt is not None and est >= nxt:
            est = max(d["last"] + timedelta(hours=12), nxt - timedelta(days=1))
        d["go_live"], d["estimated"] = est, True
        warn(f"release {d['rel']['release']}: most changes merged after the stated "
             f"go-live ({d['rel']['go_live']}); re-dated to {est.date().isoformat()}, "
             f"the last merge plus the {round(gap_h / 24, 1)}-day median wait of the "
             f"releases whose dates hold up")

    by_repo: dict[str, list[dict]] = {}
    for d in dated:
        rel, go_live = d["rel"], d["go_live"]
        if go_live is None:
            warn(f"release {rel['release']}: stated go-live contradicted by its changes "
                 f"and no merge to re-date it from -- excluded")
            continue

        for owner, name, number in rel["prs"]:
            record = prs.get((owner, name, int(number)))
            if not record:
                continue
            first = parse_dt(record.get("firstCommitAt"))
            merged = parse_dt(record.get("mergedAt"))
            if first is None or merged is None or merged > go_live:
                continue  # merged after go-live: it shipped in a later release
            # Integration merges are NOT excluded here, unlike in the forward view.
            # There they would double-count a change already measured on its first
            # hop. Here the anchor is a production date, and a team-branch-to-main
            # merge is the hop that actually delivered the change -- its oldest
            # commit is the true origin. Dropping them would discard a quarter of
            # everything the release manager recorded as shipping.
            if is_noise(record):
                continue
            by_repo.setdefault(f"{owner}/{name}", []).append({
                "release": rel["release"],
                "goLive": go_live.isoformat(),
                "title": record.get("title", ""),
                "period": go_live.date().isoformat()[:7],  # the month it reached production
                "estimated": d["estimated"],
                "number": number,
                # False where the branch was squashed on the way to main: the change
                # shipped and its release wait is known, but when the work started is
                # not, so it cannot contribute a lead time.
                "traceable": (merged - first).total_seconds() >= SQUASHED_HISTORY_H * 3600,
                "leadH": (go_live - first).total_seconds() / 3600,
                "devH": (merged - first).total_seconds() / 3600,
                "releaseH": (go_live - merged).total_seconds() / 3600,
            })
    return by_repo


# --------------------------------------------------------------------------
# 7. Aggregation
# --------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Tickets, not pull requests
#
# A CPP feature is cut as a branch in EVERY repository it touches, so one piece
# of work arrives as N pull requests. Measured per PR, a feature that took a
# fortnight across four services reports as four short changes -- the per-PR
# median is 4.2h against 22.6h per ticket, and 235.5h for the multi-repo tickets
# that are the actual features. The unit of delivery is the ticket.
#
# A ticket is complete when its LAST repository lands, because until then there
# is no releasable artifact -- which is the programme's own criterion for
# merging to a team branch.
# ---------------------------------------------------------------------------

def ticket_id(pr: dict, repo_key: str) -> list[str]:
    """The ticket(s) a change belongs to, falling back to the change itself.

    A PR with no Jira key cannot be joined to its siblings, so it is treated as a
    single-repo ticket of its own. That is the conservative direction: it can only
    make the ticket-level number look shorter, never longer.
    """
    keys = jira_keys(pr)
    return keys if keys else [f"{repo_key}#{pr['number']}"]


def ticket_spans(repo_rows: dict[str, dict]) -> dict[str, dict]:
    """Fold every counted change into the ticket it belongs to, across all repos.

    Built once over the whole collection rather than per group, so a ticket that
    spans two product areas still gets its true span; it is then reported under
    every group it touches, with the same figures. Counting it once per group it
    touched would understate exactly the cross-cutting work that takes longest.
    """
    tickets: dict[str, dict] = {}
    for repo_key, row in repo_rows.items():
        if row.get("error"):
            continue
        for pr in row["prs"]:
            if is_noise(pr) or is_integration(pr):
                continue
            first, merged = parse_dt(pr.get("firstCommitAt")), parse_dt(pr.get("mergedAt"))
            if not (first and merged and merged >= first):
                continue
            landed = parse_dt(pr.get("mainLandedAt"))
            state = pr.get("timeToMainState", "unknown")
            for tid in ticket_id(pr, repo_key):
                t = tickets.setdefault(tid, {
                    "id": tid, "repos": set(), "prs": 0, "synthetic": "#" in tid,
                    "first": first, "last_merge": merged, "landed": landed,
                    "on_main": True, "timed": True, "corrective": False, "via_team": False,
                })
                t["repos"].add(repo_key)
                t["prs"] += 1
                t["first"] = min(t["first"], first)
                t["last_merge"] = max(t["last_merge"], merged)
                # Two separate questions, and collapsing them cost the metric its
                # sample: "is every repo of this ticket on main" (has it been
                # released) and "do we know when each got there" (can it be timed).
                # A change on main whose landing merge cannot be named is released
                # but untimed -- it belongs in the numerator of Released %, and
                # nowhere in the queue median.
                if state not in ("measured", "on_main_undated"):
                    t["on_main"] = False
                if landed is None:
                    t["timed"] = False
                elif t["landed"] is None or landed > t["landed"]:
                    t["landed"] = landed
                if SHARED_BRANCH_RE.match(pr.get("base", "")):
                    t["via_team"] = True
                if is_corrective(pr):
                    t["corrective"] = True
    for t in tickets.values():
        t["dev_h"] = (t["last_merge"] - t["first"]).total_seconds() / 3600
        # Queue time is the wait for a release slot, so it only exists for work that
        # goes through a team branch. A trunk-based service merges straight to main
        # and has no queue by construction -- scoring it as a zero would drag the
        # median of everyone else's wait to nothing, which is what it did.
        t["released"] = t["via_team"] and t["on_main"]
        t["queue_h"] = (((t["landed"] - t["last_merge"]).total_seconds() / 3600)
                        if t["released"] and t["timed"] and t["landed"] else None)
    return tickets


def collect(repos: dict[str, dict], since: datetime, until: datetime, args) -> dict[str, dict]:
    ttl = 0 if args.refresh else args.cache_hours
    results: dict[str, dict] = {}

    def work(key: str):
        meta = repos[key]
        row = {"repo": key, **meta, "error": None, "prs": [], "bugs": []}
        try:
            row["prs"] = fetch_prs(meta["owner"], meta["repo"], since, until, ttl)
        except Exception as exc:  # noqa: BLE001 - report and carry on
            row["error"] = str(exc)
        if row["error"] is None and not args.no_time_to_main:
            # Observation runs from the start of the reporting year to today, not from
            # the window: a change merged in March may only reach main in September.
            # Anchoring it makes the query identical for every month, so a backfill
            # asks for a repository's landings once rather than once per month.
            anchor = datetime(since.year, 1, 1, tzinfo=timezone.utc)
            horizon = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            try:
                landings = fetch_main_landings(meta["owner"], meta["repo"], anchor, horizon, ttl)
                measurable = [pr for pr in row["prs"]
                              if pr.get("base") not in TRUNK_BRANCHES
                              and not is_noise(pr) and not is_integration(pr)]
                # Only the change's own merge commit is compared. Adding its base branch
                # doubled the cost of the most expensive query for a fallback that a
                # present merge commit makes unnecessary.
                refs = [pr.get("mergeSha", "") for pr in measurable]
                ahead = fetch_ahead_of_main(meta["owner"], meta["repo"], refs, ttl)
                now = datetime.now(timezone.utc)
                for pr in row["prs"]:
                    pr["timeToMainH"], pr["timeToMainState"] = time_to_main(
                        pr, landings, ahead, now)
            except Exception as exc:  # noqa: BLE001
                row["error"] = str(exc)
        if not args.no_issues and row["error"] is None:
            try:
                row["bugs"] = fetch_bug_issues(
                    meta["owner"], meta["repo"], since, until, args.bug_labels, ttl
                )
            except Exception as exc:  # noqa: BLE001
                row["error"] = str(exc)
        return key, row

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for key, row in pool.map(work, list(repos)):
            results[key] = row
    return results


def aggregate(repo_rows: dict[str, dict], group_key: str, azdo_builds, jira_cfg, jira_map, since, until, ttl,
              jira_auto: bool = True, jira_min_keys: int = 3,
              lead_by_repo: dict[str, list[dict]] | None = None,
              tickets: dict[str, dict] | None = None):
    groups: dict[str, dict] = {}
    for key, row in repo_rows.items():
        repo_key = key  # `key` is shadowed by the Jira-key loop below
        gid = row[group_key] if group_key != "area" else row["area"]
        g = groups.setdefault(
            gid,
            {
                "id": gid,
                "title": row.get("group_title") or gid,
                "repos": [],
                "failed_repos": [],
                "cycle_hours": [],
                "cycle_hours_team": [],
                "cycle_hours_main": [],
                "ttm_hours": [],
                "ttm_inflight_hours": [],
                "ttm_on_main_undated": 0,
                "ttm_branch_gone": 0,
                "ttm_unknown": 0,
                "merged": 0,
                "corrective": 0,
                "caught": 0,
                "escaped": 0,
                "noise_prs": 0,
                "integration_prs": 0,
                "lead_hours": [],
                "lead_estimated": 0,
                "lead_untraceable": 0,
                "release_wait_hours": [],
                "jira_projects": {},
                "model_counts": {},
                "dev_hours": [],
                "queue_hours": [],
                "tickets": 0,
                "tickets_multi_repo": 0,
                "tickets_on_main": 0,
                "tickets_synthetic": 0,
                "tickets_via_team": 0,
                "_tickets": {},
            },
        )
        g["repos"].append(key)
        g["model_counts"][row.get("model", MODEL_UNKNOWN)] = (
            g["model_counts"].get(row.get("model", MODEL_UNKNOWN), 0) + 1)
        if row["error"]:
            g["failed_repos"].append(f"{key}: {row['error'][:80]}")
            continue
        for pr in row["prs"]:
            for key in jira_keys(pr):
                proj = key.split("-")[0]
                g["jira_projects"][proj] = g["jira_projects"].get(proj, 0) + 1
            if is_noise(pr):
                g["noise_prs"] += 1
                continue
            if is_integration(pr):
                g["integration_prs"] += 1
                continue
            merged, first = parse_dt(pr["mergedAt"]), parse_dt(pr["firstCommitAt"])
            if merged and first and merged >= first:
                hours = (merged - first).total_seconds() / 3600
                g["cycle_hours"].append(hours)
                # About one change in five does not merge into a team branch. Two
                # different things, and not the same as "a feature branch reaching
                # main", which the branching model does not permit: seven
                # Modern-by-Default services have no team branch at all, so their
                # merge into main IS hop one; the remainder are exceptions inside
                # repos that do use team branches, and look like release fixes
                # forward-ported. Reported apart -- see `direct_to_main_pct` and
                # the README.
                if SHARED_BRANCH_RE.match(pr.get("base", "")):
                    g["cycle_hours_team"].append(hours)
                elif pr.get("base", "") in TRUNK_BRANCHES:
                    g["cycle_hours_main"].append(hours)
            state = pr.get("timeToMainState", "unknown")
            if state == "measured":
                g["ttm_hours"].append(pr["timeToMainH"])
            elif state == "in_flight":
                g["ttm_inflight_hours"].append(pr["timeToMainH"])
            elif state == "on_main_undated":
                g["ttm_on_main_undated"] += 1
            elif state == "branch_gone":
                g["ttm_branch_gone"] += 1
            else:
                g["ttm_unknown"] += 1
            g["merged"] += 1
            if is_corrective(pr):
                g["corrective"] += 1
            if caught_before_merge(pr):
                g["caught"] += 1
        for shipped in (lead_by_repo or {}).get(repo_key.lower(), []):
            # The release wait is anchored on the merge and the go-live, both known
            # even for a squashed branch. Only the lead time needs an origin.
            g["release_wait_hours"].append(shipped["releaseH"])
            if not shipped.get("traceable", True):
                g["lead_untraceable"] += 1
                continue
            g["lead_hours"].append(shipped["leadH"])
            if shipped.get("estimated"):
                g["lead_estimated"] += 1
        g["escaped"] += len(row["bugs"])

    # Ticket-level segments. A ticket is attributed to every group it touches, so
    # cross-cutting work appears in each area's numbers rather than in none of them.
    repo_to_groups: dict[str, list[dict]] = {}
    for g in groups.values():
        for rk in g["repos"]:
            repo_to_groups.setdefault(rk, []).append(g)
    for t in (tickets or {}).values():
        for g in {id(x): x for rk in t["repos"] for x in repo_to_groups.get(rk, [])}.values():
            g["tickets"] += 1
            g["dev_hours"].append(t["dev_h"])
            g["_tickets"][t["id"]] = (t["dev_h"], t["queue_h"])
            if len(t["repos"]) > 1:
                g["tickets_multi_repo"] += 1
            if t["synthetic"]:
                g["tickets_synthetic"] += 1
            if t["via_team"]:
                g["tickets_via_team"] += 1
            if t["released"]:
                g["tickets_on_main"] += 1
            if t["queue_h"] is not None:
                g["queue_hours"].append(t["queue_h"])

    for g in groups.values():
        hours = g["cycle_hours"]
        g["cycle_time_median_h"] = round(median(hours), 1) if hours else None
        g["cycle_time_p85_h"] = round(percentile(hours, 0.85), 1) if hours else None
        g["cycle_time_samples"] = len(hours)
        g["_hours"] = hours
        team, direct = g["cycle_hours_team"], g["cycle_hours_main"]
        g["cycle_to_team_median_h"] = round(median(team), 1) if team else None
        g["cycle_to_team_p85_h"] = round(percentile(team, 0.85), 1) if team else None
        g["cycle_to_team_samples"] = len(team)
        g["cycle_to_main_median_h"] = round(median(direct), 1) if direct else None
        g["cycle_to_main_p85_h"] = round(percentile(direct, 0.85), 1) if direct else None
        g["cycle_to_main_samples"] = len(direct)
        g["direct_to_main_pct"] = (
            rate(len(direct), len(team) + len(direct)) if team or direct else None
        )
        # Measured backwards from a real go-live date, so this needs no censoring
        # treatment -- but it only sees changes that shipped. See section 6.
        lead = g["lead_hours"]
        g["lead_time_median_d"] = round(median(lead) / 24, 1) if lead else None
        g["lead_time_p85_d"] = round(percentile(lead, 0.85) / 24, 1) if lead else None
        g["lead_samples"] = len(lead)
        # How much of the lead time rests on a go-live date the release page stated,
        # and how much on one inferred from the cadence because the page's date was
        # contradicted by its own changes.
        g["shipped_estimated_dates"] = g["lead_estimated"]
        # Changes that shipped but whose branch was squashed on the way to main, so
        # their origin -- and with it their lead time -- is not recoverable from git.
        g["shipped_untraceable"] = g["lead_untraceable"]
        g["shipped_changes"] = len(lead) + g["lead_untraceable"]
        wait = g["release_wait_hours"]
        g["release_wait_median_d"] = round(median(wait) / 24, 1) if wait else None
        ttm = g["ttm_hours"]
        g["time_to_main_median_h"] = round(median(ttm), 1) if ttm else None
        g["time_to_main_p85_h"] = round(percentile(ttm, 0.85), 1) if ttm else None
        g["time_to_main_samples"] = len(ttm)
        # Changes whose branch has not reached main, or could not be paired to a
        # landing. Reported rather than hidden: a low coverage figure means the
        # median above describes only the part of the work that got through.
        # A change is in one of four states, and they are reported separately because
        # averaging them together would lie: "still on a team branch" is not a long
        # cycle time, it is unfinished integration.
        infl = g["ttm_inflight_hours"]
        g["in_flight_changes"] = len(infl)
        g["in_flight_median_age_h"] = round(median(infl), 1) if infl else None
        g["in_flight_p85_age_h"] = round(percentile(infl, 0.85), 1) if infl else None
        g["on_main_undated"] = g["ttm_on_main_undated"]
        g["branch_deleted"] = g["ttm_branch_gone"]
        g["time_to_main_unknown"] = g["ttm_unknown"]
        settled = len(ttm) + len(infl) + g["ttm_on_main_undated"]
        g["in_flight_pct"] = rate(len(infl), settled) if settled else None
        # The number that matters most, and the one the timed median cannot give:
        # of the changes we can place, what share had actually reached main.
        g["reached_main_pct"] = (
            rate(len(ttm) + g["ttm_on_main_undated"], settled) if settled else None
        )
        g["time_to_main_coverage_pct"] = rate(len(ttm), g["merged"])
        g["_ttm"] = ttm
        g["_inflight"] = infl
        # At repo level this is the repository's own model; above it, the mix. Both
        # are reported so a lane's composition is never implied by its label alone.
        mc = g.pop("model_counts")
        real = {k: v for k, v in mc.items() if k != MODEL_UNKNOWN}
        g["delivery_model"] = (next(iter(real)) if len(real) == 1
                               else ("mixed" if real else MODEL_UNKNOWN))
        g["trunk_based_repos"] = mc.get(MODEL_TRUNK, 0)
        # ---- the three segments, each with a different owner -----------------
        # dev    first commit in any repo -> last team-branch merge   (the team)
        # queue  last team-branch merge   -> on main                  (the release
        #        train: the weekly cadence and the 20-ticket cap)
        # deploy main -> go-live, already reported as release_wait_median_d
        dev, queue = g["dev_hours"], g["queue_hours"]
        g["queue_samples"] = len(queue)
        if len(queue) < MIN_QUEUE_SAMPLES:
            queue = []
        g["dev_time_median_h"] = round(median(dev), 1) if dev else None
        g["dev_time_p85_h"] = round(percentile(dev, 0.85), 1) if dev else None
        g["queue_median_h"] = round(median(queue), 1) if queue else None
        g["queue_p85_h"] = round(percentile(queue, 0.85), 1) if queue else None
        g["ticket_count"] = g["tickets"]
        g["multi_repo_pct"] = rate(g["tickets_multi_repo"], g["tickets"]) if g["tickets"] else None
        # Share of tickets whose every repository has reached main. Read beside the
        # queue median: that median describes only the tickets that got through.
        g["tickets_reached_main_pct"] = (rate(g["tickets_on_main"], g["tickets_via_team"])
                                         if g["tickets_via_team"] else None)
        # Tickets carrying no Jira key, which therefore could not be joined to their
        # siblings. High here means the ticket-level medians are understated.
        g["unjoined_ticket_pct"] = rate(g["tickets_synthetic"], g["tickets"]) if g["tickets"] else None
        g["_dev"] = dev
        g["_queue"] = queue
        g["change_failure_rate_pct"] = rate(g["corrective"], g["merged"])
        g["cfr_source"] = "github-corrective-prs"
        if g["escaped"]:
            g["defect_escape_rate_pct"] = rate(g["escaped"], g["escaped"] + g["caught"])
            g["der_source"] = "github-issues-vs-caught"
        else:
            # These teams track defects in Jira, not GitHub Issues, so an empty
            # issue list means "no data" rather than "no escaped defects".
            g["defect_escape_rate_pct"] = None
            g["der_source"] = "unavailable (no GitHub issues — needs Jira)"
        del g["cycle_hours"], g["cycle_hours_team"], g["cycle_hours_main"]
        del g["dev_hours"], g["queue_hours"]

    # Azure DevOps overrides the change failure rate where pipeline data exists.
    if azdo_builds is not None:
        by_repo: dict[str, list[dict]] = {}
        for b in azdo_builds:
            by_repo.setdefault(azdo_repo_key(b["repo"]), []).append(b)
        for gid, g in groups.items():
            total = failed = 0
            for key in g["repos"]:
                for b in by_repo.get(key.split("/")[-1].lower(), []):
                    if not re.search(r"/(main|master)$", b["branch"] or ""):
                        continue
                    total += 1
                    if b["result"] in {"failed", "canceled", "partiallySucceeded"}:
                        failed += 1
            if total:
                g["deployments"] = total
                g["failed_deployments"] = failed
                g["change_failure_rate_pct"] = rate(failed, total)
                g["cfr_source"] = "azure-devops-pipelines"

    # Jira overrides the defect escape rate for products configured in the map.
    if jira_cfg:
        try:
            known_projects = jira_project_keys(jira_cfg, ttl)
        except Exception as exc:  # noqa: BLE001
            warn(f"could not list Jira projects, auto-scoping unvalidated: {exc}")
            known_projects = None
        for gid, g in groups.items():
            product_cfg = jira_map.get(gid)
            if not product_cfg and jira_auto:
                # Derive the team's Jira scope from the project keys its PR
                # titles actually reference, e.g. "SNI-9204: ..." -> project SNI.
                projects = [
                    proj for proj, n in sorted(g["jira_projects"].items(), key=lambda kv: -kv[1])
                    if n >= jira_min_keys and (known_projects is None or proj in known_projects)
                ][:5]
                if projects:
                    product_cfg = {"jql": f"project in ({', '.join(projects)})", "auto": True}
            if not product_cfg:
                continue
            try:
                m = jira_metrics(jira_cfg, product_cfg, since, until, ttl)
            except Exception as exc:  # noqa: BLE001
                warn(f"jira lookup failed for {gid}: {exc}")
                continue
            if m and m["total"]:
                g["jira_defects"] = m["total"]
                g["jira_escaped"] = m["escaped"]
                g["defect_escape_rate_pct"] = m["rate"]
                g["der_source"] = "jira (auto-scoped)" if product_cfg.get("auto") else "jira"

    return groups


# --------------------------------------------------------------------------
# 7. Output
# --------------------------------------------------------------------------

LEVEL_LABEL = {"area": "Product area", "product": "Product", "subdomain": "Subdomain",
               "repo": "Repository", "model": "Delivery model"}

COLUMNS = [
    ("title", "Product area", 34),
    ("repos_n", "Repos", 6),
    ("merged", "PRs", 6),
    ("ticket_count", "Tickets", 8),
    ("dev_time_median_h", "Dev p50 (h)", 12),
    ("dev_time_p85_h", "Dev p85 (h)", 12),
    ("queue_median_h", "Queue p50 (h)", 14),
    ("tickets_reached_main_pct", "Released %", 11),
    ("direct_to_main_pct", "Direct %", 10),
    ("time_to_main_median_h", "To main p50 (h)", 16),
    ("reached_main_pct", "On main %", 11),
    ("lead_time_median_d", "Lead p50 (d)", 13),
    ("shipped_changes", "Shipped", 8),
    ("change_failure_rate_pct", "CFR %", 8),
    ("defect_escape_rate_pct", "Escape %", 9),
]


def fmt(value, width: int | None = None) -> str:
    text = "-" if value is None else (f"{value:g}" if isinstance(value, float) else str(value))
    if width and len(text) > width - 1:
        text = text[: width - 2] + "…"
    return text


def print_table(groups: dict[str, dict], since: datetime, until: datetime, period: str,
                sources: list[str], level: str = "area") -> None:
    columns = [((k, LEVEL_LABEL.get(level, label), w) if k == "title" else (k, label, w))
               for k, label, w in COLUMNS]
    rows = sorted(groups.values(), key=lambda g: (-(g["merged"]), g["title"]))
    print(f"\nCPP delivery metrics — {period} ({since:%Y-%m-%d} to {until:%Y-%m-%d})")
    print(f"Sources: {', '.join(sources)}\n")
    header = "".join(label.ljust(width) for _, label, width in columns)
    print(header)
    print("-" * len(header))
    for g in rows:
        g["repos_n"] = len(g["repos"])
        print("".join(fmt(g.get(k), w).ljust(w) for k, _, w in columns))
    print("-" * len(header))

    all_hours = [h for g in rows for h in g.get("_hours", [])]
    all_ttm = [h for g in rows for h in g.get("_ttm", [])]
    # A ticket spanning two groups is reported under both, so the totals row pools
    # by ticket id rather than concatenating the group lists.
    all_tickets: dict[str, tuple] = {}
    for g in rows:
        all_tickets.update(g.get("_tickets", {}))
    all_dev = [d for d, _ in all_tickets.values()]
    all_queue = [q for _, q in all_tickets.values() if q is not None]
    
    totals = {
        "title": "ALL",
        "repos_n": sum(len(g["repos"]) for g in rows),
        "merged": sum(g["merged"] for g in rows),
        "ticket_count": len(all_tickets),
        "dev_time_median_h": round(median(all_dev), 1) if all_dev else None,
        "dev_time_p85_h": round(percentile(all_dev, 0.85), 1) if all_dev else None,
        "queue_median_h": (round(median(all_queue), 1)
                           if len(all_queue) >= MIN_QUEUE_SAMPLES else None),
        "tickets_reached_main_pct": rate(
            sum(g["tickets_on_main"] for g in rows), sum(g["tickets_via_team"] for g in rows)
        ) if sum(g["tickets_via_team"] for g in rows) else None,
        "cycle_time_median_h": round(median(all_hours), 1) if all_hours else None,
        "cycle_time_p85_h": round(percentile(all_hours, 0.85), 1) if all_hours else None,
        "direct_to_main_pct": rate(
            sum(g["cycle_to_main_samples"] for g in rows),
            sum(g["cycle_to_team_samples"] + g["cycle_to_main_samples"] for g in rows),
        ),
        "time_to_main_median_h": (round(median(all_ttm), 1) if all_ttm else None),
        "reached_main_pct": rate(
            sum(g["time_to_main_samples"] + g["on_main_undated"] for g in rows),
            sum(g["time_to_main_samples"] + g["in_flight_changes"] + g["on_main_undated"]
                for g in rows),
        ),
        "change_failure_rate_pct": rate(
            sum(g["corrective"] for g in rows), sum(g["merged"] for g in rows)
        ),
        "defect_escape_rate_pct": (
            rate(sum(g["escaped"] for g in rows), sum(g["escaped"] + g["caught"] for g in rows))
            if any(g["escaped"] for g in rows)
            else None
        ),
    }
    print("".join(fmt(totals.get(k), w).ljust(w) for k, _, w in columns))

    failures = [f for g in rows for f in g["failed_repos"]]
    if failures:
        print(f"\n{len(failures)} repo(s) could not be read:")
        for f in failures[:15]:
            print(f"  {f}")
    skipped = sum(g["integration_prs"] for g in rows)
    noise = sum(g["noise_prs"] for g in rows)
    print(f"\nExcluded: {skipped} release/rebase merges between long-lived branches, "
          f"{noise} automated or version-bump changes.")
    infl = sum(g["in_flight_changes"] for g in rows)
    undated = sum(g["on_main_undated"] for g in rows)
    gone = sum(g["branch_deleted"] for g in rows)
    if all_ttm or infl or undated or gone:
        print(f"Time to main: {len(all_ttm)} timed, {infl} still on a team branch main does not "
              f"have, {undated} on main but undateable, {gone} on a branch since deleted.")
    multi = sum(g["tickets_multi_repo"] for g in rows)
    unjoined = sum(g["tickets_synthetic"] for g in rows)
    print(f"\nUnit: the ticket, not the pull request -- a feature is branched in every repo")
    print(f"  it touches, so {len(all_tickets)} tickets carry {sum(g['merged'] for g in rows)} changes. "
          f"{multi} span more than one repo.")
    if unjoined:
        print(f"  {unjoined} carry no Jira key and could not be joined to siblings, which can")
        print("  only understate the dev-time figures below.")
    print("Dev time   = first commit in any repo -> the last team-branch merge. The team owns it.")
    print("Queue time = that last merge -> on main. The release train owns it: weekly cadence,")
    print("  capped at 20 tickets. Released % counts tickets that went via a team branch and")
    print("  whose every repo is now on main; trunk-based work has no queue and is excluded.")
    qs = sum(g["queue_samples"] for g in rows)
    if qs < MIN_QUEUE_SAMPLES:
        print(f"  Queue p50 is withheld: only {qs} ticket(s) could be dated onto main, because")
        print("  dating needs a merge into main that names the branch. Measuring this segment")
        print("  properly needs the release records, not GitHub alone.")
    print("Time to main = first commit -> the merge that put it on main (both segments).")
    print("CFR = corrective changes / all changes (or failed main-branch pipeline runs, with Azure DevOps).")
    print("Escape rate = defects raised after release / (those + defects caught by review or CI).")


def print_csv(groups: dict[str, dict]) -> None:
    fields = [
        "id", "title", "repos", "merged", "corrective", "caught", "escaped",
        "ticket_count", "dev_time_median_h", "dev_time_p85_h",
        "queue_median_h", "queue_p85_h", "queue_samples", "tickets_reached_main_pct",
        "tickets_via_team", "tickets_on_main", "tickets_multi_repo",
    "multi_repo_pct", "unjoined_ticket_pct",
        "cycle_time_median_h", "cycle_time_p85_h", "cycle_time_samples",
        "cycle_to_team_median_h", "cycle_to_team_p85_h", "cycle_to_team_samples",
        "cycle_to_main_median_h", "cycle_to_main_p85_h", "cycle_to_main_samples",
        "direct_to_main_pct", "delivery_model", "trunk_based_repos",
    "time_to_main_median_h", "time_to_main_p85_h", "time_to_main_samples",
    "time_to_main_coverage_pct", "reached_main_pct", "in_flight_changes", "in_flight_pct",
    "in_flight_median_age_h", "in_flight_p85_age_h", "on_main_undated",
    "branch_deleted", "time_to_main_unknown",
        "lead_time_median_d", "lead_time_p85_d", "release_wait_median_d",
        "shipped_changes", "lead_samples", "shipped_estimated_dates",
        "shipped_untraceable",
        "change_failure_rate_pct", "cfr_source", "defect_escape_rate_pct", "der_source",
    ]
    w = csv.DictWriter(sys.stdout, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for g in sorted(groups.values(), key=lambda g: g["title"]):
        w.writerow({**g, "repos": len(g["repos"])})


# --------------------------------------------------------------------------
# 8. Reporting window and the Grafana history file
# --------------------------------------------------------------------------


def month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year + (month == 12), (month % 12) + 1, 1, tzinfo=timezone.utc)
    return start, end


def resolve_window(args) -> tuple[datetime, datetime, str]:
    """Return (since, until, period label). Calendar months keep the monthly
    series comparable; --days is for ad-hoc looks."""
    now = datetime.now(timezone.utc)
    if args.month:
        year, month = (int(x) for x in args.month.split("-", 1))
        since, until = month_bounds(year, month)
    elif args.last_month:
        since, until = month_bounds(now.year - (now.month == 1), (now.month - 2) % 12 + 1)
    else:
        return now - timedelta(days=args.days), now, f"last-{args.days}d"
    return since, until, f"{since:%Y-%m}"


HISTORY_FIELDS = [
    "period", "period_start", "period_end", "level", "id", "title",
    "repos", "merged_prs", "noise_prs", "integration_prs",
    # The headline pair, measured per TICKET across every repo the feature touched.
    "ticket_count", "dev_time_median_h", "dev_time_p85_h",
    "queue_median_h", "queue_p85_h", "queue_samples", "tickets_reached_main_pct",
    "tickets_via_team", "tickets_on_main", "tickets_multi_repo",
    "multi_repo_pct", "unjoined_ticket_pct",
    # Per-PR cycle time, kept for continuity with earlier runs. It measures one
    # repository's slice of a change, not the change.
    "cycle_time_median_h", "cycle_time_p85_h", "cycle_time_samples",
    # Cycle time split by what the change merged into: the team branch (hop one, the
    # definition) or trunk directly (two hops' distance on the same clock).
    "cycle_to_team_median_h", "cycle_to_team_p85_h", "cycle_to_team_samples",
    "cycle_to_main_median_h", "cycle_to_main_p85_h", "cycle_to_main_samples",
    "direct_to_main_pct", "delivery_model", "trunk_based_repos",
    # time-to-main and lead time were emitted into the JSON but missing from this
    # list, so the CSV mirror silently dropped them.
    "time_to_main_median_h", "time_to_main_p85_h", "time_to_main_samples",
    "time_to_main_coverage_pct", "reached_main_pct",
    "in_flight_changes", "in_flight_pct", "in_flight_median_age_h", "in_flight_p85_age_h",
    "on_main_undated", "branch_deleted", "time_to_main_unknown",
    "lead_time_median_d", "lead_time_p85_d", "release_wait_median_d", "shipped_changes",
    "lead_samples", "shipped_estimated_dates", "shipped_untraceable",
    "change_failure_rate_pct", "corrective_changes", "deployments", "failed_deployments",
    "cfr_source", "defect_escape_rate_pct", "escaped_defects", "caught_defects",
    "der_source", "generated_at",
]


def history_rows(groups: dict[str, dict], period: str, since: datetime, until: datetime,
                 level: str) -> list[dict]:
    stamp = iso(datetime.now(timezone.utc))
    rows = []
    for g in sorted(groups.values(), key=lambda g: g["title"]):
        rows.append({
            "period": period,
            "period_start": since.strftime("%Y-%m-%d"),
            "period_end": until.strftime("%Y-%m-%d"),
            "level": level,
            "id": g["id"],
            "title": g["title"],
            "repos": len(g["repos"]),
            "merged_prs": g["merged"],
            "noise_prs": g["noise_prs"],
            "integration_prs": g["integration_prs"],
            "ticket_count": g["ticket_count"],
            "dev_time_median_h": g["dev_time_median_h"],
            "dev_time_p85_h": g["dev_time_p85_h"],
            "queue_median_h": g["queue_median_h"],
            "queue_p85_h": g["queue_p85_h"],
            "queue_samples": g["queue_samples"],
            "tickets_via_team": g["tickets_via_team"],
            "tickets_on_main": g["tickets_on_main"],
            "tickets_multi_repo": g["tickets_multi_repo"],
            "tickets_reached_main_pct": g["tickets_reached_main_pct"],
            "multi_repo_pct": g["multi_repo_pct"],
            "unjoined_ticket_pct": g["unjoined_ticket_pct"],
            "cycle_time_median_h": g["cycle_time_median_h"],
            "cycle_time_p85_h": g["cycle_time_p85_h"],
            "cycle_time_samples": g["cycle_time_samples"],
            "cycle_to_team_median_h": g["cycle_to_team_median_h"],
            "cycle_to_team_p85_h": g["cycle_to_team_p85_h"],
            "cycle_to_team_samples": g["cycle_to_team_samples"],
            "cycle_to_main_median_h": g["cycle_to_main_median_h"],
            "cycle_to_main_p85_h": g["cycle_to_main_p85_h"],
            "cycle_to_main_samples": g["cycle_to_main_samples"],
            "direct_to_main_pct": g["direct_to_main_pct"],
            "delivery_model": g["delivery_model"],
            "trunk_based_repos": g["trunk_based_repos"],
            "time_to_main_median_h": g["time_to_main_median_h"],
            "time_to_main_p85_h": g["time_to_main_p85_h"],
            "time_to_main_samples": g["time_to_main_samples"],
            "time_to_main_coverage_pct": g["time_to_main_coverage_pct"],
            "reached_main_pct": g["reached_main_pct"],
            "in_flight_changes": g["in_flight_changes"],
            "in_flight_pct": g["in_flight_pct"],
            "in_flight_median_age_h": g["in_flight_median_age_h"],
            "in_flight_p85_age_h": g["in_flight_p85_age_h"],
            "on_main_undated": g["on_main_undated"],
            "branch_deleted": g["branch_deleted"],
            "time_to_main_unknown": g["time_to_main_unknown"],
            "lead_time_median_d": g["lead_time_median_d"],
            "lead_time_p85_d": g["lead_time_p85_d"],
            "release_wait_median_d": g["release_wait_median_d"],
            "shipped_changes": g["shipped_changes"],
            "lead_samples": g["lead_samples"],
            "shipped_estimated_dates": g["shipped_estimated_dates"],
            "shipped_untraceable": g["shipped_untraceable"],
            "change_failure_rate_pct": g["change_failure_rate_pct"],
            "corrective_changes": g["corrective"],
            "deployments": g.get("deployments"),
            "failed_deployments": g.get("failed_deployments"),
            "cfr_source": g["cfr_source"],
            "defect_escape_rate_pct": g["defect_escape_rate_pct"],
            "escaped_defects": g.get("jira_escaped", g["escaped"]),
            "caught_defects": g["caught"],
            "der_source": g["der_source"],
            "generated_at": stamp,
        })
    return rows


def write_history(path: Path, groups: dict[str, dict], period: str, since: datetime,
                  until: datetime, level: str, sources: list[str],
                  allow_partial: bool = False) -> list[Path]:
    """Upsert this period's rows into the cumulative history, and mirror it as CSV.

    Re-running a period replaces its rows rather than duplicating them, so a
    backfill or a corrected run is safe to repeat.

    Refuses to write a run in which repositories failed, unless told otherwise. A
    throttled or half-failed run produces low counts that are indistinguishable from
    a genuine drop in delivery once they are in the series, and the monthly job runs
    unattended -- so the failure has to stop here rather than be discovered later in
    a dashboard.
    """
    failed = sorted({f for g in groups.values() for f in g["failed_repos"]})
    if failed and not allow_partial:
        warn(f"{len(failed)} repo(s) failed; refusing to write {period} {level} to the history:")
        for f in failed[:10]:
            warn(f"  {f}")
        warn("re-run when the API is available, or pass --allow-partial to record it anyway")
        raise SystemExit(2)

    path.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict] = []
    if path.exists():
        try:
            existing = json.loads(path.read_text()).get("rows", [])
        except (json.JSONDecodeError, AttributeError):
            warn(f"{path} was unreadable; starting a fresh history")

    fresh = history_rows(groups, period, since, until, level)
    kept = [r for r in existing if not (r.get("period") == period and r.get("level") == level)]
    rows = sorted(kept + fresh, key=lambda r: (r["period"], r["level"], r["title"]))

    path.write_text(json.dumps(
        {"updated": iso(datetime.now(timezone.utc)), "sources": sources, "rows": rows}, indent=2
    ) + "\n")

    csv_path = path.with_suffix(".csv")
    with csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=HISTORY_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return [path, csv_path]


# --------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--days", type=int, default=90, help="window size in days (default 90)")
    p.add_argument("--month", help="report one calendar month, YYYY-MM (UTC); overrides --days")
    p.add_argument("--last-month", action="store_true",
                   help="report the calendar month just gone -- what the monthly job runs")
    p.add_argument("--history", metavar="PATH",
                   help="upsert this run into a cumulative history file (JSON), and write "
                        "the same rows as CSV alongside it, for Grafana to read")
    p.add_argument("--by", choices=["area", "product", "subdomain", "repo", "model"], default="area",
                   help="reporting level (default: the eight product areas)")
    p.add_argument("--area", action="append", default=[], help="limit to product area(s)")
    p.add_argument("--product", action="append", default=[], help="limit to product id(s)")
    p.add_argument("--no-regen", action="store_true",
                   help="use repo-teams.json as-is instead of regenerating from the model")
    p.add_argument("--repo", action="append", default=[], help="limit to repo name(s)")
    p.add_argument("--format", choices=["table", "json", "csv"], default="table")
    p.add_argument("--bug-labels", default="bug,defect,production-defect")
    p.add_argument("--no-issues", action="store_true", help="skip GitHub issue lookups")
    p.add_argument("--no-lead-time", action="store_true",
                   help="skip the Confluence release-page walk (true lead time)")
    p.add_argument("--no-time-to-main", action="store_true",
                   help="skip the second-hop lookup (one extra search query per repo)")
    p.add_argument("--azdo-pipeline-filter", default="validation|deploy|release",
                   help="regex matched against Azure DevOps pipeline names")
    p.add_argument("--jira-map", default=str(REPO_ROOT / "scripts" / "jira-teams.json"),
                   help="JSON file mapping product id -> {jql, escaped}")
    p.add_argument("--owner", default="hmcts", help="GitHub org to include (default hmcts)")
    p.add_argument("--no-jira-auto", action="store_true",
                   help="do not infer a team's Jira projects from PR titles")
    p.add_argument("--jira-min-keys", type=int, default=3,
                   help="min PR references before a Jira project counts as a team's (default 3)")
    p.add_argument("--print-jira-keys", action="store_true",
                   help="show the Jira project keys each team's PRs reference, then exit")
    p.add_argument("--workers", type=int, default=4,
                   help="parallel repositories; GitHub's secondary rate limit "
                        "responds to request rate, so raising this backfires")
    p.add_argument("--cache-hours", type=float, default=6.0)
    p.add_argument("--refresh", action="store_true", help="ignore cached API responses")
    p.add_argument("--allow-partial", action="store_true",
                   help="write to the history even when some repositories failed to read")
    p.add_argument("--list-repos", action="store_true", help="print the model mapping and exit")
    args = p.parse_args()
    args.bug_labels = [l.strip() for l in args.bug_labels.split(",") if l.strip()]

    records = [r for r in load_repo_teams(regenerate=not args.no_regen) if r["owner"] == args.owner]
    if not records:
        print("No repository links found in the C4 model.", file=sys.stderr)
        return 1
    repos = build_repo_map(records)
    for meta in repos.values():
        meta["group_title"] = {
            "area": meta["area"],
            "product": meta["product_title"],
            "subdomain": meta["subdomain_title"],
            # A subdomain with one product hides everything inside it, so the
            # repository is the only level that always has something to show.
            "repo": meta["repo"],
            # Filled in after collection: the model is read from the merges.
            "model": "",
        }[args.by]

    if args.area:
        repos = {k: v for k, v in repos.items() if v["area"] in args.area}
    if args.product:
        repos = {k: v for k, v in repos.items() if v["product"] in args.product}
    if args.repo:
        repos = {k: v for k, v in repos.items() if v["repo"] in args.repo}
    if not repos:
        print("No repos matched the filters.", file=sys.stderr)
        return 1

    if args.list_repos:
        for key, m in sorted(repos.items(), key=lambda kv: (kv[1]["area"], kv[1]["product_title"], kv[0])):
            print(f"{m['area']:<32} {m['product_title']:<42} {key}")
        print(
            f"\n{len(repos)} repos across {len({m['product'] for m in repos.values()})} products "
            f"in {len({m['area'] for m in repos.values()})} product areas."
        )
        return 0

    since, until, period = resolve_window(args)
    ttl = 0 if args.refresh else args.cache_hours
    sources = ["github"]

    repo_rows = collect(repos, since, until, args)

    # The delivery model is a property of the repository, read over the whole
    # reporting year rather than this one month -- see classify_models.
    models = classify_models(repos, since, until, ttl, args.workers)
    for key, row in repo_rows.items():
        row["model"] = models.get(key, MODEL_UNKNOWN)
        if args.by == "model":
            row["group_title"] = MODEL_TITLE[row["model"]]

    azdo_builds = None
    cfg = azdo_config()
    if cfg:
        try:
            azdo_builds = fetch_azdo_builds(
                cfg, since, until, re.compile(args.azdo_pipeline_filter, re.I), ttl
            )
            sources.append(f"azure-devops ({len(azdo_builds)} runs)")
        except Exception as exc:  # noqa: BLE001
            warn(f"Azure DevOps unavailable, falling back to the GitHub proxy: {exc}")

    jira_cfg = jira_config()
    jira_map = {}
    if jira_cfg:
        map_path = Path(args.jira_map)
        if map_path.exists():
            jira_map = json.loads(map_path.read_text()).get("products", {})
            sources.append("jira")
        else:
            sources.append("jira (auto-scoped from PR titles)")

    lead_by_repo: dict[str, list[dict]] = {}
    conf_cfg = confluence_config()
    if conf_cfg and not args.no_lead_time:
        try:
            releases = walk_release_pages(conf_cfg, since, until, ttl)
            lead_by_repo = release_lead_times(releases, ttl)
            shipped = sum(len(v) for v in lead_by_repo.values())
            sources.append(f"confluence ({len(releases)} releases, {shipped} shipped changes)")
        except Exception as exc:  # noqa: BLE001 - lead time is additive, never load-bearing
            warn(f"Confluence release pages unavailable: {exc}")
    elif not conf_cfg and not args.no_lead_time:
        warn("CONFLUENCE_URL/CONFLUENCE_PERSONAL_TOKEN unset: skipping true lead time")

    tickets = ticket_spans(repo_rows)
    groups = aggregate(repo_rows, args.by, azdo_builds, jira_cfg, jira_map, since, until, ttl,
                       jira_auto=not args.no_jira_auto, jira_min_keys=args.jira_min_keys,
                       lead_by_repo=lead_by_repo, tickets=tickets)

    if args.print_jira_keys:
        print("Jira project keys referenced by each team's merged PRs:\n")
        for g in sorted(groups.values(), key=lambda g: g["title"]):
            keys = ", ".join(
                f"{k} ({n})" for k, n in sorted(g["jira_projects"].items(), key=lambda kv: -kv[1])
            )
            print(f"  {g['title']:<36} {keys or '-'}")
        print("\nUse these to write scripts/jira-teams.json if the auto-scoping is too broad.")
        return 0

    if args.format != "table":
        # Working lists kept only for the table's pooled totals row.
        for g in groups.values():
            for k in [k for k in g if k.startswith("_")]:
                del g[k]

    if args.format == "json":
        print(json.dumps(
            {
                "window": {"period": period, "since": iso(since), "until": iso(until)},
                "sources": sources,
                "groupedBy": args.by,
                "teams": sorted(groups.values(), key=lambda g: g["title"]),
            },
            indent=2,
        ))
    elif args.format == "csv":
        print_csv(groups)
    else:
        print_table(groups, since, until, period, sources, args.by)

    if args.history:
        paths = write_history(Path(args.history), groups, period, since, until, args.by,
                              sources, allow_partial=args.allow_partial)
        print(f"\nHistory updated: {' and '.join(str(p) for p in paths)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
