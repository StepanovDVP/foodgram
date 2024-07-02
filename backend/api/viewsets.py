from rest_framework import mixins, permissions, viewsets


class CustomViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                    viewsets.GenericViewSet):
    """Кастомный viewset на получение объекта/объектов."""

    permission_classes = [permissions.AllowAny]

    pass
