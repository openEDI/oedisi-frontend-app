<template>
  <div class="h-screen flex flex-col">
    <div class="bg-white border-b px-4 py-3 flex items-center justify-between">
      <div class="flex items-center gap-4">
        <Button variant="outline" @click="navigate('/')">
          🏠
        </Button>
        <h1 class="text-xl font-semibold">OEDISI Simulation Designer</h1>
      </div>
      <div class="flex items-center gap-2">
        <Button variant="outline" @click="navigate('/configs')">
          📁 Saved Templates
        </Button>
        <Button variant="outline" @click="saveDialogOpen = true">
          💾 Save Template
        </Button>
      </div>
    </div>

    <div class="flex-1 flex">
      <div class="w-64 bg-white border-r p-6 overflow-y-auto">
        <h2 class="text-lg font-semibold mb-6">Components</h2>
        <div class="space-y-4">
          <div 
            v-for="component in components" 
            :key="component.id" 
            class="p-4 bg-gray-50 rounded-lg cursor-move hover:bg-gray-100 transition-colors" 
            draggable="true" 
            @dragstart="(e) => onDragStart(component.id, e)"
          >
            <h3 class="font-medium text-sm">{{ component.name }}</h3>
            <p class="text-xs text-gray-500">{{ component.description }}</p>
          </div>
        </div>
      </div>

      <div class="flex-1 relative bg-gray-50">
        <VueFlow
          ref="vueFlowRef"
          v-model:nodes="nodes"
          v-model:edges="edges"
          class="vue-flow-container"
          :connection-line-style="{ stroke: '#b1b1b7', strokeWidth: 1 }"
          :default-edge-options="{ type: 'wiring' }"
          :fit-view-on-init="true"
          :node-types="nodeTypes"
          :edge-types="edgeTypes"
          @drop="onDrop"
          @dragover="onDragOver"
          @node-click="onNodeClick"
          @edge-click="onEdgeClick"
          @pane-click="onPaneClick"
          @connect="onConnect"
        >
          <Background pattern-color="#e5e7eb" :gap="16" />
          <Controls />
          <MiniMap />
        </VueFlow>
      </div>

      <div class="w-72 bg-white border-l p-6 overflow-y-auto">
        <h2 class="text-lg font-semibold mb-6">Properties</h2>
        <div v-if="!selectedNode && !selectedEdge" class="text-gray-500 text-center py-8">
          <p>Select a component or connection to view properties</p>
        </div>
        
        <!-- Node Properties -->
        <div v-else-if="selectedNode" class="space-y-4">
          <div class="space-y-2">
            <label class="text-sm font-semibold">Static Inputs</label>
            <div v-if="selectedNodeStaticInputs.length > 0" class="space-y-2">
              <div
                v-for="input in selectedNodeStaticInputs"
                :key="input.port_id"
                class="space-y-1"
              >
                <label class="text-xs font-medium text-gray-600">{{ input.port_id }}</label>
                <input
                  :value="getSelectedNodeConfigValue(input.port_id)"
                  class="flex h-9 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm ring-offset-white placeholder:text-gray-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                  :placeholder="`Enter ${input.port_id}`"
                  @input="onStaticInputChange(input.port_id, $event)"
                />
              </div>
            </div>
            <p v-else class="text-sm text-gray-500">No static inputs for this component.</p>
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold">Component Type</label>
            <p class="text-sm text-gray-600">{{ selectedNode.data.label }}</p>
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold">Node ID</label>
            <p class="text-sm text-gray-600 font-mono">{{ selectedNode.id }}</p>
          </div>
          <Button variant="destructive" @click="deleteNode(selectedNode.id)">
            Delete Component
          </Button>
        </div>

        <!-- Edge Properties -->
        <div v-else-if="selectedEdge" class="space-y-4">
          <div class="space-y-2">
            <label class="text-sm font-semibold">Connection ID</label>
            <p class="text-sm text-gray-600 font-mono">{{ selectedEdge.id }}</p>
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold">Source Node</label>
            <p class="text-sm text-gray-600">{{ getNodeLabel(selectedEdge.source) }}</p>
            <p class="text-xs text-gray-500 font-mono">{{ selectedEdge.source }}</p>
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold">Target Node</label>
            <p class="text-sm text-gray-600">{{ getNodeLabel(selectedEdge.target) }}</p>
            <p class="text-xs text-gray-500 font-mono">{{ selectedEdge.target }}</p>
          </div>
          <div v-if="selectedEdge.type" class="space-y-2">
            <label class="text-sm font-semibold">Connection Type</label>
            <p class="text-sm text-gray-600">{{ selectedEdge.type }}</p>
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold">Wiring Selection</label>
            <p v-if="compatibleWireOptions.length === 0" class="text-sm text-gray-500">
              No compatible dynamic output/input intersections for this connection.
            </p>
            <div v-else class="space-y-2">
              <select
                v-model="selectedWireOption"
                class="flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
              >
                <option value="" disabled>Select compatible signal</option>
                <option
                  v-for="option in compatibleWireOptions"
                  :key="wireOptionKey(option)"
                  :value="wireOptionKey(option)"
                >
                  {{ option.type }}: {{ option.sourcePortId }} → {{ option.targetPortId }}
                </option>
              </select>
              <Button
                :disabled="!selectedWireOption"
                @click="addWireToSelectedEdge"
              >
                Add Wiring
              </Button>
            </div>
          </div>
          <div v-if="selectedEdgeWires.length > 0" class="space-y-2">
            <label class="text-sm font-semibold">Wiring Diagram Entries</label>
            <div class="space-y-1">
              <div
                v-for="wire in selectedEdgeWires"
                :key="wireOptionKey(wire)"
                class="flex items-center justify-between gap-2 text-xs text-gray-600 font-mono bg-gray-50 rounded px-2 py-1"
              >
                <span>{{ wire.type }}: {{ wire.sourcePortId }} → {{ wire.targetPortId }}</span>
                <Button
                  @click="removeWireFromSelectedEdge(wire)"
                >
                  Remove
                </Button>
              </div>
            </div>
          </div>
          <Button @click="deleteEdge(selectedEdge.id)">
            Delete Connection
          </Button>
        </div>
      </div>
    </div>

    <!-- Save Dialog -->
    <div v-if="saveDialogOpen" class="fixed inset-0 z-50 bg-black/50" @click="saveDialogOpen = false">
      <div class="fixed left-[50%] top-[50%] z-50 w-full max-w-lg translate-x-[-50%] translate-y-[-50%] rounded-lg border border-gray-200 bg-white p-4 shadow-lg duration-200 text-slate-900" @click.stop>
        <div class="flex flex-col space-y-1.5 p-6">
          <h2 class="text-lg font-semibold leading-none tracking-tight">Save Simulation Template</h2>
          <p class="text-sm text-gray-500 mt-2">Enter a name and description for your simulation template</p>
        </div>
        <div class="space-y-4 p-6">
          <div class="space-y-2">
            <label class="text-sm font-semibold">Template Name</label>
            <input v-model="templateName" class="flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-base ring-offset-white placeholder:text-gray-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50" placeholder="e.g., Distribution System Test" />
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold">Description</label>
            <textarea v-model="templateDescription" class="flex min-h-[80px] w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-base ring-offset-white placeholder:text-gray-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50" placeholder="Describe your simulation template..."></textarea>
          </div>
        </div>
        <div class="flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 p-6 pt-0">
          <Button variant="outline" @click="saveDialogOpen = false">
            Cancel
          </Button>
          <Button @click="saveTemplate">
            Save Template
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, computed, watch, markRaw } from 'vue'
import { useRouter } from 'vue-router'
import { useVueFlow, VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import { api } from '@/lib/api'
import type {PortDefinition, EdgeWire, EdgeData, NodeData} from '@/lib/flowTypes'
import { COMPONENT_CATALOG } from '@/lib/componentCatalog'
import type { Node, Edge, Connection } from '@vue-flow/core'
import CustomNode from '@/components/CustomNode.vue'
import CustomEdge from '@/components/CustomEdge.vue'
import { Button } from '@/components/ui/button'

// Register custom node types
const nodeTypes = {
  custom: markRaw(CustomNode),
}

const edgeTypes = {
  wiring: markRaw(CustomEdge),
}

const router = useRouter()
const navigate = (path: string) => router.push(path)

const components = COMPONENT_CATALOG

const nodes = ref<Node[]>([])
const edges = ref<Edge[]>([])
const selectedNode = ref<Node | null>(null)
const selectedEdge = ref<Edge | null>(null)
const saveDialogOpen = ref(false)
const templateName = ref('')
const templateDescription = ref('')
const selectedWireOption = ref('')
const { screenToFlowCoordinate } = useVueFlow()

const addNode = (type: string, position: { x: number; y: number }) => {
  const component = components.find(c => c.id === type)
  const newNode: Node = {
    id: `${type}-${Date.now()}`,
    type: 'custom',
    position,
    data: {
      label: component?.name || type.charAt(0).toUpperCase() + type.slice(1),
      config: {},
      componentType: type,
    },
  }
  nodes.value.push(newNode)
}

const onDrop = async (event: DragEvent) => {
  event.preventDefault()
  const type = event.dataTransfer?.getData('application/node')
  if (type) {
    await nextTick()
    
    const position = screenToFlowCoordinate({
        x: event.clientX,
        y: event.clientY,
      })
    addNode(type, position)
  }
}

const onDragOver = (event: DragEvent) => {
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
}

const onDragStart = (componentId: string, dragEvent: DragEvent) => {
  if (dragEvent.dataTransfer) {
    dragEvent.dataTransfer.effectAllowed = 'move'
    dragEvent.dataTransfer.setData('application/node', componentId)
  }
}

const onNodeClick = (event: { node: Node }) => {
  selectedNode.value = event.node
  selectedEdge.value = null
}

const onEdgeClick = (event: { edge: Edge }) => {
  selectedEdge.value = event.edge
  selectedNode.value = null
}

const onPaneClick = () => {
  selectedNode.value = null
  selectedEdge.value = null
}

const onConnect = (connection: Connection) => {
  if (connection.source && connection.target) {
    // Check if edge already exists to avoid duplicates
    const edgeExists = edges.value.some(
      (e) => e.source === connection.source && e.target === connection.target
    )
    if (!edgeExists) {
      const newEdge: Edge = {
        id: `edge-${connection.source}-${connection.target}-${Date.now()}`,
        source: connection.source,
        target: connection.target,
        type: 'wiring',
        data: {
          wires: [],
        },
      }
      edges.value.push(newEdge)
    }
  }
}

const wireOptionKey = (wire: EdgeWire) => `${wire.type}::${wire.sourcePortId}::${wire.targetPortId}`

const parseWireOption = (value: string): EdgeWire | null => {
  const [type, sourcePortId, targetPortId] = value.split('::')
  if (!type || !sourcePortId || !targetPortId) {
    return null
  }

  return {
    type,
    sourcePortId,
    targetPortId,
  }
}

const getNodeComponentType = (nodeId: string): string | null => {
  const node = nodes.value.find((n) => n.id === nodeId)
  const data = node?.data as Record<string, unknown> | undefined
  const componentType = data?.componentType
  return typeof componentType === 'string' ? componentType : null
}

const normalizePorts = (ports: Array<Record<string, unknown>>): PortDefinition[] => {
  return ports
    .map((port) => ({
      type: typeof port.type === 'string' ? port.type : '',
      port_id: typeof port.port_id === 'string' ? port.port_id : '',
    }))
    .filter((port) => port.type && port.port_id)
}

const getCompatibleWireOptions = (edge: Edge | null): EdgeWire[] => {
  if (!edge) {
    return []
  }

  const sourceComponentType = getNodeComponentType(edge.source)
  const targetComponentType = getNodeComponentType(edge.target)

  if (!sourceComponentType || !targetComponentType) {
    return []
  }

  const sourceComponent = components.find((component) => component.id === sourceComponentType)
  const targetComponent = components.find((component) => component.id === targetComponentType)

  if (!sourceComponent || !targetComponent) {
    return []
  }

  const outputs = normalizePorts(sourceComponent.definition.dynamic_outputs)
  const inputs = normalizePorts(targetComponent.definition.dynamic_inputs)
  const options: EdgeWire[] = []
  const seen = new Set<string>()

  outputs.forEach((output) => {
    inputs.forEach((input) => {
      if (output.type === input.type) {
        const wire: EdgeWire = {
          type: output.type,
          sourcePortId: output.port_id,
          targetPortId: input.port_id,
        }
        const key = wireOptionKey(wire)
        if (!seen.has(key)) {
          seen.add(key)
          options.push(wire)
        }
      }
    })
  })

  return options
}

const compatibleWireOptions = computed<EdgeWire[]>(() => getCompatibleWireOptions(selectedEdge.value))

const selectedEdgeWires = computed<EdgeWire[]>(() => {
  if (!selectedEdge.value) {
    return []
  }

  const edgeData = selectedEdge.value.data as EdgeData | undefined
  return edgeData?.wires ?? []
})

const selectedNodeStaticInputs = computed<PortDefinition[]>(() => {
  if (!selectedNode.value) {
    return []
  }

  const nodeData = selectedNode.value.data as NodeData | undefined
  const componentType = nodeData?.componentType
  if (!componentType) {
    return []
  }

  const component = components.find((item) => item.id === componentType)
  if (!component) {
    return []
  }

  return component.definition.static_inputs
    .map((port) => ({
      type: typeof port.type === 'string' ? port.type : '',
      port_id: typeof port.port_id === 'string' ? port.port_id : '',
    }))
    .filter((port) => port.port_id)
})

const getSelectedNodeConfigValue = (portId: string): string => {
  if (!selectedNode.value) {
    return ''
  }

  const nodeData = selectedNode.value.data as NodeData | undefined
  return nodeData?.config?.[portId] ?? ''
}

const updateNodeConfig = (nodeId: string, portId: string, value: string) => {
  nodes.value = nodes.value.map((node) => {
    if (node.id !== nodeId) {
      return node
    }

    const currentData = (node.data as NodeData | undefined) ?? { label: node.id }
    const currentConfig = currentData.config ?? {}

    return {
      ...node,
      data: {
        ...currentData,
        config: {
          ...currentConfig,
          [portId]: value,
        },
      },
    }
  })

  if (selectedNode.value?.id === nodeId) {
    selectedNode.value = nodes.value.find((node) => node.id === nodeId) || null
  }
}

const onStaticInputChange = (portId: string, event: Event) => {
  if (!selectedNode.value) {
    return
  }

  const target = event.target as HTMLInputElement
  updateNodeConfig(selectedNode.value.id, portId, target.value)
}

const wireDisplayLabel = (wire: EdgeWire): string => wire.type

const buildEdgeLabel = (wires: EdgeWire[]): string | undefined => {
  if (wires.length === 0) {
    return undefined
  }

  return wires.map(wireDisplayLabel).join('\n')
}

const updateEdgeData = (edgeId: string, wires: EdgeWire[]) => {
  const nextLabel = buildEdgeLabel(wires)
  edges.value = edges.value.map((edge) => {
    if (edge.id !== edgeId) {
      return edge
    }

    return {
      ...edge,
      data: {
        ...(edge.data as Record<string, unknown> | undefined),
        wires,
      },
      label: nextLabel,
      type: 'wiring',
    }
  })

  if (selectedEdge.value?.id === edgeId) {
    const updatedEdge = edges.value.find((edge) => edge.id === edgeId) || null
    selectedEdge.value = updatedEdge
  }
}

const addWireToSelectedEdge = () => {
  if (!selectedEdge.value || !selectedWireOption.value) {
    return
  }

  const selectedWire = parseWireOption(selectedWireOption.value)
  if (!selectedWire) {
    return
  }

  const validOptions = compatibleWireOptions.value
  const isValidOption = validOptions.some((option) => wireOptionKey(option) === wireOptionKey(selectedWire))
  if (!isValidOption) {
    return
  }

  const existingWires = selectedEdgeWires.value
  const alreadyExists = existingWires.some((wire) => wireOptionKey(wire) === wireOptionKey(selectedWire))
  if (alreadyExists) {
    return
  }

  updateEdgeData(selectedEdge.value.id, [...existingWires, selectedWire])
}

const removeWireFromSelectedEdge = (wireToRemove: EdgeWire) => {
  if (!selectedEdge.value) {
    return
  }

  const updatedWires = selectedEdgeWires.value.filter(
    (wire) => wireOptionKey(wire) !== wireOptionKey(wireToRemove)
  )
  updateEdgeData(selectedEdge.value.id, updatedWires)
}

watch(
  [selectedEdge, compatibleWireOptions],
  ([edge, options]) => {
    if (!edge || options.length === 0) {
      selectedWireOption.value = ''
      return
    }

    const currentIsValid = options.some((option) => wireOptionKey(option) === selectedWireOption.value)
    if (!currentIsValid) {
      selectedWireOption.value = wireOptionKey(options[0])
    }
  },
  { immediate: true }
)

const deleteNode = (nodeId: string) => {
  nodes.value = nodes.value.filter((n) => n.id !== nodeId)
  edges.value = edges.value.filter((e) => e.source !== nodeId && e.target !== nodeId)
  selectedNode.value = null
  selectedEdge.value = null
}

const deleteEdge = (edgeId: string) => {
  edges.value = edges.value.filter((e) => e.id !== edgeId)
  selectedEdge.value = null
}

const getNodeLabel = (nodeId: string): string => {
  const node = nodes.value.find((n) => n.id === nodeId)
  return node?.data?.label || nodeId
}

const saveTemplate = async () => {
  const config = {
    id: Date.now().toString(),
    name: templateName.value || `Flow ${new Date().toLocaleString()}`,
    description: templateDescription.value,
    nodes: nodes.value,
    edges: edges.value,
    createdAt: new Date().toISOString(),
  }

  try {
    // Save to backend API (stores in data folder)
    await api.saveTemplate(config)
    
    // Also download JSON file for backup
    const jsonString = JSON.stringify(config, null, 2)
    const blob = new Blob([jsonString], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${config.name.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_${Date.now()}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    saveDialogOpen.value = false
    templateName.value = ''
    templateDescription.value = ''
    
    // Optionally navigate to saved configs page
    // router.push('/configs')
  } catch (error) {
    console.error('Error saving template:', error)
    alert('Failed to save template. Please try again.')
  }
}

// Load template from sessionStorage if available (when coming from SavedConfigs)
onMounted(() => {
  const loadTemplateData = sessionStorage.getItem('loadTemplate')
  if (loadTemplateData) {
    try {
      const config = JSON.parse(loadTemplateData)
      nodes.value = config.nodes || []
      edges.value = (config.edges || []).map((edge: Edge) => {
        const edgeData = edge.data as EdgeData | undefined
        const wires = edgeData?.wires ?? []
        return {
          ...edge,
          type: 'wiring',
          label: buildEdgeLabel(wires),
        }
      })
      // Clear the sessionStorage after loading
      sessionStorage.removeItem('loadTemplate')
    } catch (error) {
      console.error('Error loading template:', error)
    }
  }
})
</script>

<style>
.vue-flow-container {
  width: 100%;
  height: 100%;
}
</style>
