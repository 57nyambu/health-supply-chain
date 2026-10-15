from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import authenticate, login, logout
from .models import User, WorkerProfile
from .serializers import (
    UserSerializer, 
    UserCreateSerializer,
    WorkerProfileSerializer,
    PasswordResetSerializer,
    PasswordChangeSerializer,
    AuthSerializer
)
from .permissions import IsAdminOrManager, IsProfileOwner
from apps.integrations.tasks import send_welcome_credentials_task
from rest_framework_simplejwt.tokens import RefreshToken

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrManager]

    def get_permissions(self):
        if self.action == 'me':
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return super().get_serializer_class()

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        user = self.get_object()
        user.is_approved = True
        user.save()
        send_welcome_credentials_task.delay(user.id)
        return Response({'status': 'user approved'})

    @action(detail=False, methods=['post'])
    def reset_password(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            # Password reset logic
            return Response({'status': 'password reset email sent'})
        return Response(serializer.errors, status=400)

class WorkerProfileViewSet(viewsets.ModelViewSet):
    queryset = WorkerProfile.objects.all()
    serializer_class = WorkerProfileSerializer
    permission_classes = [IsAdminOrManager | IsProfileOwner]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class AuthViewSet(viewsets.ViewSet):
    serializer_class = AuthSerializer

    @action(detail=False, methods=['post'])
    def login(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        user = authenticate(request, email=email, password=password)
        if user is not None:
            if not user.is_active:
                return Response({'error': 'User account is disabled.'}, status=status.HTTP_403_FORBIDDEN)
            login(request, user)
            # IP tracking
            ip = (
                request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0]
                if request.META.get('HTTP_X_FORWARDED_FOR')
                else request.META.get('REMOTE_ADDR')
            )
            # Optionally, save IP to user profile or log it

            # JWT pair — the SPA frontend (separate origin) authenticates with
            # Authorization: Bearer <access>, not the session cookie above.
            from apps.core.permissions import user_tier, user_warehouse_id
            refresh = RefreshToken.for_user(user)
            return Response({
                'status': 'logged in',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'role': user.role,
                    'role_display': user.get_role_display(),
                    'tier': user_tier(user),
                    'warehouse_id': user_warehouse_id(user),
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                },
                'ip': ip,
            })
        return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['post'])
    def logout(self, request):
        logout(request)
        return Response({'status': 'logged out'})