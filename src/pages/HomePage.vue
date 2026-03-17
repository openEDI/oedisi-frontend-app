<template>
  <div class="min-h-screen flex items-center justify-center p-4">
    <div class="max-w-4xl w-full">
      <div class="text-center mb-12">
        <h1 class="text-5xl font-bold mb-4">OEDISI Simulation Designer</h1>
        <p class="text-xl text-muted-foreground">
          Create, configure, and manage your co-simulation workflow configurations
        </p>
      </div>

      <div class="grid md:grid-cols-2 gap-6">
        <!-- Create New Simulation -->
        <Card class="hover:shadow-lg transition-shadow">
          <CardHeader>
            <!-- We need a little more space here -->
            <div class="flex flex-col space-y-3">
              <div class="w-12 h-12 bg-blue-500 rounded-lg flex items-center justify-center">
                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
              </div>
              <CardTitle>Create a New Simulation Template</CardTitle>
              <CardDescription>
                  Design simulation workflows with drag-and-drop components and custom configurations
              </CardDescription>
            </div>
          </CardHeader>
          <CardFooter>
            <router-link to="/designer" class="w-full">
              <Button>
                Start Designing
              </Button>
            </router-link>
          </CardFooter>
        </Card>

        <!-- Saved Configs -->
        <Card class="hover:shadow-lg transition-shadow">
          <CardHeader>
            <div class="flex flex-col space-y-3">
              <div class="w-12 h-12 bg-indigo-500 rounded-lg flex items-center justify-center">
                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V7m-6 4l2 2m0 0l-2 2m2-2l-2-2m0 0l2-2"></path></svg>
              </div>
              <CardTitle>Saved Use Case Templates</CardTitle>
              <CardDescription>
                View, edit, and run your previously saved simulation workflow configurations
              </CardDescription>
            </div>
          </CardHeader>
          <CardFooter>
            <router-link to="/configs" class="w-full">
              <Button variant="outline">
                View Saved Configs
              </Button>
            </router-link>
          </CardFooter>
        </Card>

        <!-- Simulation Results -->
        <Card class="hover:shadow-lg transition-shadow">
          <CardHeader>
            <div class="flex flex-col space-y-3">
              <div class="w-12 h-12 bg-green-500 rounded-lg flex items-center justify-center">
                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
              </div>
              <CardTitle>Simulation Results</CardTitle>
              <CardDescription>
                View and analyze simulation results with interactive visualizations
              </CardDescription>
            </div>
          </CardHeader>
          <CardFooter>
            <router-link to="/simulation" class="w-full">
              <Button variant="outline">
                View Results
              </Button>
            </router-link>
          </CardFooter>
        </Card>

        <!-- Simulation Status -->
        <Card class="hover:shadow-lg transition-shadow">
          <CardHeader>
            <div class="flex flex-col space-y-3">
              <div class="w-12 h-12 bg-purple-500 rounded-lg flex items-center justify-center">
                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path></svg>
              </div>
                <CardTitle>Simulation Status</CardTitle>
                <CardDescription>
                  Monitor all simulation runs with detailed status tracking and management
                </CardDescription>
            </div>
          </CardHeader>
          <CardFooter>
            <router-link to="/status" class="w-full">
              <Button variant="outline">
                View Status
              </Button>
            </router-link>
          </CardFooter>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card'
</script>
