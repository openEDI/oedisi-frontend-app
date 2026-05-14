<template>
  <div class="min-h-screen p-8">
    <div class="max-w-6xl mx-auto">
      <div class="mb-8">
        <router-link to="/"
          class="text-primary hover:text-primary/80 mb-4 inline-block">← Back to
          Home</router-link>
        <h1 class="text-3xl font-bold mb-2">Simulation Status</h1>
        <p class="text-muted-foreground">Monitor all simulation runs with
          detailed status tracking and management</p>
      </div>

      <div class="space-y-4">
        <div v-if="runs.length === 0" class="bg-card rounded-lg p-4">
          <h2 class="text-xl font-semibold mb-2">No simulations</h2>
        </div>
        <div v-for="run in runs" :key="run.run_id"
          class="bg-card rounded-lg p-4">
          <div class="flex items-center gap-3">
            <router-link :to="`/runs/${run.run_id}`"
              class="block rounded-sm bg-muted/80 px-2.5 py-0.5 transition text-primary hover:underline text-medium font-semibold">
              {{ run.name }}</router-link>
            <StatusBadge :status="run.status" />
            <span v-if="run.exit_code !== undefined"
              class="inline-flex rounded-full px-2.5 py-0.5 text-sm font-medium">
              Exit Code: {{ run.exit_code }}</span>
            <p
              class="inline-flex rounded-full px-2.5 py-0.5 text-sm font-medium">
              Started at {{ new Date(run.started_at).toLocaleString() }}
            </p>
            <Button variant="ghost" size="sm"
              :title="run.run_dir ?? 'Copy path'"
              aria-label="Copy run directory path" @click="() => copyPath(run)">
              <Copy /> Copy path
            </Button>
            <router-link v-if="run.status === 'done'"
              :to="`/runs/${run.run_id}/results`">
              <Button size="sm" title="Load Simulation Results">
                Results
              </Button>
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { api, type RunSummary } from '@/lib/api';
import { onActivated, ref } from 'vue';
import StatusBadge from '@/components/StatusBadge.vue'
import { Button } from '@/components/ui/button'
import { Copy } from 'lucide-vue-next'

const runs = ref<RunSummary[]>([])

function copyPath(run: RunSummary) {
  navigator.clipboard.writeText(run.run_dir)
}

onActivated(async () => {
  try {
    const runList = await api.listRuns()
    runs.value = runList.sort((a, b) => b.started_at.localeCompare(a.started_at))
  } catch (e) {
    console.log('Error from listRuns:', e)
    alert('Could not list runs')
  }
})
</script>
