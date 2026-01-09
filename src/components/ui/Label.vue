<template>
  <label :class="cn('text-sm font-semibold leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 text-slate-900', props.class)" v-bind="$attrs">
    <slot />
  </label>
</template>

<script setup lang="ts">
import { cn } from '@/lib/utils'

interface Props {
  class?: string
}

defineProps<Props>()
</script>
