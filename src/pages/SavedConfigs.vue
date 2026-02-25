<template>
  <div class="min-h-screen bg-gray-50 p-8">
    <div class="max-w-6xl mx-auto">
      <div class="mb-8">
        <router-link to="/" class="text-blue-600 hover:text-blue-800 mb-4 inline-block">← Back to Home</router-link>
        <h1 class="text-3xl font-bold mb-2">Saved Simulation Templates</h1>
        <p class="text-gray-600">Manage and run your saved simulation configurations</p>
      </div>

      <div v-if="loading" class="bg-white rounded-lg p-8 text-center">
        <p class="text-gray-500">Loading templates...</p>
      </div>
      <div v-else-if="savedConfigs.length === 0" class="bg-white rounded-lg p-8 text-center">
        <p class="text-gray-500 mb-4">No saved templates yet</p>
        <router-link to="/designer">
          <button class="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-slate-900 text-white hover:bg-slate-800 h-10 px-4 py-2">
            Create Your First Template
          </button>
        </router-link>
      </div>

      <div v-else class="grid gap-4">
        <div
          v-for="config in savedConfigs"
          :key="config.id"
          class="bg-white rounded-lg border border-gray-200 p-6 hover:shadow-md transition-shadow"
        >
          <div class="flex items-start justify-between gap-4">
            <div class="flex-1">
              <h3 class="text-xl font-semibold mb-2">{{ config.name }}</h3>
              <p class="text-gray-600 mb-4">{{ config.description || 'No description' }}</p>
              
              <!-- Components List -->
              <div v-if="config.nodes && config.nodes.length > 0" class="mb-4">
                <h4 class="text-sm font-semibold text-gray-700 mb-2">Components:</h4>
                <div class="flex flex-wrap gap-2">
                  <span
                    v-for="node in config.nodes"
                    :key="node.id"
                    class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                  >
                    {{ node.data?.label || node.data?.componentType || 'Component' }}
                  </span>
                </div>
              </div>
              
              <div class="flex gap-4 text-sm text-gray-500">
                <span>Nodes: {{ config.nodes?.length || 0 }}</span>
                <span>Connections: {{ config.edges?.length || 0 }}</span>
                <span>Created: {{ formatDate(config.createdAt) }}</span>
              </div>
            </div>
            <div class="flex flex-col gap-2">
              <button
                class="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-green-600 text-white hover:bg-green-700 h-10 px-4 py-2"
                @click="runTemplate(config)"
              >
                ▶ Run
              </button>
              <button
                class="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-blue-600 text-white hover:bg-blue-700 h-10 px-4 py-2"
                @click="loadTemplate(config)"
              >
                Load
              </button>
              <button
                class="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-gray-300 bg-white hover:bg-gray-50 h-10 px-4 py-2"
                @click="downloadTemplate(config)"
              >
                Download JSON
              </button>
              <button
                class="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-red-600 text-white hover:bg-red-700 h-10 px-4 py-2"
                @click="deleteTemplate(config.id)"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api, type SavedConfig } from '@/lib/api'

const router = useRouter()
const savedConfigs = ref<SavedConfig[]>([])
const loading = ref(false)

const loadConfigs = async () => {
  loading.value = true
  try {
    savedConfigs.value = await api.getTemplates()
  } catch (error) {
    console.error('Error loading configs:', error)
  } finally {
    loading.value = false
  }
}

const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const runTemplate = (config: SavedConfig) => {
  // Store the config to run in the simulation
  sessionStorage.setItem('runTemplate', JSON.stringify(config))
  router.push('/status')
}

const loadTemplate = (config: SavedConfig) => {
  // Store the config to load in the designer
  sessionStorage.setItem('loadTemplate', JSON.stringify(config))
  router.push('/designer')
}

const downloadTemplate = (config: SavedConfig) => {
  const jsonString = JSON.stringify(config, null, 2)
  const blob = new Blob([jsonString], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${config.name.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_${config.id}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

const deleteTemplate = async (id: string) => {
  if (confirm('Are you sure you want to delete this template?')) {
    try {
      await api.deleteTemplate(id)
      savedConfigs.value = savedConfigs.value.filter((c) => c.id !== id)
    } catch (error) {
      console.error('Error deleting template:', error)
      alert('Failed to delete template. Please try again.')
    }
  }
}

onMounted(() => {
  loadConfigs()
})
</script>
