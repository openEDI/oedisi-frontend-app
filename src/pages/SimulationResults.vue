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
    <GraphicWalkerEmbed v-if="fields.length"
      :key="`${runId}/${selectedResultID ?? ''}`" :data="data"
      :fields="fields" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onActivated, watch, shallowRef } from 'vue'
import { useRoute } from 'vue-router'
import { api, type ResultEntry, } from '@/lib/api'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select/'
import GraphicWalkerEmbed from '@/components/GraphicWalkerEmbed.vue'
import { type IMutField, type IRow } from '@kanaries/graphic-walker'

const route = useRoute()
const runId = computed<string | null>(() => typeof route.params.runId === "string" ? route.params.runId : null)

const resultManifest = ref<ResultEntry[]>([])
const selectedResultID = ref<string | null>(null)
const fields = shallowRef<IMutField[]>([])
const data = shallowRef<IRow[]>([])

watch([runId, selectedResultID], async ([newRunId, newId]) => {
  if (newId !== null && newRunId !== null) {
    fields.value = []
    data.value = []
    try {
      const resultData = await api.getResult(newRunId, newId)
      data.value = resultData.data
      fields.value = resultData.fields as IMutField[]
    } catch {
      alert(`Could not load result for ${newId}`)
    }
  }
})

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
