# Delivery metrics per product team

`delivery_metrics.py` reports **cycle time**, **change failure rate** and **defect
escape rate** for each of the eight CPP product areas, using this repo's C4
model as the authoritative repo → product → area mapping.

```bash
python3 scripts/delivery_metrics.py --days 90                   # table, all areas
python3 scripts/delivery_metrics.py --list-repos                # show the mapping only
python3 scripts/delivery_metrics.py --area "Court Hearing"      # one area
python3 scripts/delivery_metrics.py --by product                # drill into products
python3 scripts/delivery_metrics.py --by repo --area DLRM         # repositories in one area
python3 scripts/delivery_metrics.py --by subdomain --format csv > metrics.csv
python3 scripts/delivery_metrics.py --format json | jq '.teams[]'
```

Reporting levels (`--by`): `area` (default, the seven product areas), `product`
(the 25 C4 products and shared components), `subdomain`, `repo`.

Two subdomains — Scheduling & Listing and DLRM — are modelled as a single product
each, so `--by product` tells you nothing about them that `--by area` did not. Use `--by repo` for those. The published report
does this automatically: those areas expand straight to repositories.

A full month over all 75 mapped repos takes ~15s cold, and is cached for
6 hours (`--refresh` to bypass, `--cache-hours` to change).

## Where the mapping comes from

The `repo-teams-json` generator in `likec4.config.ts` walks the LikeC4 model and
writes `repo-teams.json`: every `link https://github.com/... 'Repository'` in the
model, attributed to the nearest enclosing `product` **or** `shared-component`,
then to its subdomain and product area. The script regenerates that file
whenever a `.c4` source is newer than it (`--no-regen` to skip), so adding a repo
to the model is enough — there is no second list to maintain.

The eight product areas are the subdomains, with two adjustments made in the
generator's `areaOfSubdomain` / `areaOfProduct` maps:

| Product area | Model source |
|---|---|
| Case Administration | `case-administration-subdomain` |
| Case Ingestion | `case-ingestion-subdomain` ("Case and Material Ingestion") |
| Court Hearing | `court-hearings-subdomain` |
| DLRM | `dlrm-subdomain` |
| Management Information System | `opami-subdomain` (Audit System + MI System) |
| Scheduling & Listing System | `scheduling-and-listing-subdomain` |
| Platform Engineering | `shared-components-subdomain` |

An area is a subdomain, with no per-product exceptions. `cp-user-interface` was
once promoted to an area of its own; a single repository reporting beside a
25-repository area produced a row whose every figure sat on three or four changes,
so it now reports inside Platform Engineering where the model puts it.

Edit that map if the areas are ever redrawn — nothing in the Python needs to change.

Repos that sit outside a subdomain in the model (external systems) are not in
any area and so are not reported.

## Metric definitions

| Metric | Definition | Source |
|---|---|---|
| **Dev time** | Hours from a ticket's earliest first commit **in any repository** to its **last** merge into a team branch. The headline cycle-time figure. Reported as median (p50) and p85. **Never as a mean** — see below. | GitHub + Jira keys |
| **Queue time** | Hours from that last team-branch merge until the ticket is on `main` — the wait for a release slot. Withheld below 5 dateable tickets; see the caveat. | GitHub |
| **Cycle time (per PR)** | The old headline: one repository's slice of a change. Kept for continuity with earlier runs, no longer the number to quote. | GitHub |
| **Time to main** | Hours from the first commit until the change is on `main`, across both hops. Reported with `reached_main_pct`, without which it misleads. | GitHub |
| **Change failure rate** | Corrective changes ÷ all changes. | GitHub, or Azure DevOps when configured |
| **Defect escape rate** | Defects found in production ÷ all defects found. | Jira (GitHub Issues as a fallback) |

Merged PRs are selected with GitHub's search API using a `merged:` date range.
The `repository.pullRequests` connection cannot be ordered by merge date — only
by creation or last update — so paging it and stopping early silently drops
merges that sit below a recently-touched old PR.

Automated and housekeeping PRs — Renovate/Dependabot, "Bump up version",
"Update pom versions" — are excluded from all three metrics and counted
separately as `noise_prs`, since they would otherwise dominate the cycle-time
distribution.

### The branching model, and what counts as a change

CPP's flow is:

```
feature branch  ->  team branch  ->  main  ->  cut a release branch for SIT  ->  go live
```

**A change is measured once, on its first hop** — the merge where the work actually
landed. In Aug 2026 that is 335 features merging into a `team/*` branch plus 44
merging straight into main. Two later shapes are excluded and counted as
`integration_prs`:

| Shape | Why | Example |
|---|---|---|
| the second hop: `team/*` or a release branch merged into main | its features were already counted on hop one, so counting it again double-counts them — and its first commit is the day the team branch was cut, so its elapsed time is that branch's age | `team/cct-1981-release-26.22 → main` |
| main brought back *into* a team or release branch | plumbing in the other direction | `dev/main-rebase → team/CCT-1222-V2`, `[CADB-3] Update with main`, `Resolve merge conflict with main` |

Left in, these dominate the tail: the 19 team→main hops in Aug 2026 carried between
20 and 137 days of branch age each, and ten such PRs held 76% of Case
Administration's total elapsed hours.

A fix made *on* a release branch is still counted — it merges `fix/... →
team/*-release`, which neither rule catches — so a production fix is counted once,
where it was made.

Detection is structural where it can be (head is a shared branch, base is not) and
by name where it cannot be: the back-merges are named rather than structured.
`is_integration()` carries the patterns.

### Two delivery models, measured apart

Repositories are migrating to Modern by Default: trunk-based development on short-lived
feature branches, with a GitOps route to production. Those repositories have no
integration branch, so their merge into main **is** the first hop. Blending them with
the rest would time a shorter journey for one group and the full journey for the other,
in the same column — so they get their own lane, `--by model`.

The lane is read from each repository's own merges over the reporting year
(`classify_models`), not from a list that would go stale as repositories migrate. A
repository needs `MODEL_MIN_CHANGES` counted changes before its branching is taken as
evidence; below that it is `unclassified`. Classification is anchored to January so a
repository does not change lane month to month. The lanes are named for the branching
behaviour, not the programme label, because the two do not always coincide —
`cp-case-document-knowledge-service` is an MbD service that runs a `develop` integration
branch, so it is measured in the integration-branch lane.

Measured over Mar–Aug 2026:

| | Repos | Changes | Cycle p50 | Reached trunk |
|---|---|---|---|---|
| Trunk-based, no integration branch | 6 | 123 | 0.6–16.6 h | **100%, every month** |
| Via an integration branch | 60 | 1,934 | 1.7–6.2 h | 13–23% |

**Do not compare the lanes on cycle time.** The trunk-based lane often reads slower,
which is an artefact: its clock runs all the way to trunk while the other lane's stops
at the integration branch with hop two still ahead. Compare them on time to trunk and
the share arriving.

**Lead time does not cover the trunk-based lane.** It is measured backwards from the
release manager's pages, which record the weekly train; of 380 changes traced to a
production date, 1 came from that lane. GitOps deploys outside the train and leaves no
release page. Measuring it needs Flux or AKS deployment events.

### Not every change merges into an integration branch

Four changes in five merge into a team branch, which is the route the branching model
describes. The other fifth are **not** feature branches merging to main — that is not
permitted — and they are not the team→main or release→main hops either, which are
excluded as integration before anything is counted. Measured over Mar–Aug 2026:

| Route | Changes | What it is |
|---|---|---|
| Into a team branch | 1,681 (79%) | the route |
| Repositories with no integration branch | 123 (6%) | the trunk-based lane, where that merge *is* hop one |
| Exceptions inside integration-branch repos | 267 (13%) | unexplained; see below |

Of the exceptions: **80** carry a work-item key that also merged through a team branch
in the same repo — the shape of a release fix forward-ported onto main, i.e. the same
change counted twice; **128** carry a key seen only on the direct merge; **56** carry no
key. Branch names (`dev/rel-3rd-line-2613-main`, `dev/main-ali-2615`) point at release
work rather than new features, but names alone cannot settle it.

Branches with an unambiguous plumbing name — `copy-…`, `tmp/…`, `merge-…`,
`…-main-merge`, `rel26…` — merging into trunk are excluded as integration
(`PLUMBING_BRANCH_RE`), as are merges out of a `develop` integration branch. The rest is
an **open question**, and until it is answered the blended median carries a small
unquantified double-count.

### Two clocks: time to acceptance, and time to main

Because the flow has two hops, one number cannot describe it. The tool reports both.

| Metric | Clock | Answers |
|---|---|---|
| **Cycle time** | first commit → merge into the team branch (hop one) | how long a developer's change takes to be accepted |
| **Time to main** | first commit → the merge that put it on main (both hops) | how long until the work is on trunk |

Whether a change reached main is settled **per change**, not per branch: the tool asks
GitHub whether that change's own merge commit is contained in `main`
(`ref(main) { compare(headRef: <sha>) { aheadBy } }`, `aheadBy == 0` means yes). Branch
names are only used for the *date*, by pairing the change's branch to the merge that
carried it. So a change is never called "not on main" because a name failed to match.

Every change lands in one of five states, reported separately because averaging them
together would lie:

| State | Meaning |
|---|---|
| `measured` | on main, and the date is known — this is what `time_to_main_median_h` is computed over |
| `on_main_undated` | on main, but no merge into main names its branch, so there is no date |
| `in_flight` | its merge commit is not in main. `in_flight_median_age_h` is its age *so far* — a lower bound, not a completed time |
| `branch_gone` | neither the merge commit nor the branch can be compared |
| `unknown` | no merge commit and no base branch to reason about |

**`reached_main_pct` is the number to read first.** The timed median is computed only
over changes that made it, and those skew heavily toward changes that went straight to
main — so it is a floor, not an average. Quoting it without the reached-main rate beside
it would be the same mistake as quoting a mean without the median.

This is right-censored data, and the honest summary is a pair:

> *Of May 2026's 308 changes, 25% were on main by 2 September. The rest had been waiting
> a median of 110 days.*

`--no-time-to-main` skips the whole second hop (one extra search plus one comparison
query per repository). Observation always runs to today, so **the most recent month or
two will always show a low reached-main rate simply because little time has passed** —
mark them provisional in any dashboard, or the censoring reads as a collapse in
delivery.

Rate limits matter here, and not the ones you can see. The second hop adds a search and
a batched comparison per repository, which is enough to trip GitHub's **secondary** rate
limit — a limit on request *rate*, invisible to `gh api rate_limit`, which will happily
report 5000 remaining while every call is being refused. Once tripped it stays tripped
while you keep retrying.

Three things keep a backfill under it:

- calls are spaced by `GH_MIN_CALL_INTERVAL` (default 0.7s) across all worker threads —
  preventing the throttle costs far less than recovering from it;
- `--workers` defaults to 4, and raising it makes throttling worse, not better;
- when it does trip, backoff is 45s, doubling with jitter, six attempts.

If a backfill is refused from the first call, stop and leave it alone for a few minutes:
continuing to knock extends the block.

### The unit is the ticket, not the pull request

A CPP feature is branched in **every repository it touches**, so one piece of work
arrives as N pull requests. Measured per PR, a feature that took a fortnight across
four services reported as four short changes — and the medians said so:

| Unit | Median cycle time |
|---|---|
| Per PR | 4.2 h |
| Per ticket | 22.6 h |
| Per ticket, multi-repo only (n=258) | **235.5 h — 9.8 days** |

Changes are folded into tickets by the Jira keys already parsed from PR titles and
branches. A ticket's clock starts at the **earliest** first commit in any repository
and stops at the **last** merge into a team branch, because until the last repository
lands there is no releasable artifact — the programme's own criterion for merging.

Three things about this that will otherwise trip you up:

- **A ticket spanning two product areas is reported under both**, with identical
  figures. Counting it once would hide exactly the cross-cutting work that takes
  longest. The table's ALL row pools by ticket id, so it does not double-count.
- **Changes with no Jira key** cannot be joined to their siblings and become
  single-repo tickets of their own. That is between a fifth and two fifths of them
  (`unjoined_ticket_pct`), and it biases dev time **downwards** — the real figure is
  worse than the one reported, never better.
- **p85 is long** — hundreds of hours — because a ticket worked on in January and
  again in July spans the gap. That is a true elapsed time, not an artifact, but it
  is not "how long someone worked on it".

### Three segments, and who owns each

Merging to a team branch is not the end of the journey; it is the start of a wait.
The flow is: merge to the team branch when the work is done → wait for the current
release's testing to finish → rebase, retest → merge to `main` → deploy. So `main`
is close to production and **the queue sits between the team branch and `main`**.

| Segment | Clock | Owner |
|---|---|---|
| Dev time | first commit in any repo → last team-branch merge | the team |
| **Queue time** | **last team-branch merge → on `main`** | **the release train: weekly cadence, capped at ~20 tickets** |
| Deploy | `main` → go-live (`release_wait_median_d`) | the release process |

The split matters because the middle segment is not the team's to fix, and it is
where the time is.

**The "20 tickets per release" cap is not what the release pages show.** Counting
Jira keys on the 20 scheduled releases that went live March–August 2026: mean 29,
median 28, range 14–58, with 13 of the 20 above 20. Patch releases carry 1 on
average. About 98 distinct tickets go live per month across three to four scheduled
releases plus patches; the cadence is not reliably weekly. Whatever batch size is
intended, the releases that shipped were not held to it — so do not argue from the
cap, and do not treat release capacity as a fixed 87 a month.

What stands independently, because it comes from git rather than a stated policy, is
the backlog: ~1,600 changes merged in six months are not on `main`, and only 4.6% of
tickets going via a team branch have every repository landed. Work accumulates before
`main`, which is reason enough to report the segments apart — a blended number would
charge teams for a wait they do not control. The size of the release batch is not
established as the cause of it.

The rebase step does not disturb any of this. First-commit timestamps come from
`authoredDate`, which a rebase preserves; only `committedDate` is rewritten.

**Queue time is currently withheld more often than it is reported**, and this is the
main open gap. Dating a ticket's arrival on `main` needs a merge into `main` that
names its branch, and most cannot be paired — in July 2026, of 291 team-branch
changes, 274 were still in flight, 16 were on `main` but undateable, and **1** could
be timed. Below `MIN_QUEUE_SAMPLES` (5) the median is suppressed rather than printed,
because one ticket wearing a percentile's clothes is worse than a blank. Measuring
this segment properly needs the release records or Jira, not GitHub alone.

### Released % is not the same as the old "on main %"

`tickets_reached_main_pct` counts tickets that went **via a team branch** and whose
every repository is now on `main`. Trunk-based services have no queue by construction
and are excluded from it, and a multi-repo ticket needs all of its repositories to
land. Both make it much harsher than the per-PR `reached_main_pct`, and the gap is
the point: the blended per-PR figure of 13–23% was carried almost entirely by
direct-to-trunk merges, which are on `main` the moment they merge. Team-branch work
reaches `main` at around **2–17% a month**. Quote them apart or not at all.

### Three clocks, not one

The forward clocks (`cycle_time_*`, `time_to_main_*`) start at a commit and ask how
far it got. They can only see work that has already merged, and they stop at `main`,
which in a two-hop branching model is still nowhere near a user.

`lead_time_median_d` runs the other way. Every weekly release has a **Tech Focused**
page under `CROWN > Release Section` carrying a go-live date and, in Section 2, the
explicit list of GitHub PRs that shipped in it. Joining those PRs back to their first
commit gives DORA lead time for changes with a real production date rather than a
proxy, and splits cleanly in two:

| Field | Span | Reads as |
|---|---|---|
| `lead_time_median_d` | first commit → live in production | the whole pipeline |
| `release_wait_median_d` | PR merged → live in production | the release machinery |
| `shipped_changes` | — | how many changes the figure rests on |

Measured over Mar–Aug 2026 the release wait is about 9 days against a lead time of
about 11 — that is, **most of the elapsed time in a change that ships is spent after
the code is finished**, and the weekly train is a floor on it, not the cause.

**This cohort is survivorship-biased, and it must never be quoted without saying so.**
Every change here reached production. Work still sitting on a team branch never
appears on a release page, so this is "how long it takes when it works", not "how
long work takes". Read it beside `reached_main_pct`, never instead of it: the forward
view says only about a fifth to a third of merged changes reach `main` at all, and
those are the ones this figure is made of.

Three source-quality limits are reported rather than smoothed over:

- **Squashed history.** A team branch is squashed into one commit on the way to
  `main`, so that pull request's oldest commit *is* the merge. A lead time started
  from it measures the release wait and calls it lead time. 209 of the 413 changes
  that shipped in the six months to August 2026 are like this: their `devH` reads
  0.0 days and their lead time reads ~9 days, the release wait alone. Lead time is
  therefore measured only over the changes whose origin survives (`lead_samples`);
  the rest are counted in `shipped_untraceable` and still date the release wait,
  which needs only the merge and the go-live. Including them halved the platform
  median: 11.0 days against the 23.3 measured over traceable changes alone.

- **Dead links.** Roughly one PR link in six on the release pages does not resolve
  (deleted branches, renamed repos, mistyped numbers). The run warns with a count.
- **Stale go-live dates.** The date on a page is the *planned* one, and a slipped
  release is not always corrected. Where most of a release's changes merged after its
  stated go-live, measuring against that date would produce a negative wait.
  Such a release used to be dropped whole, which cost a month: June 2026's two main
  releases (26.15 and 26.16) both carry a date their own changes contradict, so the
  month reported no lead time at all while carrying the highest merged-PR count in
  the window.

  The anchor is now re-derived instead, from the cadence the trustworthy releases
  show rather than from a guess at what the page meant:

      estimate = last merge in the release + median(go-live − last merge)

  over the releases in the same window whose stated date *is* consistent with their
  merges, capped a day short of the next such release. In the six months to August
  2026 that median is 5.2 days, and it re-dates 26.15 to 24 June and 26.16 to
  26 June. Every record so dated is flagged, counted in `shipped_estimated_dates`,
  and labelled on the published report. A release whose date is contradicted and
  which has no resolvable merge to re-date from is still dropped.

Requires `CONFLUENCE_URL` plus `CONFLUENCE_PERSONAL_TOKEN` (Server/DC) or
`CONFLUENCE_USERNAME` + `CONFLUENCE_API_TOKEN` (Cloud). Without them the walk is
skipped and every other metric is unaffected. `--no-lead-time` turns it off; page
bodies are cached for a week, since a shipped release stops changing.

## Monthly runs and Grafana

`.github/workflows/delivery-metrics.yml` runs on the 1st of each month at 06:00
UTC (`cron: '0 6 1 * *'`) and reports the calendar month just gone. It appends
one row per product area to `metrics/delivery-metrics.json`, mirrors it as
`metrics/delivery-metrics.csv`, and uploads both as a workflow artifact.

Every repo in the model is public, so the workflow's default `GITHUB_TOKEN`
can read their pull requests — no PAT needed. Add `AZDO_*` / `JIRA_*` as
repository secrets to upgrade the last two metrics; absent secrets just leave
the GitHub proxies in place.

Run it by hand from the Actions tab, optionally passing a month:

```bash
gh workflow run delivery-metrics.yml -f month=2026-07
```

Re-running a month **replaces** that month's rows rather than duplicating them,
so backfills and corrected runs are safe to repeat:

```bash
for m in 2026-01 2026-02 2026-03; do
  python3 scripts/delivery_metrics.py --month "$m" --history metrics/delivery-metrics.json
done
```

### Publishing the history

By default the workflow only uploads artifacts — nothing is committed. Set the
`PUBLISH_METRICS` repository variable to `true` (Settings → Secrets and
variables → Actions → Variables) and it will also commit the history back to
`main`, giving Grafana a stable URL to poll:

```
https://raw.githubusercontent.com/hmcts/cp-c4-architecture/main/metrics/delivery-metrics.csv
```

**This repository is public**, so that publishes per-team delivery metrics
publicly. If that is not wanted, leave the variable unset and either point
Grafana at an artifact the platform team syncs internally, or change the commit
step to push to a private repo.

### Wiring up Grafana

Use the [Infinity datasource](https://grafana.com/grafana/plugins/yesoreyeram-infinity-datasource/)
(`grafana-cli plugins install yesoreyeram-infinity-datasource`) — no database
required.

| Setting | Value |
|---|---|
| Type | Infinity |
| Format | CSV (or JSON with rows path `rows`) |
| Source | URL — the raw link above |
| Parser | Backend (so Grafana can filter and transform server-side) |
| Columns | `period` as **Time** with format `YYYY-MM`, the `*_pct` and `*_h` fields as **Number**, `title` as **String** |

One panel per metric, all with the same query:

- **Cycle time** — time series, `cycle_time_median_h` by `title`, unit `hours`.
  Add `cycle_time_p85_h` as a second series to expose the tail.
- **Change failure rate** — time series or bar gauge, `change_failure_rate_pct`
  by `title`, unit `percent (0-100)`.
- **Defect escape rate** — same shape, `defect_escape_rate_pct`.
- **Reaching main** — bar gauge, `reached_main_pct` by `title`, unit `percent (0-100)`.
  Pair it with `time_to_main_median_h` on the same row; neither is readable alone, and
  a dashboard showing the median without the rate invites the wrong conclusion.

Filter with `level = 'area'` for the eight product areas. To let a dashboard
variable switch between areas and products, schedule a second step in the
workflow with `--by product --history metrics/delivery-products.json`, or write
both levels to the same history — the `level` column keeps them apart.

Trust the `cfr_source` / `der_source` columns when reading a panel: they record
whether a point came from real pipeline and Jira data or from the GitHub proxy,
so a change of source shows up as a step in the series rather than a mystery.

## Optional sources

Both are picked up from the environment automatically; without them the script
still runs on GitHub alone and labels each metric with the source it used
(`cfr_source`, `der_source` in the JSON/CSV output).

### Azure DevOps — real change failure rate

```bash
export AZDO_ORG=<organisation>
export AZDO_PROJECT=<project>
export AZURE_DEVOPS_EXT_PAT=<PAT with Build: Read>
```

Change failure rate then becomes failed main-branch pipeline runs ÷ all
main-branch runs, matched to repos by the build's GitHub repository name.
`--azdo-pipeline-filter` (default `validation|deploy|release`) selects which
pipelines count as a change reaching an environment.

### Jira — real defect escape rate

```bash
export JIRA_URL=https://<site>.atlassian.net
export JIRA_EMAIL=<you@example.com>
export JIRA_API_TOKEN=<api token>
```

Each team's Jira scope is inferred from the work-item keys in their merged PR
titles (`SNI-9204: ...` → project `SNI`), validated against the projects your
account can see. Check what it inferred with:

```bash
python3 scripts/delivery_metrics.py --print-jira-keys
```

If that inference is too broad — several teams sharing one project, say — copy
`scripts/jira-teams.json.example` to `scripts/jira-teams.json` and give the
affected products an explicit JQL scope (keyed by product id, not area). Escaped defects default to
`labels in (escaped-defect, production-defect) OR environment ~ "prod"`;
override per product with the `escaped` clause.

## Caveats worth knowing before you quote these numbers

- **Cycle time measures PR lead time, not idea-to-production.** It stops at
  merge, so release cadence and deployment lag are invisible to it. Jira
  in-progress → done would capture the fuller picture.
- **The GitHub change-failure proxy under-counts.** Failures fixed by rolling
  forward without a "fix" in the title do not register.
- **Defect escape rate needs Jira.** These repos do not use GitHub Issues, so
  without Jira credentials the column reports `-` rather than a misleading 0%.
- **p85 cycle time is long-tailed** because long-lived feature branches drag it
  out; the median is the more stable signal for week-to-week comparison. Since
  release and integration merges are excluded, what remains in the tail is real
  long-running work rather than branch age.
- **Cycle time is time to acceptance, not lead time to trunk.** In Aug 2026, 335 of
  418 merged PRs targeted a `team/*` branch. Read `time_to_main_median_h` and
  `reached_main_pct` for the trunk view — see "Two clocks" above.
- **The timed time-to-main median is biased low and is a floor.** It can only be
  computed over changes that reached main, which skews toward those that went straight
  there. Always read it with `reached_main_pct`.
- **In-flight age is censored.** `in_flight_median_age_h` says how long work has been
  waiting *so far*, which grows simply because time passes. It is not a completed
  duration and must not be averaged with timed values.
- **Do not compare these numbers to a mean.** The distribution is not merely
  skewed, it is pathological: the median PR merges about four hours after its
  first commit, while roughly a tenth of PRs carry over 80% of the total elapsed
  time, and the worst 1% (five months old and more) carry a fifth of it on their
  own. Averaging the same PRs gives 8-20 days depending on the month. Both
  numbers are arithmetically correct and they answer different questions: the
  median says how long a typical change takes, the mean says how much branch age
  is sitting in the repository. If someone quotes a ~30-day figure, they are
  almost certainly quoting a mean — reconcile before concluding either is wrong.
- **Averaging per-repo averages is a third, larger number again.** A repo that
  merged one 200-day PR then weighs the same as a repo that merged sixty. Every
  figure here is computed over PRs, never over repo averages.
