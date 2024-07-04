import short_url
from django.contrib.auth import get_user_model
from django.db.models import BooleanField, Value
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as BaseUserViewSet
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response

from recipes.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from users.models import Follow

from .filters import RecipeFilter
from .pdf_utils import create_pdf
from .permissions import IsOwnerOrAdmin
from .serializers import (AvatarSerialize, ChangePasswordSerializer,
                          IngredientSerializer, RecipeSerializer,
                          TagSerializer, UserCreateSerializer,
                          UserRecipeSerializerData, UserSerializer)
from .utils import (annotate_exists, get_ingredients_in_shopping_cart,
                    handle_action)
from .viewsets import CustomViewSet

User = get_user_model()


# class UserViewSet(viewsets.ModelViewSet):
class UserViewSet(BaseUserViewSet):
    """Создание и редактирвоание пользовательских действий."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    pagination_class = LimitOffsetPagination

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action == 'set_password':
            return ChangePasswordSerializer
        return UserSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = User.objects.all()
        if user.is_authenticated:
            annotations = [
                ('is_subscribed', Follow, 'following')
            ]
            queryset = annotate_exists(queryset, user, annotations)
        return queryset

    @action(methods=['get'], detail=False)
    def me(self, request, *args, **kwargs):
        return super(UserViewSet, self).me(request, *args, **kwargs)

    @action(detail=False, methods=['put', 'delete'],
            url_path='me/avatar')
    def upload_avatar(self, request):
        """Загрузить/удалить аватар пользователя."""
        user = request.user

        if request.method == 'DELETE':
            user.avatar.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = AvatarSerialize(user, context={'request': request},
                                     data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def subscriptions(self, request):
        """Получить все подписки текущего пользователя."""
        subscriptions = (
            User.objects
            .filter(follower__user=request.user)
            .annotate(is_subscribed=Value(True, output_field=BooleanField())))
        page = self.paginate_queryset(subscriptions)

        if page is not None:
            serializer = UserSerializer(page, many=True,
                                        context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = UserSerializer(subscriptions, many=True,
                                    context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post', 'delete'])
    def subscribe(self, request, **kwargs):
        """Подписаться на пользователя по id."""
        user = request.user
        pk = kwargs.get('id')
        return handle_action(request, pk, user, User, Follow, UserSerializer,
                             'following', update_subscribed=True)


class TagViewSet(CustomViewSet):
    """Получение тегов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer

    pagination_class = None


class IngredientViewSet(CustomViewSet):
    """Получение ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('name', None)
        if name:
            queryset = queryset.filter(name__istartswith=name)
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    """Создание и редактирвоание рецептов."""

    serializer_class = RecipeSerializer
    permission_classes = [IsOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = RecipeFilter
    ordering = ['-created_at']
    pagination_class = LimitOffsetPagination

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        user = self.request.user
        queryset = Recipe.objects.all()
        if user.is_authenticated:
            annotations = [
                ('is_favorited', Favorite, 'recipe'),
                ('is_in_shopping_cart', ShoppingCart, 'recipe')
            ]
            queryset = annotate_exists(queryset, user, annotations)
        return queryset

    @action(detail=True, methods=['get'], url_path='get-link',
            permission_classes=[permissions.AllowAny])
    def get_link(self, request, pk=None):
        """Получить короткую ссылку на рецепт."""
        recipe = get_object_or_404(Recipe, pk=pk)
        short_id = short_url.encode_url(recipe.id)
        short_link = request.build_absolute_uri(f"/s/{short_id}")
        return Response({"short-link": short_link})

    @action(methods=['post', 'delete'], detail=True,
            permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        """Добавить рецепт в избранное."""
        user = request.user
        return handle_action(request, pk, user, Recipe, Favorite,
                             UserRecipeSerializerData, 'recipe')

    @action(methods=['post', 'delete'], detail=True,
            permission_classes=[permissions.IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        """Добавить рецепт в корзину."""
        user = request.user
        return handle_action(request, pk, user, Recipe, ShoppingCart,
                             UserRecipeSerializerData, 'recipe')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.user.is_authenticated:
            user = self.request.user
            subscribed_users = set(user.following.values_list('following',
                                                              flat=True))
            context['subscribed_users'] = subscribed_users
        else:
            context['subscribed_users'] = set()
        return context

    @action(detail=False, methods=['get'],
            permission_classes=[permissions.IsAuthenticated])
    def download_shopping_cart(self, request):
        """Скачать pdf файл всех ингредиентов из корзины пользователя."""
        user = request.user
        ingredients = get_ingredients_in_shopping_cart(user)
        pdf_file = create_pdf(ingredients)
        return FileResponse(pdf_file, as_attachment=True,
                            filename='shopping_cart.pdf')
