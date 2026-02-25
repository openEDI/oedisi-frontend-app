<template>
  <BaseEdge :id="id" :path="edgePath" :marker-end="markerEnd" :style="style" />

  <EdgeLabelRenderer>
    <div
      v-if="labelText"
      class="nodrag nopan absolute pointer-events-none -translate-x-1/2 -translate-y-1/2 whitespace-pre-line bg-transparent px-1.5 py-0.5 text-center text-[10px] leading-4 text-gray-700"
      :style="{
        transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
      }"
    >
      {{ labelText }}
    </div>
  </EdgeLabelRenderer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { BaseEdge, EdgeLabelRenderer, getBezierPath, type EdgeProps } from '@vue-flow/core'

const props = defineProps<EdgeProps>()

const pathValues = computed(() =>
  getBezierPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    sourcePosition: props.sourcePosition,
    targetX: props.targetX,
    targetY: props.targetY,
    targetPosition: props.targetPosition,
  })
)

const edgePath = computed(() => pathValues.value[0])
const labelX = computed(() => pathValues.value[1])
const labelY = computed(() => pathValues.value[2])
const labelText = computed(() => (typeof props.label === 'string' ? props.label : ''))
</script>
