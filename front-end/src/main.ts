/**
 * Vue 前端应用入口。
 * 本文件负责创建 Vue 应用实例，并挂载 Pinia、Vue Router、Element Plus 和全局样式。
 */

import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';

import { createPinia } from 'pinia';
import { createApp } from 'vue';

import App from './App.vue';
import router from './router';
import './styles/main.css';

const app = createApp(App);

// Pinia 必须先注册，路由守卫中会读取登录态 store。
app.use(createPinia());
app.use(router);
app.use(ElementPlus);

app.mount('#app');
