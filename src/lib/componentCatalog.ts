import componentCatalogJSON from '@/lib/catalog.json'

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

export const COMPONENT_CATALOG: ComponentDefinition[] = componentCatalogJSON
/*
[
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
  {
    id: 'EVCSComponent',
    name: 'ORNL EV Scheduler',
    description: 'PSO-based EV charging optimization',
    definitionFile: 'ornl_ev_pso.json',
    definition: ornlEvPsoDefinition,
    inputSchema: ornlEvPsoSchema,
  },
  {
    id: 'DOPFPSOComponent',
    name: 'ORNL DOPF (PSO)',
    description: 'Distribution OPF via Particle Swarm Optimization',
    definitionFile: 'ornl_dopf_pso.json',
    definition: ornlDopfPsoDefinition,
    inputSchema: ornlDopfPsoSchema,
  },
  {
    id: 'DSSEGNWLSComponent',
    name: 'ORNL DSSE (GN-WLS)',
    description: 'Distribution state estimation via Gauss-Newton WLS',
    definitionFile: 'ornl_dsse_gnwls.json',
    definition: ornlDsseGnwlsDefinition,
    inputSchema: ornlDsseGnwlsSchema,
  },
]
*/
