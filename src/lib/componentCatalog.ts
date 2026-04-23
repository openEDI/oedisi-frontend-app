import wlsDefinition from '@/lib/definitions/wls_federate.json'
import feederDefinition from '@/lib/definitions/feeder.json'
import linDistFlowDefinition from '@/lib/definitions/lin_dist_flow_algorithm.json'
import recorderDefinition from '@/lib/definitions/recorder.json'
import sensorDefinition from '@/lib/definitions/sensor.json'
import wlsSchema from '@/lib/schemas/wls_federate.json'
import feederSchema from '@/lib/schemas/feeder.json'
import sensorSchema from '@/lib/schemas/measuring_federate.json'
import recorderSchema from '@/lib/schemas/recorder.json'
import linDistFlowSchema from '@/lib/schemas/lin_dist_flow_algorithm.json'
import omooDefinition from '@/lib/definitions/omoo_federate.json'
import omooSchema from '@/lib/schemas/omoo_federate.json'
import nlpdopfDefinition from '@/lib/definitions/nlpdopf.json'
import nlpdopfSchema from '@/lib/schemas/nlpdopf.json'
import nlpDsseDefinition from '@/lib/definitions/nlpdsse.json'
import nlpDsseSchema from '@/lib/schemas/nlpdsse.json'
import pnnlDopfAdmmDefinition from '@/lib/definitions/pnnl_dopf_admm.json'
import pnnlDopfAdmmSchema from '@/lib/schemas/pnnl_dopf_admm.json'
import pnnlHubControlDefinition from '@/lib/definitions/pnnl_hub_control.json'
import pnnlHubControlSchema from '@/lib/schemas/pnnl_hub_control.json'
import pnnlHubPowerDefinition from '@/lib/definitions/pnnl_hub_power.json'
import pnnlHubPowerSchema from '@/lib/schemas/pnnl_hub_power.json'
import pnnlHubVoltageDefinition from '@/lib/definitions/pnnl_hub_voltage.json'
import pnnlHubVoltageSchema from '@/lib/schemas/pnnl_hub_voltage.json'

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
    inputSchema: linDistFlowSchema,
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
  {
    id: 'OMOOComponent',
    name: 'OMOO',
    description: 'Optimal Power Flow',
    definitionFile: 'omoo_federate.json',
    definition: omooDefinition,
    inputSchema: omooSchema,
  },
  {
    id: 'NlpDopfComponent',
    name: 'NLP DOPF',
    description: 'Optimal Power Flow',
    definitionFile: 'nlpdopf.json',
    definition: nlpdopfDefinition,
    inputSchema: nlpdopfSchema,
  },
  {
    id: 'NlpDsseComponent',
    name: 'NLP DSSE',
    description: 'NLP State Estimator',
    definitionFile: 'nlpdsse.json',
    definition: nlpDsseDefinition,
    inputSchema: nlpDsseSchema,
  },
  {
    id: 'PnnlDopfAdmmComponent',
    name: 'ADMM DOPF',
    description: 'Optimal Power Flow (requires Hub)',
    definitionFile: 'pnnl_dopf_admm.json',
    definition: pnnlDopfAdmmDefinition,
    inputSchema: pnnlDopfAdmmSchema,
  },
  {
    id: 'PnnlHubControlComponent',
    name: 'DOPF Hub Control',
    description: 'Hub for controlling multiple DOPF',
    definitionFile: 'pnnl_hub_control.json',
    definition: pnnlHubControlDefinition,
    inputSchema: pnnlHubControlSchema,
  },
  {
    id: 'PnnlHubVoltageComponent',
    name: 'DOPF Hub Voltage',
    description: 'Hub for splitting voltage',
    definitionFile: 'pnnl_hub_voltage.json',
    definition: pnnlHubVoltageDefinition,
    inputSchema: pnnlHubVoltageSchema,
  },
  {
    id: 'PnnlHubPowerComponent',
    name: 'DOPF Hub Power',
    description: 'Hub for splitting power',
    definitionFile: 'pnnl_hub_power.json',
    definition: pnnlHubPowerDefinition,
    inputSchema: pnnlHubPowerSchema,
  },
]
