from rest_framework import serializers

from .models import User, WorkerProfile


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    mfa_enrolled = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "is_approved",
            "is_active",
            "account_locked",
            "must_change_password",
            "mfa_enrolled",
            "roles",
            "last_login",
            "date_joined",
        ]
        read_only_fields = [
            "last_login",
            "date_joined",
            "is_active",
            "account_locked",
            "must_change_password",
        ]

    def get_roles(self, obj) -> list[str]:
        """Active role codes at the request's facility (for the administration screens)."""
        from apps.access import policies
        from apps.access.drf import request_facility

        request = self.context.get("request")
        facility = request_facility(request) if request is not None else None
        return policies.role_codes(obj, facility=facility) if facility else []

    def get_mfa_enrolled(self, obj) -> bool:
        from apps.accounts.mfa import active_device

        return active_device(obj) is not None


class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name", "phone", "role", "is_approved"]
        # Without a password the account gets a one-time temporary password that must be
        # changed at first sign-in (the administrator hands it over in person).
        extra_kwargs = {"password": {"write_only": True, "required": False}}

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class WorkerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = WorkerProfile
        fields = "__all__"
