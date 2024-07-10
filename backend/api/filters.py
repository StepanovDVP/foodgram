from django_filters import rest_framework as filters
from recipes.models import Ingredient, Recipe


class RecipeFilter(filters.FilterSet):
    """Фильтрация модели Рецепт."""

    is_favorited = filters.BooleanFilter(field_name='is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(
        field_name='is_in_shopping_cart')
    author = filters.CharFilter(field_name='author__id')
    tags = filters.AllValuesMultipleFilter(field_name='tags__slug')

    class Meta:
        model = Recipe
        fields = ['is_favorited', 'is_in_shopping_cart', 'author', 'tags']


class IngredientFilter(filters.FilterSet):
    """Фильтрация модели Ингредиенты."""

    name = filters.CharFilter(field_name='name', lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ['name']
