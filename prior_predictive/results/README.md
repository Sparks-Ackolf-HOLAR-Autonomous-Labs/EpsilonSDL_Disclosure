# Prior-predictive run outputs (2026-09-02, DGX Spark)

- `raw_results.json.gz` — canonical dataset of record: 11,750 world-condition
  records (1,000 main worlds x 10 conditions + 250 sweep worlds x 7).
  NOTE: this run predates the stable-seed fix in `simulator.py` (world seeds
  came from Python's process-salted `hash()`), so re-running reproduces the
  same *distributions* but not these exact worlds. Future runs are exactly
  reproducible.
- `summary.json` — per-condition win-win/component probabilities, per prior
  card, threshold pass/fail, minimal-contract search.
- `drivers.json` — world-parameter correlations with win-win components
  (value-of-information screen behind the pilot design).
- PNG figures — see `../RESULTS.md`.

All node-hours are simulated units; nothing here is a CHPC measurement.
