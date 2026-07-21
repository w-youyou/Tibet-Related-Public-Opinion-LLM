from django.contrib import admin
from .models import User, KnowledgeBase


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'age', 'gender', 'created_at')
    list_filter = ('gender', 'created_at')
    search_fields = ('username', 'email')


@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'collection_name', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name', 'user__username', 'collection_name')
    readonly_fields = ('id', 'collection_name', 'created_at', 'updated_at')
