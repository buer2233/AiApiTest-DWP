"""账户认证 API 视图模块。
本模块提供登录、登出和当前用户信息接口，是前端登录态和 DRF Token 认证的入口。
除登录接口外，其余接口都要求用户已认证并具备平台访问权限。
"""

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import PlatformAccessPermission
from .serializers import LoginSerializer, UserSerializer


class LoginView(APIView):
    """用户登录接口。
    接收用户名和密码，认证成功后返回 DRF Token 与前端所需的用户基础信息。
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        """处理登录请求。
        Args:
            request: DRF 请求对象，body 中包含 username 和 password。
        Returns:
            Response: 登录 token 和用户基础信息。
        """
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        # Token 可复用同一个用户的既有记录，避免重复登录产生多条有效 token。
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "user": UserSerializer(user).data,
            }
        )


class LogoutView(APIView):
    """用户登出接口。
    删除当前用户的 DRF Token，使已发放 token 立即失效。
    """

    permission_classes = [IsAuthenticated, PlatformAccessPermission]

    def post(self, request):
        """处理登出请求。
        Args:
            request: 已认证的 DRF 请求对象。
        Returns:
            Response: 204 表示 token 已删除。
        """
        # 删除当前用户全部 token，确保同一账号的旧登录态不会继续访问平台接口。
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """当前用户信息接口。
    前端刷新页面后可通过该接口恢复用户角色和基础身份信息。
    """

    permission_classes = [IsAuthenticated, PlatformAccessPermission]

    def get(self, request):
        """返回当前已认证用户。
        Args:
            request: 已认证的 DRF 请求对象。
        Returns:
            Response: 当前用户的基础资料。
        """
        return Response(UserSerializer(request.user).data)
