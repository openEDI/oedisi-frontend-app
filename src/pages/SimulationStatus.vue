<template>
  <div class="min-h-screen bg-gray-50 p-8">
    <div class="max-w-6xl mx-auto">
      <div class="mb-8">
        <router-link to="/" class="text-blue-600 hover:text-blue-800 mb-4 inline-block">← Back to Home</router-link>
        <h1 class="text-3xl font-bold mb-2">Simulation Status</h1>
        <p class="text-gray-600">Monitor all simulation runs with detailed status tracking and management</p>
      </div>

      <div class="bg-white rounded-lg p-8">
        <div class="text-center text-gray-500">
          <p class="mb-4">No active simulations</p>
          <p class="text-sm">Run a simulation from your saved templates to see status updates here</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>
