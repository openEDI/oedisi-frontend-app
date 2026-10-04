import type { Edge, Node } from '@vue-flow/core'

import type { EdgeData, NodeData } from '@/lib/flowTypes'

export const ORNL_EV_SWITCHABLE_FEEDER_PREFIX = 'OrnlEvSwitchFeeder-'

const dropdownSchemaCache = new WeakMap<
  Record<string, unknown>,
  Record<string, unknown>
>()

const controlModeSchemaCache = new WeakMap<
  Record<string, unknown>,
  Record<string, unknown>
>()

const assignment = (
  buses: readonly string[],
  counts: readonly number[],
): Record<string, number[]> => {
  let next = 0
  return Object.fromEntries(buses.map((bus, index) => {
    const count = counts[index] ?? 0
    const indices = Array.from({ length: count }, () => next++)
    return [bus, indices]
  }))
}

export interface OrnlEvFeederPreset {
  id: 'ieee123' | 'smartds-p1u' | 'smartds-p6u'
  label: string
  feeder: Record<string, unknown>
  ev: Record<string, unknown>
}

const ieeeBuses = ['48.1', '65.1', '76.1'] as const
const p1uBuses = ['p1ulv4132.1', 'p1ulv4108.1', 'p1ulv4189.1'] as const
const p6uBuses = ['p6ulv16572.1', 'p6ulv26801.1', 'p6ulv26810.1'] as const

const smartDsFeeder = (
  region: 'P1U' | 'P6U',
  circuit: string,
): Record<string, unknown> => ({
  use_smartds: true,
  user_uploads_model: false,
  profile_location: `SMART-DS/v1.0/2018/SFO/${region}/profiles`,
  opendss_location:
    `SMART-DS/v1.0/2018/SFO/${region}/scenarios/solar_low_batteries_none_timeseries/opendss/${circuit}`,
  sensor_location: null,
  start_date: '2018-05-01 00:00:00',
  number_of_timesteps: 96,
  run_freq_sec: 900,
})

const evPreset = (
  buses: readonly string[],
  counts: readonly number[],
  voltageSensitivityScale: number,
  smartDs: boolean,
): Record<string, unknown> => ({
  evcs_bus: [...buses],
  evcs_bus_assignment: assignment(buses, counts),
  num_evs_per_station: [...counts],
  max_charging_rate: 22.0,
  battery_capacity: 50.0,
  charging_efficiency: 0.95,
  desired_soc: 0.9,
  soc_mean: 0.3,
  soc_std: 0.2,
  soc_lower: 0.1,
  soc_upper: 0.5,
  arrival_mean: 9.0,
  arrival_std: 1.5,
  arrival_lower: smartDs ? 7.5 : 7.0,
  arrival_upper: smartDs ? 10.5 : 11.0,
  departure_shift: 17.5,
  departure_mu: 0.0,
  departure_sigma: 0.9,
  total_hours: 24,
  control_interval: 0.25,
  random_seed: 42,
  voltage_sensitivity_scale: voltageSensitivityScale,
})

export const ORNL_EV_FEEDER_PRESETS: readonly OrnlEvFeederPreset[] = [
  {
    id: 'ieee123',
    label: 'IEEE 123',
    feeder: {
      use_smartds: false,
      user_uploads_model: false,
      profile_location: 'gadal_ieee123/profiles',
      opendss_location: 'gadal_ieee123/qsts',
      sensor_location: 'gadal_ieee123/sensors.json',
      start_date: '2017-01-01 00:00:00',
      number_of_timesteps: 96,
      run_freq_sec: 900,
    },
    ev: evPreset(ieeeBuses, [67, 67, 66], 1.0, false),
  },
  {
    id: 'smartds-p1u',
    label: 'Smart-DS SFO P1U',
    feeder: smartDsFeeder(
      'P1U',
      'p1uhs0_1247/p1uhs0_1247--p1udt942',
    ),
    ev: evPreset(p1uBuses, [25, 25, 25], 0.33, true),
  },
  {
    id: 'smartds-p6u',
    label: 'Smart-DS SFO P6U',
    feeder: smartDsFeeder(
      'P6U',
      'p6uhs10_1247/p6uhs10_1247--p6udt5293',
    ),
    ev: evPreset(p6uBuses, [25, 25, 25], 0.33, true),
  },
] as const

export const ornlEvPresetForOpenDssLocation = (location: unknown) =>
  ORNL_EV_FEEDER_PRESETS.find(
    (preset) => preset.feeder.opendss_location === location,
  )

export const hasOrnlEvConfigChange = (
  current: Record<string, unknown>,
  submitted: Record<string, unknown>,
): boolean => Object.entries(submitted).some(
  ([key, value]) => JSON.stringify(current[key]) !== JSON.stringify(value),
)

export const normalizeOrnlEvFeederFormConfig = (
  submitted: Record<string, unknown>,
): Record<string, unknown> => submitted.sensor_location === ''
  ? { ...submitted, sensor_location: null }
  : submitted

export const connectedOrnlEvNodeIds = (
  feederNodeId: string,
  nodes: readonly Node[],
  edges: readonly Edge[],
): string[] => {
  const feeder = nodes.find((node) => node.id === feederNodeId)
  if (
    !feederNodeId.startsWith(ORNL_EV_SWITCHABLE_FEEDER_PREFIX) ||
    (feeder?.data as NodeData | undefined)?.componentType !== 'Feeder'
  ) {
    return []
  }

  const nodeTypes = new Map(nodes.map((node) => [
    node.id,
    (node.data as NodeData | undefined)?.componentType,
  ]))

  return edges
    .filter((edge) => {
      if (
        edge.source !== feederNodeId ||
        nodeTypes.get(edge.target) !== 'EVCSComponent'
      ) {
        return false
      }
      const wires = (edge.data as EdgeData | undefined)?.wires ?? []
      return wires.some(
        (wire) =>
          wire.sourcePortId === 'topology' &&
          wire.targetPortId === 'topology' &&
          wire.type === 'Topology',
      )
    })
    .map((edge) => edge.target)
}

export const isSwitchableOrnlEvFeeder = (
  feederNodeId: string,
  nodes: readonly Node[],
  edges: readonly Edge[],
) => connectedOrnlEvNodeIds(feederNodeId, nodes, edges).length > 0

export const isSwitchableOrnlEvComponent = (
  evNodeId: string,
  nodes: readonly Node[],
  edges: readonly Edge[],
): boolean => {
  const evNode = nodes.find((node) => node.id === evNodeId)
  if ((evNode?.data as NodeData | undefined)?.componentType !== 'EVCSComponent') {
    return false
  }

  return nodes.some(
    (node) =>
      node.id.startsWith(ORNL_EV_SWITCHABLE_FEEDER_PREFIX) &&
      connectedOrnlEvNodeIds(node.id, nodes, edges).includes(evNodeId),
  )
}

export const withOrnlEvControlModeDropdown = (
  schema: Record<string, unknown>,
): Record<string, unknown> => {
  const cached = controlModeSchemaCache.get(schema)
  if (cached) return cached

  const properties =
    (schema.properties as Record<string, unknown> | undefined) ?? {}
  const required = Array.isArray(schema.required)
    ? [...new Set([...schema.required, 'control_mode'])]
    : ['control_mode']
  const dropdownSchema = {
    ...schema,
    required,
    properties: {
      ...properties,
      control_mode: {
        title: 'EV Charging Mode',
        description:
          'Run both modes with the same feeder and settings to enable an automatic comparison report.',
        type: 'string',
        oneOf: [
          { const: 'dopf', title: 'Controlled' },
          { const: 'uncontrolled', title: 'Baseline' },
        ],
        default: 'dopf',
      },
    },
  }
  controlModeSchemaCache.set(schema, dropdownSchema)
  return dropdownSchema
}
export const withOrnlEvFeederDropdown = (
  schema: Record<string, unknown>,
): Record<string, unknown> => {
  const cached = dropdownSchemaCache.get(schema)
  if (cached) return cached

  const properties =
    (schema.properties as Record<string, unknown> | undefined) ?? {}
  const opendssLocation =
    (properties.opendss_location as Record<string, unknown> | undefined) ?? {}
  const visibleProperties = Object.fromEntries(
    Object.entries(properties).filter(
      ([key]) => !['use_smartds', 'user_uploads_model', 'sensor_location'].includes(key),
    ),
  )
  const dropdownSchema = {
    ...schema,
    properties: {
      ...visibleProperties,
      opendss_location: {
        ...opendssLocation,
        title: 'Feeder Dataset',
        description:
          'Selecting a feeder also applies its matched profiles, dates, EV buses, assignments, and sensitivity settings.',
        oneOf: ORNL_EV_FEEDER_PRESETS.map((preset) => ({
          const: preset.feeder.opendss_location,
          title: preset.label,
        })),
      },
    },
  }
  dropdownSchemaCache.set(schema, dropdownSchema)
  return dropdownSchema
}

export interface OrnlEvFeederPresetUpdate {
  feederConfig: Record<string, unknown>
  evNodeIds: string[]
  evConfig: (current: Record<string, unknown>) => Record<string, unknown>
  preset: OrnlEvFeederPreset
}

export const buildOrnlEvFeederPresetUpdate = (
  feederNodeId: string,
  currentFeederConfig: Record<string, unknown>,
  submittedFeederConfig: Record<string, unknown>,
  nodes: readonly Node[],
  edges: readonly Edge[],
): OrnlEvFeederPresetUpdate | null => {
  const evNodeIds = connectedOrnlEvNodeIds(feederNodeId, nodes, edges)
  const preset = ornlEvPresetForOpenDssLocation(
    submittedFeederConfig.opendss_location,
  )
  if (evNodeIds.length === 0 || !preset) return null

  return {
    feederConfig: {
      ...currentFeederConfig,
      ...submittedFeederConfig,
      ...preset.feeder,
    },
    evNodeIds,
    evConfig: (current) => ({
      ...current,
      ...preset.ev,
    }),
    preset,
  }
}
