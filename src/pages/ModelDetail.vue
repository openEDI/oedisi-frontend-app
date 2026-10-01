<template>
  <div class="min-h-screen p-8">
    <div class="max-w-7xl mx-auto">
      <router-link to="/models" class="text-primary hover:text-primary/80 mb-4 inline-block">
        ← Back to Model Manager
      </router-link>

      <div v-if="loading" class="p-8 text-center text-muted-foreground">Loading model inspection...</div>
      <div v-else-if="error" class="p-8 text-center text-destructive">{{ error }}</div>
      <template v-else-if="model && inspection">
        <div class="flex flex-wrap items-start justify-between gap-4 mb-8">
          <div>
            <div class="flex items-center gap-3">
              <h1 class="text-3xl font-bold">{{ model.name }}</h1>
              <span :class="statusClass(model.status)" class="rounded-full px-2 py-1 text-xs font-medium">
                {{ statusLabel(model.status) }}
              </span>
            </div>
            <p class="text-muted-foreground mt-2">{{ model.description || 'No description' }}</p>
            <p class="font-mono text-xs text-muted-foreground mt-2 break-all">{{ model.id }}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <a :href="api.modelSourceDownloadUrl(model.id)">
              <Button variant="outline">Download Source</Button>
            </a>
            <a :href="api.modelOpenDssDownloadUrl(model.id)">
              <Button>Download OpenDSS</Button>
            </a>
          </div>
        </div>

        <div class="grid gap-4 md:grid-cols-4 mb-8">
          <Card>
            <CardHeader><CardDescription>Inspected artifact</CardDescription><CardTitle>OpenDSS</CardTitle></CardHeader>
          </Card>
          <Card>
            <CardHeader><CardDescription>Elements</CardDescription><CardTitle>{{ inspection.summary.element_count || inspection.summary.total_components }}</CardTitle></CardHeader>
          </Card>
          <Card>
            <CardHeader><CardDescription>Buses</CardDescription><CardTitle>{{ inspection.summary.bus_count || inspection.topology.nodes.length }}</CardTitle></CardHeader>
          </Card>
          <Card>
            <CardHeader><CardDescription>Power flow</CardDescription><CardTitle>{{ inspection.physics.solution.converged ? 'Converged' : 'Not solved' }}</CardTitle></CardHeader>
          </Card>
        </div>

        <div v-if="model.conversion.warnings.length" class="rounded-lg border border-amber-300 bg-amber-50 p-4 mb-8">
          <h2 class="font-semibold text-amber-900 mb-2">Conversion warnings</h2>
          <ul class="list-disc pl-5 text-sm text-amber-800 space-y-1">
            <li v-for="warning in model.conversion.warnings" :key="warning">{{ warning }}</li>
          </ul>
        </div>

        <div class="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>OpenDSS element inventory</CardTitle>
              <CardDescription>Classes and counts read from the generated DSS circuit.</CardDescription>
            </CardHeader>
            <CardContent>
              <div class="overflow-auto">
                <table class="w-full text-sm">
                  <thead><tr class="border-b text-left"><th class="py-2">Type</th><th class="py-2">Count</th></tr></thead>
                  <tbody>
                    <tr v-for="(count, type) in (inspection.summary.element_types || inspection.summary.component_types)" :key="type" class="border-b last:border-0">
                      <td class="py-2 font-mono">{{ type }}</td>
                      <td class="py-2">{{ count }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>OpenDSS circuit</CardTitle>
              <CardDescription>The generated DSS model is the inspection source of truth.</CardDescription>
            </CardHeader>
            <CardContent class="space-y-3 text-sm">
              <p><strong>Source reader:</strong> {{ model.conversion.reader }}</p>
              <p><strong>Source entrypoint:</strong> <span class="font-mono">{{ model.conversion.entrypoint || 'Detected automatically' }}</span></p>
              <p><strong>Generated entrypoint:</strong> <span class="font-mono">{{ model.conversion.artifact_entrypoint }}</span></p>
              <p><strong>DSS circuit:</strong> <span class="font-mono">{{ inspection.summary.name || 'Unnamed circuit' }}</span></p>
              <p><strong>Solution mode:</strong> {{ inspection.physics.solution.mode }}</p>
              <p><strong>Frequency:</strong> {{ inspection.physics.solution.frequency_hz }} Hz</p>
              <p><strong>Total power:</strong> {{ formatPhysicsValue(inspection.physics.circuit.total_power_kw_kvar) }}</p>
              <p><strong>Losses:</strong> {{ formatPhysicsValue(inspection.physics.circuit.losses_w_var) }}</p>
              <p><strong>Bus voltage range:</strong> {{ inspection.physics.circuit.bus_voltage_pu_min }} – {{ inspection.physics.circuit.bus_voltage_pu_max }} pu</p>
              <p><strong>Source files:</strong> {{ model.source.files.length }}</p>
              <p><strong>Generated files:</strong> {{ model.artifacts.opendss?.files.length || 0 }}</p>
              <p><strong>Profiles:</strong> {{ model.artifacts.opendss?.profiles_available ? 'Available' : 'None in generated artifact' }}</p>
              <p class="text-xs text-muted-foreground break-all"><strong>Source SHA-256:</strong> {{ model.source.sha256 }}</p>
              <details class="pt-2">
                <summary class="cursor-pointer text-primary">Show file lists</summary>
                <div class="grid gap-3 md:grid-cols-2 mt-2 text-xs">
                  <div>
                    <p class="font-semibold mb-1">Original source</p>
                    <ul class="list-disc pl-4 space-y-1 max-h-32 overflow-auto">
                      <li v-for="file in model.source.files" :key="`source-${file.path}`" class="font-mono">{{ file.path }}</li>
                    </ul>
                  </div>
                  <div>
                    <p class="font-semibold mb-1">Generated OpenDSS</p>
                    <ul class="list-disc pl-4 space-y-1 max-h-32 overflow-auto">
                      <li v-for="file in model.artifacts.opendss?.files || []" :key="`artifact-${file.path}`" class="font-mono">{{ file.path }}</li>
                    </ul>
                  </div>
                </div>
              </details>
            </CardContent>
          </Card>

          <Card class="lg:col-span-2">
            <CardHeader>
              <CardTitle>OpenDSS buses and topology</CardTitle>
              <CardDescription>Buses and connections are read directly from the generated Master.dss circuit.</CardDescription>
            </CardHeader>
            <CardContent>
                <div class="grid gap-4 md:grid-cols-2">
                <div class="rounded-md bg-muted/40 p-4">
                  <p class="text-sm font-semibold mb-2">Buses</p>
                  <div class="max-h-64 overflow-auto">
                    <table class="w-full text-xs">
                      <thead><tr class="border-b text-left"><th class="py-1">Bus</th><th class="py-1">kV base</th><th class="py-1">Nodes</th></tr></thead>
                      <tbody>
                        <tr v-for="bus in inspection.buses.slice(0, 100)" :key="bus.id" class="border-b last:border-0">
                          <td class="py-1 font-mono">{{ bus.name }}</td>
                          <td class="py-1">{{ bus.kv_base ?? '—' }}</td>
                          <td class="py-1">{{ bus.nodes.join(', ') }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <p v-if="inspection.buses.length > 100" class="text-xs text-muted-foreground mt-2">Showing first 100 buses.</p>
                </div>
                <div class="rounded-md bg-muted/40 p-4">
                  <p class="text-sm font-semibold mb-2">Connections</p>
                  <div class="max-h-64 overflow-auto space-y-1">
                    <div v-for="edge in inspection.topology.edges.slice(0, 100)" :key="`${edge.source}-${edge.target}`" class="font-mono text-xs">
                      {{ edge.source }} → {{ edge.target }} <span class="text-muted-foreground">({{ edge.element }})</span>
                    </div>
                  </div>
                  <p v-if="inspection.topology.edges.length > 100" class="text-xs text-muted-foreground mt-2">Showing first 100 connections.</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card class="lg:col-span-2">
            <CardHeader>
              <CardTitle>Sensor map</CardTitle>
              <CardDescription>
                Select a bus and phase to add voltage, real-power, or reactive-power measurements for this model.
              </CardDescription>
            </CardHeader>
            <CardContent class="space-y-4">
              <div class="flex flex-wrap items-center gap-3">
                <label class="text-sm font-semibold" for="plot-mode">Plot</label>
                <select id="plot-mode" v-model="plotMode" class="h-9 rounded-md border border-input bg-background px-3 text-sm">
                  <option value="gis" :disabled="!hasGisCoordinates">GIS map{{ hasGisCoordinates ? '' : ' (no geographic coordinates)' }}</option>
                  <option value="schematic">Schematic topology</option>
                </select>
                <label class="text-sm font-semibold" for="sensor-type">Sensor type</label>
                <select id="sensor-type" v-model="activeSensorType" class="h-9 rounded-md border border-input bg-background px-3 text-sm">
                  <option value="voltage">Voltage</option>
                  <option value="real_power">Real power</option>
                  <option value="reactive_power">Reactive power</option>
                </select>
                <label class="text-sm font-semibold" for="sensor-bus">Bus</label>
                <select id="sensor-bus" v-model="selectedBusName" class="h-9 min-w-64 rounded-md border border-input bg-background px-3 text-sm">
                  <option value="">Select a bus</option>
                  <option v-for="bus in inspection.buses" :key="bus.id" :value="bus.name">{{ bus.name }}</option>
                </select>
                <Button :disabled="sensorsSaving" :variant="sensorsSaving ? 'outline' : 'default'" @click="saveSensors">
                  {{ sensorsSaving ? 'Saving...' : 'Save sensor configuration' }}
                </Button>
                <label class="text-sm font-semibold" for="sensor-file-type">Import file as</label>
                <select id="sensor-file-type" v-model="sensorUploadType" class="h-9 rounded-md border border-input bg-background px-3 text-sm">
                  <option value="voltage">Voltage</option>
                  <option value="real_power">Real power</option>
                  <option value="reactive_power">Reactive power</option>
                </select>
                <input ref="sensorFileInput" type="file" accept=".json" class="max-w-56 text-sm" @change="uploadSensorFile" />
                <span v-if="sensorMessage" class="text-sm text-muted-foreground">{{ sensorMessage }}</span>
              </div>
              <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
                <ModelMap :geojson="inspection.geojson" :sensors="sensors" :topology="inspection.topology" :mode="plotMode" @select-bus="selectedBusName = $event" />
                <div class="rounded-md bg-muted/40 p-4">
                  <p class="font-semibold mb-2">{{ selectedBus?.name || 'Choose a bus' }}</p>
                  <p v-if="selectedBus" class="text-xs text-muted-foreground mb-3">
                    Toggle phases for {{ sensorTypeLabel(activeSensorType) }} sensors.
                  </p>
                  <div v-if="selectedBus" class="space-y-2">
                    <button
                      v-for="node in selectedBus.nodes"
                      :key="`${selectedBus.name}.${node}`"
                      class="flex w-full items-center justify-between rounded border px-3 py-2 text-sm"
                      :class="isSensorSelected(`${selectedBus.name}.${node}`) ? 'border-primary bg-primary/10' : 'border-border bg-background'"
                      @click="toggleSensor(`${selectedBus.name}.${node}`)"
                    >
                      <span class="font-mono">{{ selectedBus.name }}.{{ node }}</span>
                      <span>{{ isSensorSelected(`${selectedBus.name}.${node}`) ? 'Selected' : 'Add' }}</span>
                    </button>
                  </div>
                  <p v-else class="text-sm text-muted-foreground">Click a bus on the map or choose one above.</p>
                  <div class="mt-4 border-t pt-3 text-xs text-muted-foreground space-y-1">
                    <p>Voltage: {{ sensors.voltage.length }}</p>
                    <p>Real power: {{ sensors.real_power.length }}</p>
                    <p>Reactive power: {{ sensors.reactive_power.length }}</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card class="lg:col-span-2">
            <CardHeader>
              <CardTitle>OpenDSS elements</CardTitle>
              <CardDescription>Inspect DSS-native classes, buses, properties, powers, losses, and voltage data.</CardDescription>
              <Input v-model="componentSearch" placeholder="Search by element, class, bus, or property" />
            </CardHeader>
            <CardContent>
              <div class="overflow-auto">
                <table class="w-full text-sm">
                  <thead><tr class="border-b text-left"><th class="py-2">Class</th><th class="py-2">Element</th><th class="py-2">Buses</th><th class="py-2">Details</th></tr></thead>
                  <tbody>
                    <tr v-for="element in filteredElements.slice(0, 200)" :key="element.id" class="border-b last:border-0">
                      <td class="py-2 font-mono">{{ element.class }}</td>
                      <td class="py-2">{{ element.name }}</td>
                      <td class="py-2 font-mono text-xs">{{ element.bus_names.join(' ↔ ') }}</td>
                      <td class="py-2"><details><summary class="cursor-pointer text-primary">View DSS properties</summary><pre class="mt-2 max-w-xl overflow-auto rounded bg-muted p-2 text-xs">{{ JSON.stringify(element, null, 2) }}</pre></details></td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p v-if="filteredElements.length > 200" class="text-xs text-muted-foreground mt-3">Showing first 200 matching elements.</p>
            </CardContent>
          </Card>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onActivated, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, type ManagedModel, type ModelInspection, type ModelSensorConfig, type ModelStatus } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import ModelMap from '@/components/ModelMap.vue'

const route = useRoute()
const model = ref<ManagedModel | null>(null)
const inspection = ref<ModelInspection | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const componentSearch = ref('')
const activeSensorType = ref<keyof ModelSensorConfig>('voltage')
const selectedBusName = ref('')
const sensors = ref<ModelSensorConfig>({ voltage: [], real_power: [], reactive_power: [] })
const sensorsSaving = ref(false)
const sensorMessage = ref('')
const sensorUploadType = ref<keyof ModelSensorConfig>('voltage')
const plotMode = ref<'gis' | 'schematic'>('gis')

const selectedBus = computed(() => inspection.value?.buses.find((bus) => bus.name === selectedBusName.value) ?? null)
const hasGisCoordinates = computed(() => inspection.value?.geojson.coordinate_reference_system === 'EPSG:4326'
  && inspection.value.geojson.features.some((feature) => feature.properties?.kind === 'bus'))

const filteredElements = computed(() => {
  const elements = inspection.value?.elements ?? []
  const needle = componentSearch.value.trim().toLowerCase()
  if (!needle) return elements
  return elements.filter((element) =>
    element.name.toLowerCase().includes(needle)
    || element.class.toLowerCase().includes(needle)
    || element.id.toLowerCase().includes(needle)
    || element.bus_names.some((bus) => bus.toLowerCase().includes(needle))
    || Object.entries(element.properties).some(([key, value]) =>
      key.toLowerCase().includes(needle) || String(value).toLowerCase().includes(needle),
    )
  )
})

async function loadModel() {
  loading.value = true
  error.value = null
  try {
    const id = String(route.params.modelId)
    const [loadedModel, loadedInspection] = await Promise.all([
      api.getModel(id),
      api.getModelInspection(id),
    ])
    model.value = loadedModel
    inspection.value = loadedInspection
    plotMode.value = loadedInspection.geojson.coordinate_reference_system === 'EPSG:4326' ? 'gis' : 'schematic'
    try {
      sensors.value = await api.getModelSensors(id)
    } catch {
      sensors.value = loadedInspection.sensors ?? { voltage: [], real_power: [], reactive_power: [] }
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load model inspection'
  } finally {
    loading.value = false
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

function sensorTypeLabel(sensorType: keyof ModelSensorConfig): string {
  if (sensorType === 'real_power') return 'real-power'
  if (sensorType === 'reactive_power') return 'reactive-power'
  return 'voltage'
}

function isSensorSelected(sensorId: string): boolean {
  return sensors.value[activeSensorType.value].some((value) => value.toLowerCase() === sensorId.toLowerCase())
}

function toggleSensor(sensorId: string) {
  const selected = sensors.value[activeSensorType.value]
  sensors.value = {
    ...sensors.value,
    [activeSensorType.value]: selected.includes(sensorId)
      ? selected.filter((value) => value !== sensorId)
      : [...selected, sensorId],
  }
  sensorMessage.value = 'Unsaved changes'
}

async function saveSensors() {
  if (!model.value) return
  sensorsSaving.value = true
  sensorMessage.value = ''
  try {
    sensors.value = await api.saveModelSensors(model.value.id, sensors.value)
    sensorMessage.value = 'Sensor configuration saved'
  } catch (err) {
    sensorMessage.value = err instanceof Error ? err.message : 'Failed to save sensors'
  } finally {
    sensorsSaving.value = false
  }
}

async function uploadSensorFile(event: Event) {
  if (!model.value) return
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  sensorMessage.value = 'Importing sensor file...'
  try {
    sensors.value = await api.uploadModelSensorFile(model.value.id, file, sensorUploadType.value)
    sensorMessage.value = 'Sensor file imported'
  } catch (err) {
    sensorMessage.value = err instanceof Error ? err.message : 'Failed to import sensor file'
  } finally {
    input.value = ''
  }
}

function formatPhysicsValue(value: unknown): string {
  return Array.isArray(value) ? value.map((item) => Number(item).toFixed(3)).join(', ') : String(value ?? '—')
}

onActivated(loadModel)
</script>
