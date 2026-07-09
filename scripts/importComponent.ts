import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

// Define helper to get current dir when using ESM modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

interface ComponentNames {
  camelCaseName: string;
  pascalName: string;
  componentId: string;
}

interface ComponentMapping {
  targetName: string;
  componentId: string;
  displayName: string;
  description: string;
}

// Maps component folders under OEDISI_COMPONENTS to their expected frontend configurations
const COMPONENT_MAPPINGS: Record<string, ComponentMapping> = {
  'LocalFeeder': {
    targetName: 'feeder',
    componentId: 'Feeder',
    displayName: 'Feeder',
    description: 'OpenDSS simulation engine',
  },
  'wls_federate': {
    targetName: 'wls_federate',
    componentId: 'StateEstimatorComponent',
    displayName: 'State Estimator',
    description: 'WLS state estimator',
  },
  'lindistflow_federate': {
    targetName: 'lin_dist_flow_algorithm',
    componentId: 'LinDistFlowComponent',
    displayName: 'LinDistFlow Algorithm',
    description: 'LinDistFlow optimization algorithm',
  },
  'measuring_federate': {
    targetName: 'sensor',
    componentId: 'MeasurementComponent',
    displayName: 'Sensor',
    description: 'Sensor model',
  },
  'recorder': {
    targetName: 'recorder',
    componentId: 'Recorder',
    displayName: 'Recorder',
    description: 'Records simulation results',
  },
  'omoo_federate': {
    targetName: 'omoo_federate',
    componentId: 'OMOOComponent',
    displayName: 'OMOO',
    description: 'Optimal Power Flow',
  },
  'nlpdopf': {
    targetName: 'nlpdopf',
    componentId: 'NlpDopfComponent',
    displayName: 'NLP DOPF',
    description: 'Optimal Power Flow',
  },
  'nlpdsse': {
    targetName: 'nlpdsse',
    componentId: 'NlpDsseComponent',
    displayName: 'NLP State Estimator',
    description: 'NLP State Estimator',
  },
  'ornl-ev-pso': {
    targetName: 'ornl_ev_pso',
    componentId: 'EVCSComponent',
    displayName: 'ORNL EV Scheduler',
    description: 'PSO-based EV charging optimization',
  },
  'ornl-dopf-pso': {
    targetName: 'ornl_dopf_pso',
    componentId: 'DOPFPSOComponent',
    displayName: 'ORNL DOPF (PSO)',
    description: 'Distribution OPF via Particle Swarm Optimization',
  },
  'ornl-dsse-gnwls': {
    targetName: 'ornl_dsse_gnwls',
    componentId: 'DSSEGNWLSComponent',
    displayName: 'ORNL DSSE (GN-WLS)',
    description: 'Distribution state estimation via Gauss-Newton WLS',
  },
  'pnnl-dopf-admm': {
    targetName: 'pnnl_dopf_admm',
    componentId: 'PnnlDopfAdmmComponent',
    displayName: 'ADMM DOPF',
    description: 'Optimal Power Flow (requires Hub)',
  },
  'pnnl-hub-control': {
    targetName: 'pnnl_hub_control',
    componentId: 'PnnlHubControlComponent',
    displayName: 'DOPF Hub Control',
    description: 'Hub for controlling multiple DOPF',
  },
  'pnnl-hub-power': {
    targetName: 'pnnl_hub_power',
    componentId: 'PnnlHubPowerComponent',
    displayName: 'DOPF Hub Power',
    description: 'Hub for splitting power',
  },
  'pnnl-hub-voltage': {
    targetName: 'pnnl_hub_voltage',
    componentId: 'PnnlHubVoltageComponent',
    displayName: 'DOPF Hub Voltage',
    description: 'Hub for splitting voltage',
  },
  'pnnl-dsse-ekf': {
    targetName: 'pnnl_dsse_ekf',
    componentId: 'PnnlDsseEkfComponent',
    displayName: 'PNNL DSSE EKF',
    description: 'PNNL DSSE EKF component',
  },
  'pnnl-emt-swod': {
    targetName: 'pnnl_emt_swod',
    componentId: 'PnnlEmtSwodComponent',
    displayName: 'PNNL EMT SWOD',
    description: 'PNNL EMT SWOD component',
  },
  'player': {
    targetName: 'player',
    componentId: 'PlayerComponent',
    displayName: 'Player',
    description: 'Player component',
  },
};

/**
 * Generates consistent component names and IDs from a base name.
 */
function generateComponentNames(baseName: string): ComponentNames {
  const camelCaseName = baseName.replace(/[-_]([a-z])/g, (_, g) => g.toUpperCase()).replace(/[-_]/g, '');
  const pascalName = camelCaseName.charAt(0).toUpperCase() + camelCaseName.slice(1);
  const componentId = pascalName.endsWith('Component') ? pascalName : `${pascalName}Component`;
  return { camelCaseName, pascalName, componentId };
}

/**
 * Generates a user-friendly display name from a folder name.
 */
function generateDisplayName(folderName: string): string {
  const UPPERCASE_WORDS = ['pnnl', 'ornl', 'ev', 'dopf', 'pso', 'dsse', 'wls', 'nlp', 'admm', 'emt', 'swod'];
  return folderName
    .split(/[-_]/)
    .map(word => {
      const upper = word.toLowerCase();
      if (UPPERCASE_WORDS.includes(upper)) {
        return word.toUpperCase();
      }
      return word.charAt(0).toUpperCase() + word.slice(1);
    })
    .join(' ');
}

/**
 * Retrieves baseName, componentId, displayName, and description for a component folder.
 */
export function getComponentInfo(folderName: string, customTargetName?: string) {
  const mapping = COMPONENT_MAPPINGS[folderName];
  if (mapping && !customTargetName) {
    return {
      baseName: mapping.targetName,
      componentId: mapping.componentId,
      displayName: mapping.displayName,
      description: mapping.description,
    };
  }

  const baseName = customTargetName || folderName.replace(/-/g, '_');
  const { componentId } = generateComponentNames(baseName);
  const displayName = generateDisplayName(folderName);
  return {
    baseName,
    componentId,
    displayName,
    description: `${displayName} component`,
  };
}

/**
 * Safely removes any existing registration (imports and catalog entry) for a component.
 */
function removeExistingRegistration(content: string, baseName: string, componentId: string, folderName: string): string {
  const camelCaseName = baseName.replace(/[-_]([a-z])/g, (_, g) => g.toUpperCase()).replace(/[-_]/g, '');
  
  // 1. Remove imports matching the variable names
  const varDefRegex = new RegExp(`import\\s+${camelCaseName}Definition\\s+from\\s+['"].*?['"]\\s*;?\\n?`, 'g');
  const varSchemaRegex = new RegExp(`import\\s+${camelCaseName}Schema\\s+from\\s+['"].*?['"]\\s*;?\\n?`, 'g');
  let cleanContent = content.replace(varDefRegex, '').replace(varSchemaRegex, '');

  // 2. Remove imports matching the filenames (baseName or folderName)
  const pathDefRegex = new RegExp(`import\\s+\\w+Definition\\s+from\\s+['"]@/lib/definitions/(${baseName}|${folderName})\\.json['"]\\s*;?\\n?`, 'g');
  const pathSchemaRegex = new RegExp(`import\\s+\\w+Schema\\s+from\\s+['"]@/lib/schemas/(${baseName}|${folderName})\\.json['"]\\s*;?\\n?`, 'g');
  cleanContent = cleanContent.replace(pathDefRegex, '').replace(pathSchemaRegex, '');

  // 3. Remove existing catalog entry in COMPONENT_CATALOG if it exists
  const catalogStart = cleanContent.indexOf('export const COMPONENT_CATALOG');
  if (catalogStart !== -1) {
    const catalogEnd = cleanContent.lastIndexOf(']');
    if (catalogEnd > catalogStart) {
      const catalogSegment = cleanContent.substring(catalogStart, catalogEnd);
      
      // Match each object in the catalog array
      const entryRegex = /\{\s*[\s\S]*?\}\s*,?/g;
      let match;
      let targetEntry = '';
      
      while ((match = entryRegex.exec(catalogSegment)) !== null) {
        const entryStr = match[0];
        if (
          entryStr.includes(`definitionFile: '${baseName}.json'`) || 
          entryStr.includes(`definitionFile: "${baseName}.json"`) ||
          entryStr.includes(`definitionFile: '${folderName}.json'`) || 
          entryStr.includes(`definitionFile: "${folderName}.json"`) ||
          entryStr.includes(`id: '${componentId}'`) ||
          entryStr.includes(`id: "${componentId}"`)
        ) {
          targetEntry = entryStr;
          break;
        }
      }
      
      if (targetEntry) {
        const entryIndexInFull = catalogStart + catalogSegment.indexOf(targetEntry);
        cleanContent = cleanContent.substring(0, entryIndexInFull) + cleanContent.substring(entryIndexInFull + targetEntry.length);
      }
    }
  }
  return cleanContent;
}

/**
 * Registers the imported component in componentCatalog.ts
 */
function registerInCatalog(
  baseName: string,
  folderName: string,
  componentId: string,
  displayName: string,
  description: string
): void {
  const projectRoot = path.resolve(__dirname, '..');
  const catalogPath = path.join(projectRoot, 'src', 'lib', 'componentCatalog.ts');

  if (!fs.existsSync(catalogPath)) {
    console.warn(`Warning: componentCatalog.ts not found at ${catalogPath}. Skipping auto-registration.`);
    return;
  }

  let content = fs.readFileSync(catalogPath, 'utf-8');

  // Replace existing registration if it already exists
  content = removeExistingRegistration(content, baseName, componentId, folderName);

  const camelCaseName = baseName.replace(/[-_]([a-z])/g, (_, g) => g.toUpperCase()).replace(/[-_]/g, '');

  // 1. Insert imports before "export interface FederateDefinition"
  const importTarget = 'export interface FederateDefinition';
  const importIndex = content.indexOf(importTarget);
  if (importIndex === -1) {
    throw new Error(`Could not find insertion point "${importTarget}" in componentCatalog.ts`);
  }

  const newImports = `import ${camelCaseName}Definition from '@/lib/definitions/${baseName}.json'\nimport ${camelCaseName}Schema from '@/lib/schemas/${baseName}.json'\n`;
  content = content.slice(0, importIndex) + newImports + content.slice(importIndex);

  // 2. Insert catalog entry before the last ']' closing the array
  const lastBracketIndex = content.lastIndexOf(']');
  if (lastBracketIndex === -1) {
    throw new Error('Could not find closing bracket "]" for COMPONENT_CATALOG array in componentCatalog.ts');
  }

  const newEntry = `  {\n    id: '${componentId}',\n    name: '${displayName}',\n    description: '${description}',\n    definitionFile: '${baseName}.json',\n    definition: ${camelCaseName}Definition,\n    inputSchema: ${camelCaseName}Schema,\n  },\n`;
  
  content = content.slice(0, lastBracketIndex) + newEntry + content.slice(lastBracketIndex);

  fs.writeFileSync(catalogPath, content, 'utf-8');
  console.log(`Successfully registered "${componentId}" in componentCatalog.ts`);
}

/**
 * Registers the imported component in server/components.json
 */
function registerInServerComponents(
  componentId: string,
  definitionPath: string,
  oedisiComponentsDir: string
): void {
  const projectRoot = path.resolve(__dirname, '..');
  const serverComponentsPath = path.join(projectRoot, 'server', 'components.json');

  if (!fs.existsSync(serverComponentsPath)) {
    console.warn(`Warning: server/components.json not found at ${serverComponentsPath}. Skipping backend registration.`);
    return;
  }

  const content = fs.readFileSync(serverComponentsPath, 'utf-8');
  let json: Record<string, string>;
  try {
    json = JSON.parse(content);
  } catch (err) {
    throw new Error(`Failed to parse server/components.json: ${err}`);
  }

  const relDefPath = path.relative(oedisiComponentsDir, definitionPath);
  const mappingValue = `\${OEDISI_COMPONENTS}/${relDefPath}`;

  if (json[componentId] === mappingValue) {
    console.log(`Component "${componentId}" is already mapped in server/components.json.`);
    return;
  }

  json[componentId] = mappingValue;
  fs.writeFileSync(serverComponentsPath, JSON.stringify(json, null, 4) + '\n', 'utf-8');
  console.log(`Successfully registered "${componentId}" mapping in server/components.json`);
}

/**
 * Recursively searches for a file within a directory.
 */
function findFile(dir: string, fileName: string): string | null {
  const filePath = path.join(dir, fileName);
  if (fs.existsSync(filePath)) {
    return filePath;
  }
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.isDirectory() && entry.name !== '.git' && entry.name !== 'node_modules') {
      const found = findFile(path.join(dir, entry.name), fileName);
      if (found) return found;
    }
  }
  return null;
}

/**
 * Imports a component's definition and schema from OEDISI_COMPONENTS.
 * @param folderName The folder name under OEDISI_COMPONENTS (e.g. 'pnnl-dsse-ekf')
 * @param targetName The target base name for the JSON files (defaults to folderName with '-' replaced by '_')
 */
export function importComponent(folderName: string, targetName?: string): void {
  // 1. Check for OEDISI_COMPONENTS environment variable
  const oedisiComponentsDir = process.env.OEDISI_COMPONENTS;
  if (!oedisiComponentsDir) {
    console.error('\nError: The OEDISI_COMPONENTS environment variable is not set.');
    console.error('Please set it to the path of your OEDISI components directory.');
    console.error('Example: export OEDISI_COMPONENTS="$HOME/dev/oedisi-components/Components"\n');
    throw new Error('OEDISI_COMPONENTS environment variable is not set.');
  }

  if (!fs.existsSync(oedisiComponentsDir)) {
    throw new Error(`OEDISI_COMPONENTS directory not found at: ${oedisiComponentsDir}`);
  }

  const componentSourceDir = path.join(oedisiComponentsDir, folderName);
  if (!fs.existsSync(componentSourceDir)) {
    throw new Error(`Component folder not found: ${componentSourceDir}`);
  }

  // Get component info from mappings or dynamic generation
  const info = getComponentInfo(folderName, targetName);
  const baseName = info.baseName;
  const componentId = info.componentId;
  const displayName = info.displayName;
  const description = info.description;

  // 3. Locate component_definition.json and schema.json
  let definitionPath = path.join(componentSourceDir, 'component_definition.json');
  let schemaPath = path.join(componentSourceDir, 'schema.json');

  if (!fs.existsSync(definitionPath)) {
    const found = findFile(componentSourceDir, 'component_definition.json');
    if (found) definitionPath = found;
  }
  if (!fs.existsSync(schemaPath)) {
    const found = findFile(componentSourceDir, 'schema.json');
    if (found) schemaPath = found;
  }

  if (!fs.existsSync(definitionPath)) {
    throw new Error(`component_definition.json not found in component directory: ${componentSourceDir}`);
  }
  if (!fs.existsSync(schemaPath)) {
    throw new Error(`schema.json not found in component directory: ${componentSourceDir}`);
  }

  // Define destination paths relative to project root
  const projectRoot = path.resolve(__dirname, '..');
  const definitionsDir = path.join(projectRoot, 'src', 'lib', 'definitions');
  const schemasDir = path.join(projectRoot, 'src', 'lib', 'schemas');

  // Ensure directories exist
  if (!fs.existsSync(definitionsDir)) {
    fs.mkdirSync(definitionsDir, { recursive: true });
  }
  if (!fs.existsSync(schemasDir)) {
    fs.mkdirSync(schemasDir, { recursive: true });
  }

  const destDefinitionPath = path.join(definitionsDir, `${baseName}.json`);
  const destSchemaPath = path.join(schemasDir, `${baseName}.json`);

  // Copy files
  fs.copyFileSync(definitionPath, destDefinitionPath);
  fs.copyFileSync(schemaPath, destSchemaPath);

  console.log(`Successfully imported component "${folderName}":`);
  console.log(`  - Definition copied to: ${path.relative(projectRoot, destDefinitionPath)}`);
  console.log(`  - Schema copied to:     ${path.relative(projectRoot, destSchemaPath)}`);

  // Register in component catalog
  registerInCatalog(baseName, folderName, componentId, displayName, description);

  // Register in server components mapping
  registerInServerComponents(componentId, definitionPath, oedisiComponentsDir);
}

/**
 * Scans the OEDISI_COMPONENTS directory and imports/syncs all components.
 */
export function importAllComponents(): void {
  const oedisiComponentsDir = process.env.OEDISI_COMPONENTS;
  if (!oedisiComponentsDir) {
    console.error('\nError: The OEDISI_COMPONENTS environment variable is not set.');
    console.error('Please set it to the path of your OEDISI components directory.');
    console.error('Example: export OEDISI_COMPONENTS="$HOME/dev/oedisi-components/Components"\n');
    throw new Error('OEDISI_COMPONENTS environment variable is not set.');
  }

  if (!fs.existsSync(oedisiComponentsDir)) {
    throw new Error(`OEDISI_COMPONENTS directory not found at: ${oedisiComponentsDir}`);
  }

  const entries = fs.readdirSync(oedisiComponentsDir, { withFileTypes: true });
  const imported: string[] = [];
  const failed: string[] = [];

  for (const entry of entries) {
    if (entry.isDirectory() && entry.name !== '.git' && entry.name !== 'node_modules' && entry.name !== 'broker') {
      const folderName = entry.name;
      const componentSourceDir = path.join(oedisiComponentsDir, folderName);
      
      const hasDefinition = fs.existsSync(path.join(componentSourceDir, 'component_definition.json')) || 
                            findFile(componentSourceDir, 'component_definition.json') !== null;
      const hasSchema = fs.existsSync(path.join(componentSourceDir, 'schema.json')) || 
                        findFile(componentSourceDir, 'schema.json') !== null;

      if (hasDefinition && hasSchema) {
        try {
          console.log(`\nSyncing component: ${folderName}...`);
          importComponent(folderName);
          imported.push(folderName);
        } catch (err: unknown) {
          const errMsg = err instanceof Error ? err.message : String(err);
          console.error(`Failed to sync component "${folderName}": ${errMsg}`);
          failed.push(folderName);
        }
      }
    }
  }

  console.log('\n--- Component Sync Summary ---');
  console.log(`Successfully synced: ${imported.join(', ') || 'none'}`);
  if (failed.length > 0) {
    console.log(`Failed to sync: ${failed.join(', ')}`);
  }
}

// Allow running this script directly from the CLI
const isDirectRun = process.argv[1] && (
  process.argv[1] === __filename || 
  process.argv[1].endsWith('importComponent.ts') ||
  process.argv[1].endsWith('import-component.ts')
);

if (isDirectRun) {
  const args = process.argv.slice(2);
  if (args.includes('--all') || args.includes('-a')) {
    try {
      importAllComponents();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : String(error);
      console.error(`Import all failed: ${message}`);
      process.exit(1);
    }
  } else {
    if (args.length === 0) {
      console.error('Usage:');
      console.error('  npx tsx scripts/importComponent.ts <component-folder-name> [custom-target-name]');
      console.error('  npx tsx scripts/importComponent.ts --all');
      process.exit(1);
    }
    
    try {
      importComponent(args[0], args[1]);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : String(error);
      console.error(`Import failed: ${message}`);
      process.exit(1);
    }
  }
}
