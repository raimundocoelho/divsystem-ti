from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .forms import UserChangeForm, UserCreationForm
from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = User
    ordering = ("name",)
    list_display = ("email", "name", "tenant", "role", "is_active", "is_global_admin")
    list_filter = ("role", "is_active", "is_global_admin", "tenant")
    search_fields = ("email", "name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Identificação", {"fields": ("name", "avatar_url")}),
        ("Vínculo", {"fields": ("tenant", "role", "is_global_admin")}),
        ("Permissões", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Datas", {"fields": ("last_login_at", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "name", "tenant", "role", "password1", "password2"),
        }),
    )
    readonly_fields = ("last_login_at", "date_joined")
