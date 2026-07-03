import 'vue-router'

export {}

declare module 'vue-router' {
  interface RouteMeta {
    public?: boolean
    requiresAuth?: boolean
    adminOnly?: boolean
  }
}
