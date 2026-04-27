<template>
  <details open>
    <summary class="font-semibold">{{ name }}</summary>
    <pre ref="preEl"
      class="max-h-96 overflow-auto font-mono text-xs whitespace-pre-wrap bg-muted p-2 rounded">{{ content }}</pre>
  </details>
</template>

<script setup lang="ts">
import { watch, useTemplateRef, nextTick, onMounted } from 'vue';

const preEl = useTemplateRef('preEl')
const props = defineProps<{ name: string; content: string }>()

watch(() => props.content, async () => {
  const el = preEl.value
  if (!el) return
  const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 10
  await nextTick()
  if (atBottom) el.scrollTop = el.scrollHeight
})

onMounted(() => {
  const el = preEl.value
  if (el) el.scrollTop = el.scrollHeight
})
</script>
