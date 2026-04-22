import type {
  NodeData,
  EdgeData,
  TemplateData,
  EdgeWire,
} from '@/lib/flowTypes'
import type { Node, Edge } from '@vue-flow/core'

interface HELICSBrokerConfig {
  host?: string
  port?: number
  key?: string
  auto?: boolean
  initString: string
}

interface SharedFederateConfig {
  coreType?: string
  coreInitString?: string
  broker?: HELICSBrokerConfig
}

interface Component {
  name: string
  type: string
  host?: string
  container_port?: number
  image?: string
  parameters: Record<string, unknown>
  helics_config_override?: SharedFederateConfig
}

interface Link {
  source: string
  source_port: string
  target: string
  target_port: string
}

export interface WiringDiagram {
  name: string
  components: Component[]
  links: Link[]
  shared_helics_config?: SharedFederateConfig
}

function toComponent(node: Node<NodeData>): Component {
  if (node.data === undefined) {
    throw new Error(`Node "${node.id}" is missing all data`)
  } else if (node.data.componentType === undefined) {
    throw new Error(`Node "${node.data.label}" does not have type`)
  }
  const { name, ...parameters } = node.data.config ?? {}
  return {
    name: typeof name === 'string' ? name : node.id,
    type: node.data.componentType,
    parameters: parameters,
  }
}

function toLink(source: string, target: string, edgeWire: EdgeWire): Link {
  return {
    source: source,
    target: target,
    source_port: edgeWire.sourcePortId,
    target_port: edgeWire.targetPortId,
  }
}

function toLinks(
  nodeIdsToLabels: Map<string, string>,
  edge: Edge<EdgeData>,
): Link[] {
  const wires = edge.data?.wires ?? []
  const source = nodeIdsToLabels.get(edge.source)
  const target = nodeIdsToLabels.get(edge.target)
  if (source === undefined || target === undefined) {
    throw new Error(`Edge "${edge.id}" does not have source or target`)
  }
  return wires.map((w) => toLink(source, target, w))
}

export function toWiringDiagram(config: TemplateData): WiringDiagram {
  const nodeIdsToLabels = new Map<string, string>(
    config.nodes.map((n) => {
      const configName = n.data?.config?.name
      return [n.id, typeof configName === 'string' ? configName : n.id] as const
    }),
  )
  return {
    name: config.name,
    components: config.nodes.map(toComponent),
    links: config.edges.flatMap((e) => toLinks(nodeIdsToLabels, e)),
  }
}
