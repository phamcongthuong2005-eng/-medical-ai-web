from django.contrib import admin
from .models import TinhThanh, ChuyenKhoa, BenhVien

@admin.register(TinhThanh)
class TinhThanhAdmin(admin.ModelAdmin):
    list_display = ('id', 'ten_tinh')
    search_fields = ('ten_tinh',)

@admin.register(ChuyenKhoa)
class ChuyenKhoaAdmin(admin.ModelAdmin):
    list_display = ('id', 'ten_chuyen_khoa', 'bieu_tuong')
    search_fields = ('ten_chuyen_khoa',)

@admin.register(BenhVien)
class BenhVienAdmin(admin.ModelAdmin):
    list_display = ('id', 'ten_benh_vien', 'tinh', 'so_dien_thoai', 'trang_thai')
    list_filter = ('tinh', 'trang_thai')
    search_fields = ('ten_benh_vien', 'dia_chi')
    filter_horizontal = ('chuyen_khoas',)
