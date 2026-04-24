<template>
  <div class="min-h-screen p-8">
    <div class="max-w-6xl mx-auto space-y-8">
      <router-link to="/"
        class="text-primary hover:text-primary/80 mb-4 inline-block">← Back to
        Home</router-link>
      <h1 class="text-3xl font-bold mb-2">Simulation Status</h1>
      <div class="flex items-center gap-3">
        <h3
          class="block rounded-sm bg-muted/80 px-2.5 py-1.5 text-lg font-semibold">
          {{ runName }}
        </h3>
        <StatusBadge :status="status" />
        <span v-if="exitCode !== null"
          class="inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium">
          Exit Code: {{ exitCode }}</span>
        <Button variant="ghost" size="sm" :title="runDir ?? 'Copy path'"
          aria-label="Copy run directory path" @click="copyPath">
          <Copy /> Copy path
        </Button>
        <Button v-if="status === 'running'" variant="destructive" size="sm"
          :disabled="cancelling" title="Cancel" aria-label="Cancel simulation"
          @click="cancelSimulation">
          <Square />
          Cancel
        </Button>
        <p class="text-muted-foreground">Run ID: {{ runId }}</p>
      </div>
      <section>
        <h2 class="text-xl font-semibold">Federates</h2>
      </section>
      <section class="space-y-2">
        <h2 class="text-xl font-semibold">Logs</h2>
        <LogPanel v-for="name in components" :key="name" :name="name"
          :content="logs[name] ?? ''" />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onActivated, onDeactivated } from 'vue'
import { useRoute } from 'vue-router'
import { api, type RunSummary } from '@/lib/api'
import StatusBadge from '@/components/StatusBadge.vue'
import LogPanel from '@/components/LogPanel.vue'
import { Button } from '@/components/ui/button'
import { Copy, Square } from 'lucide-vue-next'

const route = useRoute()
const runId = computed<string>(() => String(route.params.runId))
const status = ref<'running' | 'done' | 'failed' | 'loading' | 'unknown'>('loading')
const exitCode = ref<number | null>(null)
const runDir = ref<string | null>(null)
const runName = ref<string | null>(null)
const cancelling = ref<boolean>(false)

const components = ref<string[]>(['broker'])
const logs = ref<Record<string, string>>({})

async function cancelSimulation() {
  try {
    cancelling.value = true
    await api.cancelRun(runId.value)
  } catch (error) {
    console.log("Could not cancel", error)
    alert(`Could not cancel: ${error instanceof Error ? error.message : String(error)}`)
  } finally {
    cancelling.value = false
  }
}


let timeOut: ReturnType<typeof setTimeout> | undefined = undefined

function setStatus(currentStatus: RunSummary) {
  status.value = currentStatus.status
  if (typeof currentStatus.exit_code === 'number') {
    exitCode.value = currentStatus.exit_code
  }
  runDir.value = currentStatus.run_dir
  runName.value = currentStatus.name
}

function resetStatus() {
  status.value = 'loading'
  exitCode.value = null
  runDir.value = null
  runName.value = null
  logs.value = {}
  components.value = ['broker']
}

function copyPath() {
  if (runDir.value) {
    navigator.clipboard.writeText(runDir.value)
  }
}

async function poll() {
  try {
    const currentStatus = await api.runStatus(runId.value)
    setStatus(currentStatus)
    components.value.forEach(name => api.runLog(runId.value, name).then(text => logs.value[name] = text).catch(() => {
      if (logs.value[name] === undefined) {
        logs.value[name] = "No log found"
      }
    }))
    if (currentStatus.status === 'running') {
      timeOut = setTimeout(poll, 1000)
    }
  } catch {
    alert(`Could not load run ${runId.value} `)
  }
}


onActivated(async () => {
  try {
    const wiring = await api.getWiring(runId.value)
    components.value = ['broker', ...wiring.components.map(c => c.name)]
  } catch {
    alert(`Could not load run wiring diagram ${runId.value} `)
  }
  poll()
})

onDeactivated(() => {
  clearTimeout(timeOut)
  resetStatus()
})

</script>
