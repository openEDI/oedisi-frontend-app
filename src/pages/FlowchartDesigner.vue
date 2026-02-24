<template>
  <div class="h-screen flex flex-col">
    <div class="bg-white border-b px-4 py-3 flex items-center justify-between">
      <div class="flex items-center gap-4">
        <button @click="navigate('/')" class="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 hover:bg-slate-100 hover:text-slate-900 h-10 w-10">
          🏠
        </button>
        <h1 class="text-xl font-semibold">OEDISI Simulation Designer</h1>
      </div>
      <div class="flex items-center gap-2">
        <button @click="navigate('/configs')" class="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-gray-300 bg-white hover:bg-gray-50 hover:text-slate-900 h-10 px-4 py-2">
          📁 Saved Templates
        </button>
        <button @click="saveDialogOpen = true" class="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-slate-900 text-white hover:bg-slate-800 h-10 px-4 py-2">
          💾 Save Template
        </button>
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
          @drop="onDrop"
          @dragover="onDragOver"
          @node-click="onNodeClick"
          @edge-click="onEdgeClick"
          @pane-click="onPaneClick"
          @connect="onConnect"
          :connection-line-style="{ stroke: '#b1b1b7', strokeWidth: 1 }"
          :default-edge-options="{ type: 'default' }"
          :fit-view-on-init="true"
          :node-types="nodeTypes"
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
            <label class="text-sm font-semibold">Component Type</label>
            <p class="text-sm text-gray-600">{{ selectedNode.data.label }}</p>
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold">Node ID</label>
            <p class="text-sm text-gray-600 font-mono">{{ selectedNode.id }}</p>
          </div>
          <button @click="deleteNode(selectedNode.id)" class="w-full inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-red-600 text-white hover:bg-red-700 h-10 px-4 py-2 mt-4">
            Delete Component
          </button>
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
          <div class="space-y-2" v-if="selectedEdge.type">
            <label class="text-sm font-semibold">Connection Type</label>
            <p class="text-sm text-gray-600">{{ selectedEdge.type }}</p>
          </div>
          <button @click="deleteEdge(selectedEdge.id)" class="w-full inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-red-600 text-white hover:bg-red-700 h-10 px-4 py-2 mt-4">
            Delete Connection
          </button>
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
          <button @click="saveDialogOpen = false" class="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-gray-300 bg-white hover:bg-gray-50 hover:text-slate-900 h-10 px-4 py-2">
            Cancel
          </button>
          <button @click="saveTemplate" class="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-slate-900 text-white hover:bg-slate-800 h-10 px-4 py-2">
            Save Template
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import CustomNode from '@/components/CustomNode.vue'
import { api } from '@/lib/api'
import { COMPONENT_CATALOG } from '@/lib/componentCatalog'
import type { Node, Edge, NodeClickEvent, EdgeClickEvent, PaneClickEvent, Connection } from '@vue-flow/core'

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
const vueFlowRef = ref<any>(null)

// Register custom node types
const nodeTypes = {
  custom: CustomNode,
}

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
    let position = { x: 0, y: 0 }
    
    // Try to get the Vue Flow instance and use screenToFlowCoordinate if available
    const instance = vueFlowRef.value
    if (instance?.screenToFlowCoordinate) {
      position = instance.screenToFlowCoordinate({
        x: event.clientX,
        y: event.clientY,
      })
    } else {
      // Fallback: calculate position relative to the pane
      const pane = (event.target as HTMLElement).closest('.vue-flow__viewport') || 
                   (event.target as HTMLElement).closest('.vue-flow')
      if (pane) {
        const rect = pane.getBoundingClientRect()
        // Simple position calculation (will be improved when instance is available)
        position = {
          x: event.clientX - rect.left - 100,
          y: event.clientY - rect.top - 100,
        }
      }
    }
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

const onNodeClick = (event: NodeClickEvent) => {
  selectedNode.value = event.node
  selectedEdge.value = null
}

const onEdgeClick = (event: EdgeClickEvent) => {
  selectedEdge.value = event.edge
  selectedNode.value = null
}

const onPaneClick = (event: PaneClickEvent) => {
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
        type: 'default',
      }
      edges.value.push(newEdge)
    }
  }
}

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
      edges.value = config.edges || []
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
