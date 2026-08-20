# simulation/params

Fitted distribution artifacts; the simulator reads only these, never the raw sources (A1).

- `lendingclub_marginals.json`, `auction_landscape.json`, `uplift_params.json` — written by the profiling notebooks (`analysis/profiling/01-03`).
- `repeat_applications.json` — written by `analysis/profiling/04_repeat_applications.py` from a private source table (author's industry data, P-010/C18); the committed artifact carries only the fitted two-parameter form and rounded QA targets.
