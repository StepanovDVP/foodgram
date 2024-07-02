from django.db import IntegrityError
from django.db.models import Exists, OuterRef, Sum
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response

from recipes.models import Ingredient


def handle_action(request, pk, user, obj_class, model_class, serializer_class,
                  obj_name, update_subscribed=False):
    """Создать или удалить объект."""
    obj = get_object_or_404(obj_class, pk=pk)
    if request.method == 'POST':
        try:
            model_class.objects.create(user=user, **{obj_name: obj})
        except IntegrityError:
            return Response({'status': f'Already {obj_name}'},
                            status=status.HTTP_400_BAD_REQUEST)
        if update_subscribed:
            obj.is_subscribed = True
            obj.save()
        serializer = serializer_class(obj, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    elif request.method == 'DELETE':
        try:
            instance = model_class.objects.get(user=user, **{obj_name: obj})
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except model_class.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST)


def annotate_exists(queryset, user, annotations):
    """Получить queryset для viewset."""
    for alias, model, field in annotations:
        queryset = queryset.annotate(
            **{alias: Exists(
                model.objects.filter(user=user, **{field: OuterRef('pk')}))}
        )
    return queryset


def get_ingredients_in_shopping_cart(user):
    """Вернуть ингредиенты в корзине пользователя."""
    return (Ingredient.objects
            .filter(recipe__shopping_by__user=user)
            .values('name', 'measurement_unit')
            .annotate(total_amount=Sum('recipeingredient__amount')))
