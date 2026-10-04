import type { Edge, Node } from '@vue-flow/core'

import type { EdgeData, NodeData } from '@/lib/flowTypes'

const ORNL_OD_DATA_PREFIX = '/components/ornl-od-prony/data/'
const dropdownSchemaCache = new WeakMap<
  Record<string, unknown>,
  Record<string, unknown>
>()

export interface OrnlOdDatasetPreset {
  id: string
  label: string
  filename: string
  grid: 'EI' | 'ERCOT' | 'WECC' | 'Synthetic'
  channels: number
  numberOfTimesteps: number
  sampleRateHz: number
  dominantFrequencyHz?: number
  longRun?: boolean
  od: {
    detection_window_sec: number
    prony_window_sec: number
    trigger_threshold: number
    detection_threshold2: number
    detection_cooldown_sec: number
    event_clustering_window_sec: number
    ground_truth_json: string
  }
}

const realEventOd = (
  dominantFrequencyHz: number
): OrnlOdDatasetPreset['od'] => ({
  detection_window_sec: 5.0,
  prony_window_sec: 90.0,
  trigger_threshold: 0.01,
  detection_threshold2: 0.01,
  detection_cooldown_sec: 50.0,
  event_clustering_window_sec: 2.0,
  ground_truth_json: JSON.stringify([{ frequency_hz: dominantFrequencyHz }]),
})

const file = (name: string) => `${ORNL_OD_DATA_PREFIX}${name}`

export const ORNL_OD_DATASETS: readonly OrnlOdDatasetPreset[] = [
  {
    id: 'ei-2011-04-27',
    label: 'EI — 2011-04-27 (3 PMUs, 37 s, ~0.60 Hz)',
    filename: file('EI_OscillationEvent_20110427.csv'),
    grid: 'EI',
    channels: 3,
    numberOfTimesteps: 370,
    sampleRateHz: 10.0,
    dominantFrequencyHz: 0.6,
    od: {
      detection_window_sec: 5.0,
      prony_window_sec: 10.0,
      trigger_threshold: 0.005,
      detection_threshold2: 0.005,
      detection_cooldown_sec: 9999.0,
      event_clustering_window_sec: 5.0,
      ground_truth_json: JSON.stringify([{ frequency_hz: 0.6 }]),
    },
  },
  {
    id: 'ei-2019-01-11',
    label: 'EI — 2019-01-11 (3 PMUs, 247 s, ~0.24 Hz)',
    filename: file('EI_OscillationEvent_20190111.csv'),
    grid: 'EI',
    channels: 3,
    numberOfTimesteps: 2470,
    sampleRateHz: 10.0,
    dominantFrequencyHz: 0.24,
    od: realEventOd(0.24),
  },
  {
    id: 'ei-2024-11-01',
    label: 'EI — 2024-11-01 (3 PMUs, 123 s, ~0.16 Hz)',
    filename: file('EI_OscillationEvent_20241101.csv'),
    grid: 'EI',
    channels: 3,
    numberOfTimesteps: 1229,
    sampleRateHz: 10.0,
    dominantFrequencyHz: 0.16,
    od: { ...realEventOd(0.16), prony_window_sec: 30.0 },
  },
  {
    id: 'ercot-2025-02-08',
    label: 'ERCOT — 2025-02-08 (1 PMU, 240 s, ~0.50 Hz)',
    filename: file('ERCOT_OscillationEvent_20250208.csv'),
    grid: 'ERCOT',
    channels: 1,
    numberOfTimesteps: 2401,
    sampleRateHz: 10.0,
    dominantFrequencyHz: 0.5,
    od: realEventOd(0.5),
  },
  {
    id: 'ercot-2025-04-25',
    label: 'ERCOT — 2025-04-25 (1 PMU, 360 s, ~0.50 Hz)',
    filename: file('ERCOT_OscillationEvent_20250425.csv'),
    grid: 'ERCOT',
    channels: 1,
    numberOfTimesteps: 3601,
    sampleRateHz: 10.0,
    dominantFrequencyHz: 0.5,
    od: realEventOd(0.5),
  },
  {
    id: 'ercot-2025-04-28',
    label: 'ERCOT — 2025-04-28 (1 PMU, 300 s, ~0.50 Hz)',
    filename: file('ERCOT_OscillationEvent_20250428.csv'),
    grid: 'ERCOT',
    channels: 1,
    numberOfTimesteps: 3001,
    sampleRateHz: 10.0,
    dominantFrequencyHz: 0.5,
    od: realEventOd(0.5),
  },
  {
    id: 'ercot-2025-09-09',
    label: 'ERCOT — 2025-09-09 (1 PMU, 240 s, ~0.50 Hz)',
    filename: file('ERCOT_OscillationEvent_20250909.csv'),
    grid: 'ERCOT',
    channels: 1,
    numberOfTimesteps: 2401,
    sampleRateHz: 10.0,
    dominantFrequencyHz: 0.5,
    od: realEventOd(0.5),
  },
  {
    id: 'wecc-2015-09-05',
    label: 'WECC — 2015-09-05 (3 PMUs, 30.5 min, ~0.42 Hz) — long run',
    filename: file('WECC_OscillationEvent_20150905.csv'),
    grid: 'WECC',
    channels: 3,
    numberOfTimesteps: 18320,
    sampleRateHz: 10.0,
    dominantFrequencyHz: 0.42,
    longRun: true,
    od: { ...realEventOd(0.42), prony_window_sec: 2.5 },
  },
  {
    id: 'wecc-2023-09-20',
    label: 'WECC — 2023-09-20 (3 PMUs, 360 s, ~0.20 Hz)',
    filename: file('WECC_OscillationEvent_20230920.csv'),
    grid: 'WECC',
    channels: 3,
    numberOfTimesteps: 3600,
    sampleRateHz: 10.0,
    dominantFrequencyHz: 0.2,
    od: realEventOd(0.2),
  },
  {
    id: 'wecc-2023-11-01',
    label: 'WECC — 2023-11-01 (3 PMUs, 100 s, ~0.23 Hz)',
    filename: file('WECC_OscillationEvent_20231101.csv'),
    grid: 'WECC',
    channels: 3,
    numberOfTimesteps: 1000,
    sampleRateHz: 10.0,
    dominantFrequencyHz: 0.23,
    od: { ...realEventOd(0.23), prony_window_sec: 8.0 },
  },
  {
    id: 'wecc-2025-08-12',
    label: 'WECC — 2025-08-12 (3 PMUs, 241 s, ~0.29 Hz)',
    filename: file('WECC_OscillationEvent_20250812.csv'),
    grid: 'WECC',
    channels: 3,
    numberOfTimesteps: 2410,
    sampleRateHz: 10.0,
    dominantFrequencyHz: 0.29,
    od: {
      ...realEventOd(0.29),
      trigger_threshold: 0.005,
      detection_threshold2: 0.005,
    },
  },
  {
    id: 'synthetic-10hz',
    label: 'Synthetic benchmark — 5 known events (4 channels, 500 s)',
    filename: file('synthetic_mock_10hz.csv'),
    grid: 'Synthetic',
    channels: 4,
    numberOfTimesteps: 5000,
    sampleRateHz: 10.0,
    od: {
      detection_window_sec: 5.0,
      prony_window_sec: 45.0,
      trigger_threshold: 0.005,
      detection_threshold2: 0.005,
      detection_cooldown_sec: 80.0,
      event_clustering_window_sec: 5.0,
      ground_truth_json: JSON.stringify([
        {
          start_time_sec: 30.0,
          frequency_hz: 0.5,
          amplitude: 0.03,
          damping_ratio: 0.005,
        },
        {
          start_time_sec: 130.0,
          frequency_hz: 1.0,
          amplitude: 0.03,
          damping_ratio: 0.01,
        },
        {
          start_time_sec: 230.0,
          frequency_hz: 2.0,
          amplitude: 0.03,
          damping_ratio: 0.02,
        },
        {
          start_time_sec: 330.0,
          frequency_hz: 3.0,
          amplitude: 0.03,
          damping_ratio: 0.005,
        },
        {
          start_time_sec: 430.0,
          frequency_hz: 0.7,
          amplitude: 0.03,
          damping_ratio: -0.008,
        },
      ]),
    },
  },
] as const

export const ornlOdPresetForFilename = (filename: unknown) =>
  ORNL_OD_DATASETS.find((preset) => preset.filename === filename)

export const connectedOrnlOdNodeIds = (
  playerNodeId: string,
  nodes: readonly Node[],
  edges: readonly Edge[]
): string[] => {
  const player = nodes.find((node) => node.id === playerNodeId)
  if (
    (player?.data as NodeData | undefined)?.componentType !== 'PlayerComponent'
  ) {
    return []
  }

  const nodeTypes = new Map(
    nodes.map((node) => [
      node.id,
      (node.data as NodeData | undefined)?.componentType,
    ])
  )
  return edges
    .filter((edge) => {
      if (
        edge.source !== playerNodeId ||
        nodeTypes.get(edge.target) !== 'ODComponent'
      ) {
        return false
      }
      const wires = (edge.data as EdgeData | undefined)?.wires ?? []
      return wires.some(
        (wire) =>
          wire.sourcePortId === 'publication' &&
          wire.targetPortId === 'frequency' &&
          wire.type === 'MeasurementArray'
      )
    })
    .map((edge) => edge.target)
}

export const isOrnlOdPlayer = (
  playerNodeId: string,
  nodes: readonly Node[],
  edges: readonly Edge[]
) => connectedOrnlOdNodeIds(playerNodeId, nodes, edges).length > 0

export const withOrnlOdDatasetDropdown = (
  schema: Record<string, unknown>
): Record<string, unknown> => {
  const cached = dropdownSchemaCache.get(schema)
  if (cached) return cached

  const properties =
    (schema.properties as Record<string, unknown> | undefined) ?? {}
  const filename =
    (properties.filename as Record<string, unknown> | undefined) ?? {}
  const dropdownSchema = {
    ...schema,
    properties: {
      ...properties,
      filename: {
        ...filename,
        title: 'Input Dataset',
        description:
          'Selecting a dataset also applies its matched playback and ORNL OD settings.',
        oneOf: ORNL_OD_DATASETS.map((preset) => ({
          const: preset.filename,
          title: preset.label,
        })),
      },
    },
  }
  dropdownSchemaCache.set(schema, dropdownSchema)
  return dropdownSchema
}

const jsonValuesEqual = (left: unknown, right: unknown): boolean => {
  if (Object.is(left, right)) return true
  if (Array.isArray(left) || Array.isArray(right)) {
    return (
      Array.isArray(left) &&
      Array.isArray(right) &&
      left.length === right.length &&
      left.every((value, index) => jsonValuesEqual(value, right[index]))
    )
  }
  if (
    left === null ||
    right === null ||
    typeof left !== 'object' ||
    typeof right !== 'object'
  ) {
    return false
  }

  const leftRecord = left as Record<string, unknown>
  const rightRecord = right as Record<string, unknown>
  const leftKeys = Object.keys(leftRecord)
  const rightKeys = Object.keys(rightRecord)
  return (
    leftKeys.length === rightKeys.length &&
    leftKeys.every(
      (key) =>
        Object.prototype.hasOwnProperty.call(rightRecord, key) &&
        jsonValuesEqual(leftRecord[key], rightRecord[key])
    )
  )
}

export const mergeOrnlOdPlayerConfig = (
  current: Record<string, unknown>,
  submitted: Record<string, unknown>
): Record<string, unknown> => ({ ...current, ...submitted })

export const hasOrnlOdPlayerConfigChange = (
  current: Record<string, unknown>,
  submitted: Record<string, unknown>
): boolean =>
  !jsonValuesEqual(current, mergeOrnlOdPlayerConfig(current, submitted))

export interface OrnlOdPresetUpdate {
  playerConfig: Record<string, unknown>
  odNodeIds: string[]
  odConfig: (current: Record<string, unknown>) => Record<string, unknown>
  preset: OrnlOdDatasetPreset
}

export const buildOrnlOdPresetUpdate = (
  playerNodeId: string,
  currentPlayerConfig: Record<string, unknown>,
  submittedPlayerConfig: Record<string, unknown>,
  nodes: readonly Node[],
  edges: readonly Edge[]
): OrnlOdPresetUpdate | null => {
  const odNodeIds = connectedOrnlOdNodeIds(playerNodeId, nodes, edges)
  const preset = ornlOdPresetForFilename(submittedPlayerConfig.filename)
  if (odNodeIds.length === 0 || !preset) {
    return null
  }

  return {
    playerConfig: {
      ...currentPlayerConfig,
      ...submittedPlayerConfig,
      filename: preset.filename,
      data_type: 'MeasurementArray',
      number_of_timesteps: preset.numberOfTimesteps,
      start_time_index: 0,
      run_freq_time_step: 1 / preset.sampleRateHz,
    },
    odNodeIds,
    odConfig: (current) => ({
      ...current,
      sample_rate_hz: preset.sampleRateHz,
      ...preset.od,
    }),
    preset,
  }
}
