"""Rebuild the report artifact's embedded data block from the corrected history."""
import json, glob, re, sys, statistics as st
from datetime import datetime, timezone as tz
sys.path.insert(0, "scripts")
import delivery_metrics as dm   # reuse the collector's own exclusion rules

H = json.load(open("metrics/delivery-metrics.json"))
RT = json.load(open("repo-teams.json"))["repos"]
prod_area = {r["product"]: r["area"] for r in RT}

periods = sorted({r["period"] for r in H["rows"]})
rows = H["rows"]

def months_for(level, ident):
    out = []
    for p in periods:
        r = next((x for x in rows if x["period"] == p and x["level"] == level and x["id"] == ident), None)
        out.append({
            "period": p,
            "prs": r["merged_prs"] if r else 0,
            "noise": r["noise_prs"] if r else 0,
            "integration": r["integration_prs"] if r else 0,
            "ttm": r["time_to_main_median_h"] if r else None,
            "ttm85": r["time_to_main_p85_h"] if r else None,
            "onMain": r["reached_main_pct"] if r else None,
            "inFlight": r["in_flight_changes"] if r else 0,
            "inFlightAge": r["in_flight_median_age_h"] if r else None,
            "p50": r["cycle_time_median_h"] if r else None,
            "p85": r["cycle_time_p85_h"] if r else None,
            # Ticket-level: the unit of delivery is the feature, which is branched in
            # every repo it touches. `p50`/`p85` above are one repo's slice of it.
            "tickets": r.get("ticket_count") if r else 0,
            "dev50": r.get("dev_time_median_h") if r else None,
            "dev85": r.get("dev_time_p85_h") if r else None,
            "queue50": r.get("queue_median_h") if r else None,
            "queueN": r.get("queue_samples") if r else 0,
            "released": r.get("tickets_reached_main_pct") if r else None,
            "viaTeam": r.get("tickets_via_team") if r else 0,
            "multiRepo": r.get("tickets_multi_repo") if r else 0,
            "noKeyPct": r.get("unjoined_ticket_pct") if r else None,
            "cfr": r["change_failure_rate_pct"] if r else None,
            "corrective": r["corrective_changes"] if r else 0,
            "lead": r.get("lead_time_median_d") if r else None,
            "lead85": r.get("lead_time_p85_d") if r else None,
            "relWait": r.get("release_wait_median_d") if r else None,
            "shipped": r.get("shipped_changes") if r else 0,
            # Changes dated from a go-live the release page stated vs one inferred
            # from the cadence because the page's own changes contradicted its date.
            "estDates": r.get("shipped_estimated_dates") if r else 0,
            "leadN": r.get("lead_samples") if r else 0,
            # Shipped, but squashed on the way to main, so no origin to measure from.
            "untraceable": r.get("shipped_untraceable") if r else 0,
            "model": r.get("delivery_model") if r else None,
            "trunkRepos": r.get("trunk_based_repos") if r else 0,
        })
    return out

def _lead_stats(recs):
    """Pooled over changes, not a median of medians.

    Lead time comes only from the changes whose origin survives the trip to main. A
    team branch squashed into a single commit carries no history: its "first commit"
    is the merge, so a lead time taken from it is the release wait wearing a longer
    name. Those changes still count as shipped, and still date the release wait.
    """
    blank = {"lead": None, "lead85": None, "relWait": None, "dev": None,
             "shipped": 0, "leadN": 0, "estDates": 0, "untraceable": 0}
    if not recs:
        return blank
    q = lambda a, x: sorted(a)[min(len(a) - 1, int(round(x * (len(a) - 1))))]
    keep = [r for r in recs if r.get("traceable", True)]
    lead = [r["leadH"] / 24 for r in keep]
    wait = [r["releaseH"] / 24 for r in recs]
    dev = [r["devH"] / 24 for r in keep]
    return {"lead": round(st.median(lead), 1) if lead else None,
            "lead85": round(q(lead, .85), 1) if lead else None,
            "relWait": round(st.median(wait), 1) if wait else None,
            "dev": round(st.median(dev), 1) if dev else None,
            "shipped": len(recs), "leadN": len(keep),
            "estDates": sum(1 for r in keep if r.get("estimated")),
            "untraceable": len(recs) - len(keep)}


# Route split. Which route a change took only means something against what its own
# repository does: a Modern-by-Default service has no team branch to skip, so its
# merge into main is hop one, not a hop skipped. So the repos are classified first,
# from their own six months of merges, and only then are the changes bucketed.
def _routes():
    def win(per):
        y, mm = map(int, per.split("-"))
        s = datetime(y, mm, 1, tzinfo=tz.utc)
        return s, datetime(y + (mm == 12), 1 if mm == 12 else mm + 1, 1, tzinfo=tz.utc)
    repos = sorted({(r["owner"], r["repo"]) for r in RT})
    fetched = {}
    for owner, name in repos:
        for per in periods:
            s, u = win(per)
            v = dm.cache_get(f"prs:v3:{owner}/{name}:{dm.iso(s)}:{dm.iso(u)}", 24 * 365)
            if v:
                fetched[(name, per)] = v
    uses_team = {}
    for (name, _), v in fetched.items():
        for pr in v:
            if not pr.get("mergedAt") or dm.is_noise(pr) or dm.is_integration(pr):
                continue
            if dm.SHARED_BRANCH_RE.match(pr.get("base", "")):
                uses_team[name] = True
    out = {}
    for (name, per), v in fetched.items():
        for pr in v:
            if not pr.get("mergedAt") or dm.is_noise(pr) or dm.is_integration(pr):
                continue
            m, fc = dt(pr["mergedAt"]), dt(pr.get("firstCommitAt"))
            if not (m and fc and m >= fc):
                continue
            base = pr.get("base", "")
            if dm.SHARED_BRANCH_RE.match(base):
                route = "team"
            elif base in dm.TRUNK_BRANCHES:
                route = "exception" if uses_team.get(name) else "noTeamBranch"
            else:
                continue
            out.setdefault(per, {}).setdefault(route, []).append(
                (m - fc).total_seconds() / 3600)
    return out


def _tickets():
    """Ticket-level dev time per period, pooled over the whole platform.

    Folds the same cached pull requests into tickets by Jira key, so a feature
    branched in four repos is one row rather than four. Deduplicated by ticket id
    within the period, which is what the per-area rows cannot be summed to give.
    """
    def win(per):
        y, mm = map(int, per.split("-"))
        s = datetime(y, mm, 1, tzinfo=tz.utc)
        return s, datetime(y + (mm == 12), 1 if mm == 12 else mm + 1, 1, tzinfo=tz.utc)
    out = {}
    for owner, name in sorted({(r["owner"], r["repo"]) for r in RT}):
        for per in periods:
            s, u = win(per)
            for pr in dm.cache_get(f"prs:v3:{owner}/{name}:{dm.iso(s)}:{dm.iso(u)}", 24 * 365) or []:
                if not pr.get("mergedAt") or dm.is_noise(pr) or dm.is_integration(pr):
                    continue
                m, fc = dt(pr["mergedAt"]), dt(pr.get("firstCommitAt"))
                if not (m and fc and m >= fc):
                    continue
                for tid in dm.ticket_id(pr, name):
                    t = out.setdefault(per, {}).setdefault(
                        tid, {"first": fc, "last": m, "repos": set(), "synthetic": "#" in tid})
                    t["first"] = min(t["first"], fc)
                    t["last"] = max(t["last"], m)
                    t["repos"].add(name)
    stats = {}
    for per, tix in out.items():
        h = sorted((t["last"] - t["first"]).total_seconds() / 3600 for t in tix.values())
        n = len(h)
        q = lambda x: h[min(n - 1, int(round(x * (n - 1))))]
        stats[per] = {"tickets": n,
                      "dev50": round(q(.5), 1) if n else None,
                      "dev85": round(q(.85), 1) if n else None,
                      "multiRepo": sum(1 for t in tix.values() if len(t["repos"]) > 1),
                      "noKeyPct": round(100 * sum(1 for t in tix.values() if t["synthetic"]) / n, 1)
                                  if n else None}
    return stats


def _ticket_origins():
    """When each ticket's work began, across the WHOLE window rather than per month.

    Cycle time is measured per ticket -- a feature is branched in every repository it
    touches -- so lead time has to be, or the two are not segments of one journey.
    A ticket that starts in May and ships in August has its origin in May's cache,
    which is why this is built over every period at once.
    """
    out = {}
    for owner, name in sorted({(r["owner"], r["repo"]) for r in RT}):
        for per in periods:
            y, mm = map(int, per.split("-"))
            s = datetime(y, mm, 1, tzinfo=tz.utc)
            u = datetime(y + (mm == 12), 1 if mm == 12 else mm + 1, 1, tzinfo=tz.utc)
            for pr in dm.cache_get(f"prs:v3:{owner}/{name}:{dm.iso(s)}:{dm.iso(u)}", 24 * 365) or []:
                if not pr.get("mergedAt") or dm.is_noise(pr) or dm.is_integration(pr):
                    continue
                fc = dt(pr.get("firstCommitAt"))
                if not fc:
                    continue
                # Only real Jira keys join across repositories; a synthetic per-PR id
                # cannot be matched to anything on a release page.
                for tid in dm.jira_keys(pr):
                    t = out.setdefault(tid, {"first": fc, "repos": set()})
                    t["first"] = min(t["first"], fc)
                    t["repos"].add(name)
    return out


def _ticket_lead(pool, origins):
    """Ticket-level lead time: first commit in any repository -> live in production.

    A ticket is dated by the FIRST release that carried any of its changes, and only
    counted where its origin is known from the window. The origin is capped at the
    window's start, so a ticket that began before March is dropped rather than
    reported with a truncated clock.
    """
    first_release = {}
    for recs in pool.values():
        for rec in recs:
            gl = dt(rec.get("goLive"))
            if not gl:
                continue
            # Same key rules as everywhere else, so the two sides of the join agree.
            for k in dm.jira_keys({"title": rec.get("title", ""), "branch": ""}):
                if k not in first_release or gl < first_release[k]:
                    first_release[k] = gl
    win_start = datetime.fromisoformat(periods[0] + "-01").replace(tzinfo=tz.utc)
    by_period, unknown, truncated = {}, 0, 0
    for k, gl in first_release.items():
        o = origins.get(k)
        if not o:
            unknown += 1
            continue
        if o["first"] <= win_start:
            truncated += 1
            continue
        if gl < o["first"]:
            continue
        by_period.setdefault(gl.strftime("%Y-%m"), []).append(
            {"lead": (gl - o["first"]).total_seconds() / 3600 / 24, "repos": o["repos"]})
    return by_period, unknown, truncated


def _ticket_lead_stats(rows):
    if not rows:
        return {"tLead": None, "tLead85": None, "tLeadN": 0}
    v = sorted(r["lead"] for r in rows)
    q = lambda x: v[min(len(v) - 1, int(round(x * (len(v) - 1))))]
    return {"tLead": round(q(.5), 1), "tLead85": round(q(.85), 1), "tLeadN": len(v)}


def _split_stats(routes):
    """routes: {"team": [...], "exception": [...], "noTeamBranch": [...]} of hours."""
    q = lambda a, x: sorted(a)[min(len(a) - 1, int(round(x * (len(a) - 1))))]
    out = {}
    n = sum(len(v) for v in routes.values())
    for name in ("team", "exception", "noTeamBranch"):
        v = routes.get(name, [])
        out[name + "N"] = len(v)
        out[name + "P50"] = round(st.median(v), 1) if v else None
        out[name + "P85"] = round(q(v, .85), 1) if v else None
    out["direct"] = (round(100 * (out["exceptionN"] + out["noTeamBranchN"]) / n, 1)
                     if n else None)
    out["exceptionPct"] = round(100 * out["exceptionN"] / n, 1) if n else None
    return out


def collect(level):
    ids = {}
    for r in rows:
        if r["level"] == level:
            ids.setdefault(r["id"], r)
    return ids

areas = []
for ident, sample in collect("area").items():
    areas.append({"title": sample["title"],
                  "repos": max(r["repos"] for r in rows if r["level"] == "area" and r["id"] == ident),
                  "months": months_for("area", ident)})
areas.sort(key=lambda a: -sum(m["prs"] for m in a["months"]))

products = []
for ident, sample in collect("product").items():
    products.append({"id": ident, "title": sample["title"],
                     "area": prod_area.get(ident, "—"),
                     "repos": max(r["repos"] for r in rows if r["level"] == "product" and r["id"] == ident),
                     "months": months_for("product", ident)})
products.sort(key=lambda p: (p["area"], -sum(m["prs"] for m in p["months"])))

# Platform: PR counts summed from the areas; p50/p85 pooled over every PR, which is
# what the script's ALL row does — a median of medians would be meaningless.
def dt(s): return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None
seen, hours = set(), {}
for f in glob.glob(".metrics-cache/*.json"):
    try: d = json.load(open(f))
    except Exception: continue
    v = d.get("value") if isinstance(d, dict) else d
    if not isinstance(v, list): continue
    for pr in v:
        if not isinstance(pr, dict) or "mergedAt" not in pr: continue
        # Pre-"base" cache entries are a stale copy of the same PRs; the current
        # records carry the base branch and are the ones to pool.
        if "base" not in pr: continue
        k = (pr.get("number"), pr.get("mergedAt"), pr.get("title"))
        if k in seen: continue
        seen.add(k)
        if dm.is_noise(pr) or dm.is_integration(pr): continue
        m, fc = dt(pr["mergedAt"]), dt(pr.get("firstCommitAt"))
        if not (m and fc and m >= fc): continue
        hours.setdefault(m.strftime("%Y-%m"), []).append((m - fc).total_seconds() / 3600)

# True lead time, pooled over every change that reached production in the month.
lead_pool = {}
ticket_lead = {}
try:
    from datetime import timezone
    _cfg = dm.confluence_config()
    _since = datetime.fromisoformat(periods[0] + "-01").replace(tzinfo=timezone.utc)
    _end = datetime.fromisoformat(periods[-1] + "-01").replace(tzinfo=timezone.utc)
    _until = (_end.replace(year=_end.year + 1, month=1) if _end.month == 12
              else _end.replace(month=_end.month + 1))
    _rel = dm.walk_release_pages(_cfg, _since, _until, 24.0 * 7)
    for recs in dm.release_lead_times(_rel, 24.0 * 30).values():
        for rec in recs:
            lead_pool.setdefault(rec["period"], []).append(rec)
    print("  lead-time records pooled:", sum(len(v) for v in lead_pool.values()))
    # Lead time on the same unit as cycle time: per ticket, first commit in any
    # repository to the go-live of the first release that carried it.
    _origins = _ticket_origins()
    ticket_lead, _tl_unknown, _tl_trunc = _ticket_lead(lead_pool, _origins)
    print(f"  ticket-level lead: {sum(len(v) for v in ticket_lead.values())} tickets "
          f"({_tl_unknown} released with no origin in the window, "
          f"{_tl_trunc} started before it)")
except Exception as exc:
    print("  lead time unavailable:", exc)

routes = _routes()
print('  route split:', {k: {r: len(v) for r, v in d.items()} for k, d in sorted(routes.items())})

tickets_by_period = _tickets()
platform = []
for p in periods:
    h = sorted(hours.get(p, []))
    n = len(h)
    q = (lambda x: h[min(n - 1, int(round(x * (n - 1))))]) if n else (lambda x: None)
    prs = sum(m["prs"] for a in areas for m in a["months"] if m["period"] == p)
    corr = sum(m["corrective"] for a in areas for m in a["months"] if m["period"] == p)
    if n and n != prs:
        print(f"  note {p}: pooled sample {n} vs area total {prs}")
    am = [r for r in rows if r["level"] == "area" and r["period"] == p]
    timed = sum(r["time_to_main_samples"] or 0 for r in am)
    und = sum(r["on_main_undated"] or 0 for r in am)
    infl = sum(r["in_flight_changes"] or 0 for r in am)
    settled = timed + und + infl
    platform.append({"period": p, "prs": prs, "corrective": corr,
                     "onMain": round(100 * (timed + und) / settled, 1) if settled else None,
                     "inFlight": infl,
                     "cfr": round(100 * corr / prs, 1) if prs else None,
                     "p50": round(q(.5), 1) if n else None,
                     "p85": round(q(.85), 1) if n else None,
                     "mean": round(st.mean(h) / 24, 1) if n else None,
                     "over30": round(100 * sum(1 for x in h if x / 24 > 30) / n, 1) if n else None,
                     **_lead_stats(lead_pool.get(p, [])),
                     **_ticket_lead_stats(ticket_lead.get(p, [])),
                     **_split_stats(routes.get(p, {})),
                     **tickets_by_period.get(p, {}),
                     # Counts sum exactly across areas; medians do not, which is why
                     # dev time above is pooled from the tickets themselves.
                     "viaTeam": sum(r.get("tickets_via_team") or 0 for r in am),
                     "released": (round(100 * sum(r.get("tickets_on_main") or 0 for r in am)
                                        / sum(r.get("tickets_via_team") or 0 for r in am), 1)
                                  if sum(r.get("tickets_via_team") or 0 for r in am) else None),
                     "queueN": sum(r.get("queue_samples") or 0 for r in am)})

# Repository level. A subdomain modelled as a single product (Scheduling & Listing,
# DLRM, Common Platform UI) has nothing to show one level down, so the repository is
# the level that always resolves to something.
repo_meta = {}
for r in RT:
    repo_meta.setdefault(r["repo"], {"area": r["area"], "product": r["product"],
                                     "productTitle": r["productTitle"],
                                     "components": []})
    repo_meta[r["repo"]]["components"].append(r["component"])

repos_out = []
for ident, sample in collect("repo").items():
    meta = repo_meta.get(ident, {})
    repos_out.append({"repo": ident,
                      "area": meta.get("area", "\u2014"),
                      "product": meta.get("product", "\u2014"),
                      "components": meta.get("components", []),
                      "months": months_for("repo", ident)})
repos_out.sort(key=lambda r: (r["area"], r["product"], -sum(m["prs"] for m in r["months"])))

# Pooled across every shipped change in the window, so the headline figure and the
# prose quote the same number rather than a median of monthly medians.
overall = _lead_stats([r for v in lead_pool.values() for r in v])
overall.update(_ticket_lead_stats([r for v in ticket_lead.values() for r in v]))
overall["releases"] = len(_rel) if "_rel" in dir() else None
_all_routes = {}
for _d in routes.values():
    for _r, _v in _d.items():
        _all_routes.setdefault(_r, []).extend(_v)
overall.update(_split_stats(_all_routes))

# The delivery-model lane. Read straight from the `model` level in the history
# rather than re-derived here, so the page and the collector cannot drift apart.
LANES = ["Trunk-based, no integration branch", "Via an integration branch"]
lanes = []
for title in LANES:
    ident = next((r["id"] for r in rows if r["level"] == "model" and r["title"] == title), None)
    if ident is None:
        continue
    lanes.append({"title": title,
                  "repos": max((r["repos"] for r in rows
                                if r["level"] == "model" and r["id"] == ident), default=0),
                  "months": months_for("model", ident)})

out = {"periods": periods, "areas": areas, "platform": platform, "lanes": lanes,
       "products": products, "repos": repos_out, "overall": overall}
open("/private/tmp/claude-501/-Users-dineshsharma-cpp/72bc58ca-ccfe-43f5-9324-23830fc1cb28/scratchpad/data.json", "w").write(json.dumps(out, separators=(",", ":")))
print("lanes:", [(l["title"], sum(m["prs"] for m in l["months"])) for l in lanes])
print("areas:", len(areas), "products:", len(products), "repos:", len(repos_out))
for p in platform: print(p)
print("overall:", overall)
