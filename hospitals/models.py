from django.db import models

class TinhThanh(models.Model):
    ten_tinh = models.CharField(max_length=100, unique=True, verbose_name='Tên tỉnh/thành phố')

    class Meta:
        verbose_name = 'Tỉnh / Thành phố'
        verbose_name_plural = 'Tỉnh / Thành phố'
        ordering = ['ten_tinh']

    def __str__(self):
        return self.ten_tinh


class ChuyenKhoa(models.Model):
    ten_chuyen_khoa = models.CharField(max_length=150, verbose_name='Tên chuyên khoa')
    mo_ta = models.TextField(blank=True, null=True, verbose_name='Mô tả chuyên khoa')
    bieu_tuong = models.CharField(max_length=50, default='bi-heart-pulse', verbose_name='Icon Bootstrap')

    class Meta:
        verbose_name = 'Chuyên khoa'
        verbose_name_plural = 'Chuyên khoa'
        ordering = ['ten_chuyen_khoa']

    def __str__(self):
        return self.ten_chuyen_khoa


class BenhVien(models.Model):
    tinh = models.ForeignKey(TinhThanh, on_delete=models.CASCADE, related_name='benh_viens', verbose_name='Tỉnh/Thành phố')
    ten_benh_vien = models.CharField(max_length=255, verbose_name='Tên bệnh viện')
    dia_chi = models.CharField(max_length=255, verbose_name='Địa chỉ')
    so_dien_thoai = models.CharField(max_length=20, blank=True, null=True, verbose_name='Số điện thoại')
    email = models.EmailField(blank=True, null=True, verbose_name='Email liên hệ')
    mo_ta = models.TextField(blank=True, null=True, verbose_name='Mô tả bệnh viện')
    website = models.URLField(blank=True, null=True, verbose_name='Website')
    hinh_anh = models.CharField(max_length=500, blank=True, null=True, default='https://images.unsplash.com/photo-1587351021759-3e566b6af7cc?w=800', verbose_name='Ảnh đại diện URL')
    trang_thai = models.BooleanField(default=True, verbose_name='Đang hoạt động')
    chuyen_khoas = models.ManyToManyField(ChuyenKhoa, related_name='benh_viens', blank=True, verbose_name='Các chuyên khoa cung cấp')

    class Meta:
        verbose_name = 'Bệnh viện'
        verbose_name_plural = 'Bệnh viện'
        ordering = ['ten_benh_vien']

    def __str__(self):
        return f"{self.ten_benh_vien} ({self.tinh.ten_tinh})"
