import { createRouter, createWebHistory } from 'vue-router'

// 路由懒加载
const Home = () => import('@/views/Home.vue')
const Holdings = () => import('@/views/Holdings.vue')
const Analysis = () => import('@/views/Analysis.vue')
const Quant = () => import('@/views/Quant.vue')

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
