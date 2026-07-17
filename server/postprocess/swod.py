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
        sections.append(("Detected Oscillation Frequencies Over Time (Timeline)", C.img_html(figures[0])))
    if len(figures) >= 2:
        sections.append(("SSP (Real/Reactive Power) Over Time — All Channels", C.img_html(figures[1])))
    if len(figures) >= 3:
        sections.append(("Source Localization Snapshot — Time-Averaged", C.img_html(figures[2])))

    # Summary stat band
    try:
        import pandas as pd
        freq_df = pd.read_feather(outputs_dir / "swod_oscillation_frequency.feather")
        channels = [c for c in freq_df.columns if c != "time"]
        
        # Calculate some summary stats
        n_detections = 0
        active_channels = []
        for ch in channels:
            if (freq_df[ch] > 0.01).any():
                active_channels.append(ch)
                n_detections += int((freq_df[ch] > 0.01).sum())
                
        stats_items = [
            ("Monitored Channels", str(len(channels))),
            ("Channels with Detections", str(len(active_channels))),
            ("Active Detections count", str(n_detections)),
        ]
        sections.insert(0, ("Detection Summary", C.stat_band(stats_items)))
    except Exception:
        pass

    return "Sliding Window Oscillation Detection — Report", sections


def notebook_render(run_dir) -> None:
    _title, sections = build_sections(Path(run_dir))
    C.display_sections(sections)
