import fs from 'node:fs'
import path from 'node:path'

import type { Edge, Node } from '@vue-flow/core'
import { describe, expect, it } from 'vitest'

import type { EdgeData, NodeData, TemplateData } from '@/lib/flowTypes'
import {
  buildOrnlOdPresetUpdate,
  connectedOrnlOdNodeIds,
  hasOrnlOdPlayerConfigChange,
  isOrnlOdPlayer,
  mergeOrnlOdPlayerConfig,
  ORNL_OD_DATASETS,
  withOrnlOdDatasetDropdown,
} from '@/lib/ornlOdDatasets'

const templatesDir = path.resolve(process.cwd(), 'data/templates/dev')

const readTemplate = (filename: string) =>
  JSON.parse(
    fs.readFileSync(path.join(templatesDir, filename), 'utf8')
  ) as TemplateData

const playerNodes = (template: TemplateData) =>
  template.nodes.filter(
    (node) => node.data?.componentType === 'PlayerComponent'
  )

describe('ORNL OD dataset presets', () => {
  it('defines the complete packaged inventory with safe portable paths', () => {
    expect(ORNL_OD_DATASETS).toHaveLength(12)
    expect(new Set(ORNL_OD_DATASETS.map((preset) => preset.id))).toHaveLength(
      12
    )
    expect(
      new Set(ORNL_OD_DATASETS.map((preset) => preset.filename))
    ).toHaveLength(12)

    for (const preset of ORNL_OD_DATASETS) {
      expect(preset.filename).toMatch(
        /^\/components\/ornl-od-prony\/data\/[^/]+\.csv$/
      )
      expect(preset.numberOfTimesteps).toBeGreaterThan(0)
      expect(preset.sampleRateHz).toBe(10)
      expect(preset.channels).toBeGreaterThan(0)
      expect(JSON.parse(preset.od.ground_truth_json)).toBeInstanceOf(Array)
    }

    expect(ORNL_OD_DATASETS.find((preset) => preset.longRun)?.id).toBe(
      'wecc-2015-09-05'
    )
    expect(ORNL_OD_DATASETS.filter((preset) => preset.longRun)).toHaveLength(1)

    expect(
      ORNL_OD_DATASETS.find((preset) => preset.id === 'ei-2024-11-01')?.od
        .prony_window_sec
    ).toBe(30)
    expect(
      ORNL_OD_DATASETS.find((preset) => preset.id === 'wecc-2015-09-05')?.od
        .prony_window_sec
    ).toBe(2.5)
    expect(
      ORNL_OD_DATASETS.find((preset) => preset.id === 'wecc-2023-11-01')?.od
        .prony_window_sec
    ).toBe(8)
    expect(
      ORNL_OD_DATASETS.find((preset) => preset.id === 'wecc-2025-08-12')?.od
        .trigger_threshold
    ).toBe(0.005)
  })

  it('matches packaged files and metadata when OEDISI_COMPONENTS is set', () => {
    const componentsRoot = process.env.OEDISI_COMPONENTS
    if (!componentsRoot) return
    expect(fs.existsSync(componentsRoot)).toBe(true)

    for (const preset of ORNL_OD_DATASETS) {
      const basename = path.basename(preset.filename)
      const dataPath = path.join(
        componentsRoot,
        'ornl-od-prony',
        'data',
        basename
      )
      expect(fs.existsSync(dataPath), preset.id).toBe(true)
      expect(fs.existsSync(`${dataPath}_metadata.json`), preset.id).toBe(true)

      const rowCount =
        fs.readFileSync(dataPath, 'utf8').trimEnd().split(/\r?\n/).length - 1
      expect(rowCount, preset.id).toBe(preset.numberOfTimesteps)
    }
  })

  it('adds a dropdown to a clone without mutating the shared Player schema', () => {
    const schema = {
      type: 'object',
      properties: {
        filename: { title: 'Filename', type: 'string' },
        data_type: { title: 'Data Type', type: 'string' },
      },
    }
    const original = structuredClone(schema)
    const scoped = withOrnlOdDatasetDropdown(schema) as {
      properties: {
        filename: { oneOf: Array<{ const: string; title: string }> }
      }
    }

    expect(schema).toEqual(original)
    expect(scoped).not.toBe(schema)
    expect(scoped.properties.filename.oneOf).toHaveLength(12)
    expect(
      scoped.properties.filename.oneOf.map((choice) => choice.const)
    ).toEqual(ORNL_OD_DATASETS.map((preset) => preset.filename))
    expect(withOrnlOdDatasetDropdown(schema)).toBe(scoped)
  })

  it('suppresses identity-only form emissions while retaining hidden runtime fields', () => {
    const current = {
      name: 'player',
      filename: ORNL_OD_DATASETS[0].filename,
      data_type: 'MeasurementArray',
      number_of_timesteps: 370,
      start_time_index: 0,
      run_freq_time_step: 0.1,
      nested: { retained: true },
    }
    const initialEmission = {
      name: 'player',
      filename: ORNL_OD_DATASETS[0].filename,
      data_type: 'MeasurementArray',
      number_of_timesteps: 370,
      start_time_index: 0,
      nested: { retained: true },
    }

    expect(hasOrnlOdPlayerConfigChange(current, initialEmission)).toBe(false)
    expect(mergeOrnlOdPlayerConfig(current, initialEmission)).toEqual(current)
    expect(
      hasOrnlOdPlayerConfigChange(current, {
        ...initialEmission,
        filename: ORNL_OD_DATASETS[1].filename,
      })
    ).toBe(true)
  })
})

describe('ORNL OD graph isolation', () => {
  it('recognizes only Players wired to ODComponent.frequency', () => {
    for (const filename of [
      'ornl_od_player_ei20110427.json',
      'ornl_od_player_synthetic_mock.json',
    ]) {
      const template = readTemplate(filename)
      const players = playerNodes(template)
      expect(players).toHaveLength(1)
      expect(
        isOrnlOdPlayer(players[0].id, template.nodes, template.edges)
      ).toBe(true)
    }

    const pnnl = readTemplate('pnnl_emt_swod.json')
    expect(playerNodes(pnnl)).toHaveLength(2)
    for (const player of playerNodes(pnnl)) {
      expect(isOrnlOdPlayer(player.id, pnnl.nodes, pnnl.edges)).toBe(false)
      expect(connectedOrnlOdNodeIds(player.id, pnnl.nodes, pnnl.edges)).toEqual(
        []
      )
    }
  })

  it('does not identify any Player in non-ORNL canonical workflows', () => {
    for (const filename of fs
      .readdirSync(templatesDir)
      .filter((name) => name.endsWith('.json'))) {
      if (filename.startsWith('ornl_od_player_')) continue
      const template = readTemplate(filename)
      for (const player of playerNodes(template)) {
        expect(
          isOrnlOdPlayer(player.id, template.nodes, template.edges),
          filename
        ).toBe(false)
      }
    }
  })

  it('requires the exact publication-to-frequency MeasurementArray wire', () => {
    const nodes = [
      {
        id: 'player',
        data: { label: 'Player', componentType: 'PlayerComponent' },
      },
      { id: 'od', data: { label: 'OD', componentType: 'ODComponent' } },
    ] as Node<NodeData>[]
    const edge = (
      sourcePortId: string,
      targetPortId: string,
      type = 'MeasurementArray'
    ) =>
      [
        {
          id: 'edge',
          source: 'player',
          target: 'od',
          data: { wires: [{ sourcePortId, targetPortId, type }] },
        },
      ] as Edge<EdgeData>[]

    expect(
      isOrnlOdPlayer('player', nodes, edge('publication', 'frequency'))
    ).toBe(true)
    expect(isOrnlOdPlayer('player', nodes, edge('publication', 'other'))).toBe(
      false
    )
    expect(isOrnlOdPlayer('player', nodes, edge('other', 'frequency'))).toBe(
      false
    )
    expect(
      isOrnlOdPlayer(
        'player',
        nodes,
        edge('publication', 'frequency', 'string')
      )
    ).toBe(false)
  })
})

describe('ORNL OD synchronized updates', () => {
  it('updates only the selected Player and its directly connected OD node', () => {
    const template = readTemplate('ornl_od_player_ei20110427.json')
    const player = playerNodes(template)[0]
    const current = player.data?.config ?? {}
    const target = ORNL_OD_DATASETS.find(
      (preset) => preset.id === 'ercot-2025-04-25'
    )
    expect(target).toBeDefined()

    const update = buildOrnlOdPresetUpdate(
      player.id,
      { ...current, retained_player_field: 'keep' },
      { ...current, filename: target?.filename },
      template.nodes,
      template.edges
    )

    expect(update).not.toBeNull()
    expect(update?.odNodeIds).toEqual(['ODComponent-1780000000002'])
    expect(update?.playerConfig).toMatchObject({
      filename: target?.filename,
      data_type: 'MeasurementArray',
      number_of_timesteps: 3601,
      start_time_index: 0,
      run_freq_time_step: 0.1,
      retained_player_field: 'keep',
    })

    const odConfig = update?.odConfig({ name: 'od', retained_od_field: 'keep' })
    expect(odConfig).toMatchObject({
      name: 'od',
      retained_od_field: 'keep',
      sample_rate_hz: 10,
      prony_window_sec: 90,
      ground_truth_json: JSON.stringify([{ frequency_hz: 0.5 }]),
    })
  })

  it('keeps two ORNL OD workflows independent', () => {
    const nodes = [
      {
        id: 'player-a',
        data: { label: 'Player A', componentType: 'PlayerComponent' },
      },
      { id: 'od-a', data: { label: 'OD A', componentType: 'ODComponent' } },
      {
        id: 'player-b',
        data: { label: 'Player B', componentType: 'PlayerComponent' },
      },
      { id: 'od-b', data: { label: 'OD B', componentType: 'ODComponent' } },
    ] as Node<NodeData>[]
    const edges = [
      {
        id: 'edge-a',
        source: 'player-a',
        target: 'od-a',
        data: {
          wires: [
            {
              type: 'MeasurementArray',
              sourcePortId: 'publication',
              targetPortId: 'frequency',
            },
          ],
        },
      },
      {
        id: 'edge-b',
        source: 'player-b',
        target: 'od-b',
        data: {
          wires: [
            {
              type: 'MeasurementArray',
              sourcePortId: 'publication',
              targetPortId: 'frequency',
            },
          ],
        },
      },
    ] as Edge<EdgeData>[]
    const target = ORNL_OD_DATASETS.find(
      (preset) => preset.id === 'synthetic-10hz'
    )

    const update = buildOrnlOdPresetUpdate(
      'player-a',
      {},
      { filename: target?.filename },
      nodes,
      edges
    )
    expect(update?.odNodeIds).toEqual(['od-a'])
  })

  it('returns no update for PNNL SWOD Players', () => {
    const pnnl = readTemplate('pnnl_emt_swod.json')
    for (const player of playerNodes(pnnl)) {
      const update = buildOrnlOdPresetUpdate(
        player.id,
        player.data?.config ?? {},
        { filename: ORNL_OD_DATASETS[0].filename },
        pnnl.nodes,
        pnnl.edges
      )
      expect(update).toBeNull()
    }
  })
})
