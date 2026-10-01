import { type TemplateData } from './flowTypes'
import { type WiringDiagram } from './wiringDiagram'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

export interface RunSummary {
  run_id: string
  name: string
  status: 'running' | 'done' | 'failed' | 'unknown'
  started_at: string
  ended_at?: string
  template_id: string | null
  exit_code?: number
  run_dir: string
}

export interface ResultEntry {
  id: string
  label: string
  type: string
  size_bytes: number
  quantity?: OutputAnnotation
}

export type ModelStatus = 'converting' | 'ready' | 'ready_with_warnings' | 'failed'

export interface ModelFile {
  path: string
  size_bytes: number
}

export interface ModelSummary {
  name: string
  uuid: string
  description: string
  source_of_truth?: 'opendss' | string
  total_components: number
  element_count?: number
  bus_count?: number
  element_types?: Record<string, number>
  component_types: Record<string, number>
  topology_nodes: number
  topology_edges: number
}

export interface ManagedModel {
  id: string
  name: string
  description: string
  domain: string
  source_format: string
  status: ModelStatus
  created_at: string
  updated_at: string
  source: {
    original_filename: string
    files: ModelFile[]
    sha256: string
  }
  conversion: {
    format: string
    reader: string
    entrypoint: string | null
    source_files: string[]
    load_model_ids: string[]
    warnings: string[]
    reason: string
    requested_format: string
    original_filename: string
    artifact_format: string
    artifact_entrypoint: string
  }
  artifacts: Record<string, {
    format: string
    entrypoint: string
    files: ModelFile[]
    profiles_available?: boolean
  }>
  inspection_summary: ModelSummary
}

export interface ModelElement {
  id: string
  name: string
  class: string
  enabled: boolean
  num_phases: number
  num_terminals: number
  bus_names: string[]
  properties: Record<string, unknown>
  powers: number[]
  losses: number[]
  voltages_mag_angle: number[]
}

export interface ModelBus {
  id: string
  name: string
  nodes: number[]
  kv_base?: number
  x?: number
  y?: number
  voltage_mag_angle: number[]
  pu_voltage_mag_angle: number[]
  pde_elements: string[]
  pce_elements: string[]
}

export interface ModelComponent {
  _type?: string
  uuid?: string
  name?: string
  [key: string]: unknown
}

export interface ModelTopology {
  nodes: Array<{ id: string; [key: string]: unknown }>
  edges: Array<{ source: string; target: string; [key: string]: unknown }>
}

export interface ModelGeoJson {
  type: 'FeatureCollection'
  coordinate_reference_system?: string
  features: Array<{
    type: 'Feature'
    geometry: { type: string; coordinates: unknown }
    properties?: Record<string, unknown>
  }>
}

export type ModelSensorConfig = Record<'voltage' | 'real_power' | 'reactive_power', string[]>

export interface ModelInspection {
  source_of_truth?: 'opendss' | string
  format?: string
  entrypoint?: string
  summary: ModelSummary
  buses: ModelBus[]
  elements: ModelElement[]
  topology: ModelTopology
  geojson: ModelGeoJson
  sensors?: ModelSensorConfig
  physics: {
    solution: Record<string, unknown>
    circuit: Record<string, unknown>
  }
}

export class StartError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'StartError'
    this.status = status
  }
}

export interface Topology {
  base_voltage_magnitudes: {
    ids: string[]
    values: number[]
  }
}

export interface OutputAnnotation {
  type?: string
  unit?: string
  source?: string
  source_port?: string
}

export const api = {
  // Get all templates
  async getTemplates(): Promise<TemplateData[]> {
    const response = await fetch(`${API_BASE_URL}/templates`)
    if (!response.ok) {
      throw new Error('Failed to fetch templates')
    }
    return await response.json()
  },

  // Get a single template by ID
  async getTemplate(id: string): Promise<TemplateData> {
    try {
      const response = await fetch(`${API_BASE_URL}/templates/${id}`)
      if (!response.ok) {
        throw new Error('Failed to fetch template')
      }
      return await response.json()
    } catch (error) {
      console.error('Error fetching template:', error)
      throw error
    }
  },

  // Save a template
  async saveTemplate(
    template: TemplateData
  ): Promise<{ success: boolean; id: string }> {
    const response = await fetch(`${API_BASE_URL}/templates`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(template),
    })
    if (!response.ok) {
      throw new Error('Failed to save template')
    }

    return await response.json()
  },

  // Delete a template
  async deleteTemplate(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/templates/${id}`, {
      method: 'DELETE',
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const errorMessage =
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      throw new Error(errorMessage)
    }
  },

  async listModels(): Promise<ManagedModel[]> {
    const response = await fetch(`${API_BASE_URL}/models`)
    if (!response.ok) {
      throw new Error('Failed to fetch models')
    }
    return await response.json()
  },

  async uploadModel(
    file: File,
    options: {
      name?: string
      description?: string
      inputFormat?: string
      loadModelId?: string
      crs?: string
    } = {}
  ): Promise<ManagedModel> {
    const form = new FormData()
    form.append('file', file)
    if (options.name) form.append('name', options.name)
    if (options.description) form.append('description', options.description)
    form.append('input_format', options.inputFormat || 'auto')
    if (options.loadModelId) form.append('load_model_id', options.loadModelId)
    if (options.crs) form.append('crs', options.crs)
    const response = await fetch(`${API_BASE_URL}/models/upload`, {
      method: 'POST',
      body: form,
    })
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const detail = errorData.detail
      const errorMessage = typeof detail === 'string'
        ? detail
        : detail?.message || `HTTP ${response.status}: ${response.statusText}`
      const error = new Error(errorMessage) as Error & { detail?: unknown }
      error.detail = detail
      throw error
    }
    return await response.json()
  },

  async getModel(id: string): Promise<ManagedModel> {
    const response = await fetch(`${API_BASE_URL}/models/${encodeURIComponent(id)}`)
    if (!response.ok) throw new Error('Failed to fetch model')
    return await response.json()
  },

  async updateModel(id: string, payload: { name?: string; description?: string }): Promise<ManagedModel> {
    const response = await fetch(`${API_BASE_URL}/models/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!response.ok) throw new Error('Failed to update model')
    return await response.json()
  },

  async deleteModel(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/models/${encodeURIComponent(id)}`, { method: 'DELETE' })
    if (!response.ok) throw new Error('Failed to delete model')
  },

  async getModelInspection(id: string): Promise<ModelInspection> {
    const response = await fetch(`${API_BASE_URL}/models/${encodeURIComponent(id)}/inspection`)
    if (!response.ok) throw new Error('Failed to inspect model')
    return await response.json()
  },

  async getModelComponents(
    id: string,
    options: { search?: string; componentType?: string; offset?: number; limit?: number } = {}
  ): Promise<{ items: ModelComponent[]; total: number; offset: number; limit: number }> {
    const params = new URLSearchParams()
    if (options.search) params.set('search', options.search)
    if (options.componentType) params.set('component_type', options.componentType)
    if (options.offset !== undefined) params.set('offset', String(options.offset))
    if (options.limit !== undefined) params.set('limit', String(options.limit))
    const suffix = params.toString() ? `?${params.toString()}` : ''
    const response = await fetch(`${API_BASE_URL}/models/${encodeURIComponent(id)}/components${suffix}`)
    if (!response.ok) throw new Error('Failed to fetch model components')
    return await response.json()
  },

  async getModelTopology(id: string): Promise<ModelTopology> {
    const response = await fetch(`${API_BASE_URL}/models/${encodeURIComponent(id)}/topology`)
    if (!response.ok) throw new Error('Failed to fetch model topology')
    return await response.json()
  },

  async getModelSensors(id: string): Promise<ModelSensorConfig> {
    const response = await fetch(`${API_BASE_URL}/models/${encodeURIComponent(id)}/sensors`)
    if (!response.ok) throw new Error('Failed to fetch model sensors')
    return await response.json()
  },

  async saveModelSensors(id: string, config: ModelSensorConfig): Promise<ModelSensorConfig> {
    const response = await fetch(`${API_BASE_URL}/models/${encodeURIComponent(id)}/sensors`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    })
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data?.detail?.message || data?.detail || 'Failed to save model sensors')
    }
    return await response.json()
  },

  async uploadModelSensorFile(
    id: string,
    file: File,
    sensorType: keyof ModelSensorConfig,
  ): Promise<ModelSensorConfig> {
    const form = new FormData()
    form.append('file', file)
    form.append('sensor_type', sensorType)
    const response = await fetch(`${API_BASE_URL}/models/${encodeURIComponent(id)}/sensors/upload`, {
      method: 'POST',
      body: form,
    })
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data?.detail?.message || data?.detail || 'Failed to upload sensor file')
    }
    return await response.json()
  },

  modelSourceDownloadUrl(id: string): string {
    return `${API_BASE_URL}/models/${encodeURIComponent(id)}/source/download`
  },

  modelOpenDssDownloadUrl(id: string): string {
    return `${API_BASE_URL}/models/${encodeURIComponent(id)}/artifacts/opendss/download`
  },

  async startRun(
    wiringDiagram: WiringDiagram,
    templateId?: string
  ): Promise<{ run_id: string }> {
    const response = await fetch(
      `${API_BASE_URL}/runs${templateId ? '?template_id=' + encodeURIComponent(templateId) : ''}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(wiringDiagram),
      }
    )
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const errorMessage =
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      throw new StartError(response.status, errorMessage)
    }

    return await response.json()
  },
  async runStatus(run_id: string): Promise<RunSummary> {
    const response = await fetch(`${API_BASE_URL}/runs/${run_id}`, {
      method: 'GET',
    })
    if (!response.ok) {
      throw new Error('Failed to get run')
    }

    return await response.json()
  },
  async listRuns(): Promise<RunSummary[]> {
    const response = await fetch(`${API_BASE_URL}/runs`, {
      method: 'GET',
    })
    if (!response.ok) {
      throw new Error('Failed to list runs')
    }

    return await response.json()
  },
  async cancelRun(run_id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/runs/${run_id}`, {
      method: 'DELETE',
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const errorMessage =
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      throw new Error(errorMessage)
    }
  },
  async runLog(run_id: string, component: string): Promise<string> {
    const response = await fetch(
      `${API_BASE_URL}/runs/${run_id}/logs/${encodeURIComponent(component)}`,
      {
        method: 'GET',
      }
    )

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const errorMessage =
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      throw new Error(errorMessage)
    }
    return await response.text()
  },
  runDownloadUrl(run_id: string): string {
    return `${API_BASE_URL}/runs/${run_id}/download`
  },
  async getWiring(run_id: string): Promise<WiringDiagram> {
    const response = await fetch(`${API_BASE_URL}/runs/${run_id}/wiring`, {
      method: 'GET',
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const errorMessage =
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      throw new Error(errorMessage)
    }
    return await response.json()
  },
  async listResults(run_id: string): Promise<ResultEntry[]> {
    const response = await fetch(`${API_BASE_URL}/runs/${run_id}/results`, {
      method: 'GET',
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const errorMessage =
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      throw new Error(errorMessage)
    }
    return await response.json()
  },
  async getResult(
    run_id: string,
    dataset_id: string
  ): Promise<{
    columns: string[]
    data: Array<Record<string, number | string>>
  }> {
    const response = await fetch(
      `${API_BASE_URL}/runs/${run_id}/results/${encodeURIComponent(dataset_id)}`,
      {
        method: 'GET',
      }
    )

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const errorMessage =
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      throw new Error(errorMessage)
    }
    return await response.json()
  },
  async getMetrics(
    run_id: string,
    primary: string,
    comparison: string
  ): Promise<{
    metric: string
    columns: string[]
    data: Array<{ time: string; value: number }>
  }> {
    const response = await fetch(
      `${API_BASE_URL}/runs/${run_id}/metrics?primary=${encodeURIComponent(primary)}&comparison=${encodeURIComponent(comparison)}`,
      {
        method: 'GET',
      }
    )

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const errorMessage =
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      throw new Error(errorMessage)
    }
    return await response.json()
  },
  async getTopology(run_id: string): Promise<Topology | null> {
    const response = await fetch(`${API_BASE_URL}/runs/${run_id}/topology`, {
      method: 'GET',
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const errorMessage =
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      throw new Error(errorMessage)
    }
    return await response.json()
  },
  async createNotebook(
    run_id: string
  ): Promise<{ exists: boolean; created: boolean; jupyter_url: string }> {
    const response = await fetch(
      `${API_BASE_URL}/runs/${run_id}/notebook`,
      { method: 'POST' }
    )
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const errorMessage =
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      throw new Error(errorMessage)
    }
    return await response.json()
  },
  async getNotebookStatus(
    run_id: string
  ): Promise<{ exists: boolean; jupyter_url: string }> {
    const response = await fetch(
      `${API_BASE_URL}/runs/${run_id}/notebook`,
      { method: 'GET' }
    )
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const errorMessage =
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      throw new Error(errorMessage)
    }
    return await response.json()
  },
  async deleteNotebook(run_id: string): Promise<void> {
    const response = await fetch(
      `${API_BASE_URL}/runs/${run_id}/notebook`,
      { method: 'DELETE' }
    )
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const errorMessage =
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      throw new Error(errorMessage)
    }
  },
  async saveNotebookToTemplate(
    run_id: string
  ): Promise<{ success: boolean; template_id: string }> {
    const response = await fetch(
      `${API_BASE_URL}/runs/${run_id}/notebook/save-to-template`,
      { method: 'POST' }
    )
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const errorMessage =
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      throw new Error(errorMessage)
    }
    return await response.json()
  },
  async createTemplateNotebook(
    templateId: string
  ): Promise<{ exists: boolean; created: boolean; jupyter_url: string }> {
    const response = await fetch(
      `${API_BASE_URL}/templates/${templateId}/notebook`,
      { method: 'POST' }
    )
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const errorMessage =
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      throw new Error(errorMessage)
    }
    return await response.json()
  },
  async getTemplateNotebookStatus(
    templateId: string
  ): Promise<{ exists: boolean; jupyter_url: string }> {
    const response = await fetch(
      `${API_BASE_URL}/templates/${templateId}/notebook`,
      { method: 'GET' }
    )
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const errorMessage =
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      throw new Error(errorMessage)
    }
    return await response.json()
  },
  async deleteTemplateNotebook(templateId: string): Promise<void> {
    const response = await fetch(
      `${API_BASE_URL}/templates/${templateId}/notebook`,
      { method: 'DELETE' }
    )
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const errorMessage =
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      throw new Error(errorMessage)
    }
  },
}
