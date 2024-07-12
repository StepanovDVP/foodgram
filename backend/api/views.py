import short_url
from django.contrib.auth import get_user_model
from django.db.models import (BooleanField, Exists, OuterRef, Prefetch, Sum,
                              Value)
from rest_framework.pagination import PageNumberPagination
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as BaseUserViewSet
from recipes.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from users.models import Follow

from .filters import IngredientFilter, RecipeFilter
from .pdf_utils import create_pdf
from .permissions import IsOwnerOrAdmin
from .serializers import (AvatarSerialize, CustomUserSerializer,
                          FavoriteSerializer, FollowSerializer,
                          IngredientSerializer, RecipeCreateSerializer,
                          RecipeReadSerializer, ShoppingCartSerializer,
                          TagSerializer, UserSerializer)

User = get_user_model()


class UserViewSet(BaseUserViewSet):
    """Создание и редактирвоание пользовательских действий."""

    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny, ]

    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        user = self.request.user
        queryset = User.objects.all()
        if user.is_authenticated:
            queryset = queryset.annotate(
                is_subscribed=Exists(Follow.objects.filter(
                    user=user, following=OuterRef('pk'))
                )
            )
        return queryset

    @action(methods=['get'], detail=False,
            permission_classes=[permissions.IsAuthenticated])
    def me(self, request, *args, **kwargs):
        return super(UserViewSet, self).me(request)

    @action(detail=False, methods=['put'], url_path='me/avatar',
            permission_classes=[permissions.IsAuthenticated])
    def upload_avatar(self, request):
        """Загрузить/удалить аватар пользователя."""
        user = request.user
        serializer = AvatarSerialize(
            user, context={'request': request}, data=request.data
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @upload_avatar.mapping.delete
    def delete_avatar(self, request):
        user = request.user
        user.avatar.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'],
            permission_classes=[permissions.IsAuthenticated])
    def subscriptions(self, request):
        """Получить все подписки текущего пользователя."""
        subscriptions = (
            User.objects
            .filter(follower__user=request.user)
            .annotate(is_subscribed=Value(True, output_field=BooleanField())))
        page = self.paginate_queryset(subscriptions)
        serializer = CustomUserSerializer(
            page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post'],
            permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request, **kwargs):
        """Подписаться на пользователя по id."""
        author_id = kwargs.get('id')
        author = get_object_or_404(User, pk=author_id)
        data = {
            'following': author.id,
            'user': request.user.id
        }
        serializer = FollowSerializer(
            data=data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscribe(self, request, **kwargs):
        """Отписаться от пользователя по id."""
        author_id = kwargs.get('id')
        author = get_object_or_404(User, pk=author_id)
        delete_cnt, _ = Follow.objects.filter(
            user=request.user, following=author.id).delete()

        if not delete_cnt:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Получение тегов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.AllowAny]

    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Получение ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter
    permission_classes = [permissions.AllowAny]


class UserActionsMixin:
    @staticmethod
    def add_object(request, pk, serializer_class):
        recipe = get_object_or_404(Recipe, pk=pk)
        data = {
            'recipe': recipe.id,
            'user': request.user.id
        }
        serializer = serializer_class(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def delete_object(request, pk, model):
        recipe = get_object_or_404(Recipe, pk=pk)
        delete_cnt, _ = model.objects.filter(
            user=request.user, recipe=recipe.id).delete()

        if not delete_cnt:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CustomPageNumberPagination(PageNumberPagination):
    page_size_query_param = 'limit'
    page_size = 10


class RecipeViewSet(UserActionsMixin, viewsets.ModelViewSet):
    """Создание и редактирвоание рецептов."""

    serializer_class = RecipeCreateSerializer
    permission_classes = [IsOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = RecipeFilter
    ordering = ['-created_at']
    pagination_class = CustomPageNumberPagination

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeReadSerializer
        return RecipeCreateSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Recipe.objects.all()

        if user.is_authenticated:
            annotations = [
                ('is_favorited', Favorite, 'recipe'),
                ('is_in_shopping_cart', ShoppingCart, 'recipe'),
            ]
            for alias, model, field in annotations:
                queryset = queryset.annotate(
                    **{alias: Exists(
                        model.objects.filter(
                            user=user, **{field: OuterRef('pk')}))}
                )

            author = Prefetch(
                'author', queryset=User.objects.annotate(
                    is_subscribed=Exists(
                        Follow.objects.filter(
                            user=user,
                            following=OuterRef('pk')
                        )
                    )
                )
            )
            queryset = queryset.prefetch_related(author)
        else:
            queryset = queryset.annotate(
                is_favorited=Value(False, output_field=BooleanField()),
                is_in_shopping_cart=Value(False, output_field=BooleanField()),
                is_subscribed=Value(False, output_field=BooleanField())
            )

        return queryset

    @action(detail=True, methods=['get'], url_path='get-link',
            permission_classes=[permissions.AllowAny])
    def get_link(self, request, pk=None):
        """Получить короткую ссылку на рецепт."""
        recipe = get_object_or_404(Recipe, pk=pk)
        short_id = short_url.encode_url(recipe.id)
        short_link = request.build_absolute_uri(f"/s/{short_id}")
        return Response({"short-link": short_link})

    @action(methods=['post'], detail=True,
            permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        """Добавить рецепт в избранное."""
        return self.add_object(request, pk, FavoriteSerializer)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        """Удалить рецепт из избранного."""
        return self.delete_object(request, pk, Favorite)

    @action(methods=['post'], detail=True,
            permission_classes=[permissions.IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        """Добавить рецепт в корзину."""
        return self.add_object(request, pk, ShoppingCartSerializer)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        """Удалить рецепт из корзины."""
        return self.delete_object(request, pk, ShoppingCart)

    @staticmethod
    def get_ingredients_in_shopping_cart(user):
        """Вернуть ингредиенты в корзине пользователя."""
        return (Ingredient.objects
                .filter(recipe__shopping__user=user)
                .values('name', 'measurement_unit')
                .annotate(total_amount=Sum('recipeingredient__amount')))

    @action(detail=False, methods=['get'],
            permission_classes=[permissions.IsAuthenticated])
    def download_shopping_cart(self, request):
        """Скачать pdf файл всех ингредиентов из корзины пользователя."""
        user = request.user
        pdf_file = create_pdf(self.get_ingredients_in_shopping_cart(user))
        return FileResponse(pdf_file, as_attachment=True,
                            filename='shopping_cart.pdf')
