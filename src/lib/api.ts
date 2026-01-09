const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001/api'

export interface SavedConfig {
  id: string
  name: string
  description: string
  nodes: any[]
  edges: any[]
  createdAt: string
}

export const api = {
  // Get all templates
  async getTemplates(): Promise<SavedConfig[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/templates`)
      if (!response.ok) {
        throw new Error('Failed to fetch templates')
      }
      return await response.json()
    } catch (error) {
      console.error('Error fetching templates:', error)
      // Fallback to localStorage if API fails
      const localData = localStorage.getItem('flowchartConfigs')
      return localData ? JSON.parse(localData) : []
    }
  },

  // Get a single template by ID
  async getTemplate(id: string): Promise<SavedConfig> {
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
  async saveTemplate(template: SavedConfig): Promise<{ success: boolean; id: string }> {
    try {
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
      const result = await response.json()
      
      // Also save to localStorage as backup
      const localConfigs = JSON.parse(localStorage.getItem('flowchartConfigs') || '[]')
      const existingIndex = localConfigs.findIndex((c: SavedConfig) => c.id === template.id)
      if (existingIndex >= 0) {
        localConfigs[existingIndex] = template
      } else {
        localConfigs.push(template)
      }
      localStorage.setItem('flowchartConfigs', JSON.stringify(localConfigs))
      
      return result
    } catch (error) {
      console.error('Error saving template:', error)
      // Fallback to localStorage if API fails
      const localConfigs = JSON.parse(localStorage.getItem('flowchartConfigs') || '[]')
      const existingIndex = localConfigs.findIndex((c: SavedConfig) => c.id === template.id)
      if (existingIndex >= 0) {
        localConfigs[existingIndex] = template
      } else {
        localConfigs.push(template)
      }
      localStorage.setItem('flowchartConfigs', JSON.stringify(localConfigs))
      return { success: true, id: template.id }
    }
  },

  // Delete a template
  async deleteTemplate(id: string): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/templates/${id}`, {
        method: 'DELETE',
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        const errorMessage = errorData.error || `HTTP ${response.status}: ${response.statusText}`
        console.error('API delete failed:', errorMessage)
        throw new Error(errorMessage)
      }
      
      // Also remove from localStorage as backup
      const localConfigs = JSON.parse(localStorage.getItem('flowchartConfigs') || '[]')
      const filtered = localConfigs.filter((c: SavedConfig) => c.id !== id)
      localStorage.setItem('flowchartConfigs', JSON.stringify(filtered))
    } catch (error) {
      console.error('Error deleting template from API:', error)
      // Fallback to localStorage if API fails
      try {
        const localConfigs = JSON.parse(localStorage.getItem('flowchartConfigs') || '[]')
        const filtered = localConfigs.filter((c: SavedConfig) => c.id !== id)
        localStorage.setItem('flowchartConfigs', JSON.stringify(filtered))
        console.log('Deleted from localStorage as fallback')
        // Don't throw if localStorage fallback succeeds
        return
      } catch (localError) {
        console.error('Error with localStorage fallback:', localError)
        throw error // Re-throw original error if fallback also fails
      }
    }
  },
}

