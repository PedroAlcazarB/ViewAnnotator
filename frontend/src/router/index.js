import { createRouter, createWebHistory } from 'vue-router'
import WelcomeView from '@/views/WelcomeView.vue'
import DatasetsView from '@/views/DatasetsView.vue'
import DatasetView from '@/views/DatasetView.vue'
import ModelsView from '@/views/ModelsView.vue'
import CategoriesView from '@/views/CategoriesView.vue'
import { useAuthStore } from '@/stores/authStore'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'welcome',
      component: WelcomeView
    },
    {
      path: '/datasets',
      name: 'datasets',
      component: DatasetsView,
      meta: { requiresAuth: true }
    },
    {
      path: '/datasets/:id',
      name: 'dataset',
      component: DatasetView,
      meta: { requiresAuth: true }
    },
    {
      path: '/models',
      name: 'models',
      component: ModelsView,
      meta: { requiresAuth: true }
    },
    {
      path: '/categories',
      name: 'categories',
      component: CategoriesView,
      meta: { requiresAuth: true }
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/'
    }
  ]
})

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  if (!authStore.isInitialized) {
    try {
      await authStore.init()
    } catch (error) {
      console.error('Error initializing auth store before navigation:', error)
    }
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'welcome' })
    return
  }

  next()
})

export default router
