import type { Edge, Node } from '@vue-flow/core'
import { describe, expect, it } from 'vitest'

import type { EdgeData, NodeData } from '@/lib/flowTypes'
import {
  ORNL_EV_FEEDER_PRESETS,
  buildOrnlEvFeederPresetUpdate,
  connectedOrnlEvNodeIds,
  hasOrnlEvConfigChange,
  isSwitchableOrnlEvComponent,
  isSwitchableOrnlEvFeeder,
  normalizeOrnlEvFeederFormConfig,
  withOrnlEvControlModeDropdown,
  withOrnlEvFeederDropdown,
} from '@/lib/ornlEvFeederPresets'

const feederId = 'OrnlEvSwitchFeeder-test'
const evId = 'EVCSComponent-test'

const nodes: Node<NodeData>[] = [
  {
    id: feederId,
    type: 'custom',
    position: { x: 0, y: 0 },
    data: {
      label: 'Feeder',
      componentType: 'Feeder',
      config: {
        opendss_location: 'gadal_ieee123/qsts',
        name: 'feeder',
      },
    },
  },
  {
    id: evId,
    type: 'custom',
    position: { x: 1, y: 0 },
    data: {
      label: 'ORNL EV Scheduler',
      componentType: 'EVCSComponent',
      config: { name: 'evcs', control_mode: 'uncontrolled' },
    },
  },
]

const edges: Edge<EdgeData>[] = [
  {
    id: 'feeder-to-ev',
    source: feederId,
    target: evId,
    data: {
      wires: [
        {
          type: 'Topology',
          sourcePortId: 'topology',
          targetPortId: 'topology',
        },
      ],
    },
  },
]

describe('ORNL EV feeder presets', () => {
  it('ignores no-op form events while detecting real changes', () => {
    const current = {
      opendss_location: 'gadal_ieee123/qsts',
      use_smartds: false,
      control_mode: 'dopf',
      evcs_bus: ['48.1', '65.1', '76.1'],
    }

    expect(hasOrnlEvConfigChange(current, { ...current })).toBe(false)
    expect(hasOrnlEvConfigChange(current, {
      opendss_location: current.opendss_location,
      control_mode: current.control_mode,
      evcs_bus: [...current.evcs_bus],
    })).toBe(false)
    expect(hasOrnlEvConfigChange(current, {
      control_mode: 'uncontrolled',
    })).toBe(true)
  })
  it('defines IEEE-123, P1U, and P6U choices', () => {
    expect(ORNL_EV_FEEDER_PRESETS.map((preset) => preset.id)).toEqual([
      'ieee123',
      'smartds-p1u',
      'smartds-p6u',
    ])
    expect(ORNL_EV_FEEDER_PRESETS[2]?.label).toBe('Smart-DS SFO P6U')
  })

  it('limits switching to marked Feeder nodes wired to ORNL EV', () => {
    expect(connectedOrnlEvNodeIds(feederId, nodes, edges)).toEqual([evId])
    expect(isSwitchableOrnlEvFeeder(feederId, nodes, edges)).toBe(true)
    expect(
      isSwitchableOrnlEvFeeder('LocalFeeder-test', [
        { ...nodes[0], id: 'LocalFeeder-test' },
        nodes[1],
      ], [{ ...edges[0], source: 'LocalFeeder-test' }]),
    ).toBe(false)
  })

  it('limits the charging-mode dropdown to the connected ORNL EV node', () => {
    expect(isSwitchableOrnlEvComponent(evId, nodes, edges)).toBe(true)
    expect(isSwitchableOrnlEvComponent(feederId, nodes, edges)).toBe(false)
  })

  it('adds friendly controlled and baseline choices without mutating the EV schema', () => {
    const schema = {
      type: 'object',
      properties: { random_seed: { type: 'integer' } },
      required: ['random_seed'],
    }
    const original = structuredClone(schema)
    const scoped = withOrnlEvControlModeDropdown(schema) as {
      properties: { control_mode: { oneOf: Array<{ const: string; title: string }> } }
      required: string[]
    }

    expect(schema).toEqual(original)
    expect(scoped.properties.control_mode.oneOf).toEqual([
      { const: 'dopf', title: 'Controlled' },
      { const: 'uncontrolled', title: 'Baseline' },
    ])
    expect(scoped.required).toContain('control_mode')
    expect(withOrnlEvControlModeDropdown(schema)).toBe(scoped)
  })
  it('adds a dropdown without mutating the shared Feeder schema', () => {
    const schema = {
      type: 'object',
      properties: {
        opendss_location: { type: 'string', title: 'OpenDSS Location' },
        use_smartds: { type: 'boolean' },
        user_uploads_model: { type: 'boolean' },
        sensor_location: { type: 'string' },
      },
    }
    const original = structuredClone(schema)
    const scoped = withOrnlEvFeederDropdown(schema) as {
      properties: {
        opendss_location: { oneOf: unknown[] }
        use_smartds?: unknown
        user_uploads_model?: unknown
        sensor_location?: unknown
      }
    }

    expect(schema).toEqual(original)
    expect(scoped).not.toBe(schema)
    expect(scoped.properties.opendss_location.oneOf).toHaveLength(3)
    expect(scoped.properties.use_smartds).toBeUndefined()
    expect(scoped.properties.user_uploads_model).toBeUndefined()
    expect(scoped.properties.sensor_location).toBeUndefined()
    expect(withOrnlEvFeederDropdown(schema)).toBe(scoped)
  })

  it('maps P1U to P1U feeder and EV settings and preserves a null sensor path', () => {
    const p1u = ORNL_EV_FEEDER_PRESETS[1]
    const normalized = normalizeOrnlEvFeederFormConfig({
      opendss_location: p1u.feeder.opendss_location,
      sensor_location: '',
    })
    const update = buildOrnlEvFeederPresetUpdate(
      feederId,
      nodes[0]?.data?.config ?? {},
      normalized,
      nodes,
      edges,
    )

    expect(normalized.sensor_location).toBeNull()
    expect(update?.feederConfig).toMatchObject({
      profile_location: 'SMART-DS/v1.0/2018/SFO/P1U/profiles',
      sensor_location: null,
    })
    expect(update?.evConfig(nodes[1]?.data?.config ?? {})).toMatchObject({
      evcs_bus: ['p1ulv4132.1', 'p1ulv4108.1', 'p1ulv4189.1'],
    })
  })

  it('applies P6U feeder and EV settings while preserving control mode', () => {
    const p6u = ORNL_EV_FEEDER_PRESETS[2]
    const update = buildOrnlEvFeederPresetUpdate(
      feederId,
      nodes[0]?.data?.config ?? {},
      { opendss_location: p6u.feeder.opendss_location },
      nodes,
      edges,
    )

    expect(update).not.toBeNull()
    expect(update?.feederConfig).toMatchObject({
      use_smartds: true,
      profile_location: 'SMART-DS/v1.0/2018/SFO/P6U/profiles',
      name: 'feeder',
    })
    expect(update?.evNodeIds).toEqual([evId])
    expect(update?.evConfig(nodes[1]?.data?.config ?? {})).toMatchObject({
      control_mode: 'uncontrolled',
      evcs_bus: ['p6ulv16572.1', 'p6ulv26801.1', 'p6ulv26810.1'],
      num_evs_per_station: [25, 25, 25],
      voltage_sensitivity_scale: 0.33,
    })
  })

  it('restores all IEEE-specific values when switching back', () => {
    const ieee = ORNL_EV_FEEDER_PRESETS[0]
    const p1u = ORNL_EV_FEEDER_PRESETS[1]
    const update = buildOrnlEvFeederPresetUpdate(
      feederId,
      { ...p1u.feeder, name: 'feeder' },
      { opendss_location: ieee.feeder.opendss_location },
      nodes,
      edges,
    )
    const ev = update?.evConfig({
      ...p1u.ev,
      name: 'evcs',
      control_mode: 'dopf',
    })

    expect(update?.feederConfig).toMatchObject({
      use_smartds: false,
      sensor_location: 'gadal_ieee123/sensors.json',
      start_date: '2017-01-01 00:00:00',
    })
    expect(ev).toMatchObject({
      control_mode: 'dopf',
      evcs_bus: ['48.1', '65.1', '76.1'],
      num_evs_per_station: [67, 67, 66],
      voltage_sensitivity_scale: 1.0,
    })
  })
})
