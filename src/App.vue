<template>
  <div class="bg-background text-foreground">
    <RouterView v-slot="{ Component }">
      <KeepAlive>
        <component :is="Component" />
      </KeepAlive>
    </RouterView>
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>
