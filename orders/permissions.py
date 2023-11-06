from rest_framework import permissions

from django.contrib.auth.models import User

def get_username(request):
    """Получение id пользователя"""
    if request.user.is_authenticated:
        user_id = request.user.id
        return user_id


class IsAdmin(permissions.BasePermission):
    """Правило для админов"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)


class IsOwner(permissions.BasePermission):
    """Правило для владельцев"""
    def has_object_permission(self, request, view, obj):
        return request.user.id == obj.id