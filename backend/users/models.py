from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import UniqueConstraint


class MyUser(AbstractUser):
    """Модель пользователя."""

    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    email = models.EmailField(max_length=254, unique=True)

    def __str__(self):
        return self.username


class Follow(models.Model):
    """Модель подписок."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='following',
        on_delete=models.CASCADE
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='follower',
        on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            UniqueConstraint(fields=['user', 'following'],
                             name='unique_subscription'),
            models.CheckConstraint(
                check=~models.Q(user=models.F("following")),
                name="unique_subscription_to_yourself",
            ),
        ]
