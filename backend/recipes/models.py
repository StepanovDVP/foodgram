from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

User = get_user_model()


class ShoppingCart(models.Model):
    """Модель корзины пользователя."""

    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='shopping')
    recipe = models.ForeignKey('Recipe', on_delete=models.CASCADE,
                               related_name='shopping_by')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_user_recipe_shopping'
            )
        ]


class Favorite(models.Model):
    """Связь пользователя и рецептов для избранного."""

    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='favorites')
    recipe = models.ForeignKey('Recipe', on_delete=models.CASCADE,
                               related_name='favorited_by')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_user_recipe'
            )
        ]


class Tag(models.Model):
    """Модель для тега."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Модель ингредиетов."""

    name = models.CharField(max_length=200)
    measurement_unit = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.name} ({self.measurement_unit})"


class Recipe(models.Model):
    """Модель рецепта."""

    author = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name='recipes')
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to='recipes/', null=True,
                              default=None)
    description = models.TextField()
    ingredients = models.ManyToManyField(Ingredient,
                                         through='RecipeIngredient')
    tags = models.ManyToManyField(Tag)
    cooking_time = models.PositiveIntegerField(help_text="Время в минутах")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} - {self.author}'


class RecipeIngredient(models.Model):
    """Связь ингредиента и  рецепта."""

    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE,
                               related_name='recipeIngredient')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    amount = models.IntegerField(validators=[MinValueValidator(1)])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient'
            ),
        ]
