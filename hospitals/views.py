from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
from .models import TinhThanh, ChuyenKhoa, BenhVien

def hospital_list_view(request):
    """
    Trang danh sách bệnh viện có bộ lọc động theo Tỉnh/Thành phố và Chuyên khoa
    """
    tinh_id = request.GET.get('tinh')
    chuyen_khoa_id = request.GET.get('chuyen_khoa')
    keyword = request.GET.get('q', '').strip()

    provinces = TinhThanh.objects.all()
    specialties = ChuyenKhoa.objects.all()

    hospitals = BenhVien.objects.filter(trang_thai=True).select_related('tinh').prefetch_related('chuyen_khoas')

    # Lọc theo Tỉnh/Thành phố nếu người dùng chọn
    selected_province = None
    if tinh_id:
        hospitals = hospitals.filter(tinh_id=tinh_id)
        selected_province = TinhThanh.objects.filter(id=tinh_id).first()

    # Lọc theo Chuyên khoa nếu có
    selected_specialty = None
    if chuyen_khoa_id:
        hospitals = hospitals.filter(chuyen_khoas__id=chuyen_khoa_id)
        selected_specialty = ChuyenKhoa.objects.filter(id=chuyen_khoa_id).first()

    # Tìm kiếm từ khóa
    if keyword:
        hospitals = hospitals.filter(
            Q(ten_benh_vien__icontains=keyword) |
            Q(dia_chi__icontains=keyword) |
            Q(mo_ta__icontains=keyword)
        )

    context = {
        'hospitals': hospitals,
        'provinces': provinces,
        'specialties': specialties,
        'selected_province': selected_province,
        'selected_specialty': selected_specialty,
        'keyword': keyword,
        'total_count': hospitals.count(),
    }
    return render(request, 'hospitals/hospital_list.html', context)


def hospital_detail_view(request, pk):
    """
    Chi tiết bệnh viện và các bác sĩ làm việc tại bệnh viện đó
    """
    hospital = get_object_or_404(BenhVien.objects.select_related('tinh').prefetch_related('chuyen_khoas'), pk=pk)
    doctors = hospital.bac_sis.filter(trang_thai=True).select_related('chuyen_khoa')
    return render(request, 'hospitals/hospital_detail.html', {
        'hospital': hospital,
        'doctors': doctors,
    })


# ================= AJAX API ENDPOINTS =================
def api_provinces(request):
    """API trả về danh sách tất cả Tỉnh/Thành phố"""
    provinces = list(TinhThanh.objects.values('id', 'ten_tinh'))
    return JsonResponse({'status': 'success', 'data': provinces})


def api_hospitals_by_province(request, tinh_id):
    """
    API cốt lõi: Chọn tỉnh -> Lấy danh sách bệnh viện thuộc tỉnh đó
    """
    hospitals = BenhVien.objects.filter(tinh_id=tinh_id, trang_thai=True)
    
    # Nếu có lọc thêm chuyên khoa
    ck_id = request.GET.get('chuyen_khoa_id')
    if ck_id:
        hospitals = hospitals.filter(chuyen_khoas__id=ck_id)

    data = []
    for h in hospitals:
        data.append({
            'id': h.id,
            'ten_benh_vien': h.ten_benh_vien,
            'dia_chi': h.dia_chi,
            'so_dien_thoai': h.so_dien_thoai,
            'email': h.email,
            'hinh_anh': h.hinh_anh,
            'website': h.website,
            'mo_ta': h.mo_ta,
            'chuyen_khoas': list(h.chuyen_khoas.values('id', 'ten_chuyen_khoa'))
        })
    return JsonResponse({'status': 'success', 'tinh_id': tinh_id, 'data': data})


def api_specialties_by_hospital(request, hospital_id):
    """API lấy các chuyên khoa có tại bệnh viện đã chọn"""
    hospital = get_object_or_404(BenhVien, pk=hospital_id)
    specialties = list(hospital.chuyen_khoas.values('id', 'ten_chuyen_khoa', 'bieu_tuong'))
    return JsonResponse({'status': 'success', 'hospital_id': hospital_id, 'data': specialties})
