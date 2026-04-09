import { toWiringDiagram } from '@/lib/wiringDiagram'
import { describe, it, expect } from 'vitest'
import type { Node } from '@vue-flow/core'
import { NodeData, TemplateData } from '@/lib/flowTypes'

function makeTemplate(overrides = {}): TemplateData {
  return {
    id: '1',
    name: 'name',
    description: '',
    nodes: [],
    edges: [],
    createdAt: 'test-time',
    ...overrides,
  }
}

function makeNode(id: string = 'node1', overrides = {}): Node<NodeData> {
  return {
    id: id,
    position: { x: 0, y: 0 },
    data: {
      label: 'feeder_1',
      componentType: 'feeder',
      ...overrides,
    },
  }
}

describe('toWiringDiagram', () => {
  it('Accepts empty', () => {
    expect(toWiringDiagram(makeTemplate())).toEqual({
      name: 'name',
      components: [],
      links: [],
    })
  })

  it('One node', () => {
    expect(toWiringDiagram(makeTemplate({ nodes: [makeNode()] }))).toEqual({
      name: 'name',
      components: [
        {
          name: 'feeder_1',
          type: 'feeder',
          parameters: {},
        },
      ],
      links: [],
    })
  })

  it('Two nodes', () => {
    expect(
      toWiringDiagram(
        makeTemplate({
          nodes: [
            makeNode('node1', { label: 'feeder_1' }),
            makeNode('node2', { label: 'feeder_2' }),
          ],
          edges: [
            {
              id: 'edge1',
              source: 'node1',
              target: 'node2',
              data: {
                wires: [
                  {
                    type: 'VoltageMagnitude',
                    sourcePortId: 'voltage_magnitude',
                    targetPortId: 'voltage_magnitude',
                  },
                ],
              },
            },
          ],
        }),
      ),
    ).toEqual({
      name: 'name',
      components: [
        {
          name: 'feeder_1',
          type: 'feeder',
          parameters: {},
        },
        {
          name: 'feeder_2',
          type: 'feeder',
          parameters: {},
        },
      ],
      links: [
        {
          source: 'feeder_1',
          source_port: 'voltage_magnitude',
          target: 'feeder_2',
          target_port: 'voltage_magnitude',
        },
      ],
    })
  })

  it('throws when missing componentType', () => {
    expect(() =>
      toWiringDiagram(
        makeTemplate({
          nodes: [makeNode('node1', { componentType: undefined })],
        }),
      ),
    ).toThrow()
  })

  it('throws when missing data', () => {
    expect(() =>
      toWiringDiagram(
        makeTemplate({
          nodes: [
            {
              id: 'node1',
              position: { x: 0, y: 0 },
            },
          ],
        }),
      ),
    ).toThrow()
  })

  it('throws when missing node id', () => {
    expect(() =>
      toWiringDiagram(
        makeTemplate({
          nodes: [
            makeNode('node1', { label: 'feeder_1' }),
            makeNode('node2', { label: 'feeder_2' }),
          ],
          edges: [
            {
              id: 'node1',
              source: 'node3',
              target: 'node4',
              data: { wires: [] },
            },
          ],
        }),
      ),
    ).toThrow()
  })
})
