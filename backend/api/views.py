import short_url
from django.db.models import Value, BooleanField
from rest_framework import viewsets, permissions, status, filters
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.authtoken.models import Token
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.http import FileResponse

from .permissions import IsOwnerOrAdmin
from .serializers import (UserCreateSerializer, UserSerializer,
                          ChangePasswordSerializer, TagSerializer,
                          IngredientSerializer, RecipeSerializer, AvatarSerialize,
                          UserRecipeSerializerData)
from .viewsets import CustomViewSet
from users.models import Follow
from recipes.models import (Tag, Ingredient, Recipe,
                            RecipeIngredient, Favorite, ShoppingCart)
from .utils import handle_action, annotate_exists, get_ingredients_in_shopping_cart
from .filters import RecipeFilter
from .createpdf import create_pdf

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    pagination_class = LimitOffsetPagination

    def get_permissions(self):
        if self.action in ['create', 'list', 'retrieve', 'login']:
            self.permission_classes = [permissions.AllowAny]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
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

    @action(methods=['get'], detail=False, url_path='me')
    def get_yourself(self, request):
        user = self.request.user
        serializer = UserSerializer(user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def login(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        try:
            user = User.objects.get(email=email)
            if not user.check_password(password):
                return Response(status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        token, created = Token.objects.get_or_create(user=user)
        return Response({'auth_token': token.key})

    @action(detail=False, methods=['post'])
    def logout(self, request):
        try:
            token = Token.objects.get(user=request.user.id)
            token.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Token.DoesNotExist:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['put', 'delete'],
            url_path='me/avatar')
    def upload_avatar(self, request):
        user = request.user

        if request.method == 'DELETE':
            user.avatar.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = AvatarSerialize(user, context={'request': request}, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def set_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data,
                                              context={'request': request})
        if serializer.is_valid():
            new_password = serializer.validated_data['new_password']
            user = request.user
            user.set_password(new_password)
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def subscriptions(self, request):
        subscriptions = User.objects.filter(follower__user=request.user).annotate(
            is_subscribed=Value(True, output_field=BooleanField())
        )
        page = self.paginate_queryset(subscriptions)
        if page is not None:
            serializer = UserSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = UserSerializer(subscriptions, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post', 'delete'])
    def subscribe(self, request, pk=None):
        user = request.user
        return handle_action(request, pk, user, User, Follow,
                             UserSerializer, 'following', update_subscribed=True)


class TagViewSet(CustomViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer

    pagination_class = None


class IngredientViewSet(CustomViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]  # ?
    search_fields = ['^name']  # ?

    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('name', None)
        if name:
            queryset = queryset.filter(name__istartswith=name)
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    permission_classes = [IsOwnerOrAdmin]

    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

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
        recipe = get_object_or_404(Recipe, pk=pk)
        short_id = short_url.encode_url(recipe.id)
        short_link = request.build_absolute_uri(f"/s/{short_id}")
        return Response({"short-link": short_link})

    @action(methods=['post', 'delete'], detail=True,
            permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        user = request.user
        return handle_action(request, pk, user, Recipe, Favorite,
                             UserRecipeSerializerData, 'recipe')

    @action(methods=['post', 'delete'], detail=True,
            permission_classes=[permissions.IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        user = request.user
        return handle_action(request, pk, user, Recipe, ShoppingCart,
                             UserRecipeSerializerData, 'recipe')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.user.is_authenticated:
            user = self.request.user
            subscribed_users = set(user.following.values_list('following', flat=True))
            context['subscribed_users'] = subscribed_users
        else:
            context['subscribed_users'] = set()
        return context

    @action(detail=False, methods=['get'],
            permission_classes=[permissions.IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user
        ingredients = get_ingredients_in_shopping_cart(user)
        pdf_file = create_pdf(ingredients)
        return FileResponse(pdf_file, as_attachment=True, filename='shopping_cart.pdf')
