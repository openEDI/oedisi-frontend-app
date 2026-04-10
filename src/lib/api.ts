import { TemplateData } from './flowTypes'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001/api'

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
    template: TemplateData,
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
        errorData.error || `HTTP ${response.status}: ${response.statusText}`
      throw new Error(errorMessage)
    }
  },
}
