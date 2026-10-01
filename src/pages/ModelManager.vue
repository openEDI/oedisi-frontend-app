<template>
  <div class="min-h-screen p-8">
    <div class="max-w-6xl mx-auto">
      <div class="flex items-start justify-between gap-4 mb-8">
        <div>
          <router-link to="/" class="text-primary hover:text-primary/80 mb-4 inline-block">
            ← Back to Home
          </router-link>
          <h1 class="text-3xl font-bold mb-2">Model Manager</h1>
          <p class="text-muted-foreground">
            Upload, convert, and inspect distribution models before using them in a simulation.
          </p>
        </div>
        <router-link to="/designer">
          <Button variant="outline">Open Designer</Button>
        </router-link>
      </div>

      <Card class="mb-8">
        <CardHeader>
          <CardTitle>Upload a model</CardTitle>
          <CardDescription>
            GDM, CIM, OpenDSS, and CYME inputs are detected and converted to an OpenDSS artifact for the Feeder component.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form class="grid gap-4 md:grid-cols-2" @submit.prevent="upload">
            <div class="md:col-span-2 border-2 border-dashed rounded-lg p-6 text-center bg-muted/30">
              <input
                id="model-file"
                ref="fileInput"
                type="file"
                class="block w-full text-sm"
                accept=".zip,.json,.dss,.xml,.rdf"
                required
                @change="handleFileSelect"
              />
              <p v-if="selectedFile" class="text-sm text-muted-foreground mt-2">
                Selected: {{ selectedFile.name }}
              </p>
            </div>

            <div class="space-y-2">
              <label for="model-name" class="text-sm font-semibold">Display name</label>
              <Input id="model-name" v-model="name" placeholder="e.g. IEEE 123 QSTS" />
            </div>
            <div class="space-y-2">
              <label for="model-format" class="text-sm font-semibold">Input format</label>
              <select
                id="model-format"
                v-model="inputFormat"
                class="h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
              >
                <option value="auto">Automatic detection</option>
                <option value="gdm">GDM</option>
                <option value="cim">CIM</option>
                <option value="opendss">OpenDSS</option>
                <option value="cyme">CYME</option>
              </select>
            </div>

            <div class="md:col-span-2 space-y-2">
              <label for="model-description" class="text-sm font-semibold">Description</label>
              <Textarea id="model-description" v-model="description" rows="2" placeholder="What is this model used for?" />
            </div>

            <div v-if="availableLoadModelIds.length > 0" class="md:col-span-2 space-y-2 rounded-md border border-amber-300 bg-amber-50 p-4">
              <label for="load-model-id" class="text-sm font-semibold">CYME load model</label>
              <select
                id="load-model-id"
                v-model="loadModelId"
                class="h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm"
              >
                <option value="" disabled>Select a LoadModelID</option>
                <option v-for="id in availableLoadModelIds" :key="id" :value="id">{{ id }}</option>
              </select>
            </div>

            <div class="md:col-span-2 flex items-center gap-3">
              <Button type="submit" :disabled="uploading || !selectedFile">
                {{ uploading ? 'Converting...' : 'Upload and Convert' }}
              </Button>
              <span v-if="error" class="text-sm text-destructive">{{ error }}</span>
            </div>
          </form>
        </CardContent>
      </Card>

      <div class="flex items-center justify-between mb-4">
        <div>
          <h2 class="text-xl font-semibold">Managed models</h2>
          <p class="text-sm text-muted-foreground">Select a ready model from the Feeder configuration in the designer.</p>
        </div>
        <Button variant="ghost" size="sm" @click="loadModels">Refresh</Button>
      </div>

      <div v-if="loading" class="bg-card rounded-lg p-8 text-center">
        <p class="text-muted-foreground">Loading models...</p>
      </div>
      <div v-else-if="models.length === 0" class="bg-card rounded-lg p-8 text-center">
        <p class="text-muted-foreground">No managed models yet. Upload one above to get started.</p>
      </div>
      <div v-else class="grid gap-4 md:grid-cols-2">
        <Card v-for="model in models" :key="model.id" class="flex flex-col">
          <CardHeader>
            <div class="flex min-w-0 items-start justify-between gap-3">
              <div class="min-w-0 flex-1">
                <CardTitle class="truncate">{{ model.name }}</CardTitle>
                <CardDescription class="line-clamp-2">{{ model.description || 'No description' }}</CardDescription>
              </div>
              <span :class="statusClass(model.status)" class="shrink-0 rounded-full px-2 py-1 text-xs font-medium whitespace-nowrap">
                {{ statusLabel(model.status) }}
              </span>
            </div>
          </CardHeader>
          <CardContent class="flex-1 space-y-4">
            <div class="flex flex-wrap gap-2 text-xs">
              <span class="rounded bg-secondary px-2 py-1">Source: {{ model.source_format.toUpperCase() }}</span>
              <span class="rounded bg-secondary px-2 py-1">Target: OpenDSS</span>
              <span class="rounded bg-secondary px-2 py-1">
                Profiles: {{ model.artifacts.opendss?.profiles_available ? 'available' : 'none' }}
              </span>
              <span class="rounded bg-secondary px-2 py-1">
                {{ model.inspection_summary.element_count || model.inspection_summary.total_components }} DSS elements
              </span>
            </div>
            <p v-if="model.conversion.warnings.length" class="text-sm text-amber-700">
              {{ model.conversion.warnings.length }} conversion warning(s) — inspect before running.
            </p>
            <p class="text-xs text-muted-foreground font-mono break-all">ID: {{ model.id }}</p>
          </CardContent>
          <CardFooter class="flex flex-wrap gap-2">
            <router-link :to="`/models/${model.id}`">
              <Button>Inspect</Button>
            </router-link>
            <a :href="api.modelOpenDssDownloadUrl(model.id)">
              <Button variant="outline">Download OpenDSS</Button>
            </a>
            <Button variant="destructive" @click="removeModel(model)">Delete</Button>
          </CardFooter>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onActivated, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, type ManagedModel, type ModelStatus } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'

const fileInput = ref<HTMLInputElement | null>(null)
const router = useRouter()
const selectedFile = ref<File | null>(null)
const models = ref<ManagedModel[]>([])
const loading = ref(false)
const uploading = ref(false)
const error = ref<string | null>(null)
const name = ref('')
const description = ref('')
const inputFormat = ref('auto')
const loadModelId = ref('')
const availableLoadModelIds = ref<string[]>([])

function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
  if (selectedFile.value && !name.value) {
    name.value = selectedFile.value.name.replace(/\.[^/.]+$/, '')
  }
}

async function loadModels() {
  loading.value = true
  try {
    models.value = await api.listModels()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load models'
  } finally {
    loading.value = false
  }
}

function getErrorDetail(errorValue: unknown): { message?: string; available_load_model_ids?: string[] } | null {
  const detail = (errorValue as { detail?: unknown })?.detail
  return detail && typeof detail === 'object' ? detail as { message?: string; available_load_model_ids?: string[] } : null
}

async function upload() {
  if (!selectedFile.value) return
  uploading.value = true
  error.value = null
  try {
    const model = await api.uploadModel(selectedFile.value, {
      name: name.value,
      description: description.value,
      inputFormat: inputFormat.value,
      loadModelId: loadModelId.value || undefined,
    })
    selectedFile.value = null
    name.value = ''
    description.value = ''
    loadModelId.value = ''
    availableLoadModelIds.value = []
    if (fileInput.value) fileInput.value.value = ''
    await loadModels()
    await router.push(`/models/${model.id}`)
  } catch (err) {
    const detail = getErrorDetail(err)
    availableLoadModelIds.value = detail?.available_load_model_ids ?? []
    error.value = detail?.message || (err instanceof Error ? err.message : 'Upload failed')
  } finally {
    uploading.value = false
  }
}

async function removeModel(model: ManagedModel) {
  if (!confirm(`Delete ${model.name}? This removes the source and generated artifact.`)) return
  try {
    await api.deleteModel(model.id)
    models.value = models.value.filter((item) => item.id !== model.id)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to delete model'
  }
}

function statusLabel(status: ModelStatus): string {
  return status.replace(/_/g, ' ')
}

function statusClass(status: ModelStatus): string {
  if (status === 'ready') return 'bg-green-100 text-green-800'
  if (status === 'ready_with_warnings') return 'bg-amber-100 text-amber-800'
  if (status === 'failed') return 'bg-red-100 text-red-800'
  return 'bg-blue-100 text-blue-800'
}

onActivated(loadModels)
</script>
