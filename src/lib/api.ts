import { type TemplateData } from './flowTypes'
import { type WiringDiagram } from './wiringDiagram'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001/api'

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
      throw new Error(errorMessage)
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
}
