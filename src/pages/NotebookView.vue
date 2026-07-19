<template>
  <div class="flex flex-col h-screen">
    <div class="flex items-center gap-3 p-4 border-b">
      <router-link :to="`/runs/${runId}/results`"
        class="text-primary hover:text-primary/80">← Back to
        Results</router-link>
      <h1 class="text-xl font-bold flex-1">Notebook</h1>
      <Button variant="destructive" size="sm" @click="handleDelete">
        Delete Notebook
      </Button>
    </div>
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <p class="text-muted-foreground">Loading notebook...</p>
    </div>
    <div v-else-if="error" class="flex-1 flex items-center justify-center">
      <p class="text-destructive">{{ error }}</p>
    </div>
    <iframe v-else-if="jupyterUrl" :src="jupyterUrl"
      class="flex-1 w-full border-0" allow="clipboard-write" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onActivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'

const route = useRoute()
const router = useRouter()
const runId = computed<string>(() => String(route.params.runId))

const jupyterUrl = ref<string | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

async function loadNotebook() {
  loading.value = true
  error.value = null
  try {
    const status = await api.getNotebookStatus(runId.value)
    if (!status.exists) {
      const result = await api.createNotebook(runId.value)
      jupyterUrl.value = result.jupyter_url
    } else {
      jupyterUrl.value = status.jupyter_url
    }
  } catch (e) {
    error.value = `Failed to load notebook: ${e instanceof Error ? e.message : String(e)}`
  } finally {
    loading.value = false
  }
}

async function handleDelete() {
  if (!confirm('Delete this notebook? This cannot be undone.')) return
  try {
    await api.deleteNotebook(runId.value)
    router.push(`/runs/${runId.value}/results`)
  } catch (e) {
    alert(`Failed to delete notebook: ${e instanceof Error ? e.message : String(e)}`)
  }
}

onActivated(() => {
  loadNotebook()
})
</script>
