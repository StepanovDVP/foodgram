from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import MyUser


@admin.register(MyUser)
class MyUserAdmin(UserAdmin):
    search_fields = ['email', 'username']
