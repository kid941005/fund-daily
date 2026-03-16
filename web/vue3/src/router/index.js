import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/views/Home.vue'
import Holdings from '@/views/Holdings.vue'
import Analysis from '@/views/Analysis.vue'

const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/holdings', name: 'Holdings', component: Holdings },
  { path: '/analysis', name: 'Analysis', component: Analysis }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
