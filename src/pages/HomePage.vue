<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
    <div class="max-w-4xl w-full">
      <div class="text-center mb-12">
        <h1 class="text-5xl font-bold mb-4 text-slate-900">OEDISI Simulation Designer</h1>
        <p class="text-xl text-gray-600">
          Create, configure, and manage your co-simulation workflow configurations
        </p>
      </div>

      <div class="grid md:grid-cols-2 gap-6">
        <!-- Create New Simulation -->
        <div class="rounded-lg border border-gray-200 bg-white text-slate-900 shadow-sm hover:shadow-lg transition-shadow">
          <div class="flex flex-col space-y-1.5 p-6">
            <div class="flex flex-col space-y-3">
              <div class="w-12 h-12 bg-blue-500 rounded-lg flex items-center justify-center">
                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
              </div>
              <div>
                <h3 class="text-lg font-semibold">Create a New Simulation Template</h3>
                <p class="text-sm text-gray-600 mt-1">
                  Design simulation workflows with drag-and-drop components and custom configurations
                </p>
              </div>
            </div>
          </div>
          <div class="flex items-center p-6 pt-0">
            <router-link to="/designer" class="w-full">
              <button class="w-full inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-slate-900 text-white hover:bg-slate-800 h-10 px-4 py-2">
                Start Designing
              </button>
            </router-link>
          </div>
        </div>

        <!-- Saved Configs -->
        <div class="rounded-lg border border-gray-200 bg-white text-slate-900 shadow-sm hover:shadow-lg transition-shadow">
          <div class="flex flex-col space-y-1.5 p-6">
            <div class="flex flex-col space-y-3">
              <div class="w-12 h-12 bg-indigo-500 rounded-lg flex items-center justify-center">
                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V7m-6 4l2 2m0 0l-2 2m2-2l-2-2m0 0l2-2"></path></svg>
              </div>
              <div>
                <h3 class="text-lg font-semibold">Saved Use Case Templates</h3>
                <p class="text-sm text-gray-600 mt-1">
                  View, edit, and run your previously saved simulation workflow configurations
                </p>
              </div>
            </div>
          </div>
          <div class="flex items-center p-6 pt-0">
            <router-link to="/configs" class="w-full">
              <button class="w-full inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-gray-300 bg-white hover:bg-gray-50 hover:text-slate-900 h-10 px-4 py-2">
                View Saved Configs
              </button>
            </router-link>
          </div>
        </div>

        <!-- Simulation Results -->
        <div class="rounded-lg border border-gray-200 bg-white text-slate-900 shadow-sm hover:shadow-lg transition-shadow">
          <div class="flex flex-col space-y-1.5 p-6">
            <div class="flex flex-col space-y-3">
              <div class="w-12 h-12 bg-green-500 rounded-lg flex items-center justify-center">
                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
              </div>
              <div>
                <h3 class="text-lg font-semibold">Simulation Results</h3>
                <p class="text-sm text-gray-600 mt-1">
                  View and analyze simulation results with interactive visualizations
                </p>
              </div>
            </div>
          </div>
          <div class="flex items-center p-6 pt-0">
            <router-link to="/simulation" class="w-full">
              <button class="w-full inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-gray-300 bg-white hover:bg-gray-50 hover:text-slate-900 h-10 px-4 py-2">
                View Results
              </button>
            </router-link>
          </div>
        </div>

        <!-- Simulation Status -->
        <div class="rounded-lg border border-gray-200 bg-white text-slate-900 shadow-sm hover:shadow-lg transition-shadow">
          <div class="flex flex-col space-y-1.5 p-6">
            <div class="flex flex-col space-y-3">
              <div class="w-12 h-12 bg-purple-500 rounded-lg flex items-center justify-center">
                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path></svg>
              </div>
              <div>
                <h3 class="text-lg font-semibold">Simulation Status</h3>
                <p class="text-sm text-gray-600 mt-1">
                  Monitor all simulation runs with detailed status tracking and management
                </p>
              </div>
            </div>
          </div>
          <div class="flex items-center p-6 pt-0">
            <router-link to="/status" class="w-full">
              <button class="w-full inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-gray-300 bg-white hover:bg-gray-50 hover:text-slate-900 h-10 px-4 py-2">
                View Status
              </button>
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>
