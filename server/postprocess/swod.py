"""SWOD (pnnl-emt-swod) post-process report generator."""
from __future__ import annotations

import logging
from pathlib import Path

from pnnl_emt_swod.plotting import plot_results_from_feather

from . import common as C

logger = logging.getLogger(__name__)


def build_sections(run_dir: Path) -> tuple[str, list[tuple[str, str]]]:
    run_dir = Path(run_dir)
    sections: list[tuple[str, str]] = []
    
    outputs_dir = run_dir / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    import shutil
    for ext in ("*.feather", "*.csv"):
        for path in run_dir.rglob(ext):
            if path.parent != outputs_dir:
                dest = outputs_dir / path.name
                if not dest.exists():
                    try:
                        shutil.copy(path, dest)
                    except Exception:
                        pass

    needed = ["swod_oscillation_frequency.feather", "swod_real_ssp.feather"]
    missing = [f for f in needed if not (outputs_dir / f).exists()]
    
    if missing:
        sections.append(
            ("SWOD Post-process Report", f"<p>Required output files not found: {', '.join(missing)}. Simulation may not have completed successfully.</p>")
        )
        return "Sliding Window Oscillation Detection — Report", sections
        
    try:
        figures = plot_results_from_feather(outputs_dir)
    except Exception as e:
        sections.append(
            ("SWOD Post-process Report", f"<p>Error generating figures from recorded simulation data: {e}</p>")
        )
        return "Sliding Window Oscillation Detection — Report", sections

    if len(figures) >= 1:
        sections.append(("Dissipation Energy Factor (DEF) per Channel", C.img_html(figures[0])))
    if len(figures) >= 2:
        sections.append(("Sub/Super-synchronous Power (SSP) per Channel", C.img_html(figures[1])))
    if len(figures) >= 3:
        sections.append(("Apparent Oscillation Power & Participation Index", C.img_html(figures[2])))
    if len(figures) >= 4:
        sections.append(("Oscillation Frequency & Amplitude Distribution", C.img_html(figures[3])))
    if len(figures) >= 5:
        sections.append(("Grid Network Topology & Oscillation Origin Map", C.img_html(figures[4])))

    # Summary stat band
    try:
        import pandas as pd
        import numpy as np
        from pnnl_emt_swod.plotting import V_ABC_TO_BUS

        freq_df = pd.read_feather(outputs_dir / "swod_oscillation_frequency.feather")
        amp_df = pd.read_feather(outputs_dir / "swod_oscillation_amplitude.feather")
        all_channels = [c for c in freq_df.columns if c not in ("time", "Time")]
        p1_channels = [c for c in all_channels if c.endswith("_1")]
        if not p1_channels:
            p1_channels = all_channels

        n_detections = 0
        active_buses = set()
        bus_parts = {}

        for ch in p1_channels:
            freqs = freq_df[ch].to_numpy()
            amps = amp_df[ch].to_numpy()
            det_mask = freqs > 0.01
            raw_v = ch.split("_")[0]
            bus_name = V_ABC_TO_BUS.get(raw_v, raw_v)
            if np.any(det_mask):
                active_buses.add(bus_name)
                n_detections += int(np.sum(det_mask))
                bus_parts[bus_name] = max(bus_parts.get(bus_name, 0.0), float(np.mean(amps[det_mask])))

        origin_bus = max(bus_parts, key=bus_parts.get) if bus_parts else "Unknown"

        stats_items = [
            ("Monitored Buses", str(len(p1_channels))),
            ("Buses with Detections", str(len(active_buses))),
            ("Active Detections Count", str(n_detections)),
            ("Oscillation Origin Bus", f"Bus {origin_bus}"),
        ]
        sections.insert(0, ("Detection & Source Summary", C.stat_band(stats_items)))
    except Exception:
        pass

    return "Sliding Window Oscillation Detection — Report", sections


def notebook_render(run_dir) -> None:
    _title, sections = build_sections(Path(run_dir))
    C.display_sections(sections)
