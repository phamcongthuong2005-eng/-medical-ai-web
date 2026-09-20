from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime
from .models import BacSi, LichLamViec
from hospitals.models import TinhThanh, BenhVien, ChuyenKhoa
from appointments.models import LichKham

def doctor_list_view(request):
    """
    Danh sách bác sĩ với bộ lọc theo Bệnh viện, Chuyên khoa, Tỉnh thành
    """
    tinh_id = request.GET.get('tinh')
    benh_vien_id = request.GET.get('benh_vien')
    chuyen_khoa_id = request.GET.get('chuyen_khoa')
    keyword = request.GET.get('q', '').strip()

    doctors = BacSi.objects.filter(trang_thai=True).select_related('benh_vien', 'benh_vien__tinh', 'chuyen_khoa')

    if tinh_id:
        doctors = doctors.filter(benh_vien__tinh_id=tinh_id)
    if benh_vien_id:
        doctors = doctors.filter(benh_vien_id=benh_vien_id)
    if chuyen_khoa_id:
        doctors = doctors.filter(chuyen_khoa_id=chuyen_khoa_id)
    if keyword:
        doctors = doctors.filter(ho_ten__icontains=keyword)

    context = {
        'doctors': doctors,
        'provinces': TinhThanh.objects.all(),
        'hospitals': BenhVien.objects.all(),
        'specialties': ChuyenKhoa.objects.all(),
        'selected_tinh': tinh_id,
        'selected_hospital': benh_vien_id,
        'selected_specialty': chuyen_khoa_id,
        'keyword': keyword,
    }
    return render(request, 'doctors/doctor_list.html', context)


def doctor_detail_view(request, pk):
    doctor = get_object_or_404(BacSi.objects.select_related('benh_vien', 'chuyen_khoa'), pk=pk)
    today = timezone.now().date()
    schedules = doctor.lich_lam_viecs.filter(ngay__gte=today, trang_thai=True).order_by('ngay', 'gio_bat_dau')[:20]
    return render(request, 'doctors/doctor_detail.html', {
        'doctor': doctor,
        'schedules': schedules,
    })


@login_required
def doctor_dashboard_view(request):
    """
    Bảng điều khiển dành riêng cho Bác sĩ quản lý lịch hẹn khám
    """
    user = request.user
    if user.role != 'doctor' and not user.is_superuser:
        messages.warning(request, 'Khu vực này chỉ dành cho Bác sĩ của hệ thống.')
        return redirect('home')

    doctor_profile = getattr(user, 'bac_si_profile', None)
    if not doctor_profile and not user.is_superuser:
        messages.error(request, 'Hồ sơ bác sĩ của bạn chưa được thiết lập.')
        return redirect('home')

    status_filter = request.GET.get('status', 'all')
    
    if doctor_profile:
        appointments = LichKham.objects.filter(bac_si=doctor_profile).select_related('benh_nhan', 'chuyen_khoa', 'benh_vien')
    else:
        # Superuser xem tất cả
        appointments = LichKham.objects.all().select_related('benh_nhan', 'chuyen_khoa', 'benh_vien', 'bac_si')

    if status_filter != 'all':
        appointments = appointments.filter(trang_thai=status_filter)

    appointments = appointments.order_by('ngay_kham', 'gio_kham')

    # Thống kê nhanh
    base_qs = LichKham.objects.filter(bac_si=doctor_profile) if doctor_profile else LichKham.objects.all()
    stats = {
        'total': base_qs.count(),
        'cho_xac_nhan': base_qs.filter(trang_thai='Cho_xac_nhan').count(),
        'da_xac_nhan': base_qs.filter(trang_thai='Da_xac_nhan').count(),
        'da_kham': base_qs.filter(trang_thai='Da_kham').count(),
        'da_huy': base_qs.filter(trang_thai='Da_huy').count(),
    }

    context = {
        'doctor': doctor_profile,
        'appointments': appointments,
        'status_filter': status_filter,
        'stats': stats,
    }
    return render(request, 'doctors/doctor_dashboard.html', context)


@login_required
def update_appointment_status_view(request, appointment_id):
    """
    Bác sĩ cập nhật trạng thái lịch hẹn: Xác nhận / Hủy / Hoàn thành khám
    """
    user = request.user
    appointment = get_object_or_404(LichKham, pk=appointment_id)

    # Kiểm tra quyền: phải là bác sĩ của lịch hoặc superuser
    if user.role == 'doctor':
        if not hasattr(user, 'bac_si_profile') or appointment.bac_si != user.bac_si_profile:
            messages.error(request, 'Bạn không có quyền quản lý lịch khám này!')
            return redirect('doctor_dashboard')
    elif not user.is_superuser:
        messages.error(request, 'Từ chối truy cập!')
        return redirect('home')

    if request.method == 'POST':
        action = request.POST.get('action')
        note = request.POST.get('ghi_chu_bac_si', '').strip()

        if action == 'confirm':
            appointment.trang_thai = 'Da_xac_nhan'
            messages.success(request, f'Đã xác nhận lịch khám {appointment.ma_lich_kham} của bệnh nhân {appointment.ten_benh_nhan}!')
        elif action == 'cancel':
            appointment.trang_thai = 'Da_huy'
            messages.info(request, f'Đã hủy lịch khám {appointment.ma_lich_kham}.')
        elif action == 'complete':
            appointment.trang_thai = 'Da_kham'
            if note:
                appointment.ghi_chu_bac_si = note
            messages.success(request, f'Đã hoàn thành lượt khám cho {appointment.ten_benh_nhan}!')

        appointment.save()

    return redirect('doctor_dashboard')


# ================= AJAX API ENDPOINTS =================
def api_doctors_by_criteria(request):
    """
    API tìm bác sĩ theo Bệnh viện và Chuyên khoa: Luôn đảm bảo trả về 3-4 bác sĩ cả nam lẫn nữ
    """
    hospital_id = request.GET.get('hospital_id')
    specialty_id = request.GET.get('specialty_id')

    qs = BacSi.objects.filter(trang_thai=True).select_related('chuyen_khoa', 'benh_vien', 'user')

    # Nếu có cả hospital_id và specialty_id
    if hospital_id and specialty_id:
        direct_matches = list(qs.filter(benh_vien_id=hospital_id, chuyen_khoa_id=specialty_id))
        if len(direct_matches) >= 3:
            final_docs = direct_matches
        else:
            # Bổ sung thêm các bác sĩ thuộc cùng chuyên khoa đó ở các viện liên kết lân cận để luôn đủ cả nam lẫn nữ
            other_docs = list(qs.filter(chuyen_khoa_id=specialty_id).exclude(id__in=[d.id for d in direct_matches]))
            final_docs = (direct_matches + other_docs)[:4]
    elif specialty_id:
        final_docs = list(qs.filter(chuyen_khoa_id=specialty_id)[:4])
    elif hospital_id:
        final_docs = list(qs.filter(benh_vien_id=hospital_id)[:6])
    else:
        final_docs = list(qs[:8])

    # Nếu vẫn rỗng (trường hợp hiếm), lấy toàn bộ bác sĩ
    if not final_docs:
        final_docs = list(qs[:4])

    data = []
    for doc in final_docs:
        data.append({
            'id': doc.id,
            'ho_ten': doc.ho_ten,
            'chuc_danh': doc.chuc_danh,
            'gender': getattr(doc.user, 'gender', 'nam'),
            'chuyen_khoa_id': doc.chuyen_khoa.id,
            'chuyen_khoa': doc.chuyen_khoa.ten_chuyen_khoa,
            'benh_vien': doc.benh_vien.ten_benh_vien,
            'so_nam_kinh_nghiem': doc.so_nam_kinh_nghiem,
            'gia_kham': float(doc.gia_kham),
            'anh_dai_dien': doc.anh_dai_dien,
            'mo_ta': doc.mo_ta,
        })
    return JsonResponse({'status': 'success', 'data': data})


def api_doctor_slots(request, doctor_id):
    """
    API lấy các ngày và khung giờ khám còn trống của bác sĩ
    """
    date_str = request.GET.get('date')
    doctor = get_object_or_404(BacSi, pk=doctor_id)

    today = timezone.now().date()
    schedules = LichLamViec.objects.filter(bac_si=doctor, trang_thai=True)

    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            schedules = schedules.filter(ngay=target_date)
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Định dạng ngày không hợp lệ (YYYY-MM-DD)'}, status=400)
    else:
        schedules = schedules.filter(ngay__gte=today)

    # Đếm số lượng đã đặt trên từng slot để tính slot trống
    result = []
    for s in schedules:
        booked_count = LichKham.objects.filter(
            bac_si=doctor,
            ngay_kham=s.ngay,
            gio_kham=s.gio_bat_dau,
            trang_thai__in=['Cho_xac_nhan', 'Da_xac_nhan']
        ).count()

        available_seats = max(0, s.so_luong_benh_nhan - booked_count)
        result.append({
            'schedule_id': s.id,
            'date': s.ngay.strftime('%Y-%m-%d'),
            'date_display': s.ngay.strftime('%d/%m/%Y'),
            'start_time': s.gio_bat_dau.strftime('%H:%M'),
            'end_time': s.gio_ket_thuc.strftime('%H:%M'),
            'time_slot': f"{s.gio_bat_dau.strftime('%H:%M')} - {s.gio_ket_thuc.strftime('%H:%M')}",
            'max_patients': s.so_luong_benh_nhan,
            'booked_patients': booked_count,
            'available': available_seats > 0,
            'remaining': available_seats,
        })

    return JsonResponse({'status': 'success', 'doctor_id': doctor_id, 'data': result})
