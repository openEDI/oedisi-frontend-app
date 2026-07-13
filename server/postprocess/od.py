"""OD (ornl-od) post-process: detected-event figures + tables for one run.

Data sources (inside the run dir):
  outputs/events.feather  -> one row per detected event (mode_0..4 freq/damping/amp/phase)
  build/**/<player csv>   -> measured input signal (detection-timeline backdrop)
  wiring.json ODComponent.parameters.ground_truth_json (optional) -> truth comparison
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from . import common as C


def _load_events(run_dir: Path) -> pd.DataFrame:
    path = run_dir / "outputs" / "events.feather"
    if not path.exists():
        raise FileNotFoundError(f"events.feather not found in {run_dir / 'outputs'}")
    df = pd.read_feather(path)
    if "event_id" in df.columns:
        df = df.drop_duplicates(subset="event_id", keep="last").reset_index(drop=True)
    return df


def _ground_truth(run_dir: Path) -> list[dict] | None:
    wiring = C.load_wiring(run_dir)
    params = C.component_params(wiring, "ODComponent")
    raw = params.get("ground_truth_json")
    if not raw:
        return None
    try:
        truth = json.loads(raw) if isinstance(raw, str) else raw
        return truth if isinstance(truth, list) and truth else None
    except (ValueError, TypeError):
        return None


def _signal(run_dir: Path):
    """Measured input signal from the Player CSV: (t_seconds, freq_dev_mHz, label).

    The build dir carries a copy of the component data, so the plot works on any
    machine the run was made on; falls back to OEDISI_COMPONENTS for older runs.
    """
    try:
        wiring = C.load_wiring(run_dir)
        params = C.component_params(wiring, "Player")
    except Exception:  # noqa: BLE001
        return None
    fname = str(params.get("filename") or "").replace("\\", "/")
    if not fname:
        return None
    base = fname.rsplit("/", 1)[-1]
    cands = [p for p in (run_dir / "build").rglob(base) if p.is_file()]
    if not cands:
        comp_root = os.environ.get("OEDISI_COMPONENTS")
        if comp_root and "/components/" in fname:
            c = Path(comp_root) / fname.split("/components/", 1)[1]
            if c.exists():
                cands = [c]
    if not cands:
        return None
    try:
        sig = pd.read_csv(cands[0])
        tcol = sig.columns[0]
        units = [c for c in sig.columns if c != tcol]
        if not units:
            return None
        try:
            tt = pd.to_datetime(sig[tcol])
            t = (tt - tt.iloc[0]).dt.total_seconds().to_numpy(dtype=float)
        except (ValueError, TypeError):
            step = float(params.get("run_freq_time_step") or 1.0)
            t = np.arange(len(sig)) * step
        y = pd.to_numeric(sig[units[0]], errors="coerce").to_numpy(dtype=float)
        n_steps = int(params.get("number_of_timesteps") or 0)
        if 0 < n_steps < len(t):
            t, y = t[:n_steps], y[:n_steps]
        dec = max(1, len(t) // 50000)
        t, y = t[::dec], y[::dec]
        dev_mhz = (y - np.nanmedian(y)) * 1000.0
        label = units[0].replace("_", " ")
        return t, dev_mhz, label
    except Exception:  # noqa: BLE001
        return None


def _match_pairs(df: pd.DataFrame, f0, truth):
    """Nearest-start matching (30 s tolerance), same rules as the metrics table."""
    if not truth or f0 is None:
        return [], set(), 0, 0
    used: set[int] = set()
    pairs: list[tuple[int, dict, int | None]] = []
    n = len(df)
    for k, tr in enumerate(truth):
        tf = tr.get("frequency_hz")
        ts = tr.get("start_time_sec")
        best_i, best_d = None, None
        for i in range(n):
            if i in used:
                continue
            if ts is not None and "start_time_sec" in df.columns:
                d = abs(float(df["start_time_sec"][i]) - float(ts))
                if d > 30.0:
                    continue
            elif tf:
                d = abs(float(f0[i]) - float(tf))
            else:
                continue
            if best_d is None or d < best_d:
                best_i, best_d = i, d
        if best_i is not None:
            used.add(best_i)
        pairs.append((k, tr, best_i))
    missed = sum(1 for _, _, i in pairs if i is None)
    fa = n - len(used)
    return pairs, used, missed, fa


def build_sections(run_dir: Path) -> tuple[str, list[tuple[str, str]]]:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    run_dir = Path(run_dir)
    df = _load_events(run_dir)
    n = len(df)
    sections: list[tuple[str, str]] = []

    if n == 0:
        sections.append(("Detected events", "<p>No oscillation events were detected in this run.</p>"))
        return "Oscillation Detection — Report", sections

    f0 = df.get("mode_0_freq_hz")
    d0 = df.get("mode_0_damping")

    show_cols = [c for c in [
        "event_id", "time", "start_time_sec", "reporting_time_sec", "n_voted_units",
        "mode_0_freq_hz", "mode_0_damping", "mode_0_amp",
    ] if c in df.columns]
    rows = []
    for _, r in df[show_cols].iterrows():
        row = []
        for c in show_cols:
            v = r[c]
            if isinstance(v, float):
                row.append(f"{v:.4g}")
            else:
                row.append(str(v))
        rows.append(row)
    events_section = (
        "Detected events (dominant mode)",
        C.table_html(show_cols, rows),
    )

    truth = _ground_truth(run_dir)
    pairs, m_used, m_missed, m_fa = _match_pairs(df, f0, truth)

    sig = _signal(run_dir)
    if sig is not None:
        t_s, dev_mhz, unit_label = sig
        fig, ax = plt.subplots(figsize=(10.8, 4.2))
        ax.plot(t_s, dev_mhz, color=C.MBLUE, lw=0.7,
                label=f"Measured frequency ({unit_label})")
        amp = float(np.nanmax(np.abs(dev_mhz))) if len(dev_mhz) else 1.0
        ylim = max(amp * 1.15, 1e-6)
        ax.set_ylim(-ylim, ylim)
        if truth:
            for k, tr in enumerate(truth):
                ts = tr.get("start_time_sec")
                if ts is None:
                    continue
                ts = float(ts)
                ax.axvline(ts, color="#666666", ls="--", lw=1.0)
                ax.axvspan(ts, ts + 60.0, color=C.ORANGE, alpha=0.12)
                ax.text(ts + 30.0, ylim * 0.87, f"E{k + 1}", color=C.ORANGE,
                        fontweight="bold", ha="center", fontsize=10)
        if "start_time_sec" in df.columns:
            ax.plot(df["start_time_sec"], np.zeros(n), "v", color=C.RED, ms=10,
                    zorder=5, ls="none", label="detection")
        if truth:
            sub = f"{len(m_used)}/{len(truth)} detected, {m_fa} false alarms, {m_missed} missed"
        else:
            sub = f"{n} event{'s' if n != 1 else ''} detected"
        ax.set_title(
            f"Detection timeline — measured signal · true onsets (dashed) · red = detection · {sub}",
            loc="left", fontsize=11, color=C.NAVY, fontweight="bold")
        ax.set_xlabel("time (s)")
        ax.set_ylabel("freq deviation (mHz)")
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(axis="y", color="#EDF0F4", lw=0.8)
        sections.append(("Detection timeline (measured signal)", C.img_html(fig)))
    elif "start_time_sec" in df.columns and f0 is not None:
        fig, ax = plt.subplots(figsize=(8.6, 3.6))
        colors = [C.RED if (d0 is not None and d < 0) else C.GREEN for d in (d0 if d0 is not None else [0] * n)]
        ax.stem(df["start_time_sec"], f0, basefmt=" ", linefmt="-", markerfmt="o")
        for x, y, col, eid in zip(df["start_time_sec"], f0, colors, df.get("event_id", range(1, n + 1))):
            ax.plot([x], [y], "o", color=col, ms=9, zorder=5)
            ax.annotate(f"E{int(eid)}", (x, y), textcoords="offset points", xytext=(6, 6),
                        fontsize=9, color=C.NAVY, fontweight="bold")
        ax.set_xlabel("event start time (s)")
        ax.set_ylabel("dominant frequency (Hz)")
        ax.set_title("Detection timeline — when events occurred and at what frequency (red = growing)",
                     loc="left", fontsize=11, color=C.NAVY, fontweight="bold")
        ax.grid(axis="y", color="#EDF0F4", lw=0.8)
        sections.append(("Detection timeline", C.img_html(fig)))

    if truth and f0 is not None:
        rows_fb = [(k, tr, i) for k, tr, i in pairs
                   if i is not None and tr.get("frequency_hz")]
        if rows_fb:
            fig, ax = plt.subplots(figsize=(7.6, 3.6))
            x = np.arange(len(rows_fb))
            tvals = [float(tr["frequency_hz"]) for _, tr, _ in rows_fb]
            dvals = [float(f0[i]) for _, _, i in rows_fb]
            ax.bar(x - 0.16, tvals, width=0.3, color=C.NAVY, label="true")
            ax.bar(x + 0.16, dvals, width=0.3, color=C.GREEN, label="detected")
            ax.set_xlim(-0.6, max(len(rows_fb), 4) - 0.4)
            for xx, dv in zip(x, dvals):
                ax.text(xx + 0.16, dv, f"{dv:.4g}", ha="center", va="bottom",
                        fontsize=9, color=C.GREEN, fontweight="bold")
            accs = [max(0.0, 1 - abs(dv - tv) / tv) * 100 for tv, dv in zip(tvals, dvals)]
            ax.set_xticks(x)
            ax.set_xticklabels([f"E{k + 1}" for k, _, _ in rows_fb])
            ax.set_ylabel("frequency (Hz)")
            ax.margins(y=0.15)
            ax.set_title(f"Mode frequency vs truth · {float(np.mean(accs)):.0f}% match",
                         loc="left", fontsize=11, color=C.NAVY, fontweight="bold")
            ax.legend(loc="upper right", fontsize=9)
            ax.grid(axis="y", color="#EDF0F4", lw=0.8)
            sections.append(("Mode frequency vs truth", C.img_html(fig)))

    if d0 is not None:
        fig, ax = plt.subplots(figsize=(7.8, 3.6))
        x = np.arange(n)
        dvals = [float(v) for v in d0]
        cols_ = [C.RED if v < 0 else C.GREEN for v in dvals]
        ax.bar(x, dvals, color=cols_, width=0.4)
        ax.set_xlim(-0.6, max(n, 4) - 0.4)
        span = max(abs(min(dvals)), abs(max(dvals)), 1e-9)
        for xx, v in zip(x, dvals):
            ax.text(xx, v + (span * 0.04 if v >= 0 else -span * 0.04), f"{v:+.3f}",
                    ha="center", va="bottom" if v >= 0 else "top",
                    fontsize=9, fontweight="bold", color=C.GREEN if v >= 0 else C.RED)
        ax.axhline(0, color=C.NAVY, lw=1.0)
        eids = [f"E{int(e)}" for e in df.get("event_id", range(1, n + 1))]
        ax.set_xticks(x)
        ax.set_xticklabels(eids)
        ax.set_ylabel("damping ratio")
        ax.margins(y=0.25)
        growing = [e for e, v in zip(eids, dvals) if v < 0]
        note = f"{'/'.join(growing)} GROWING = alarm" if growing else "all decaying (safe)"
        ax.set_title(f"Damping sign → stability · {note}",
                     loc="left", fontsize=11, color=C.NAVY, fontweight="bold")
        ax.legend(handles=[Patch(color=C.GREEN, label="+ decaying (safe)"),
                           Patch(color=C.RED, label="− growing (alarm)")],
                  loc="upper right", fontsize=8)
        sections.append(("Damping sign (stability)", C.img_html(fig)))

    if truth:
        # Full metrics scorecard — formulas mirror the component's od_federate/metrics.py
        def _num(i: int, col: str):
            if col not in df.columns:
                return None
            v = df[col][i]
            try:
                v = float(v)
            except (TypeError, ValueError):
                return None
            return v if np.isfinite(v) else None

        t_rows = []
        used: set[int] = set()
        lat_list: list[float] = []
        fq_list: list[float] = []
        am_list: list[float] = []
        dp_list: list[float] = []
        for tr in truth:
            tf = tr.get("frequency_hz")
            ts = tr.get("start_time_sec")
            ta = tr.get("amplitude")
            tz = tr.get("damping_ratio")
            best_i, best_d = None, None
            for i in range(n):
                if i in used:
                    continue
                if ts is not None and "start_time_sec" in df.columns:
                    d = abs(float(df["start_time_sec"][i]) - float(ts))
                    if d > 30.0:
                        continue
                elif tf:
                    d = abs(float(f0[i]) - float(tf))
                else:
                    continue
                if best_d is None or d < best_d:
                    best_i, best_d = i, d
            if best_i is None:
                t_rows.append([ts if ts is not None else "—", tf, "—", "—", "—", "—", "MISSED"])
                continue
            used.add(best_i)
            fd = float(f0[best_i])
            facc = max(0.0, 1 - abs(fd - float(tf)) / float(tf)) * 100 if tf else None
            lat = None
            rep = _num(best_i, "reporting_time_sec")
            if ts is not None and rep is not None and tf:
                lat = (rep - float(ts)) * float(tf)
            aacc = None
            det_start = _num(best_i, "start_time_sec")
            det_amp = _num(best_i, "mode_0_amp")
            if None not in (ts, ta, tz, det_start, det_amp) and tf:
                omega_d = 2 * np.pi * float(tf)
                sigma = float(tz) * omega_d / np.sqrt(1 - float(tz) ** 2)
                equiv_amp = det_amp / np.exp(-sigma * (det_start - float(ts)))
                aacc = max(0.0, 1 - abs(equiv_amp - float(ta)) / float(ta)) * 100
            dacc = None
            det_z = _num(best_i, "mode_0_damping")
            if tz is not None and det_z is not None and float(tz) != 0:
                dacc = max(0.0, 1 - abs(det_z - float(tz)) / abs(float(tz))) * 100
            for v, acc_list in ((lat, lat_list), (facc, fq_list), (aacc, am_list), (dacc, dp_list)):
                if v is not None:
                    acc_list.append(v)
            t_rows.append([
                ts if ts is not None else "—", tf, f"{fd:.4g}",
                f"{facc:.1f} %" if facc is not None else "—",
                f"{aacc:.1f} %" if aacc is not None else "—",
                f"{dacc:.1f} %" if dacc is not None else "—",
                f"{lat:.2f} cyc" if lat is not None else "—",
            ])
        for i in range(n):
            if i not in used:
                t_rows.append(["—", "—", f"{float(f0[i]):.4g}", "—", "—", "—", "FALSE ALARM"])
        missed = sum(1 for r in t_rows if r[-1] == "MISSED")
        false_alarms = n - len(used)

        def _mean(vals: list[float], fmt: str) -> str:
            return fmt.format(sum(vals) / len(vals)) if vals else "—"

        sections.append((
            "Ground-truth comparison (full metrics)",
            C.stat_band([
                ("truth events", f"{len(truth)}"),
                ("matched", f"{len(used)}"),
                ("missed", f"{missed}"),
                ("false alarms", f"{false_alarms}"),
                ("mean latency", _mean(lat_list, "{:.2f} cyc")),
                ("freq accuracy", _mean(fq_list, "{:.1f} %")),
                ("amplitude accuracy", _mean(am_list, "{:.1f} %")),
                ("damping accuracy", _mean(dp_list, "{:.1f} %")),
            ])
            + C.table_html(
                ["true start (s)", "true freq (Hz)", "detected freq (Hz)", "freq accuracy",
                 "amplitude accuracy", "damping accuracy", "detection latency"],
                t_rows,
            ),
        ))
    else:
        sections.append((
            "Ground truth",
            "<p class='note'>No ground truth configured for this run — real field events report detection "
            "and frequency characterization only (full accuracy scoring needs known truth).</p>",
        ))

    sections.append(events_section)
    return "Oscillation Detection — Report", sections


def notebook_render(run_dir) -> None:
    _title, sections = build_sections(Path(run_dir))
    C.display_sections(sections)
