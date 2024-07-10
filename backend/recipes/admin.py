from django.contrib import admin
from django.db.models import Count

from .models import Ingredient, Recipe, Tag


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'total_favorites')
    search_fields = ['author__username', 'name']
    list_filter = ['tags']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(total_favorites=Count('favorites'))
        return queryset

    def total_favorites(self, obj):
        return obj.total_favorites

    total_favorites.admin_order_field = 'total_favorites'
    total_favorites.short_description = 'Total Favorites'


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ['name']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
