from django.contrib import admin
from .models import ChatSession, ChatMessage

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'user', 'created_at', 'updated_at')
    search_fields = ('session_key', 'user__username')

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'sender', 'message', 'created_at')
    list_filter = ('sender', 'created_at')
    search_fields = ('message',)
