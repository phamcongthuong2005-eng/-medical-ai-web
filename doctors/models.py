from django.db import models
from django.conf import settings
from hospitals.models import BenhVien, ChuyenKhoa

class BacSi(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bac_si_profile', verbose_name='Tài khoản người dùng')
    benh_vien = models.ForeignKey(BenhVien, on_delete=models.CASCADE, related_name='bac_sis', verbose_name='Bệnh viện công tác')
    chuyen_khoa = models.ForeignKey(ChuyenKhoa, on_delete=models.CASCADE, related_name='bac_sis', verbose_name='Chuyên khoa')
    ho_ten = models.CharField(max_length=150, verbose_name='Họ và tên bác sĩ')
    chuc_danh = models.CharField(max_length=100, default='Bác sĩ Chuyên khoa I', verbose_name='Chức danh / Học vị')
    so_nam_kinh_nghiem = models.PositiveIntegerField(default=5, verbose_name='Số năm kinh nghiệm')
    mo_ta = models.TextField(blank=True, null=True, verbose_name='Tiểu sử & Chuyên môn')
    anh_dai_dien = models.CharField(max_length=500, blank=True, null=True, default='https://images.unsplash.com/photo-1622253692010-333f2da6031d?w=600', verbose_name='Ảnh đại diện URL')
    gia_kham = models.DecimalField(max_digits=10, decimal_places=0, default=200000, verbose_name='Giá khám tham khảo (VNĐ)')
    trang_thai = models.BooleanField(default=True, verbose_name='Sẵn sàng nhận lịch')

    class Meta:
        verbose_name = 'Bác sĩ'
        verbose_name_plural = 'Bác sĩ'
        ordering = ['ho_ten']

    def __str__(self):
        return f"{self.chuc_danh} {self.ho_ten} ({self.chuyen_khoa.ten_chuyen_khoa} - {self.benh_vien.ten_benh_vien})"


class LichLamViec(models.Model):
    bac_si = models.ForeignKey(BacSi, on_delete=models.CASCADE, related_name='lich_lam_viecs', verbose_name='Bác sĩ')
    ngay = models.DateField(verbose_name='Ngày làm việc')
    gio_bat_dau = models.TimeField(verbose_name='Giờ bắt đầu')
    gio_ket_thuc = models.TimeField(verbose_name='Giờ kết thúc')
    so_luong_benh_nhan = models.PositiveIntegerField(default=5, verbose_name='Số lượng bệnh nhân tối đa/khung')
    trang_thai = models.BooleanField(default=True, verbose_name='Hoạt động')

    class Meta:
        verbose_name = 'Lịch làm việc bác sĩ'
        verbose_name_plural = 'Lịch làm việc bác sĩ'
        ordering = ['ngay', 'gio_bat_dau']

    def __str__(self):
        return f"{self.bac_si.ho_ten} | {self.ngay} | {self.gio_bat_dau.strftime('%H:%M')} - {self.gio_ket_thuc.strftime('%H:%M')}"
