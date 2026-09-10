# GreenCalculus open factor data

[![factors](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fgreencalculus%2Fgreencalculus-open-data%2Fmain%2Fmanifest.json&query=%24.rows_total&label=factors&color=04BF62)](./coverage/index.csv)
[![republishable](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fgreencalculus%2Fgreencalculus-open-data%2Fmain%2Fmanifest.json&query=%24.rows_redistributable&label=republishable&color=04BF62)](./LICENCES.md)
[![data version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fgreencalculus%2Fgreencalculus-open-data%2Fmain%2Fmanifest.json&query=%24.data_version&label=data&color=04BF62)](https://verify.greencalculus.com)
[![no API key](https://img.shields.io/badge/API%20key-not%20needed-04BF62)](https://greencalculus.com/developers/)
[![licence](https://img.shields.io/badge/licence-MIT-blue)](./LICENSE)

**What the GreenCalculus corpus covers — 16,673 emission factors from 137
publishers, with each publisher's licence and whether it may be republished.**

Every row is generated from the live API by [`build.py`](./build.py). Nothing is
hand-maintained: the licence filter is each publisher's own terms as recorded in
the API response, so an upstream licence re-review changes this export on the
next run.

Data version **2026.188** (2026-09-10).

## What's here

**[`coverage/index.csv`](./coverage/index.csv)** — 16,673 rows, one per factor
key. Key, name,
section, unit, gas, GHG Protocol scope, publisher, licence, whether it's
redistributable, and why not when it isn't.

**No factor values.** This is GreenCalculus's own metadata about what the corpus
covers, not any publisher's data — so it is publishable regardless of upstream
terms, and you can use it freely to answer "is there a factor for X?" without
worrying about anyone's licence.

**[`LICENCES.md`](./LICENCES.md)** — every source, its publisher, its licence,
and the attribution line that licence requires. Plus every excluded source with
the publisher's own stated reason, verbatim.

## Want the numbers?

The values are not in this repo. Look any factor up from the API — **no API key
needed**, the corpus is open to read:

```bash
curl "https://api.greencalculus.com/v1/factors?key_prefix=grid.gbr.electricity.location_based&limit=1"
```

```python
pip install greencalculus
```
```python
from greencalculus import GreenCalculus
f = GreenCalculus().factor("grid.gbr.electricity.location_based")   # no key
print(f["value"], f["unit"])                       # 0.13096 kg CO2e per kWh
print(f["factor"]["source"]["cell_ref"])           # 'UK electricity'!E25
print(f["factor"]["citation"]["proof_url"])        # a page your reader can check
```

Every factor also has a permanent verification page showing the publisher, the
document, the exact cell and whether it may be republished —
`verify.greencalculus.com/<key>`.

## The split

Of 16,673 factors across 137 sources:

- **15,347 factors / 75 sources** carry a licence that permits republication
  (Open Government Licence, CC BY 4.0, Etalab, US public domain, Eurostat reuse…).
- **1,326 factors / 62 sources** do not, and the reason is the publisher's own:
  paid standards (ISO, EN 15978), NonCommercial or NoDerivatives terms (PCAF,
  SBTi, WBCSD Pathfinder), share-alike that would be viral over your results
  (EXIOBASE, ecoinvent), or simply no grant found (ICAO).

One source is **held back by hand**: `IEA_AI_ENERGY_2025` is flagged CC BY 4.0
upstream, which conflicts with our reading of the IEA's terms on third-party
footprints. It stays out until that is resolved with the publisher. The
`DENY` set in `build.py` can only ever *remove* a source, never add one, so a
mistake there costs coverage rather than causing a licence breach.

## Rebuild

```bash
python3 build.py                # coverage/ + LICENCES.md   (what this repo ships)
python3 build.py --with-values  # also open/ — the republishable subset WITH values
```

`open/` is gitignored. Whether to publish values is a deliberate decision, not a
build flag away from happening by accident.

## Licence

Code: MIT. `coverage/index.csv` is GreenCalculus metadata, published CC BY 4.0 —
attribute *GreenCalculus (greencalculus.com)*. Factor **values** obtained from
the API carry the licence of their underlying source, named in every response.
