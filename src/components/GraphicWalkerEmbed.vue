<template>
  <div ref="gwContainer" class="min-h-200 w-full">
  </div>
</template>

<script setup lang="ts">
import { embedGraphicWalker, type IMutField, type IRow } from '@kanaries/graphic-walker';
import { onMounted, useTemplateRef } from 'vue';

const gwContainer = useTemplateRef<HTMLDivElement>('gwContainer')
const props = defineProps<{ data: IRow[]; fields: IMutField[] }>()

onMounted(() => { embedGraphicWalker(gwContainer.value, { data: props.data, fields: props.fields, appearance: 'media' }) })

</script>
