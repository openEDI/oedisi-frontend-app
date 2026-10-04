# Post-process reports

Per-use-case result reports, rendered from a **parameterized Jupyter notebook** into
static HTML and served from the run page ("Post-process report" button on finished
runs). This is an interim result view until native plotting lands in the UI — each
use case needs different post-processing, so each use case owns its own figures.

## How it works

```
POST /api/runs/{run_id}/report        (first call generates, later calls hit the cache)
GET  /api/runs/{run_id}/report        (serves the cached HTML)
```

1. `report.py` detects the run's use case from its `wiring.json` component types.
2. It executes `notebooks/<usecase>_report.ipynb` headlessly (nbclient), injecting the
   run directory as a parameter, and converts it to HTML (nbconvert, code hidden).
3. The HTML is cached at `runs/<user>/<run_id>/report/report.html` together with a
   `meta.json` (engine used, generation time, comparison context). The cache
   invalidates itself when the comparison context changes (e.g. a new baseline run
   appears for the EV report).
4. If the notebook engine fails for any reason, the same figures are rendered
   directly in-process — the button always works.

The notebooks are thin wrappers: all figure logic lives in this package, so one can also open the notebook interactively (Jupyter / VS Code), point it at any run directory, and customize the analysis.

## Add a report for YOUR use case (5 edits)

1. **Create `server/postprocess/<yourcase>.py`** with one required function:

   ```python
   def build_sections(run_dir: Path) -> tuple[str, list[tuple[str, str]]]:
       """Return (report_title, [(section_heading, section_html), ...])."""
   ```

   **This function is the flexible part — it's where your figures go.** Each section
   is `(heading, html)`, and that `html` can be anything self-contained: your own
   matplotlib styling, Plotly, custom HTML/CSS. The framework never inspects it, so
   your report looks however you want.

   For the EV/OD example style, the optional helpers in `common.py` are:
   `img_html(fig)` (matplotlib figure → embedded PNG), `table_html(headers, rows)`,
   `stat_band([(label, value), ...])`, plus `load_wiring(run_dir)` /
   `component_params(wiring, "YourComponent")` to read the run. Add a
   `notebook_render(run_dir)` passthrough (copy the two lines from `ev.py`).

   > **What's yours vs. shared:** you fully control the content *inside* every
   > section (your figures, your style). The page frame around them — background,
   > section cards, heading fonts — comes from `common.py` and is shared across all
   > use cases for a consistent look.

2. **Register the builder** in `report.py` → `_BUILDERS = {..., "yourcase": yourcase_mod.build_sections}`.

3. **Register detection** in `report.py` → `detect_usecase()`: map your component
   type (as it appears in `wiring.json`) to `"yourcase"`.

4. **Register the output gate** in `report.py` → `_require_outputs()`: the files that
   must exist under `runs/.../outputs/` before a report makes sense (the endpoint
   returns 409 "wait for the run to finish" until they do).

5. **Copy a notebook**: duplicate `notebooks/ev_report.ipynb` →
   `<yourcase>_report.ipynb`, change the title cell and the module name in the render
   cell, and add it to `_NOTEBOOKS` in `report.py`.

Optional: implement `context_signature(run_dir) -> str` and register it in
`_CONTEXTS` if your report compares against a companion run (see `ev.py` — it pairs
a controlled run with its uncontrolled baseline and re-generates the cached report
automatically when a new baseline appears).

Restart the backend; the button appears on finished runs of your use case.

## Reference implementations

- `ev.py` — EV scheduling: feeder voltage map/profile, demand and EV-load overlays
  against the uncontrolled baseline run, cumulative-energy shift/trim view.
- `od.py` — oscillation detection: measured-signal detection timeline, mode
  frequency vs truth, damping/stability panel, ground-truth metrics scorecard.
