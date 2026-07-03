import { VueQueryPlugin } from '@tanstack/vue-query'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import './assets/main.css'

const app = createApp(App)

// Pinia 必须早于 router 安装，因为路由守卫会读取登录态 store。
app.use(createPinia())
app.use(router)
app.use(VueQueryPlugin)
app.use(ElementPlus)

app.mount('#app')
