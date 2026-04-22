import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/pages/HomePage.vue'
import FlowchartDesigner from '@/pages/FlowchartDesigner.vue'
import SavedConfigs from '@/pages/SavedConfigs.vue'
import SimulationResults from '@/pages/SimulationResults.vue'
import RunsList from '@/pages/RunsList.vue'
import RunsDetail from '@/pages/RunsDetail.vue'

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
    path: '/runs',
    component: RunsList,
  },
  {
    path: '/runs/:runId',
    component: RunsDetail,
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
