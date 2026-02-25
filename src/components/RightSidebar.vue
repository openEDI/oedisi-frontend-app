<template>
  <div class="w-72 bg-white border-l p-6 overflow-y-auto">
    <h2 class="text-lg font-semibold mb-6">Properties</h2>

    <div v-if="!selected" class="text-gray-500 text-center py-8">
      <p>Select a component to view properties</p>
    </div>

    <div v-else class="space-y-4">
      <div v-if="'data' in selected">
        <Label class="block mb-2">Label</Label>
        <Input
          :value="selected.data.label"
          placeholder="Node label"
          @input="$emit('update-node', selected.id, { label: $event.target.value })"
        />
      </div>

      <div v-if="'data' in selected" class="space-y-3">
        <Label class="block">Configuration</Label>
        <div class="space-y-2">
          <Button
            variant="outline"
            size="sm"
            class="w-full justify-start"
            @click="isConfigOpen = !isConfigOpen"
          >
            {{ isConfigOpen ? '▼' : '▶' }} Advanced Settings
          </Button>
          <div v-if="isConfigOpen" class="pl-4 space-y-2 border-l">
            <Input
              placeholder="Add config key"
              @keydown.enter="addConfigField"
            />
          </div>
        </div>
      </div>

      <Button
        variant="destructive"
        class="w-full mt-4"
        @click="$emit('delete')"
      >
        Delete Component
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Label from '@/components/ui/Label.vue'
import Input from '@/components/ui/Input.vue'
import Button from '@/components/ui/Button.vue'

interface Props {
  selected: any | null
}

const props = withDefaults(defineProps<Props>(), {
  selected: null,
})

const isConfigOpen = ref(false)

const emit = defineEmits<{
  (e: 'update-node', nodeId: string, data: Record<string, any>): void
  (e: 'update-edge', edgeId: string, data: Record<string, any>): void
  (e: 'delete'): void
}>()

const addConfigField = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.value && props.selected && 'data' in props.selected) {
    const key = target.value
    const newConfig = { ...props.selected.data.config, [key]: '' }
    emit('update-node', props.selected.id, { config: newConfig })
    target.value = ''
  }
}
</script>
