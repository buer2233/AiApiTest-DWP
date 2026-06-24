"""测试任务 API 路由模块。
本模块通过 DRF DefaultRouter 暴露测试任务 ViewSet，最终挂载到全局 `/api/test-runs/`。
"""

from rest_framework.routers import DefaultRouter

from .views import TestRunViewSet


router = DefaultRouter()
# 空前缀表示当前 include 路径本身就是资源根路径，例如 `/api/test-runs/`。
router.register("", TestRunViewSet, basename="test-run")

urlpatterns = router.urls
