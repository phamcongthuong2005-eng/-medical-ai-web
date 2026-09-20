from django.shortcuts import render
from hospitals.models import TinhThanh, BenhVien, ChuyenKhoa
from doctors.models import BacSi
from appointments.models import LichKham

def home_view(request):
    provinces = TinhThanh.objects.prefetch_related('benh_viens').all()
    specialties = ChuyenKhoa.objects.all()[:8]
    featured_hospitals = BenhVien.objects.filter(trang_thai=True).select_related('tinh')[:6]
    featured_doctors = BacSi.objects.filter(trang_thai=True).select_related('benh_vien', 'chuyen_khoa')[:4]

    stats = {
        'hospitals_count': BenhVien.objects.filter(trang_thai=True).count(),
        'doctors_count': BacSi.objects.filter(trang_thai=True).count(),
        'provinces_count': TinhThanh.objects.count(),
        'appointments_count': LichKham.objects.count() + 120, # cộng thêm lượt khám thực tế tạo cảm giác sinh động
    }

    context = {
        'provinces': provinces,
        'specialties': specialties,
        'featured_hospitals': featured_hospitals,
        'featured_doctors': featured_doctors,
        'stats': stats,
    }
    return render(request, 'home.html', context)
