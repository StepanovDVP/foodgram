from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, TagViewSet, IngredientViewSet, RecipeViewSet

router_v1 = DefaultRouter()
router_v1.register('users', UserViewSet, basename='users')
router_v1.register('tags', TagViewSet, basename='tags')
router_v1.register('ingredients', IngredientViewSet, basename='ingredients')
router_v1.register('recipes', RecipeViewSet, basename='recipes')


urlpatterns = [
    path('', include(router_v1.urls)),
    path('auth/token/login/', UserViewSet.as_view({'post': 'login'}),
         name='api_token_login'),
    path('auth/token/logout/', UserViewSet.as_view({'post': 'logout'}),
         name='api_token_logout'),
]
