"""Resolve the physical quantity behind each result dataset in a WiringDiagram.

A Recorder's output files inherit their quantity (VoltagesMagnitude, PowersReal,
...) from the concrete output port feeding it. Measurement federates republish
their input unchanged, so the walk follows their subscription one hop further
back. Depends only on oedisi models, so it could move into oedisi proper.
"""

from __future__ import annotations

from oedisi.componentframework.basic_component import ComponentDescription
from oedisi.componentframework.system_configuration import Link, WiringDiagram
from pydantic import BaseModel

RECORDER_TYPE = "Recorder"

PASS_THROUGH_TYPES = {"MeasurementComponent"}
"""Component types whose publication republishes their subscription unchanged."""

SUBSCRIPTION_PORT = "subscription"
"""Input port name shared by recorders and measurement federates."""

CARRIER_TYPES = {"MeasurementArray", ""}
"""Port types that say nothing about the physical quantity they carry."""


class OutputAnnotation(BaseModel):
    """Physical quantity resolved for one output file.

    ``type=None`` means unknown — callers must not apply unit conversion.
    """

    type: str | None = None
    unit: str | None = None
    source: str | None = None
    source_port: str | None = None


class OutputsList(BaseModel):
    """Component name → output filename → annotation. Persisted per build."""

    components: dict[str, dict[str, OutputAnnotation]] = {}


class WiringIndex:
    """Dict lookups for walking a WiringDiagram backward."""

    def __init__(self, wiring: WiringDiagram) -> None:
        self.components = {c.name: c for c in wiring.components}
        self._link_into = {
            (link.target, link.target_port): link for link in wiring.links
        }

    def upstream(self, component_name: str, input_port: str) -> Link | None:
        return self._link_into.get((component_name, input_port))


def resolve_source_annotation(
    index: WiringIndex,
    descriptions: dict[str, ComponentDescription],
    source_name: str,
    source_port: str,
) -> OutputAnnotation:
    """Annotation for the output port at (source_name, source_port).

    Hops backward through measurement federates; anything unresolvable
    (unknown component, missing link, carrier-typed endpoint) is unknown.
    """
    visited: set[tuple[str, str]] = set()
    while (source_name, source_port) not in visited:
        visited.add((source_name, source_port))
        component = index.components.get(source_name)
        if component is None:
            break
        if component.type in PASS_THROUGH_TYPES:
            link = index.upstream(source_name, SUBSCRIPTION_PORT)
            if link is None:
                break
            source_name, source_port = link.source, link.source_port
            continue
        description = descriptions.get(component.type)
        if description is None:
            break
        output_ports = {t.port_name: t for t in description.dynamic_outputs}
        port = output_ports.get(source_port)
        if port is None or port.type in CARRIER_TYPES:
            break
        return OutputAnnotation(
            type=port.type,
            unit=port.unit or None,
            source=source_name,
            source_port=source_port,
        )
    return OutputAnnotation()


def annotate_outputs(
    wiring: WiringDiagram, descriptions: dict[str, ComponentDescription]
) -> OutputsList:
    """Annotate every Recorder's output files with their resolved quantity."""
    index = WiringIndex(wiring)
    components: dict[str, dict[str, OutputAnnotation]] = {}
    for component in wiring.components:
        if component.type != RECORDER_TYPE:
            continue
        link = index.upstream(component.name, SUBSCRIPTION_PORT)
        annotation = OutputAnnotation()
        if link is not None:
            annotation = resolve_source_annotation(
                index, descriptions, link.source, link.source_port
            )
        files = {
            filename: annotation
            for key in ("feather_filename", "csv_filename")
            if (filename := component.parameters.get(key))
        }
        if files:
            components[component.name] = files
    return OutputsList(components=components)
