<template>
  <div class="custom-node">
    <Handle type="target" :position="Position.Left" />
    <div class="node-content">
      <div class="node-label">{{ data.label }}</div>
    </div>
    <Handle type="source" :position="Position.Right" />
  </div>
</template>

<script setup lang="ts">
import { Handle, Position } from '@vue-flow/core'
import type { NodeProps } from '@vue-flow/core'

interface CustomNodeData {
  label: string
  componentType?: string
  config?: Record<string, string>
}

defineProps<NodeProps<CustomNodeData>>()
</script>

<style scoped>
.custom-node {
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px 16px;
  min-width: 120px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  position: relative;
}

.custom-node:hover {
  border-color: #3b82f6;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.node-content {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.node-label {
  font-weight: 500;
  font-size: 14px;
  color: #1f2937;
  text-align: center;
}

:deep(.vue-flow__handle) {
  width: 10px;
  height: 10px;
  background: #3b82f6;
  border: 2px solid white;
  border-radius: 50%;
}
</style>
