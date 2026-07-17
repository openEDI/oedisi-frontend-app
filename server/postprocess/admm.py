"""ADMM (pnnl-dopf-admm) post-process report generator."""
from __future__ import annotations

import logging
from pathlib import Path

from oedisi.types.data_types import Topology
from admm_federate.adapter import area_disconnects, disconnect_areas, generate_graph
from admm_federate.plotting import (
    load_scenario_parameters,
    get_der_mapping,
    load_recorder_data,
    process_voltages,
    process_power_flows,
    process_generation_adequacy,
    process_convergence,
    plot_network_partition,
    plot_voltage_comparison,
    plot_power_flow_comparison,
    plot_generation_adequacy,
    plot_algorithmic_convergence,
)

from . import common as C

logger = logging.getLogger(__name__)


def build_sections(run_dir: Path) -> tuple[str, list[tuple[str, str]]]:
    run_dir = Path(run_dir)
    wiring = C.load_wiring(run_dir)
    
    # 1. Load scenario parameters
    area_ids, area_params = load_scenario_parameters(wiring)
    sections: list[tuple[str, str]] = []
    
    if not area_ids:
        sections.append(
            ("ADMM Post-process Report", "<p>No ADMM components found in the scenario configuration.</p>")
        )
        return "Distribution OPF (ADMM) — Report", sections
        
    outputs_dir = run_dir / "outputs"
    topology_path = outputs_dir / "topology.json"
    if not topology_path.exists():
        sections.append(
            ("ADMM Post-process Report", "<p>Required topology.json was not found in simulation outputs.</p>")
        )
        return "Distribution OPF (ADMM) — Report", sections
        
    try:
        topology = Topology.model_validate_json(topology_path.read_text(encoding="utf-8"))
    except Exception as e:
        sections.append(
            ("ADMM Post-process Report", f"<p>Error loading grid network topology model: {e}</p>")
        )
        return "Distribution OPF (ADMM) — Report", sections

    # 2. Partition grid and resolve areas
    try:
        slack_bus = topology.slack_bus[0].split(".", 1)[0]
        G = generate_graph(topology.incidences, slack_bus)
        
        graph_for_partition = G.copy()
        graph_for_split = G.copy()
        boundaries = area_disconnects(graph_for_partition, n_max=len(area_ids))
        areas_clean = disconnect_areas(graph_for_split, boundaries)
        
        area_buses = [list(area.nodes()) for area in areas_clean]
        der_map = get_der_mapping(topology_path)
    except Exception as e:
        sections.append(
            ("ADMM Post-process Report", f"<p>Error preprocessing grid network partitions: {e}</p>")
        )
        return "Distribution OPF (ADMM) — Report", sections

    # 3. Load simulation results (ingesting recorder data)
    data = load_recorder_data(outputs_dir, wiring)
    
    # 4. Process metrics
    voltage_data = process_voltages(data, area_ids, area_buses, topology)
    flow_data = process_power_flows(
        data, area_ids, area_params, G, area_buses, der_map, slack_bus
    )
    adequacy_df = process_generation_adequacy(topology, area_ids, area_buses)
    convergence_data = process_convergence(data, area_ids)

    # 5. Find coordinate files in build directory recursively
    coords_dir = run_dir / "build"
    for p in (run_dir / "build").rglob("Buscoords.dss"):
        coords_dir = p.parent
        break
    else:
        for p in (run_dir / "build").rglob("Buscoords.dat"):
            coords_dir = p.parent
            break

    # 6. Generate Figures and build sections
    fig_partition = plot_network_partition(G, boundaries, areas_clean, slack_bus, coords_dir)
    if fig_partition:
        sections.append(("Distribution Grid Control Area Partition Map", C.img_html(fig_partition)))
        
    fig_volt = plot_voltage_comparison(voltage_data)
    if fig_volt:
        sections.append(("Bus Voltage Profile Distribution per Area (ADMM vs Feeder)", C.img_html(fig_volt)))

    fig_flow = plot_power_flow_comparison(flow_data)
    if fig_flow:
        sections.append(("Boundary Power Flow Comparison: ADMM vs. Feeder Reference", C.img_html(fig_flow)))

    fig_adeq = plot_generation_adequacy(adequacy_df)
    if fig_adeq:
        sections.append(("Generation Adequacy: Rated Capacity vs. Rated Load per Area", C.img_html(fig_adeq)))

    fig_conv = plot_algorithmic_convergence(convergence_data)
    if fig_conv:
        sections.append(("Decentralized Algorithm Convergence Profile", C.img_html(fig_conv)))
        
    # Build a summary statistics section
    stats_items = []
    stats_items.append(("Control Areas", str(len(area_ids))))
    stats_items.append(("Total Nodes", str(G.number_of_nodes())))
    stats_items.append(("Boundary Switches", str(len(boundaries))))
    stats_items.append(("Total DERs", str(len(der_map))))
    
    sections.insert(0, ("Simulation Overview & Summary Statistics", C.stat_band(stats_items)))

    return "Distribution OPF (ADMM) — Report", sections


def notebook_render(run_dir) -> None:
    _title, sections = build_sections(Path(run_dir))
    C.display_sections(sections)
