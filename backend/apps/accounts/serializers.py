from django.contrib.auth import authenticate
from rest_framework import serializers

from apps.permissions.services import get_user_role_assignments

from .models import User


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "institution",
            "campus",
            "is_staff",
            "is_active",
            "roles",
        ]
        read_only_fields = fields

    def get_roles(self, obj):
        return get_user_role_assignments(obj)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        request = self.context.get("request")
        user = authenticate(
            request=request,
            username=attrs.get("email"),
            password=attrs.get("password"),
        )
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("User account is inactive.")
        attrs["user"] = user
        return attrs
