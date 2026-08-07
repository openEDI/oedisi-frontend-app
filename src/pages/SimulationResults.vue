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
        <div class="flex items-center gap-3">
          <label for="comparison">Compare with:</label>
          <Select v-model="comparisonResultIndex">
            <SelectTrigger id="comparison" class="w-48">
              <SelectValue placeholder="None" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem :value="null">None</SelectItem>
              <SelectItem
                v-for="{ result, index } in getCompatibleResults(resultManifest, selectedResultIndex)"
                :key="result.id" :value="index">{{ result.label }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
    <div class="flex items-center gap-3 mb-3">
      <label for="row_index">Time Index</label>
      <input id="row_index" v-model.number="selectedRow" type="range" :min="0"
        :max="maxRow" class="flex-1 max-w-lg" />
      <p v-if="avgMetric">{{ avgMetric.metric }}: {{ (avgMetric.avg *
        100).toFixed(2) }}%
      </p>
    </div>
    <div ref="chartEl" class="overflow-x-auto text-foreground"></div>
  </div>
</template>

<script setup lang="ts">
import { watch, ref, computed, onActivated } from 'vue'
import { useRoute } from 'vue-router'
import { api, Topology, type ResultEntry, } from '@/lib/api'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select/'
import { isCompatible } from '@/lib/portCompatibility'
import * as Plot from '@observablehq/plot'

const route = useRoute()
const runId = computed<string | null>(() => typeof route.params.runId === "string" ? route.params.runId : null)

const resultManifest = ref<ResultEntry[]>([])
const selectedResultIndex = ref<number | null>(null)
const comparisonResultIndex = ref<number | null>(null)
const selectedRow = ref<number>(0)
const resultData = ref<Awaited<ReturnType<typeof api.getResult>> | null>(null)
const comparisonData = ref<Awaited<ReturnType<typeof api.getResult>> | null>(null)

const metrics = ref<{
  metric: string, data: Array<{ time: string, value: number }>
} | null>(null)
const avgMetric = computed<{
  metric: string, avg: number
} | null>(
  () => {
    if (!metrics.value || metrics.value.data.length === 0) {
      return null
    }
    return {
      metric: metrics.value.metric,
      avg: metrics.value.data.reduce(
        (sum, current) => sum + current.value, 0) / metrics.value.data.length
    }
  })

const maxRow = computed<number>(() => sharedTimes.value.length - 1)
const sharedTimes = computed<string[]>(() => {
  if (resultData.value === null) {
    return []
  }
  const times = getAllTimes(resultData.value.data)
  if (comparisonData.value === null) {
    return times
  }
  const comparisonTimes: Set<string> = new Set(getAllTimes(comparisonData.value.data))
  return times.filter(time => comparisonTimes.has(time))
})

const topology = ref<Topology | null>(null)

const chartEl = ref<HTMLElement | null>(null)

function getCompatibleResults(resultManifest: ResultEntry[], index: number | null) {
  if (typeof index !== 'number') {
    return []
  }
  const annotation = resultManifest[index].quantity
  return resultManifest.map(
    (result, index) => ({ result, index })
  ).filter(
    ({ result, index: comparedIndex }) => index !== comparedIndex && isCompatible(result?.quantity?.type ?? null, annotation?.type ?? null)
  )
}

watch(selectedResultIndex, async (selectedId) => {
  if (typeof runId.value === 'string' && typeof selectedId === 'number') {
    comparisonResultIndex.value = null
    resultData.value = await api.getResult(runId.value, resultManifest.value[selectedId].id)
    selectedRow.value = Math.max(0, Math.min(selectedRow.value, maxRow.value))
  }
})

watch(comparisonResultIndex, async (selectedId) => {
  if (typeof runId.value === 'string' && typeof selectedId === 'number') {
    comparisonData.value = await api.getResult(runId.value, resultManifest.value[selectedId].id)
    selectedRow.value = Math.max(0, Math.min(selectedRow.value, maxRow.value))
    if (typeof selectedResultIndex.value === 'number') {
      metrics.value = await api.getMetrics(
        runId.value,
        resultManifest.value[selectedResultIndex.value].id,
        resultManifest.value[selectedId].id
      )
    }
  } else if (selectedId === null) {
    comparisonData.value = null
    metrics.value = null
  }
})

function divideTopology(data: Record<string, number>, base_voltage_magnitudes: { ids: string[], values: number[] }) {
  const newData: Record<string, number> = {}
  for (const [index, key] of base_voltage_magnitudes.ids.entries()) {
    newData[key] = data[key] / base_voltage_magnitudes.values[index]
  }
  return newData
}

function getPlotVersion(topology: Topology | null, data: Awaited<ReturnType<typeof api.getResult>>, entry: ResultEntry, row_index: number) {
  let rowData = getDataRow(data.data, row_index)
  if (topology && entry.quantity) {
    const type = entry.quantity.type
    if (type === 'VoltagesReal' || type === 'VoltagesMagnitude' ||
      type === 'VoltagesImaginary') {
      rowData = divideTopology(rowData, topology.base_voltage_magnitudes)
    }
  }
  return Object.entries(rowData).map(([bus, value]) => ({ bus, value, dataset: entry.label }))
}

watch([resultData, comparisonData, topology, selectedRow], ([data, comparisonData, topology, row_index]) => {
  if (!chartEl.value) return
  if (!data || typeof selectedResultIndex.value !== 'number' ||
    data.data.length == 0 || row_index >= sharedTimes.value.length) {
    chartEl.value.replaceChildren()
    return
  }
  const time = sharedTimes.value[row_index]
  const main_index = getAllTimes(data.data).findIndex(t => t === time)
  const entry = resultManifest.value[selectedResultIndex.value]
  const snapshot = getPlotVersion(topology, data, entry, main_index)
  if (!comparisonData || typeof comparisonResultIndex.value !== 'number' || comparisonData.data.length == 0) {
    const chart = Plot.plot({
      marks: [Plot.dot(snapshot, { x: 'bus', y: 'value', tip: { fill: 'var(--popover)' } })],
      x: { type: 'band', ticks: [], label: 'bus' },
      marginBottom: 40,
      style: { background: 'transparent' },
      title: `${getTitleName(entry)} at ${time}`,
      y: {},
    })
    chartEl.value.replaceChildren(chart)
    return
  }
  const second_index = getAllTimes(comparisonData.data).findIndex(t => t === time)
  const entry2 = resultManifest.value[comparisonResultIndex.value]
  const snapshot2 = getPlotVersion(topology, comparisonData, entry2, second_index)
  const chart = Plot.plot({
    marks: [
      Plot.dot(snapshot, { x: 'bus', y: 'value', fill: 'dataset', tip: { fill: 'var(--popover)' } }),
      Plot.dot(snapshot2, { x: 'bus', y: 'value', stroke: 'dataset', r: 5, tip: { fill: 'var(--popover)' } })
    ],
    x: { type: 'band', ticks: [], label: 'bus' },
    marginBottom: 40,
    style: { background: 'transparent' },
    title: `Comparing ${getTitleName(entry)} to ${getTitleName(entry2)} at ${time}`,
    y: {},
    color: { legend: true },
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

function getAllTimes(data: Array<Record<string, string | number>>): string[] {
  return data.map(row => row.time).filter(time => typeof time === 'string')
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
  comparisonResultIndex.value = null
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
