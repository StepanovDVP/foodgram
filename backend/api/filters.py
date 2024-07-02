from django_filters import rest_framework as filters

from recipes.models import Recipe


class RecipeFilter(filters.FilterSet):
    """Фильтрация модели Рецепт."""

    is_favorited = filters.BooleanFilter(method='filter_fields')
    is_in_shopping_cart = filters.BooleanFilter(method='filter_fields')
    author = filters.CharFilter(field_name='author__id')
    tags = filters.CharFilter(method='filter_tags')

    class Meta:
        model = Recipe
        fields = ['is_favorited', 'is_in_shopping_cart', 'author', 'tags']

    def filter_fields(self, queryset, name, value):
        user = self.request.user
        if user.is_authenticated:
            return queryset.filter(**{name: value})
        return queryset

    def filter_tags(self, queryset, name, value):
        tags = self.request.query_params.getlist('tags')
        if tags:
            queryset = queryset.filter(tags__slug__in=tags).distinct()
        return queryset
