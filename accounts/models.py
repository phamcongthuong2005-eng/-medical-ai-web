from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('patient', 'Bệnh nhân'),
        ('doctor', 'Bác sĩ'),
        ('admin', 'Quản trị viên'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient', verbose_name='Vai trò')
    phone = models.CharField(max_length=15, blank=True, null=True, verbose_name='Số điện thoại')
    full_name = models.CharField(max_length=150, blank=True, null=True, verbose_name='Họ và tên')
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name='Địa chỉ')
    date_of_birth = models.DateField(blank=True, null=True, verbose_name='Ngày sinh')
    gender = models.CharField(max_length=10, choices=(('nam', 'Nam'), ('nu', 'Nữ'), ('khac', 'Khác')), default='nam', verbose_name='Giới tính')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='Ảnh đại diện')

    def save(self, *args, **kwargs):
        if not self.full_name and (self.first_name or self.last_name):
            self.full_name = f"{self.last_name} {self.first_name}".strip()
        super().save(*args, **kwargs)

    def is_patient(self):
        return self.role == 'patient'

    def is_doctor(self):
        return self.role == 'doctor'

    def is_admin_role(self):
        return self.role == 'admin' or self.is_superuser

    def __str__(self):
        return self.full_name or self.username
