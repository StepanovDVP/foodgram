import base64

from django.contrib.auth import get_user_model
from rest_framework import serializers
from djoser.serializers import (UserCreateSerializer as BaseUserCreateSerializer,
                                UserSerializer as BaseUserSerializer)
from django.core.files.base import ContentFile

from recipes.models import Tag, Ingredient, Recipe, RecipeIngredient, Favorite

User = get_user_model()


class ChangePasswordSerializer(serializers.ModelSerializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ('current_password', 'new_password')

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Incorrect current password")
        return value


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class UserCreateSerializer(BaseUserCreateSerializer):
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)

    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name', 'password')


class UserRecipeSerializerData(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class AvatarSerialize(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)


class UserSerializer(BaseUserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta(BaseUserSerializer.Meta):
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name', 'is_subscribed',
                  'recipes', 'recipes_count', 'avatar')

    def get_fields(self):
        fields = super(UserSerializer, self).get_fields()
        request = self.context.get('request', None)
        if request and (
                request.resolver_match.url_name not in
                ('users-subscriptions', 'users-subscribe')):
            fields.pop('recipes', None)
            fields.pop('recipes_count', None)
        return fields

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_is_subscribed(self, obj):
        if hasattr(obj, 'is_subscribed'):
            return obj.is_subscribed
        subscribed_users = self.context.get('subscribed_users', set())
        return obj.id in subscribed_users

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit', None)
        recipes = obj.recipes.all()
        if recipes_limit:
            recipes = recipes[:int(recipes_limit)]
        return UserRecipeSerializerData(recipes, many=True).data


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be "
                                              "a positive integer greater than zero.")
        return value

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['id'] = instance.ingredient.id
        return representation


class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(many=True, source='recipeIngredient')
    text = serializers.CharField(source='description')
    is_favorited = serializers.BooleanField(default=False)
    is_in_shopping_cart = serializers.BooleanField(default=False)
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients', 'is_favorited', 'is_in_shopping_cart',
                  'name', 'image', 'text', 'cooking_time')

    def validate_cooking_time(self, value):
        if value < 1:
            raise serializers.ValidationError()
        return value

    def validate_ingredients(self, value):
        return self._check_params(value, ingredient=True)

    def validate_tags(self, value):
        return self._check_params(value, tags=True)

    def _check_params(self, value, tags=False, ingredient=False):
        if not value:
            raise serializers.ValidationError("Cannot be empty")

        seen_params = set()
        param = None
        for item in value:
            if tags:
                param = item.id
            elif ingredient:
                param = item['id']
            if param in seen_params:
                raise serializers.ValidationError()
            seen_params.add(param)
        return value

    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipeIngredient')
        tags_data = validated_data.pop('tags')
        validated_data.pop('is_favorited'), validated_data.pop('is_in_shopping_cart')
        recipe = Recipe.objects.create(**validated_data)
        self._save_ingredients(recipe, ingredients_data)
        recipe.tags.set(tags_data)
        return recipe

    def update(self, instance, validated_data):
        if ('recipeIngredient' not in validated_data
                or 'tags' not in validated_data):
            raise serializers.ValidationError()

        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        instance.cooking_time = validated_data.get('cooking_time', instance.cooking_time)
        instance.image = validated_data.get('image', instance.image)

        tags_data = validated_data.pop('tags')
        self.validate_tags(tags_data)
        instance.tags.set(tags_data)

        ingredients_data = validated_data.pop('recipeIngredient')
        self.validate_ingredients(ingredients_data)
        instance.ingredients.clear()
        self._save_ingredients(instance, ingredients_data)

        instance.save()
        return instance

    def _save_ingredients(self, recipe, ingredients_data):
        for item in ingredients_data:
            ingredient = item['id']
            amount = item['amount']
            RecipeIngredient.objects.create(
                recipe=recipe, ingredient=ingredient, amount=amount)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['tags'] = TagSerializer(instance.tags, many=True).data
        return representation
