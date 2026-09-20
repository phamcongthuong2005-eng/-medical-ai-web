from django.contrib import admin
from .models import BacSi, LichLamViec

@admin.register(BacSi)
class BacSiAdmin(admin.ModelAdmin):
    list_display = ('id', 'ho_ten', 'chuc_danh', 'chuyen_khoa', 'benh_vien', 'so_nam_kinh_nghiem', 'gia_kham', 'trang_thai')
    list_filter = ('benh_vien', 'chuyen_khoa', 'trang_thai')
    search_fields = ('ho_ten', 'user__username')

@admin.register(LichLamViec)
class LichLamViecAdmin(admin.ModelAdmin):
    list_display = ('id', 'bac_si', 'ngay', 'gio_bat_dau', 'gio_ket_thuc', 'so_luong_benh_nhan', 'trang_thai')
    list_filter = ('ngay', 'trang_thai')
    search_fields = ('bac_si__ho_ten',)
