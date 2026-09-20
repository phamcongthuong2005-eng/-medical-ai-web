from django.urls import path
from . import views

urlpatterns = [
    path('', views.booking_wizard_view, name='booking_wizard'),
    path('booking/', views.booking_wizard_view),
    path('my-appointments/', views.my_appointments_view, name='my_appointments'),
    path('<int:pk>/cancel/', views.cancel_appointment_view, name='cancel_appointment'),
    path('<int:pk>/success/', views.booking_success_view, name='booking_success'),

    # API
    path('api/create/', views.api_create_appointment, name='api_create_appointment'),
]
