export interface ComponentDefinition {
  id: string
  name: string
  description: string
}

export const COMPONENT_CATALOG: ComponentDefinition[] = [
  {
    id: 'feeder',
    name: 'Feeder',
    description: 'OpenDSS simulation engine',
  },
  {
    id: 'wls_se_algorihtm',
    name: 'State Estimator',
    description: 'WSL State Estimator',
  },
  {
    id: 'sensor',
    name: 'Sensor',
    description: 'Sensor model',
  },
  {
    id: 'recorder',
    name: 'Recorder',
    description: 'Records simulation results',
  },
]