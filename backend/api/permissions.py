from rest_framework import permissions


class IsOwnerOrAdmin(permissions.IsAuthenticatedOrReadOnly):
    """Custom permission."""

    def has_object_permission(self, request, view, obj):
        return (request.method in permissions.SAFE_METHODS
                or obj.author == request.user
                or request.user.is_superuser)
