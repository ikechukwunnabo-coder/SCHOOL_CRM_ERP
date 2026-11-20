from django.contrib.auth import login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_event

from .serializers import LoginSerializer, UserSerializer


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []  # ensure CSRF cookie issuance without session auth enforcement

    def get(self, request):
        from django.middleware.csrf import get_token

        return Response({"csrfToken": get_token(request)})


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            log_event(
                "auth.login_failed",
                actor=None,
                target_type="accounts.User",
                reason="invalid_credentials_or_validation",
                metadata={"email": str(request.data.get("email", ""))[:254]},
                request=request,
            )
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = serializer.validated_data["user"]
        login(request, user)
        log_event(
            "auth.login_succeeded",
            actor=user,
            target_type="accounts.User",
            target_id=user.pk,
            institution_id=getattr(user, "institution_id", None),
            campus_id=getattr(user, "campus_id", None),
            request=request,
        )
        return Response({"user": UserSerializer(user).data}, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        actor = request.user
        institution_id = getattr(actor, "institution_id", None)
        campus_id = getattr(actor, "campus_id", None)
        user_id = getattr(actor, "pk", "")
        logout(request)
        log_event(
            "auth.logout",
            actor=actor if getattr(actor, "is_authenticated", False) else None,
            target_type="accounts.User",
            target_id=user_id,
            institution_id=institution_id,
            campus_id=campus_id,
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({"user": UserSerializer(request.user).data})

