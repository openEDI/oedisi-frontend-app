<template>
  <div :class="cn('rounded-lg border border-gray-200 bg-white text-slate-900 shadow-sm', props.class)">
    <div v-if="$slots.header" :class="cn('flex flex-col space-y-1.5 p-6')">
      <slot name="header" />
    </div>
    <div v-if="$slots.default" :class="cn('p-6 pt-0')">
      <slot />
    </div>
    <div v-if="$slots.footer" :class="cn('flex items-center p-6 pt-0')">
      <slot name="footer" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { cn } from '@/lib/utils'

interface Props {
  class?: string
}

defineProps<Props>()
</script>
