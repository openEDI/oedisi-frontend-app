import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/pages/Home.vue'
import FlowchartDesigner from '@/pages/FlowchartDesigner.vue'
import SavedConfigs from '@/pages/SavedConfigs.vue'
import SimulationResults from '@/pages/SimulationResults.vue'
import SimulationStatus from '@/pages/SimulationStatus.vue'

const routes = [
  {
    path: '/',
    component: Home,
  },
  {
    path: '/designer',
    component: FlowchartDesigner,
  },
  {
    path: '/configs',
    component: SavedConfigs,
  },
  {
    path: '/simulation',
    component: SimulationResults,
  },
  {
    path: '/status',
    component: SimulationStatus,
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
