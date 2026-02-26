
export interface PortDefinition {
  type: string
  port_id: string
}

export interface NodeData {
  label: string
  config?: Record<string, string>
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
