<template>
  <span
    class="inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium capitalize"
    :class="statusClasses[status]">{{ status }}</span>
</template>

<script setup lang="ts">

type Status = 'running' | 'done' | 'failed' | 'loading'

const statusClasses: Record<Status, string> = {
  running: 'bg-blue-100 text-blue-800',
  done: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  loading: 'bg-gray-100 text-gray-800',
}

defineProps<{ status: Status }>()
</script>
