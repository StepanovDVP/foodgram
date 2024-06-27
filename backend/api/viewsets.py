from rest_framework import viewsets, mixins, permissions


class CustomViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                    viewsets.GenericViewSet):
    permission_classes = [permissions.AllowAny]

    pass
