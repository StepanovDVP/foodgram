from django.contrib.auth import get_user_model
from drf_extra_fields.fields import Base64ImageField
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from users.models import Follow

User = get_user_model()


class UserRecipeSerializerData(serializers.ModelSerializer):
    """Получение рецептов в составе поля 'recipes'."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        extra_kwargs = {
            'Meta': {'ordering': ['-created_at']}
        }


class AvatarSerialize(serializers.ModelSerializer):
    """Сериализатор для аватара."""

    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя."""

    is_subscribed = serializers.BooleanField(default=False)

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'avatar')


class CustomUserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователей с полями 'recipes', 'recipes_count'."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.BooleanField(default=False)

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count', 'avatar')

    @staticmethod
    def get_recipes_count(obj):
        return obj.recipes.count()

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit', None)
        recipes = obj.recipes.all()

        if recipes_limit:
            try:
                recipes_limit = int(recipes_limit)
                recipes = recipes[:recipes_limit]
            except ValueError:
                pass

        return UserRecipeSerializerData(recipes, many=True).data


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор модели Tag."""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор модели Ingredient."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):
    """Сериализатор модели RecipeIngredient."""

    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeIngredientReadSerializer(serializers.ModelSerializer):
    """Сериализатор модели RecipeIngredient (list, retrieve)."""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор модели Recipe (list, retrieve)."""

    author = UserSerializer()
    ingredients = RecipeIngredientReadSerializer(
        many=True, source='recipe_ingredient')
    tags = TagSerializer(many=True)
    is_favorited = serializers.BooleanField(default=False)
    is_in_shopping_cart = serializers.BooleanField(default=False)
    text = serializers.CharField(source='description')

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'is_favorited', 'is_in_shopping_cart',
                  'name', 'image', 'text', 'cooking_time')


class RecipeCreateSerializer(serializers.ModelSerializer):
    """Сериализатор модели Recipe."""

    ingredients = RecipeIngredientCreateSerializer(many=True)
    text = serializers.CharField(source='description')
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = ('ingredients', 'tags', 'image',
                  'name', 'text', 'cooking_time')

    @staticmethod
    def validate_image(value):
        if not value:
            raise serializers.ValidationError()
        return value

    def validate(self, data):
        for field in ('ingredients', 'tags'):
            value = data.get(field)
            if not value:
                raise serializers.ValidationError(
                    {field: f'{field} не может быть пустым!'}
                )
            ids = [
                item.id if field == 'tags' else item['id'] for item in value
            ]

            if len(ids) != len(set(ids)):
                raise serializers.ValidationError(
                    {field: f'Поле {field} содержит дублирующиеся значения!'}
                )
        return data

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        validated_data['author'] = self.context['request'].user
        recipe = Recipe.objects.create(**validated_data)
        self._save_ingredients(recipe, ingredients_data)
        recipe.tags.set(tags_data)
        return recipe

    def update(self, instance, validated_data):
        tags_data = validated_data.pop('tags')
        ingredients_data = validated_data.pop('ingredients')
        instance = super().update(instance, validated_data)

        instance.tags.set(tags_data)
        instance.ingredients.clear()
        self._save_ingredients(instance, ingredients_data)

        return instance

    @staticmethod
    def _save_ingredients(recipe, ingredients_data):
        recipe_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=item['id'],
                amount=item['amount']
            )
            for item in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data


class FollowSerializer(serializers.ModelSerializer):
    """Сериализация подписок."""

    following = serializers.SlugRelatedField(
        slug_field='id', queryset=User.objects.all(),
    )

    class Meta:
        model = Follow
        fields = ('user', 'following')
        validators = [
            UniqueTogetherValidator(
                queryset=Follow.objects.all(),
                fields=('user', 'following')
            )
        ]

    def validate_following(self, data):
        user = self._kwargs['context']['request'].user
        if user == data:
            raise serializers.ValidationError()
        return data

    def to_representation(self, instance):
        representation = CustomUserSerializer(
            instance.following, context=self.context).data
        representation['is_subscribed'] = True
        return representation


class BaseUserRecipeSerializer(serializers.ModelSerializer):
    """Базовый сериализатор для избранных рецептов и корзины покупок."""

    recipe = serializers.SlugRelatedField(
        slug_field='id', queryset=Recipe.objects.all()
    )

    class Meta:
        fields = ('user', 'recipe')

    def to_representation(self, instance):
        return UserRecipeSerializerData(
            instance.recipe, context=self.context).data


class FavoriteSerializer(BaseUserRecipeSerializer):
    """Сериализация избранных рецептов."""

    class Meta(BaseUserRecipeSerializer.Meta):
        model = Favorite
        validators = [
            UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=('user', 'recipe')
            )
        ]


class ShoppingCartSerializer(BaseUserRecipeSerializer):
    """Сериализация добавления рецептов в корзину."""

    class Meta(BaseUserRecipeSerializer.Meta):
        model = ShoppingCart
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=('user', 'recipe')
            )
        ]
