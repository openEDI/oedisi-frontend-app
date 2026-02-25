import wslDefinition from '@/lib/definations/wls_federate.json'
import feederDefinition from '@/lib/definations/feeder.json'
import linDistFlowDefinition from '@/lib/definations/lin_dist_flow_algorithm.json'
import recorderDefinition from '@/lib/definations/recorder.json'
import sensorDefinition from '@/lib/definations/sensor.json'

export interface FederateDefinition {
  directory: string
  execute_function: string
  static_inputs: Array<Record<string, unknown>>
  dynamic_inputs: Array<Record<string, unknown>>
  dynamic_outputs: Array<Record<string, unknown>>
}

export interface ComponentDefinition {
  id: string
  name: string
  description: string
  definitionFile: string
  definition: FederateDefinition
}

export const COMPONENT_CATALOG: ComponentDefinition[] = [
  {
    id: 'feeder',
    name: 'Feeder',
    description: 'OpenDSS simulation engine',
    definitionFile: 'feeder.json',
    definition: feederDefinition,
  },
  {
    id: 'wls_se_algorihtm',
    name: 'State Estimator',
    description: 'WSL state estimator',
    definitionFile: 'wls_federate.json',
    definition: wslDefinition,
  },
  {
    id: 'lin_dist_flow_algorithm',
    name: 'LinDistFlow Algorithm',
    description: 'LinDistFlow optimization algorithm',
    definitionFile: 'lin_dist_flow_algorithm.json',
    definition: linDistFlowDefinition,
  },
  {
    id: 'sensor',
    name: 'Sensor',
    description: 'Sensor model',
    definitionFile: 'sensor.json',
    definition: sensorDefinition,
  },
  {
    id: 'recorder',
    name: 'Recorder',
    description: 'Records simulation results',
    definitionFile: 'recorder.json',
    definition: recorderDefinition,
  },
]