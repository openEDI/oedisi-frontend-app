<template>
  <div class="min-h-screen p-8">
    <div class="max-w-6xl mx-auto space-y-8">
      <router-link to="/"
        class="text-primary hover:text-primary/80 mb-4 inline-block">← Back to
        Home</router-link>
      <h1 class="text-3xl font-bold mb-2">Simulation Status</h1>
      <div class="flex items-center gap-3">
        <p class="text-muted-foreground">Run ID: {{ runId }}</p>
        <span class="inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium"
          :class="statusClasses[status]">{{ status }}</span>
        <span v-if="exitCode !== null"
          class="inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium">
          Exit Code: {{ exitCode }}</span>
      </div>
      <section>
        <h2 class="text-xl font-semibold">Federates</h2>
      </section>
      <section>
        <h2 class="text-xl font-semibold">Logs</h2>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onActivated, onDeactivated } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/lib/api'

const route = useRoute()
const runId = computed<string>(() => String(route.params.runId))
const status = ref<'running' | 'done' | 'failed' | 'loading'>('loading')
const exitCode = ref<number | null>(null)

const statusClasses: Record<typeof status.value, string> = {
  running: 'bg-blue-100 text-blue-800',
  done: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  loading: 'bg-gray-100 text-gray-800',
}

let timeOut: ReturnType<typeof setTimeout> | undefined = undefined

function setStatus(currentStatus: { status: 'done' | 'running' | 'failed'; exit_code?: number }) {
  status.value = currentStatus.status
  if (typeof currentStatus.exit_code === 'number') {
    exitCode.value = currentStatus.exit_code
  }
}

function resetStatus() {
  status.value = 'loading'
  exitCode.value = null
}

async function poll() {
  try {
    const currentStatus = await api.runStatus(runId.value)
    setStatus(currentStatus)
    if (currentStatus.status === 'running') {
      timeOut = setTimeout(poll, 1000)
    }
  } catch {
    alert(`Could not load run ${runId.value}`)
  }
}


onActivated(poll)

onDeactivated(() => {
  clearTimeout(timeOut)
  resetStatus()
})

</script>
