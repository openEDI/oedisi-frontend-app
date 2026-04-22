<template>
  <div class="h-screen flex flex-col">
    <div class="bg-card border-b px-4 py-3 flex items-center justify-between">
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
      <div class="w-64 bg-card border-r p-6 overflow-y-auto">
        <h2 class="text-lg font-semibold mb-6">Components</h2>
        <div class="space-y-4">
          <div v-for="component in components" :key="component.id"
            class="p-4 bg-muted rounded-lg cursor-move hover:bg-muted/80 transition-colors" draggable="true"
            @dragstart="(e) => onDragStart(component.id, e)">
            <h3 class="font-medium text-sm">{{ component.name }}</h3>
            <p class="text-xs text-muted-foreground">{{ component.description }}</p>
          </div>
        </div>
      </div>

      <div class="flex-1 relative bg-muted">
        <VueFlow ref="vueFlowRef" v-model:nodes="nodes" v-model:edges="edges" class="vue-flow-container"
          :connection-line-style="{ stroke: 'var(--foreground)', strokeWidth: 1 }"
          :default-edge-options="{ type: 'wiring' }" :fit-view-on-init="true" :node-types="nodeTypes"
          :edge-types="edgeTypes" @drop="onDrop" @dragover="onDragOver" @node-click="onNodeClick"
          @edge-click="onEdgeClick" @pane-click="onPaneClick" @connect="onConnect">
          <Background pattern-color="var(--muted-foreground)" :gap="16" />
          <Controls />
          <MiniMap node-color="var(--muted-foreground)" mask-color="var(--background)"
            :style="{ background: 'var(--card)' }" />
        </VueFlow>
      </div>

      <div class="w-72 bg-card border-l p-6 overflow-y-auto">
        <h2 class="text-lg font-semibold mb-6">Properties</h2>
        <div v-if="!selectedNode && !selectedEdge" class="text-muted-foreground text-center py-8">
          <p>Select a component or connection to view properties</p>
        </div>

        <!-- Node Properties -->
        <div v-else-if="selectedNode" class="space-y-4">
          <div class="space-y-2">
            <label class="text-sm font-semibold">Static Inputs</label>
            <div v-if="selectedNodeSchema" class="space-y-2">
              <JsonForms :data="nodeConfig" :schema="selectedNodeSchema" :renderers="renderers" :ajv="ajv"
                :validation-mode="'ValidateAndHide'" @change="updateNodeConfig" />
            </div>
            <p v-else class="text-sm text-muted-foreground">No static inputs for this component.</p>
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold">Component Type</label>
            <p class="text-sm text-muted-foreground">{{ selectedNode.data.label }}</p>
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold">Node ID</label>
            <p class="text-sm text-muted-foreground font-mono">{{ selectedNode.id }}</p>
          </div>
          <Button variant="destructive" @click="deleteNode(selectedNode.id)">
            Delete Component
          </Button>
        </div>

        <!-- Edge Properties -->
        <div v-else-if="selectedEdge" class="space-y-4">
          <div class="space-y-2">
            <label class="text-sm font-semibold">Connection ID</label>
            <p class="text-sm text-muted-foreground font-mono">{{ selectedEdge.id }}</p>
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold">Source Node</label>
            <p class="text-sm text-muted-foreground">{{ getNodeLabel(selectedEdge.source) }}</p>
            <p class="text-xs text-muted-foreground font-mono">{{ selectedEdge.source }}</p>
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold">Target Node</label>
            <p class="text-sm text-muted-foreground">{{ getNodeLabel(selectedEdge.target) }}</p>
            <p class="text-xs text-muted-foreground font-mono">{{ selectedEdge.target }}</p>
          </div>
          <div v-if="selectedEdge.type" class="space-y-2">
            <label class="text-sm font-semibold">Connection Type</label>
            <p class="text-sm text-muted-foreground">{{ selectedEdge.type }}</p>
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold">Wiring Selection</label>
            <p v-if="compatibleWireOptions.length === 0" class="text-sm text-muted-foreground">
              No compatible dynamic output/input intersections for this connection.
            </p>
            <div v-else class="space-y-2">
              <select v-model="selectedWireOption"
                class="h-10 w-full rounded-md border border-border px-3 py-2 bg-card text-sm">
                <option value="" disabled>Select compatible signal</option>
                <option v-for="option in compatibleWireOptions" :key="wireOptionKey(option)"
                  :value="wireOptionKey(option)">
                  {{ option.type }}: {{ option.sourcePortId }} → {{ option.targetPortId }}
                </option>
              </select>
              <Button :disabled="!selectedWireOption" @click="addWireToSelectedEdge">
                Add Wiring
              </Button>
            </div>
          </div>
          <div v-if="selectedEdgeWires.length > 0" class="space-y-2">
            <label class="text-sm font-semibold">Wiring Diagram Entries</label>
            <div class="space-y-1">
              <div v-for="wire in selectedEdgeWires" :key="wireOptionKey(wire)"
                class="flex items-center justify-between gap-2 text-xs text-muted-foreground font-mono bg-muted/50 rounded px-2 py-1">
                <span>{{ wire.type }}: {{ wire.sourcePortId }} → {{ wire.targetPortId }}</span>
                <Button variant="ghost" size="sm" @click="removeWireFromSelectedEdge(wire)">
                  Remove
                </Button>
              </div>
            </div>
          </div>
          <Button variant="destructive" @click="deleteEdge(selectedEdge.id)">
            Delete Connection
          </Button>
        </div>
      </div>
    </div>

    <!-- Save Dialog -->
    <Dialog v-model:open="saveDialogOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Save Simulation Template</DialogTitle>
          <DialogDescription>Enter a name and description for your simulation template</DialogDescription>
        </DialogHeader>
        <div class="space-y-2">
          <label class="text-sm font-semibold">Template Name</label>
          <Input v-model="templateName" placeholder="e.g., Distribution System Test" />
        </div>
        <div class="space-y-2">
          <label class="text-sm font-semibold">Description</label>
          <Textarea v-model="templateDescription" placeholder="Describe your simulation template..."></Textarea>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="saveDialogOpen = false">Cancel</Button>
          <Button variant="secondary" @click="exportTemplate">Export as Wiring Diagram</Button>
          <Button @click="saveTemplate">Save Template</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, computed, watch, markRaw, provide } from 'vue'
import { useRouter } from 'vue-router'
import { useVueFlow, VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import { api } from '@/lib/api'
import type { PortDefinition, EdgeWire, EdgeData, NodeData, TemplateData } from '@/lib/flowTypes'
import { COMPONENT_CATALOG } from '@/lib/componentCatalog'
import type { Node, Edge, Connection } from '@vue-flow/core'
import CustomNode from '@/components/CustomNode.vue'
import CustomEdge from '@/components/CustomEdge.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Dialog, DialogDescription, DialogTitle, DialogHeader, DialogContent, DialogFooter } from '@/components/ui/dialog'
import { isCompatible } from '@/lib/portCompatibility'
import { JsonForms } from '@jsonforms/vue'
import { vanillaRenderers, defaultStyles, mergeStyles } from '@jsonforms/vue-vanilla'
import { createAjv, JsonSchema } from '@jsonforms/core'
import { toWiringDiagram, WiringDiagram } from '@/lib/wiringDiagram'

const renderers = markRaw(vanillaRenderers)
const ajv = createAjv({ useDefaults: true })

const nodePropertyStyles = mergeStyles(defaultStyles, {
  control: {
    root: 'mb-3',
    label: 'text-xs font-medium text-muted-foreground mb-1',
    input: 'flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm',
    asterisk: 'text-red-500 ml-0.5',
  },
  arrayList: {
    root: 'mb-3',
    label: 'text-xs font-medium text-muted-foreground mb-1',
    addButton: 'text-xs px-2 py-1 border border-input rounded-md mt-1 hover:bg-muted cursor-pointer',
    itemWrapper: 'flex items-center gap-2 mb-1',
    itemDelete: 'text-xs text-red-500 cursor-pointer hover:text-red-700',
    noData: 'text-xs text-muted-foreground',
  },
})

provide('styles', nodePropertyStyles)

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
const selectedNodeId = ref<string | null>(null)
const selectedEdgeId = ref<string | null>(null)
const selectedNode = computed<Node | null>(() => {
  return nodes.value.find((node) => node.id === selectedNodeId.value) ?? null
})
const selectedEdge = computed<Edge | null>(() => {
  return edges.value.find((edge) => edge.id === selectedEdgeId.value) ?? null
})
const saveDialogOpen = ref(false)
const templateName = ref('')
const templateDescription = ref('')
const selectedWireOption = ref('')
const { screenToFlowCoordinate } = useVueFlow()

const addNode = (type: string, position: { x: number; y: number }) => {
  const component = components.find(c => c.id === type)
  const newNode: Node<NodeData> = {
    id: `${type}-${Date.now()}`,
    type: 'custom',
    position,
    data: {
      label: component?.name || type.charAt(0).toUpperCase() + type.slice(1),
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
  selectedNodeId.value = event.node.id
  selectedEdgeId.value = null
}

const onEdgeClick = (event: { edge: Edge }) => {
  selectedEdgeId.value = event.edge.id
  selectedNodeId.value = null
}

const onPaneClick = () => {
  selectedNodeId.value = null
  selectedEdgeId.value = null
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
      if (isCompatible(output.type, input.type)) {
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

const selectedNodeSchema = computed<JsonSchema | null>(() => {
  if (!selectedNode.value) {
    return null
  }

  const nodeData = selectedNode.value.data as NodeData | undefined
  const componentType = nodeData?.componentType
  if (!componentType) {
    return null
  }

  const component = components.find((item) => item.id === componentType)
  if (!component) {
    return null
  }
  if (!component.inputSchema) {
    return null
  }
  return component.inputSchema ?? {}
})

/*const nodeConfig = computed(() => {
  return selectedNode.value?.data?.config
})*/
const nodeConfig = computed(() => {
  const nodeData = selectedNode.value?.data as NodeData | undefined
  return nodeData?.config ?? {}
})

const updateNodeConfig = (event: { data: unknown }) => {
  const node = nodes.value.find((node) => node.id === selectedNodeId.value)
  if (!node) {
    return
  }
  const currentData = (node.data as NodeData | undefined) ?? { label: node.id }
  node.data = { ...currentData, config: event.data }
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
  const edge = edges.value.find((edge) => edge.id === edgeId)
  if (!edge) {
    return
  }
  edge.data = {
    ...(edge.data as Record<string, unknown> | undefined),
    wires
  }
  edge.label = nextLabel
  edge.type = 'wiring'
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
  selectedNodeId.value = null
  selectedEdgeId.value = null
}

const deleteEdge = (edgeId: string) => {
  edges.value = edges.value.filter((e) => e.id !== edgeId)
  selectedEdgeId.value = null
}

const getNodeLabel = (nodeId: string): string => {
  const node = nodes.value.find((n) => n.id === nodeId)
  return node?.data?.label || nodeId
}

function getTemplate(name: string, description: string, nodes: Node[], edges: Edge[]): TemplateData {
  return {
    id: Date.now().toString(),
    name: name || `Flow ${new Date().toLocaleString()}`,
    description: description,
    nodes: nodes,
    edges: edges,
    createdAt: new Date().toISOString(),
  }
}

const saveTemplate = async () => {
  const config: TemplateData = getTemplate(templateName.value, templateDescription.value, nodes.value, edges.value)

  try {
    await api.saveTemplate(config)

    saveDialogOpen.value = false
  } catch (error) {
    console.error('Error saving template:', error)
    alert('Failed to save template. Please try again.')
  }
}

const exportTemplate = () => {
  const config: TemplateData = getTemplate(templateName.value, templateDescription.value, nodes.value, edges.value)
  let wiringDiagram: WiringDiagram
  try {
    wiringDiagram = toWiringDiagram(config)
  } catch (error) {
    console.error('Error exporting wiring diagram:', error)
    alert('Failed to export wiring diagram. Check that all components and connections are configured.')
    return
  }

  const jsonString = JSON.stringify(wiringDiagram, null, 2)
  const blob = new Blob([jsonString], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${config.name.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_wiring_${Date.now()}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)

  saveDialogOpen.value = false
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

.vue-flow__controls {
  background: var(--card);
  border-color: var(--border);
}

.vue-flow .vue-flow__controls-button {
  background: var(--card);
  border-bottom-color: var(--border);
}

.vue-flow .vue-flow__controls-button svg {
  stroke: var(--foreground);
  fill: var(--foreground);
}

.vue-flow .vue-flow__controls-button:hover {
  background: var(--muted);
}

.array-list-item-delete {
  font-size: 0;
}

.array-list-item-delete::after {
  content: "×";
  font-size: 0.875rem;
}

.control input[type="checkbox"] {
  width: 1rem;
  height: 1rem;
  margin-right: 0.5rem;
  cursor: pointer;
}

@media (prefers-color-scheme: dark) {
  .control input[type="checkbox"] {
    color-scheme: dark;
  }
}
</style>
