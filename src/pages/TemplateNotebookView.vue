<template>
  <div class="flex flex-col h-screen">
    <div class="flex items-center gap-3 p-4 border-b">
      <router-link to="/configs"
        class="text-primary hover:text-primary/80">← Back to
        Templates</router-link>
      <h1 class="text-xl font-bold flex-1">Template Notebook</h1>
      <Button variant="destructive" size="sm" @click="handleDelete"
        :disabled="!jupyterUrl">
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
const templateId = computed<string>(() => String(route.params.templateId))

const jupyterUrl = ref<string | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

async function loadNotebook() {
  loading.value = true
  error.value = null
  try {
    const status = await api.getTemplateNotebookStatus(templateId.value)
    if (!status.exists) {
      const result = await api.createTemplateNotebook(templateId.value)
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
  if (!confirm('Delete this template notebook? This cannot be undone.')) return
  try {
    await api.deleteTemplateNotebook(templateId.value)
    router.push('/configs')
  } catch (e) {
    alert(`Failed to delete notebook: ${e instanceof Error ? e.message : String(e)}`)
  }
}

onActivated(() => {
  loadNotebook()
})
</script>
