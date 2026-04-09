import type { Node, Edge } from '@vue-flow/core'

export interface PortDefinition {
  type: string
  port_id: string
}

export interface NodeData {
  label: string
  config?: Record<string, unknown>
  componentType?: string
}

export interface EdgeWire {
  type: string
  sourcePortId: string
  targetPortId: string
}

export interface EdgeData {
  wires?: EdgeWire[]
}

export interface TemplateData {
  id: string
  name: string
  description: string
  nodes: Node<NodeData>[]
  edges: Edge<EdgeData>[]
  createdAt: string
}
