<template>
  <div class="min-h-screen max-w-6xl mx-auto p-8">
    <div class="mb-8">
      <router-link to="/"
        class="text-primary hover:text-primary/80 mb-4 inline-block">← Back to
        Home</router-link>
      <div class="flex items-center justify-between mb-3">
        <h1 class="text-3xl font-bold">Simulation Results</h1>
        <Select v-model="selectedResultID">
          <SelectTrigger class="w-full max-w-48">
            <SelectValue placeholder="Dataset:" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem v-for="result in resultManifest" :key="result.id"
              :value="result.id">{{ result.label }}</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onActivated } from 'vue'
import { useRoute } from 'vue-router'
import { api, type ResultEntry, } from '@/lib/api'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select/'

const route = useRoute()
const runId = computed<string | null>(() => typeof route.params.runId === "string" ? route.params.runId : null)

const resultManifest = ref<ResultEntry[]>([])
const selectedResultID = ref<string | null>(null)

onActivated(async () => {
  try {
    if (typeof runId.value === 'string') {
      resultManifest.value = await api.listResults(runId.value)
      if (resultManifest.value.length > 0) {
        selectedResultID.value = resultManifest.value[0].id
      }
    }
  } catch {
    alert(`Could not load list of results for ${runId.value} `)
  }
})
</script>
