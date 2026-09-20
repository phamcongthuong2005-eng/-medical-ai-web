from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'full_name', 'phone', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Thông tin bổ sung', {'fields': ('role', 'full_name', 'phone', 'address', 'date_of_birth', 'gender', 'avatar')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Thông tin bổ sung', {'fields': ('role', 'full_name', 'phone', 'address', 'date_of_birth', 'gender')}),
    )
    search_fields = ('username', 'full_name', 'email', 'phone')
