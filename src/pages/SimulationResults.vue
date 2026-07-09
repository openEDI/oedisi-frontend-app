<template>
  <div class="min-h-screen max-w-6xl mx-auto p-8">
    <div class="mb-8">
      <router-link to="/"
        class="text-primary hover:text-primary/80 mb-4 inline-block">← Back to
        Home</router-link>
      <div class="flex items-center justify-between mb-3">
        <h1 class="text-3xl font-bold">Simulation Results</h1>
        <Select v-model="selectedResultIndex">
          <SelectTrigger class="w-full max-w-48">
            <SelectValue placeholder="Dataset:" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem v-for="(result, index) in resultManifest"
              :key="result.id" :value="index">{{ result.label }}</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
    <div class="flex items-center gap-3 mb-3">
      <label for="row_index">Time Index</label>
      <input id="row_index" v-model.number="selectedRow" type="range" :min="0"
        :max="maxRow" class="flex-1 max-w-lg" />
    </div>
    <div ref="chartEl" class="overflow-x-auto text-foreground"></div>
  </div>
</template>

<script setup lang="ts">
import { watch, ref, computed, onActivated } from 'vue'
import { useRoute } from 'vue-router'
import { api, Topology, type ResultEntry, } from '@/lib/api'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select/'
import * as Plot from '@observablehq/plot'

const route = useRoute()
const runId = computed<string | null>(() => typeof route.params.runId === "string" ? route.params.runId : null)

const resultManifest = ref<ResultEntry[]>([])
const selectedResultIndex = ref<number | null>(null)
const selectedRow = ref<number>(0)
const resultData = ref<Awaited<ReturnType<typeof api.getResult>> | null>(null)
const maxRow = computed<number>(() =>
  resultData.value ? resultData.value.data.length - 1 : 0
)

const topology = ref<Topology | null>(null)

const chartEl = ref<HTMLElement | null>(null)

watch(selectedResultIndex, async (selectedId) => {
  if (typeof runId.value === 'string' && typeof selectedId === 'number') {
    resultData.value = await api.getResult(runId.value, resultManifest.value[selectedId].id)
    selectedRow.value = Math.min(selectedRow.value, resultData.value.data.length - 1)
  }
})

function divideTopology(data: Record<string, number>, base_voltage_magnitudes: { ids: string[], values: number[] }) {
  const newData: Record<string, number> = {}
  for (const [index, key] of base_voltage_magnitudes.ids.entries()) {
    newData[key] = data[key] / base_voltage_magnitudes.values[index]
  }
  return newData
}

watch([resultData, topology, selectedRow], ([data, topology, row_index]) => {
  if (!chartEl.value) return
  if (!data || typeof selectedResultIndex.value !== 'number' ||
    data.data.length == 0) {
    chartEl.value.replaceChildren()
    return
  }
  let rowData = getDataRow(data.data, row_index)
  const entry: ResultEntry = resultManifest.value[selectedResultIndex.value]
  if (topology && entry.quantity) {
    const type = entry.quantity.type
    if (type === 'VoltagesReal' || type === 'VoltagesMagnitude' ||
      type === 'VoltagesImaginary') {
      rowData = divideTopology(rowData, topology.base_voltage_magnitudes)
    }
  }
  const snapshot = Object.entries(rowData)
    .map(([bus, value]) => ({ bus, value }))
  const chart = Plot.plot({
    marks: [Plot.dot(snapshot, { x: 'bus', y: 'value', tip: { fill: 'var(--popover)' } })],
    x: { type: 'band', ticks: [], label: 'bus' },
    marginBottom: 40,
    style: { background: 'transparent' },
    title: `${getTitleName(entry)} at ${getTime(data.data, row_index)}`,
    y: { zero: true },
  })
  chartEl.value.replaceChildren(chart)
})

function getDataRow(data: Array<Record<string, string | number>>, rowIndex: number): Record<string, number> {
  const row = data[rowIndex]
  const subset: Record<string, number> = {}
  for (const key in row) {
    if (typeof row[key] === 'number') {
      subset[key] = row[key]
    }
  }
  return subset
}

function getTime(data: Array<Record<string, string | number>>, rowIndex: number): string {
  if ("time" in data[rowIndex] && typeof data[rowIndex]["time"] === 'string') {
    return data[rowIndex]["time"]
  }
  throw new Error("Could not get time from data")
}

function getTitleName(entry: ResultEntry) {
  if (!entry.quantity?.type) {
    return entry.label
  }
  return `${entry.label} ${entry.quantity.type}`
}

onActivated(async () => {
  if (typeof runId.value !== 'string') {
    return
  }
  selectedResultIndex.value = null
  topology.value = null
  selectedRow.value = 0
  try {
    resultManifest.value = await api.listResults(runId.value)
    if (resultManifest.value.length > 0) {
      selectedResultIndex.value = 0
    }
  } catch {
    alert(`Could not load list of results for ${runId.value} `)
  }
  try {
    topology.value = await api.getTopology(runId.value)
  } catch {
    alert(`Could not load topology from results for ${runId.value} `)
  }
})
</script>
