from django.db import models
from django.conf import settings
from hospitals.models import BenhVien, ChuyenKhoa
from doctors.models import BacSi
import uuid

class LichKham(models.Model):
    STATUS_CHOICES = (
        ('Cho_xac_nhan', 'Chờ xác nhận'),
        ('Da_xac_nhan', 'Đã xác nhận'),
        ('Da_huy', 'Đã hủy'),
        ('Da_kham', 'Đã khám xong'),
    )

    ma_lich_kham = models.CharField(max_length=20, unique=True, editable=False, verbose_name='Mã đặt lịch')
    benh_nhan = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lich_khams', verbose_name='Bệnh nhân')
    benh_vien = models.ForeignKey(BenhVien, on_delete=models.CASCADE, related_name='lich_khams', verbose_name='Bệnh viện')
    chuyen_khoa = models.ForeignKey(ChuyenKhoa, on_delete=models.CASCADE, related_name='lich_khams', verbose_name='Chuyên khoa')
    bac_si = models.ForeignKey(BacSi, on_delete=models.CASCADE, related_name='lich_khams', verbose_name='Bác sĩ phụ trách')
    ngay_kham = models.DateField(verbose_name='Ngày khám')
    gio_kham = models.TimeField(verbose_name='Giờ khám')
    trieu_chung = models.TextField(blank=True, null=True, verbose_name='Triệu chứng mô tả')
    ly_do_kham = models.CharField(max_length=255, blank=True, null=True, verbose_name='Lý do khám')
    ten_benh_nhan = models.CharField(max_length=150, blank=True, null=True, verbose_name='Tên người khám')
    so_dien_thoai = models.CharField(max_length=20, blank=True, null=True, verbose_name='Số điện thoại liên hệ')
    trang_thai = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Cho_xac_nhan', verbose_name='Trạng thái lịch')
    ghi_chu_bac_si = models.TextField(blank=True, null=True, verbose_name='Ghi chú/Chẩn đoán của bác sĩ')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Thời điểm đặt lịch')

    def save(self, *args, **kwargs):
        if not self.ma_lich_kham:
            self.ma_lich_kham = f"LK-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Lịch khám'
        verbose_name_plural = 'Lịch khám'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.ma_lich_kham}] {self.ten_benh_nhan or self.benh_nhan.username} - {self.bac_si.ho_ten} ({self.ngay_kham} {self.gio_kham})"
