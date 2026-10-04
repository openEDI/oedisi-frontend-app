import fs from 'node:fs'
import path from 'node:path'

import { describe, expect, it } from 'vitest'

import type { TemplateData } from '@/lib/flowTypes'
import { toWiringDiagram } from '@/lib/wiringDiagram'

const templatesDir = path.resolve(process.cwd(), 'data/templates/dev')
const catalogPath = path.resolve(process.cwd(), 'src/lib/catalog.json')
const catalog = JSON.parse(fs.readFileSync(catalogPath, 'utf8')) as Array<{
  id: string
}>
const catalogIds = new Set(catalog.map((component) => component.id))
const templateFiles = fs
  .readdirSync(templatesDir)
  .filter((name) => name.endsWith('.json'))
  .sort()

const requiredTemplates = [
  'nrel_dsse.json',
  'nrel_dsse_small_smartds.json',
  'standard_dsse.json',
  'nlpdopf_ieee123.json',
  'nlpdsse_ieee123.json',
  'ornl_dopf_pso_ieee123.json',
  'ornl_dsse_gnwls_ieee123.json',
  'ornl_ev_pso_ieee123_200ev.json',
  'ornl_ev_pso_ieee123_200ev_uncontrolled.json',
  'ornl_ev_pso_feeder_selection.json',
  'ornl_ev_pso_case2_smartds_dopf.json',
  'ornl_ev_pso_case2_smartds_uncontrolled.json',
  'ornl_od_player_ei20110427.json',
  'ornl_od_player_synthetic_mock.json',
  'pnnl-dopf-admm-ieee123.json',
  'pnnl-dopf-admm-ieee123-multi-objective.json',
  'pnnl-emt-swod-1khz.json',
  'pnnl-emt-swod-25khz.json',
  'pnnl_dsse_ekf.json',
  'pnnl_dopf_lindistflow_ieee123.json',
  'pnnl_emt_swod.json',
]

describe('cross-lab release templates', () => {
  it('contains every required NLR/NREL, ORNL, and PNNL use case', () => {
    expect(templateFiles).toEqual(expect.arrayContaining(requiredTemplates))
  })

  for (const filename of templateFiles) {
    it(`${filename} uses the current UI format and registered components`, () => {
      const template = JSON.parse(
        fs.readFileSync(path.join(templatesDir, filename), 'utf8'),
      ) as TemplateData

      expect(Array.isArray(template.nodes)).toBe(true)
      expect(Array.isArray(template.edges)).toBe(true)

      for (const node of template.nodes) {
        expect(node.data?.componentType).toBeTruthy()
        expect(catalogIds.has(node.data?.componentType ?? '')).toBe(true)
      }

      const wiring = toWiringDiagram(template)
      expect(wiring.components).toHaveLength(template.nodes.length)
    })
  }
})
