import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue')
    },
    {
      path: '/sources/:id',
      name: 'source-detail',
      component: () => import('@/views/SourceDetailView.vue'),
      props: true
    },
    {
      path: '/search',
      name: 'search',
      component: () => import('@/views/SearchView.vue')
    },
    {
      path: '/ocr',
      name: 'ocr',
      component: () => import('@/views/OcrView.vue')
    },
    {
      path: '/timeline',
      name: 'timeline',
      component: () => import('@/views/TimelineView.vue')
    },
    {
      path: '/convert',
      name: 'convert',
      component: () => import('@/views/ConvertView.vue')
    }
  ]
})

export default router
