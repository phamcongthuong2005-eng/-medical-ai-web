from django.db import models
from django.conf import settings

class ChatSession(models.Model):
    session_key = models.CharField(max_length=100, unique=True, verbose_name='Khóa phiên chat')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_sessions', verbose_name='Người dùng')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian tạo')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Cập nhật lúc')

    class Meta:
        verbose_name = 'Phiên chat'
        verbose_name_plural = 'Phiên chat'
        ordering = ['-updated_at']

    def __str__(self):
        return f"Session {self.session_key} - {self.user.username if self.user else 'Khách'}"


class ChatMessage(models.Model):
    SENDER_CHOICES = (
        ('user', 'Người dùng'),
        ('ai', 'AI Chatbot'),
    )
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages', verbose_name='Phiên chat')
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES, verbose_name='Người gửi')
    message = models.TextField(verbose_name='Nội dung tin nhắn')
    data_json = models.JSONField(blank=True, null=True, verbose_name='Dữ liệu động đính kèm')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian gửi')

    class Meta:
        verbose_name = 'Tin nhắn chat'
        verbose_name_plural = 'Tin nhắn chat'
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.sender}] {self.message[:30]}..."
