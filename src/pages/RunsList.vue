<template>
  <div class="min-h-screen p-8">
    <div class="max-w-6xl mx-auto">
      <div class="mb-8">
        <router-link to="/" class="text-primary hover:text-primary/80 mb-4 inline-block">← Back to Home</router-link>
        <h1 class="text-3xl font-bold mb-2">Simulation Status</h1>
        <p class="text-muted-foreground">Monitor all simulation runs with detailed status tracking and management</p>
      </div>

      <div class="bg-card rounded-lg p-8">
        <div class="text-center text-muted-foreground">
          <p class="mb-4">No active simulations</p>
          <p class="text-sm">Run a simulation from your saved templates to see status updates here</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>
