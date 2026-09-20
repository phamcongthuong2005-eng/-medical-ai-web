from django.urls import path
from . import views

urlpatterns = [
    path('', views.hospital_list_view, name='hospital_list'),
    path('<int:pk>/', views.hospital_detail_view, name='hospital_detail'),

    # APIs cho AJAX & Chatbot
    path('api/provinces/', views.api_provinces, name='api_provinces'),
    path('api/by-province/<int:tinh_id>/', views.api_hospitals_by_province, name='api_hospitals_by_province'),
    path('api/<int:hospital_id>/specialties/', views.api_specialties_by_hospital, name='api_specialties_by_hospital'),
]
