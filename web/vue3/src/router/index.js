import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/views/Home.vue'
import Holdings from '@/views/Holdings.vue'
import Analysis from '@/views/Analysis.vue'
import Quant from '@/views/Quant.vue'

const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/holdings', name: 'Holdings', component: Holdings },
  { path: '/analysis', name: 'Analysis', component: Analysis },
  { path: '/quant', name: 'Quant', component: Quant }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
