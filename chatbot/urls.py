from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_page_view, name='chat_page'),
    path('api/send/', views.api_send_message, name='api_send_message'),
    path('api/history/', views.api_get_history, name='api_get_history'),
]
