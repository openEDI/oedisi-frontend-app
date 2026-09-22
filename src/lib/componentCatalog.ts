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

export function makeDefaults(inputSchema: Record<string, unknown>) {
  const props = inputSchema.properties
  if (typeof props === 'object' && props !== null) {
    return Object.fromEntries(
      Object.entries(props)
        .filter(([, value]) => value.default !== undefined)
        .map(([key, value]) => [key, structuredClone(value.default)])
    )
  } else {
    return {}
  }
}
