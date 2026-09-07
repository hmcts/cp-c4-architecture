# The published baseline report

Two files, and one generated artifact that is not committed:

| File | What it is |
|---|---|
| `build_data.py` | Folds `metrics/delivery-metrics.json` plus the release pages into `data.json` — the shape the page reads. Run it from the repository root. |
| `delivery-baseline.html` | The page itself. Hand-written; `data.json` is spliced into its `<script id="data">` block. |
| `data.json` | Generated. Not committed — rebuild it. |

## Rebuilding

```bash
export CONFLUENCE_URL="https://tools.hmcts.net/confluence/"
export CONFLUENCE_PERSONAL_TOKEN="…"        # a Confluence personal access token
python3 scripts/report/build_data.py        # from the repository ROOT, not this directory
```

It writes `data.json` beside itself and prints the platform row for each period, which
is the quickest way to see whether a change to the collector moved a number it should
not have. Splice the result into the page's `<script id="data">` block to publish.

The collector must have been run first — `build_data.py` reads the history file it
writes, and the API caches it fills. See `../README.md` for that.

## Why the numbers on the page are not always the sum of the numbers under them

Three traps, all of them deliberate and all of them explained on the page itself:

- **Tickets do not sum up the tree.** A ticket branched across two areas is reported
  under both, and pooled by id at the platform row — so the total is smaller than the
  sum of the areas, not larger.
- **Medians do not add.** Lead time is measured end to end on one clock, never
  assembled from a median dev time plus a median queue plus a median deploy.
- **The three segments cover different populations.** Cycle time counts what reached a
  team branch, queue age counts what has *not* reached `main`, and lead time counts
  what shipped. They are disjoint by construction.
