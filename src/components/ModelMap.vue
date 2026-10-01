<template>
  <div ref="mapElement" class="h-[560px] w-full rounded-md border border-border" />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { ModelGeoJson, ModelSensorConfig } from '@/lib/api'

const props = defineProps<{
  geojson: ModelGeoJson
  sensors: ModelSensorConfig
  topology: {
    nodes: Array<{ id: string; [key: string]: unknown }>
    edges: Array<{ source: string; target: string; [key: string]: unknown }>
  }
  mode: 'gis' | 'schematic'
}>()

const emit = defineEmits<{
  selectBus: [busName: string]
}>()

const mapElement = ref<HTMLElement | null>(null)
let map: L.Map | null = null
let layer: L.GeoJSON | null = null

function schematicGeoJson(): ModelGeoJson {
  const hasLocalCoordinates = props.geojson.features.some(
    (feature) => feature.properties?.kind === 'bus',
  )
  if (hasLocalCoordinates) {
    return props.geojson
  }

  const positions = new Map<string, [number, number]>()
  const adjacency = new Map<string, Set<string>>()
  props.topology.nodes.forEach((node) => adjacency.set(node.id, new Set()))
  props.topology.edges.forEach((edge) => {
    adjacency.get(edge.source)?.add(edge.target)
    adjacency.get(edge.target)?.add(edge.source)
  })

  // A deterministic breadth-first layout is a better fallback for radial
  // feeders than an arbitrary file-order grid.  It keeps electrically close
  // buses near each other and works without geographic coordinates.
  const levels = new Map<string, number>()
  const queue = props.topology.nodes.length ? [props.topology.nodes[0].id] : []
  if (queue.length) levels.set(queue[0], 0)
  while (queue.length) {
    const current = queue.shift() as string
    const nextLevel = (levels.get(current) || 0) + 1
    for (const neighbor of adjacency.get(current) || []) {
      if (!levels.has(neighbor)) {
        levels.set(neighbor, nextLevel)
        queue.push(neighbor)
      }
    }
  }
  props.topology.nodes.forEach((node, index) => {
    if (!levels.has(node.id)) levels.set(node.id, 0)
    const level = levels.get(node.id) || 0
    const sameLevel = props.topology.nodes.filter((candidate) => (levels.get(candidate.id) || 0) === level)
    const row = sameLevel.findIndex((candidate) => candidate.id === node.id)
    positions.set(node.id, [level * 120, row * 45 + (index % 3) * 4])
  })
  const features: ModelGeoJson['features'] = props.topology.nodes.map((node) => ({
    type: 'Feature',
    geometry: { type: 'Point', coordinates: positions.get(node.id) || [0, 0] },
    properties: { kind: 'bus', id: node.id, name: node.id },
  }))
  props.topology.edges.forEach((edge, index) => {
    const source = positions.get(edge.source)
    const target = positions.get(edge.target)
    if (!source || !target) return
    features.push({
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: [source, target] },
      properties: { kind: 'element', id: `schematic-edge-${index}`, ...edge },
    })
  })
  return { type: 'FeatureCollection', coordinate_reference_system: undefined, features }
}

function sensorTypeForBus(busName: string): string | null {
  const hasSensor = (type: keyof ModelSensorConfig) =>
    props.sensors[type].some((sensorId) => sensorId.toLowerCase().startsWith(`${busName.toLowerCase()}.`))
  if (hasSensor('voltage')) return 'voltage'
  if (hasSensor('real_power')) return 'real_power'
  if (hasSensor('reactive_power')) return 'reactive_power'
  return null
}

function sensorColor(type: string | null): string {
  if (type === 'voltage') return '#2563eb'
  if (type === 'real_power') return '#dc2626'
  if (type === 'reactive_power') return '#9333ea'
  return '#16a34a'
}

function renderMap() {
  if (!map) return
  layer?.remove()
  const modelGeoJson = props.mode === 'schematic' ? schematicGeoJson() : props.geojson
  layer = L.geoJSON(modelGeoJson as GeoJSON.GeoJsonObject, {
    style: (feature) => ({
      color: feature?.properties?.kind === 'element' ? '#64748b' : '#94a3b8',
      weight: feature?.properties?.kind === 'element' ? 1 : 0,
      opacity: 0.65,
    }),
    pointToLayer: (_feature, latLng) => {
      const busName = String(_feature?.properties?.name || _feature?.properties?.id || '')
      const sensorType = sensorTypeForBus(busName)
      return L.circleMarker(latLng, {
        radius: sensorType ? 6 : 3,
        color: sensorColor(sensorType),
        fillColor: sensorColor(sensorType),
        fillOpacity: sensorType ? 0.9 : 0.55,
        weight: sensorType ? 2 : 1,
      })
    },
    onEachFeature: (feature, featureLayer) => {
      const properties = feature.properties || {}
      if (properties.kind === 'bus') {
        const busName = String(properties.name || properties.id)
        const sensorType = sensorTypeForBus(busName)
        featureLayer.bindTooltip(`${busName}${sensorType ? ` · ${sensorType} sensor` : ''}`)
        featureLayer.on('click', () => emit('selectBus', busName))
      } else if (properties.element) {
        featureLayer.bindTooltip(String(properties.element))
      }
    },
  }).addTo(map)

  const bounds = layer.getBounds()
  if (bounds.isValid()) {
    map.invalidateSize()
    map.fitBounds(bounds.pad(0.08), {
      padding: [24, 24],
      maxZoom: props.mode === 'schematic' ? 4 : 18,
    })
  }
}

function createMap() {
  if (!mapElement.value) return
  map = L.map(mapElement.value, {
    preferCanvas: true,
    crs: props.mode === 'schematic' ? L.CRS.Simple : L.CRS.EPSG3857,
    minZoom: props.mode === 'schematic' ? -8 : 0,
    maxZoom: 20,
    zoomSnap: 0.25,
  })
  if (props.mode === 'gis') {
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 20,
    }).addTo(map)
  }
  renderMap()
}

onMounted(() => {
  createMap()
})

watch(() => [props.geojson, props.sensors, props.topology], renderMap, { deep: true })
watch(() => props.mode, () => {
  if (!mapElement.value) return
  map?.remove()
  map = L.map(mapElement.value, {
    preferCanvas: true,
    crs: props.mode === 'schematic' ? L.CRS.Simple : L.CRS.EPSG3857,
    minZoom: props.mode === 'schematic' ? -8 : 0,
    maxZoom: 20,
    zoomSnap: 0.25,
  })
  if (props.mode === 'gis') {
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 20,
    }).addTo(map)
  }
  renderMap()
})

onBeforeUnmount(() => {
  map?.remove()
  map = null
})
</script>
