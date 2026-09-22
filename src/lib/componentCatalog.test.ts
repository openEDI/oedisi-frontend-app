import { COMPONENT_CATALOG, makeDefaults } from '@/lib/componentCatalog'
import { describe, it, expect } from 'vitest'

describe('componentCatalog', () => {
  it('has Feeder first', () => {
    expect(COMPONENT_CATALOG[0].id === 'Feeder').toBe(true)
  })
})

describe('makeDefaults', () => {
  it('produces the expected default for Feeders', () => {
    expect(COMPONENT_CATALOG[0].inputSchema).toBeDefined()
    expect(makeDefaults(COMPONENT_CATALOG[0].inputSchema || {})).toStrictEqual({
      use_smartds: false,
      user_uploads_model: false,
      profile_location: 'gadal_ieee123/profiles',
      opendss_location: 'gadal_ieee123/qsts',
      sensor_location: 'gadal_ieee123/sensors.json',
      start_date: '2017-01-01 00:00:00',
      number_of_timesteps: 1,
      run_freq_sec: 900,
      start_time_index: 0,
      topology_output: 'topology.json',
      use_sparse_admittance: false,
    })
  })
})
