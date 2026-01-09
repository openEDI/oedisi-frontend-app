<template>
  <div class="w-64 bg-white border-r p-6 overflow-y-auto">
    <h2 class="text-lg font-semibold mb-6">Components</h2>

    <div class="space-y-4">
      <div
        v-for="component in components"
        :key="component.id"
        class="p-4 bg-gray-50 rounded-lg cursor-move hover:bg-gray-100 transition-colors"
        draggable
        @dragstart="onDragStart(component.id, $event as DragEvent)"
      >
        <div class="flex items-center gap-3">
          <component :is="component.icon" :size="20" class="text-blue-600" />
          <div>
            <h3 class="font-medium text-sm">{{ component.name }}</h3>
            <p class="text-xs text-gray-500">{{ component.description }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Zap, Database, Network, Settings } from 'lucide-vue-next'

interface Component {
  id: string
  name: string
  description: string
  icon: any
}

const components: Component[] = [
  {
    id: 'feeder',
    name: 'Feeder',
    description: 'OpenDSS simulation engine',
    icon: Zap,
  },
  {
    id: 'wls_se_algorihtm',
    name: 'State Estimator',
    description: 'WSL State Estimator',
    icon: Settings,
  },
  {
    id: 'sensor',
    name: 'Sensor',
    description: 'Sensor model',
    icon: Network,
  },
  {
    id: 'recorder',
    name: 'Recorder',
    description: 'Records simulation results',
    icon: Database,
  },
]

const onDragStart = (componentId: string, dragEvent: DragEvent) => {
  if (dragEvent.dataTransfer) {
    dragEvent.dataTransfer.effectAllowed = 'move'
    dragEvent.dataTransfer.setData('application/node', componentId)
  }
}
</script>
