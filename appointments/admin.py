from django.contrib import admin
from .models import LichKham

@admin.register(LichKham)
class LichKhamAdmin(admin.ModelAdmin):
    list_display = ('ma_lich_kham', 'ten_benh_nhan', 'bac_si', 'benh_vien', 'chuyen_khoa', 'ngay_kham', 'gio_kham', 'trang_thai', 'created_at')
    list_filter = ('trang_thai', 'ngay_kham', 'benh_vien', 'chuyen_khoa')
    search_fields = ('ma_lich_kham', 'ten_benh_nhan', 'so_dien_thoai', 'bac_si__ho_ten')
