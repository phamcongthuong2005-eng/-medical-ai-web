from django.urls import path
from . import views

urlpatterns = [
    path('', views.doctor_list_view, name='doctor_list'),
    path('<int:pk>/', views.doctor_detail_view, name='doctor_detail'),
    path('dashboard/', views.doctor_dashboard_view, name='doctor_dashboard'),
    path('appointment/<int:appointment_id>/update-status/', views.update_appointment_status_view, name='update_appointment_status'),

    # APIs
    path('api/by-criteria/', views.api_doctors_by_criteria, name='api_doctors_by_criteria'),
    path('api/<int:doctor_id>/slots/', views.api_doctor_slots, name='api_doctor_slots'),
]
