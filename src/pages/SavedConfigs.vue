<template>
  <div class="min-h-screen p-8">
    <div class="max-w-6xl mx-auto">
      <div class="mb-8">
        <router-link to="/"
          class="text-primary hover:text-primary/80 mb-4 inline-block">← Back to
          Home</router-link>
        <h1 class="text-3xl font-bold mb-2">Saved Simulation Templates</h1>
        <p class="text-muted-foreground">Manage and run your saved simulation
          configurations</p>
      </div>

      <div v-if="loading" class="bg-card rounded-lg p-8 text-center">
        <p class="text-muted-foreground">Loading templates...</p>
      </div>
      <div v-else-if="savedConfigs.length === 0"
        class="bg-card rounded-lg p-8 text-center">
        <p class="text-muted-foreground mb-4">No saved templates yet</p>
        <router-link to="/designer">
          <Button>
            Create Your First Template
          </Button>
        </router-link>
      </div>

      <div v-else class="grid gap-4">
        <Card v-for="config in savedConfigs" :key="config.id"
          class="hover:shadow-md transition-shadow">
          <CardHeader>
            <CardTitle>{{ config.name }}</CardTitle>
            <CardDescription>{{ config.description }}</CardDescription>
          </CardHeader>
          <CardContent class="flex items-start justify-between gap-4">
            <div class="flex-1">
              <!-- Components List -->
              <div v-if="config.nodes && config.nodes.length > 0" class="mb-4">
                <h4 class="text-sm font-semibold text-foreground mb-2">
                  Components:</h4>
                <div class="flex flex-wrap gap-2">
                  <span v-for="node in config.nodes" :key="node.id"
                    class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-secondary text-secondary-foreground">
                    {{ node.data?.label || node.data?.componentType ||
                    'Component' }}
                  </span>
                </div>
              </div>

              <div class="flex gap-4 text-sm text-muted-foreground">
                <span>Nodes: {{ config.nodes?.length || 0 }}</span>
                <span>Connections: {{ config.edges?.length || 0 }}</span>
                <span>Created: {{ formatDate(config.createdAt) }}</span>
              </div>
            </div>
            <div class="flex flex-col gap-2">
              <Button :disabled="runPending" @click="runTemplate(config)">
                ▶ Run
              </Button>
              <Button variant="secondary" @click="loadTemplate(config)">
                Load
              </Button>
              <Button variant="outline" @click="downloadTemplate(config)">
                Download JSON
              </Button>
              <Button variant="destructive" @click="deleteTemplate(config.id)">
                Delete
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onActivated, toRaw } from 'vue'
import { type HistoryState, useRouter } from 'vue-router'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { TemplateData } from '@/lib/flowTypes'
import { toWiringDiagram } from '@/lib/wiringDiagram'

const router = useRouter()
const savedConfigs = ref<TemplateData[]>([])
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

const runPending = ref(false)

const runTemplate = async (config: TemplateData) => {
  // Convert to wiringDiagram and start a run.
  try {
    runPending.value = true
    const wiringDiagram = toWiringDiagram(config)
    const { run_id: runId } = await api.startRun(wiringDiagram, config.id)
    router.push(`/runs/${runId}`)
  } catch (error) {
    console.error('runTemplate error:', error)
    alert(`Failed to run template:\n${error instanceof Error ? error.message : String(error)}`)
  } finally {
    runPending.value = false
  }
}

const loadTemplate = (config: TemplateData) => {
  // Use history API to push config to designer.
  router.push({ path: '/designer', state: { template: toRaw(config) } as unknown as HistoryState })
}

const downloadTemplate = (config: TemplateData) => {
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

onActivated(() => {
  loadConfigs()
})
</script>
