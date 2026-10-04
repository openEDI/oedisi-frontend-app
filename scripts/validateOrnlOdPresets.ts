import fs from 'node:fs'
import path from 'node:path'

import type { TemplateData } from '@/lib/flowTypes'
import { ORNL_OD_DATASETS } from '@/lib/ornlOdDatasets'
import { toWiringDiagram } from '@/lib/wiringDiagram'

interface RunStatus {
  run_id: string
  status: string
  exit_code?: number
  started_at: string
  ended_at?: string
}

interface ResultManifestEntry {
  id: string
  size_bytes?: number
}

interface ResultPayload {
  data: Array<Record<string, number | string>>
}

const option = (name: string) => {
  const prefix = `--${name}=`
  return process.argv
    .find((arg) => arg.startsWith(prefix))
    ?.slice(prefix.length)
}

const baseUrl = (option('base-url') ?? 'http://127.0.0.1:3001/api').replace(
  /\/$/,
  ''
)
const timeoutMinutes = Number(option('timeout-minutes') ?? 60)
const requestedIds = new Set(
  (option('ids') ?? '')
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean)
)
const presets =
  requestedIds.size > 0
    ? ORNL_OD_DATASETS.filter((preset) => requestedIds.has(preset.id))
    : ORNL_OD_DATASETS

if (presets.length === 0) {
  throw new Error('No ORNL OD presets matched --ids')
}

const sleep = (milliseconds: number) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds))

const requestJson = async <T>(url: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(url, init)
  if (!response.ok) {
    throw new Error(
      `${init?.method ?? 'GET'} ${url}: HTTP ${response.status} ${await response.text()}`
    )
  }
  return (await response.json()) as T
}

const templatePath = path.resolve(
  process.cwd(),
  'data/templates/dev/ornl_od_player_ei20110427.json'
)
const sourceTemplate = JSON.parse(
  fs.readFileSync(templatePath, 'utf8')
) as TemplateData

const runPreset = async (preset: (typeof ORNL_OD_DATASETS)[number]) => {
  const template = structuredClone(sourceTemplate)
  template.name = `ORNL OD preset validation — ${preset.id}`
  const player = template.nodes.find(
    (node) => node.data?.componentType === 'PlayerComponent'
  )
  const od = template.nodes.find(
    (node) => node.data?.componentType === 'ODComponent'
  )
  if (!player?.data || !od?.data) {
    throw new Error(
      'Validation template is missing PlayerComponent or ODComponent'
    )
  }

  player.data.config = {
    ...(player.data.config ?? {}),
    filename: preset.filename,
    data_type: 'MeasurementArray',
    number_of_timesteps: preset.numberOfTimesteps,
    start_time_index: 0,
    run_freq_time_step: 1 / preset.sampleRateHz,
  }
  od.data.config = {
    ...(od.data.config ?? {}),
    sample_rate_hz: preset.sampleRateHz,
    ...preset.od,
  }

  const started = Date.now()
  const { run_id: runId } = await requestJson<{ run_id: string }>(
    `${baseUrl}/runs`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(toWiringDiagram(template)),
    }
  )
  console.log(`[${preset.id}] started ${runId}`)

  let status: RunStatus
  for (;;) {
    status = await requestJson<RunStatus>(`${baseUrl}/runs/${runId}`)
    if (status.status !== 'running') break
    if (Date.now() - started > timeoutMinutes * 60_000) {
      await fetch(`${baseUrl}/runs/${runId}`, { method: 'DELETE' })
      throw new Error(
        `[${preset.id}] exceeded ${timeoutMinutes} minutes and was cancelled`
      )
    }
    await sleep(1_000)
  }

  if (status.status !== 'done' || status.exit_code !== 0) {
    const logs = await Promise.all(
      ['player', 'od', 'recorder_events'].map(async (component) => {
        const response = await fetch(
          `${baseUrl}/runs/${runId}/logs/${component}`
        )
        return response.ok
          ? `${component}:\n${await response.text()}`
          : `${component}: unavailable`
      })
    )
    throw new Error(
      `[${preset.id}] failed with ${status.exit_code}\n${logs.join('\n')}`
    )
  }

  const results = await requestJson<ResultManifestEntry[]>(
    `${baseUrl}/runs/${runId}/results`
  )
  const recorderEvents = results.find(
    (result) => result.id === 'recorder_events'
  )
  if (!recorderEvents) {
    throw new Error(`[${preset.id}] recorder_events output is missing`)
  }
  if (recorderEvents.size_bytes === 0) {
    throw new Error(`[${preset.id}] completed without a detected event`)
  }
  const events = await requestJson<ResultPayload>(
    `${baseUrl}/runs/${runId}/results/recorder_events`
  )
  if (events.data.length === 0) {
    throw new Error(`[${preset.id}] completed without a detected event`)
  }

  let closestFrequencyError: number | undefined
  if (preset.dominantFrequencyHz !== undefined) {
    const frequencies = events.data
      .map((event) => Number(event.mode_0_freq_hz))
      .filter(Number.isFinite)
    closestFrequencyError = Math.min(
      ...frequencies.map((frequency) =>
        Math.abs(frequency - preset.dominantFrequencyHz!)
      )
    )
    const tolerance = Math.max(0.05, preset.dominantFrequencyHz * 0.25)
    if (
      !Number.isFinite(closestFrequencyError) ||
      closestFrequencyError > tolerance
    ) {
      throw new Error(
        `[${preset.id}] closest dominant-frequency error ${closestFrequencyError} exceeds ${tolerance}`
      )
    }
  }

  const report = await requestJson<{ usecase: string; engine: string }>(
    `${baseUrl}/runs/${runId}/report`,
    { method: 'POST' }
  )
  if (report.usecase !== 'od') {
    throw new Error(
      `[${preset.id}] generated unexpected ${report.usecase} report`
    )
  }

  const elapsedSeconds = (Date.now() - started) / 1_000
  const summary = {
    preset: preset.id,
    run_id: runId,
    elapsed_seconds: Number(elapsedSeconds.toFixed(1)),
    detected_events: events.data.length,
    closest_frequency_error_hz:
      closestFrequencyError === undefined
        ? undefined
        : Number(closestFrequencyError.toFixed(4)),
    report_engine: report.engine,
  }
  console.log(JSON.stringify(summary))
  return summary
}

const summaries = []
for (const preset of presets) {
  summaries.push(await runPreset(preset))
}

console.log(
  JSON.stringify({ base_url: baseUrl, validated: summaries }, null, 2)
)
