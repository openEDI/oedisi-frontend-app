import wlsDefinition from '@/lib/definitions/wls_federate.json'
import feederDefinition from '@/lib/definitions/feeder.json'
import linDistFlowDefinition from '@/lib/definitions/lin_dist_flow_algorithm.json'
import recorderDefinition from '@/lib/definitions/recorder.json'
import sensorDefinition from '@/lib/definitions/sensor.json'
import wlsSchema from '@/lib/schemas/wls_federate.json'
import feederSchema from '@/lib/schemas/feeder.json'
import sensorSchema from '@/lib/schemas/measuring_federate.json'
import recorderSchema from '@/lib/schemas/recorder.json'

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
  inputSchema?: Record<string, unknown>
}

export const COMPONENT_CATALOG: ComponentDefinition[] = [
  {
    id: 'Feeder',
    name: 'Feeder',
    description: 'OpenDSS simulation engine',
    definitionFile: 'feeder.json',
    definition: feederDefinition,
    inputSchema: feederSchema,
  },
  {
    id: 'StateEstimatorComponent',
    name: 'State Estimator',
    description: 'WLS state estimator',
    definitionFile: 'wls_federate.json',
    definition: wlsDefinition,
    inputSchema: wlsSchema,
  },
  {
    id: 'LinDistFlowComponent',
    name: 'LinDistFlow Algorithm',
    description: 'LinDistFlow optimization algorithm',
    definitionFile: 'lin_dist_flow_algorithm.json',
    definition: linDistFlowDefinition,
  },
  {
    id: 'MeasurementComponent',
    name: 'Sensor',
    description: 'Sensor model',
    definitionFile: 'sensor.json',
    definition: sensorDefinition,
    inputSchema: sensorSchema,
  },
  {
    id: 'Recorder',
    name: 'Recorder',
    description: 'Records simulation results',
    definitionFile: 'recorder.json',
    definition: recorderDefinition,
    inputSchema: recorderSchema,
  },
]
