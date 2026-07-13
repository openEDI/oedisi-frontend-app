"""EV (ornl-ev-pso) post-process: voltage + load figures for one run, with an automatic
with/without-control comparison when a companion run exists.

Data sources (inside a run dir):
  outputs/voltage_real.feather + voltage_imag.feather  -> per-bus-phase voltage magnitude
  outputs/powers_real.feather                          -> per-bus real power (negative = supply)
  outputs/topology.json (base_voltage_magnitudes)      -> per-unit conversion
  build/feeder/opendss/{Buscoords,Lines,Transformers}.dss -> feeder map (when present)
  wiring.json EVCSComponent.parameters (control_mode, evcs_bus) + Feeder parameters

Companion pairing: a run whose EVCSComponent.control_mode is on the other side of the
uncontrolled/controlled split, on the same feeder (matched Feeder parameters), newest first.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import common as C

V_LIMIT = 0.95
_FEEDER_SIG_KEYS = ("use_smartds", "opendss_location", "number_of_timesteps", "start_date")


def _base_bus(col: str) -> str:
    return col.lower().split(".")[0]


def _wiring(run_dir: Path) -> dict:
    return C.load_wiring(run_dir)


def _control_mode(wiring: dict) -> str:
    return str(C.component_params(wiring, "EVCSComponent").get("control_mode", "unknown"))


def _feeder_sig(wiring: dict) -> tuple:
    p = C.component_params(wiring, "Feeder")
    return tuple(p.get(k) for k in _FEEDER_SIG_KEYS)


def _run_freq_hours(wiring: dict) -> float:
    p = C.component_params(wiring, "Feeder")
    try:
        return float(p.get("run_freq_sec", 900.0)) / 3600.0
    except (TypeError, ValueError):
        return 0.25


def _ev_buses(wiring: dict) -> set[str]:
    buses = C.component_params(wiring, "EVCSComponent").get("evcs_bus") or []
    return {str(b).lower().split(".")[0] for b in buses}


def _has_outputs(run_dir: Path) -> bool:
    out = run_dir / "outputs"
    return all(
        (out / f).exists()
        for f in ("voltage_real.feather", "voltage_imag.feather", "topology.json")
    )


def _find_companion(run_dir: Path) -> tuple[Path, str] | None:
    try:
        wiring = _wiring(run_dir)
        my_mode = _control_mode(wiring)
        my_sig = _feeder_sig(wiring)
    except Exception:  # noqa: BLE001
        return None
    my_uncontrolled = my_mode == "uncontrolled"
    candidates: list[tuple[float, Path, str]] = []
    for other in run_dir.parent.iterdir():
        if not other.is_dir() or other.name == run_dir.name:
            continue
        try:
            w = C.load_wiring(other)
            if "EVCSComponent" not in C.component_types(w):
                continue
            mode = _control_mode(w)
            if (mode == "uncontrolled") == my_uncontrolled:
                continue
            if _feeder_sig(w) != my_sig:
                continue
            if not _has_outputs(other):
                continue
            rec = json.loads((other / "run.json").read_text(encoding="utf-8"))
            if rec.get("exit_code") != 0:
                continue
            candidates.append((other.stat().st_mtime, other, mode))
        except Exception:  # noqa: BLE001
            continue
    if not candidates:
        return None
    candidates.sort(reverse=True)
    _, path, mode = candidates[0]
    return path, mode


def context_signature(run_dir: Path) -> str:
    """Identity of the companion this report would be built against ("" if none).

    Stored in the report cache meta — when a baseline run appears (or a newer
    one replaces it), the cached report is stale and regenerates on next request.
    """
    comp = _find_companion(Path(run_dir))
    return comp[0].name if comp else ""


class _RunData:
    def __init__(self, run_dir: Path, label: str):
        self.run_dir = Path(run_dir)
        self.label = label
        out = self.run_dir / "outputs"
        vr = pd.read_feather(out / "voltage_real.feather")
        vi = pd.read_feather(out / "voltage_imag.feather")
        topo = json.loads((out / "topology.json").read_text(encoding="utf-8"))
        bv = topo["base_voltage_magnitudes"]
        base = dict(zip(bv["ids"], bv["values"]))
        self.cols = [c for c in vr.columns if c != "time"]
        mag = np.sqrt(vr[self.cols].to_numpy() ** 2 + vi[self.cols].to_numpy() ** 2)
        self.pu = mag / np.array([base.get(c, np.nan) for c in self.cols])
        self.finite = np.isfinite(self.pu)
        self.busmin = np.nanmin(np.where(self.finite, self.pu, np.nan), axis=0)
        self.steps = self.pu.shape[0]
        pw = out / "powers_real.feather"
        self.demand = None
        self.powers = None
        if pw.exists():
            pr = pd.read_feather(pw)
            pcols = [c for c in pr.columns if c != "time"]
            arr = pr[pcols].to_numpy()
            self.powers = (pcols, arr)
            self.demand = -np.nansum(np.where(arr < 0, arr, 0), axis=1)

    def vmin(self) -> float:
        return float(np.nanmin(self.busmin))

    def viol_samples(self) -> int:
        return int(np.nansum((self.pu < V_LIMIT) & self.finite))

    def viol_buses(self) -> list[str]:
        per: dict[str, float] = {}
        for c, v in zip(self.cols, self.busmin):
            b = _base_bus(c)
            per[b] = min(per.get(b, np.inf), float(v))
        return sorted(b for b, v in per.items() if v < V_LIMIT)

    def ev_voltage(self, ev_buses: set[str]) -> np.ndarray | None:
        idx = [i for i, c in enumerate(self.cols) if _base_bus(c) in ev_buses]
        if not idx:
            return None
        return np.nanmin(self.pu[:, idx], axis=1)

    def ev_load(self, ev_buses: set[str]) -> np.ndarray | None:
        if self.powers is None:
            return None
        pcols, arr = self.powers
        idx = [i for i, c in enumerate(pcols) if _base_bus(c) in ev_buses]
        if not idx:
            return None
        return np.nansum(arr[:, idx], axis=1)

    def peak_demand(self) -> float | None:
        return float(np.nanmax(self.demand)) if self.demand is not None else None


def _feeder_graph(run_dir: Path):
    d = run_dir / "build" / "feeder" / "opendss"
    coords: dict[str, tuple[float, float]] = {}
    bc = d / "Buscoords.dss"
    if not bc.exists():
        return None
    for ln in bc.read_text(encoding="utf-8", errors="ignore").splitlines():
        p = ln.split()
        if len(p) >= 3:
            try:
                coords[p[0].lower()] = (float(p[1]), float(p[2]))
            except ValueError:
                pass
    edges: set[tuple[str, str]] = set()
    for fname in ("Lines.dss", "Transformers.dss"):
        f = d / fname
        if not f.exists():
            continue
        for ln in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            if fname == "Lines.dss":
                a = re.search(r"bus1=([^\s]+)", ln, re.I)
                b = re.search(r"bus2=([^\s]+)", ln, re.I)
                pair = [a.group(1), b.group(1)] if a and b else []
            else:
                pair = re.findall(r"bus=([^\s]+)", ln, re.I) if ln.lower().startswith("new transformer") else []
            bs = [_base_bus(x) for x in pair]
            for i in range(len(bs) - 1):
                if bs[i] in coords and bs[i + 1] in coords and bs[i] != bs[i + 1]:
                    edges.add((bs[i], bs[i + 1]))
    return coords, edges


def build_sections(run_dir: Path) -> tuple[str, list[tuple[str, str]]]:
    import matplotlib.pyplot as plt

    run_dir = Path(run_dir)
    wiring = _wiring(run_dir)
    my_mode = _control_mode(wiring)
    ev_buses = _ev_buses(wiring)
    dt_h = _run_freq_hours(wiring)

    this = _RunData(run_dir, "this run")
    comp = None
    pair = _find_companion(run_dir)
    if pair:
        comp_dir, _comp_mode = pair
        comp = _RunData(comp_dir, "companion")

    # semantic roles: baseline = uncontrolled, styled gray/red; the other styled green
    if comp and my_mode == "uncontrolled":
        unc, ctl = this, comp
    elif comp:
        unc, ctl = comp, this
    else:
        unc, ctl = None, None
    if unc and ctl:
        unc.label = "without control"
        ctl.label = "with control"

    sections: list[tuple[str, str]] = []


    graph = _feeder_graph(run_dir)
    if graph:
        coords, edges = graph
        per: dict[str, float] = {}
        for c, v in zip(this.cols, this.busmin):
            b = _base_bus(c)
            per[b] = min(per.get(b, np.inf), float(v))
        fig, ax = plt.subplots(figsize=(7.4, 5.2))
        for u, v in edges:
            ax.plot([coords[u][0], coords[v][0]], [coords[u][1], coords[v][1]],
                    color=C.LIGHT, lw=0.9, zorder=1)
        xs = [coords[b][0] for b in coords]
        ys = [coords[b][1] for b in coords]
        cs = [(C.RED if per.get(b, 1.0) < V_LIMIT else C.GREEN) for b in coords]
        ax.scatter(xs, ys, s=26, c=cs, edgecolor="white", lw=0.35, zorder=2)
        evs = [b for b in coords if b in ev_buses]
        if evs:
            ax.scatter([coords[b][0] for b in evs], [coords[b][1] for b in evs],
                       s=110, facecolor="none", edgecolor=C.ORANGE, lw=2.0, zorder=5)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title("Feeder map — this run's bus minimum voltage (orange ring = EV bus)",
                     loc="left", fontsize=11, color=C.NAVY, fontweight="bold")
        sections.append(("Feeder voltage map (this run)", C.img_html(fig)))

    if graph:
        coords, edges = graph
        degree: dict[str, int] = {}
        for u, v in edges:
            degree[u] = degree.get(u, 0) + 1
            degree[v] = degree.get(v, 0) + 1
        hub = max(degree, key=degree.get) if degree else next(iter(coords))
        rx, ry = coords[hub]
        dist = np.array([
            math.hypot(coords.get(_base_bus(c), (rx, ry))[0] - rx,
                       coords.get(_base_bus(c), (rx, ry))[1] - ry)
            for c in this.cols
        ])
        order = np.argsort(dist)
    else:
        order = np.argsort(this.busmin)[::-1]
    x = np.arange(len(this.cols))
    fig, ax = plt.subplots(figsize=(8.6, 4.0))
    ax.axhline(V_LIMIT, color=C.RED, ls="--", lw=1.3)
    ax.text(len(this.cols) * 0.99, V_LIMIT + 0.002, f"{V_LIMIT} limit", ha="right",
            va="bottom", fontsize=9, color=C.RED, fontweight="bold")
    if comp and unc and ctl and list(unc.cols) == list(this.cols) == list(ctl.cols):
        ax.plot(x, unc.busmin[order], color=C.GRAY, lw=1.4, label=unc.label)
        ax.plot(x, ctl.busmin[order], color=C.GREEN, lw=1.8, label=ctl.label)
    else:
        ax.plot(x, this.busmin[order], color=C.MBLUE, lw=1.5, label=this.label)
    evx = [i for i, o in enumerate(order) if _base_bus(this.cols[o]) in ev_buses]
    if evx:
        ax.scatter(evx, [this.busmin[order][i] for i in evx], s=55, color=C.ORANGE,
                   edgecolor=C.RED, lw=1.2, zorder=5, label="EV buses")
    ax.legend(loc="lower left", frameon=False, fontsize=9)
    ax.set_xticks([])
    ax.set_ylabel("min voltage (p.u.)")
    ax.set_xlabel("bus-phase measurement points")
    ax.set_title("Per-bus minimum voltage — with vs without control", loc="left",
                 fontsize=11, color=C.NAVY, fontweight="bold")
    ax.grid(axis="y", color="#EDF0F4", lw=0.8)
    sections.append(("Voltage profile (minimum per bus)", C.img_html(fig)))

    def _hours(n: int) -> np.ndarray:
        return np.arange(n) * dt_h

    ev_v_this = this.ev_voltage(ev_buses)
    if ev_v_this is not None:
        fig, ax = plt.subplots(figsize=(8.6, 3.6))
        if comp and unc and ctl:
            vu = unc.ev_voltage(ev_buses)
            vc = ctl.ev_voltage(ev_buses)
            if vu is not None:
                ax.plot(_hours(len(vu)), vu, color=C.GRAY, lw=1.5, label=unc.label)
            if vc is not None:
                ax.plot(_hours(len(vc)), vc, color=C.GREEN, lw=1.8, label=ctl.label)
        else:
            ax.plot(_hours(len(ev_v_this)), ev_v_this, color=C.MBLUE, lw=1.6, label=this.label)
        ax.axhline(V_LIMIT, color=C.RED, ls="--", lw=1.3)
        ax.set_xlabel("hours from start")
        ax.set_ylabel("voltage (p.u.)")
        ax.set_title("EV-bus voltage over time (worst EV bus each step)", loc="left",
                     fontsize=11, color=C.NAVY, fontweight="bold")
        ax.legend(loc="lower right", frameon=False, fontsize=9)
        ax.grid(axis="y", color="#EDF0F4", lw=0.8)
        sections.append(("EV-bus voltage over time", C.img_html(fig)))

    if this.demand is not None:
        fig, ax = plt.subplots(figsize=(8.6, 3.6))
        if comp and unc and ctl and unc.demand is not None and ctl.demand is not None:
            ax.plot(_hours(len(unc.demand)), unc.demand, color=C.GRAY, lw=1.5, label=unc.label)
            ax.plot(_hours(len(ctl.demand)), ctl.demand, color=C.GREEN, lw=1.8, label=ctl.label)
            pu_, pc_ = unc.peak_demand(), ctl.peak_demand()
            ax.set_title(
                f"Feeder demand over time — peak {pu_:.0f} → {pc_:.0f} kW "
                f"({100 * (pc_ - pu_) / pu_:+.1f} %)",
                loc="left", fontsize=11, color=C.NAVY, fontweight="bold")
        else:
            ax.plot(_hours(len(this.demand)), this.demand, color=C.MBLUE, lw=1.6, label=this.label)
            ax.set_title("Feeder demand over time", loc="left", fontsize=11,
                         color=C.NAVY, fontweight="bold")
        ax.set_xlabel("hours from start")
        ax.set_ylabel("feeder supply (kW)")
        ax.legend(loc="upper left", frameon=False, fontsize=9)
        ax.grid(axis="y", color="#EDF0F4", lw=0.8)
        sections.append(("Feeder demand (load) over time", C.img_html(fig)))

    ev_l_this = this.ev_load(ev_buses)
    if ev_l_this is not None:
        fig, ax = plt.subplots(figsize=(8.6, 3.6))
        if comp and unc and ctl:
            lu = unc.ev_load(ev_buses)
            lc = ctl.ev_load(ev_buses)
            if lu is not None:
                ax.plot(_hours(len(lu)), lu, color=C.GRAY, lw=1.5, label=unc.label)
            if lc is not None:
                ax.plot(_hours(len(lc)), lc, color=C.GREEN, lw=1.8, label=ctl.label)
            if lu is not None and lc is not None:
                h = _hours(len(lu))
                ax.fill_between(h, lc, lu, where=lu > lc, color=C.ORANGE,
                                alpha=0.25, lw=0, label="charging reduced at peak")
                if bool(np.any(lc > lu + 1e-6)):
                    ax.fill_between(h, lu, lc, where=lc > lu, color=C.GREEN,
                                    alpha=0.25, lw=0, label="charging shifted later")
        else:
            ax.plot(_hours(len(ev_l_this)), ev_l_this, color=C.MBLUE, lw=1.6, label=this.label)
        ax.set_xlabel("hours from start")
        ax.set_ylabel("EV-bus power (kW)")
        ax.set_title("Load at the EV buses over time (residential + EV charging)",
                     loc="left", fontsize=11, color=C.NAVY, fontweight="bold")
        ax.legend(loc="upper right", frameon=False, fontsize=9)
        ax.grid(axis="y", color="#EDF0F4", lw=0.8)
        sections.append(("EV-bus load over time", C.img_html(fig)))

    if ev_l_this is not None and comp and unc and ctl:
        lu = unc.ev_load(ev_buses)
        lc = ctl.ev_load(ev_buses)
        if lu is not None and lc is not None:
            cu = np.nancumsum(lu) * dt_h
            cc = np.nancumsum(lc) * dt_h
            fig, ax = plt.subplots(figsize=(8.6, 3.6))
            h = _hours(len(lu))
            ax.plot(h, cu, color=C.GRAY, lw=1.6, label="without control")
            ax.plot(h, cc, color=C.GREEN, lw=1.9, label="with control")
            pct = 100 * cc[-1] / cu[-1] if cu[-1] else float("nan")
            ax.annotate(f"{pct:.1f} % of uncontrolled energy delivered",
                        (h[-1], cc[-1]), textcoords="offset points", xytext=(-8, -14),
                        ha="right", fontsize=9.5, color=C.GREEN, fontweight="bold")
            ax.set_xlabel("hours from start")
            ax.set_ylabel("cumulative EV-bus energy (kWh)")
            ax.set_title("Cumulative EV-bus energy — a late catch-up = shifted charging; "
                         "a persistent gap = trimmed charging",
                         loc="left", fontsize=11, color=C.NAVY, fontweight="bold")
            ax.legend(loc="lower right", frameon=False, fontsize=9)
            ax.grid(axis="y", color="#EDF0F4", lw=0.8)
            sections.append(("Cumulative EV energy (shift vs trim)", C.img_html(fig)))

    return "EV Scheduling — Report", sections


def notebook_render(run_dir) -> None:
    _title, sections = build_sections(Path(run_dir))
    C.display_sections(sections)
