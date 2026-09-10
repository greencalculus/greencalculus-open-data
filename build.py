#!/usr/bin/env python3
"""Build the open GreenCalculus factor exports from the live API.

Two products, deliberately separate:

  coverage/   WHAT the corpus contains — key, name, section, publisher, unit,
              licence, redistributable. No factor values. This is GreenCalculus's
              own metadata about coverage, not any publisher's data, so it can be
              published whatever the upstream licence says.

  open/       The redistributable SUBSET, values included — only rows whose
              publisher licence the corpus itself flags redistributable.

Nothing here is hand-maintained: the licence filter is the publishers' own
terms as recorded in the API response, so a licence re-review upstream changes
this export on the next run.

Usage:  python build.py [--with-values]
"""
import argparse, csv, json, sys, time, urllib.parse, urllib.request
from collections import Counter
from pathlib import Path

BASE = "https://api.greencalculus.com/v1/factors"

# Human override. The API's own `redistributable` flag is the baseline; this set
# can only ever REMOVE a source from the open export, never add one — so a wrong
# entry here costs coverage, not a licence breach.
#
#   IEA_AI_ENERGY_2025 — the corpus flags it CC BY 4.0 / redistributable, but our
#   licence audit found the IEA prohibits third-party publication of derived
#   footprints. Held out until that conflict is resolved with the publisher.
DENY = {
    "IEA_AI_ENERGY_2025",
}
UA = "greencalculus-open-data/1.0 (+https://github.com/jeremiahsay/greencalculus-sdk)"
OUT = Path(__file__).parent


def get(**params):
    url = BASE + "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def fetch_all():
    rows, licences, cursor, pages = [], {}, None, 0
    while True:
        page = get(limit=500, cursor=cursor)
        meta = page["meta"]
        licences.update(meta.get("licences") or {})
        batch = page.get("factors") or []
        rows.extend(batch)
        pages += 1
        cursor = meta.get("next_cursor")
        print(f"\r  page {pages:>3}  rows {len(rows):>6,}", end="", file=sys.stderr, flush=True)
        if not cursor or not batch:
            print(file=sys.stderr)
            return rows, licences, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-values", action="store_true",
                    help="also write open/ — the redistributable subset WITH factor values")
    args = ap.parse_args()

    print("Fetching the corpus (keyless, edge-cached)…", file=sys.stderr)
    rows, licences, meta = fetch_all()
    version, updated = meta["gc_version"], meta["gc_updated"]
    print(f"  {len(rows):,} rows at data version {version} ({updated})", file=sys.stderr)

    def lic(r):
        return licences.get((r.get("source") or {}).get("id")) or {}

    def src_id(r):
        return (r.get("source") or {}).get("id")

    def publishable(r):
        return lic(r).get("redistributable") is True and src_id(r) not in DENY

    ok = [r for r in rows if publishable(r)]
    no = [r for r in rows if not publishable(r)]
    held = sorted({src_id(r) for r in rows if lic(r).get("redistributable") is True and src_id(r) in DENY})
    if held:
        print(f"  held out by DENY despite an open licence flag: {', '.join(held)}", file=sys.stderr)

    # ---------- coverage: no values ----------
    (OUT / "coverage").mkdir(exist_ok=True)
    with (OUT / "coverage" / "index.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["key", "name", "section", "activity_type", "unit", "gas", "scope",
                    "source_id", "publisher", "licence", "redistributable", "excluded_reason", "updated"])
        for r in sorted(rows, key=lambda r: r["key"]):
            f, s, L = r.get("factor") or {}, r.get("source") or {}, lic(r)
            w.writerow([r["key"], r.get("name"), r.get("section"), r.get("activity_type"),
                        f.get("unit"), f.get("gas"), (r.get("scope") or {}).get("ghg_protocol"),
                        s.get("id"), L.get("publisher"), L.get("name"),
                        "yes" if publishable(r) else "no",
                        "" if publishable(r) else ("held: licence conflict under review"
                                                   if s.get("id") in DENY else "publisher terms"),
                        r.get("updated")])

    # ---------- licences ----------
    counts = Counter((r.get("source") or {}).get("id") for r in rows)
    lines = [f"# Sources and licences\n",
             f"Data version **{version}** ({updated}) · {len(rows):,} factors from {len(counts)} sources.\n",
             "Attribution is a condition of nearly every licence below. If you use the open",
             "export, reproduce the attribution line for each source you actually use.\n",
             "## Redistributable\n",
             "| Rows | Source | Publisher | Licence | Attribution required |",
             "|---:|---|---|---|---|"]
    for sid, n in counts.most_common():
        L = licences.get(sid) or {}
        if L.get("redistributable") is not True or sid in DENY:
            continue
        lines.append(f"| {n:,} | `{sid}` | {L.get('publisher','')} | {L.get('name','')} | {L.get('attribution','')} |")
    lines += ["\n## Excluded — not redistributable\n",
              "These are served by the API (you may look them up and cite them) but their",
              "upstream terms do not allow us to republish the values in bulk. The reason is",
              "the publisher's, recorded verbatim.\n",
              "| Rows | Source | Licence | Why excluded |", "|---:|---|---|---|"]
    for sid, n in counts.most_common():
        L = licences.get(sid) or {}
        if L.get("redistributable") is True and sid not in DENY:
            continue
        why = ("**held — licence conflict under review**" if sid in DENY else L.get('basis', '—'))
        lines.append(f"| {n:,} | `{sid}` | {L.get('name','—')} | {why} |")
    (OUT / "LICENCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---------- open subset, values ----------
    if args.with_values:
        (OUT / "open").mkdir(exist_ok=True)
        with (OUT / "open" / "factors.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["key", "name", "value", "unit", "gas", "gwp_set", "basis", "section",
                        "scope", "country_iso3", "source_id", "publisher", "cell_ref",
                        "retrieved", "licence", "attribution", "data_version", "proof_url"])
            for r in sorted(ok, key=lambda r: r["key"]):
                f, s, L = r.get("factor") or {}, r.get("source") or {}, lic(r)
                c = r.get("citation") or {}
                w.writerow([r["key"], r.get("name"), f.get("value"), f.get("unit"), f.get("gas"),
                            f.get("gwp_set"), f.get("basis"), r.get("section"),
                            (r.get("scope") or {}).get("ghg_protocol"), f.get("country_iso3"),
                            s.get("id"), L.get("publisher"), s.get("cell_ref"), s.get("retrieved"),
                            L.get("name"), L.get("attribution"), version, c.get("proof_url")])
        with (OUT / "open" / "factors.jsonl").open("w", encoding="utf-8") as fh:
            for r in sorted(ok, key=lambda r: r["key"]):
                fh.write(json.dumps({**r, "data_version": version}, ensure_ascii=False) + "\n")

    manifest = {
        "data_version": version, "data_updated": updated,
        "generated_from": "https://api.greencalculus.com/v1/factors (keyless)",
        "rows_total": len(rows), "rows_redistributable": len(ok), "rows_excluded": len(no),
        "sources_total": len(counts),
        "sources_redistributable": len({src_id(r) for r in ok}),
        "held_by_override": held,
        "values_included": bool(args.with_values),
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
