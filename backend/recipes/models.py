from constants import (INGREDIENT_AMOUNT_MAX, INGREDIENT_AMOUNT_MIN,
                       MAX_LENGTH_INGREDIENT_MEASUREMENT_UNIT,
                       MAX_LENGTH_INGREDIENT_NAME, MAX_LENGTH_RECIPE_NAME,
                       MAX_LENGTH_TAG, MAX_TIME_COOKING, MIN_TIME_COOKING)
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

User = get_user_model()


class BaseModelShoppingCartFavorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recipe = models.ForeignKey('Recipe', on_delete=models.CASCADE)

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_user_recipe'
            )
        ]


class ShoppingCart(BaseModelShoppingCartFavorite):
    """Модель корзины пользователя."""

    class Meta(BaseModelShoppingCartFavorite.Meta):
        default_related_name = 'shopping'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_user_recipe_shopping'
            )
        ]


class Favorite(BaseModelShoppingCartFavorite):
    """Связь пользователя и рецептов для избранного."""

    class Meta(BaseModelShoppingCartFavorite.Meta):
        default_related_name = 'favorites'


class Tag(models.Model):
    """Модель для тега."""

    name = models.CharField(max_length=MAX_LENGTH_TAG, unique=True)
    slug = models.SlugField(max_length=MAX_LENGTH_TAG, unique=True)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Модель ингредиетов."""

    name = models.CharField(
        max_length=MAX_LENGTH_INGREDIENT_NAME)
    measurement_unit = models.CharField(
        max_length=MAX_LENGTH_INGREDIENT_MEASUREMENT_UNIT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_ingredient'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.measurement_unit})"


class Recipe(models.Model):
    """Модель рецепта."""

    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='recipes'
    )
    name = models.CharField(max_length=MAX_LENGTH_RECIPE_NAME)
    image = models.ImageField(
        upload_to='recipes/',
    )
    description = models.TextField()
    ingredients = models.ManyToManyField(
        Ingredient, through='RecipeIngredient'
    )
    tags = models.ManyToManyField(Tag)
    cooking_time = models.PositiveSmallIntegerField(
        help_text="Время в минутах",
        validators=[
            MinValueValidator(
                MIN_TIME_COOKING,
                message=f'минимально допустимое значение {MIN_TIME_COOKING}'
            ),
            MaxValueValidator(
                MAX_TIME_COOKING,
                message=f'максимально допустимое значение {MAX_TIME_COOKING}'),
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} - {self.author}'


class RecipeIngredient(models.Model):
    """Связь ингредиента и  рецепта."""

    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='recipe_ingredient'
    )
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    amount = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(
                INGREDIENT_AMOUNT_MIN,
                message=f'минимально допустимое значение {INGREDIENT_AMOUNT_MIN}'
            ),
            MaxValueValidator(
                INGREDIENT_AMOUNT_MAX,
                message=f'максимально допустимое значение {INGREDIENT_AMOUNT_MAX}'),
        ]
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient'
            ),
        ]
