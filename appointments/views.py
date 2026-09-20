from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime
import json

from .models import LichKham
from hospitals.models import TinhThanh, BenhVien, ChuyenKhoa
from doctors.models import BacSi, LichLamViec
from accounts.models import User

def booking_wizard_view(request):
    """
    Giao diện đặt lịch khám thông minh 7 bước:
    Triệu chứng -> Chuyên khoa -> Tỉnh thành -> Bệnh viện -> Bác sĩ -> Ngày/Giờ -> Đặt lịch
    """
    provinces = TinhThanh.objects.all()
    specialties = ChuyenKhoa.objects.all()
    hospitals = BenhVien.objects.filter(trang_thai=True)

    # Pre-select từ URL nếu có
    init_tinh = request.GET.get('tinh', '')
    init_hospital = request.GET.get('hospital', '')
    init_specialty = request.GET.get('specialty', '')
    init_doctor = request.GET.get('doctor', '')
    init_symptom = request.GET.get('symptom', '')

    context = {
        'provinces': provinces,
        'specialties': specialties,
        'hospitals': hospitals,
        'init_tinh': init_tinh,
        'init_hospital': init_hospital,
        'init_specialty': init_specialty,
        'init_doctor': init_doctor,
        'init_symptom': init_symptom,
    }
    return render(request, 'appointments/booking.html', context)


@login_required
def my_appointments_view(request):
    """
    Trang xem lịch khám cá nhân của bệnh nhân
    """
    appointments = LichKham.objects.filter(benh_nhan=request.user).select_related(
        'benh_vien', 'benh_vien__tinh', 'chuyen_khoa', 'bac_si'
    ).order_by('-created_at')

    return render(request, 'appointments/my_appointments.html', {
        'appointments': appointments
    })


@login_required
def cancel_appointment_view(request, pk):
    """
    Bệnh nhân tự hủy lịch khám của mình
    """
    appointment = get_object_or_404(LichKham, pk=pk, benh_nhan=request.user)
    if appointment.trang_thai in ['Cho_xac_nhan', 'Da_xac_nhan']:
        appointment.trang_thai = 'Da_huy'
        appointment.save()
        messages.success(request, f'Đã hủy thành công cuộc hẹn [{appointment.ma_lich_kham}].')
    else:
        messages.error(request, 'Không thể hủy lịch khám ở trạng thái hiện tại.')
    return redirect('my_appointments')


def booking_success_view(request, pk):
    appointment = get_object_or_404(LichKham.objects.select_related('benh_vien', 'chuyen_khoa', 'bac_si'), pk=pk)
    return render(request, 'appointments/booking_success.html', {'appointment': appointment})


# ================= AJAX API ĐẶT LỊCH (Dùng chung cho cả Form và AI Chatbot) =================
def api_create_appointment(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Chỉ chấp nhận phương thức POST'}, status=405)

    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        hospital_id = data.get('hospital_id')
        specialty_id = data.get('specialty_id')
        doctor_id = data.get('doctor_id')
        date_str = data.get('date')
        time_str = data.get('time')
        full_name = data.get('full_name', '').strip()
        phone = data.get('phone', '').strip()
        symptom = data.get('symptom', '').strip()
        reason = data.get('reason', '').strip()

        # Kiểm tra tính hợp lệ dữ liệu
        if not all([hospital_id, specialty_id, doctor_id, date_str, time_str]):
            return JsonResponse({'status': 'error', 'message': 'Vui lòng chọn đầy đủ Bệnh viện, Chuyên khoa, Bác sĩ, Ngày và Giờ khám!'}, status=400)

        hospital = get_object_or_404(BenhVien, pk=hospital_id)
        specialty = get_object_or_404(ChuyenKhoa, pk=specialty_id)
        doctor = get_object_or_404(BacSi, pk=doctor_id)

        try:
            booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            booking_time = datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Định dạng ngày hoặc giờ không hợp lệ'}, status=400)

        # Xác định user đặt lịch
        if request.user.is_authenticated:
            user = request.user
            if not full_name:
                full_name = user.full_name or user.username
            if not phone:
                phone = user.phone or ''
        else:
            # Khách vãng lai: Tạo hoặc liên kết user tạm
            if not phone:
                return JsonResponse({'status': 'error', 'message': 'Vui lòng nhập số điện thoại để liên hệ xác nhận!'}, status=400)
            username_guest = f"guest_{phone}"
            user, _ = User.objects.get_or_create(
                username=username_guest,
                defaults={
                    'full_name': full_name or 'Bệnh nhân',
                    'phone': phone,
                    'role': 'patient',
                }
            )

        # Kiểm tra slot có còn khả dụng không
        existing_count = LichKham.objects.filter(
            bac_si=doctor,
            ngay_kham=booking_date,
            gio_kham=booking_time,
            trang_thai__in=['Cho_xac_nhan', 'Da_xac_nhan']
        ).count()

        # Giới hạn mỗi slot tối đa 4 người
        if existing_count >= 4:
            return JsonResponse({'status': 'error', 'message': 'Khung giờ này đã đầy, vui lòng chọn khung giờ khác!'}, status=400)

        # Tạo lịch khám
        appointment = LichKham.objects.create(
            benh_nhan=user,
            benh_vien=hospital,
            chuyen_khoa=specialty,
            bac_si=doctor,
            ngay_kham=booking_date,
            gio_kham=booking_time,
            ten_benh_nhan=full_name,
            so_dien_thoai=phone,
            trieu_chung=symptom,
            ly_do_kham=reason or 'Đặt lịch qua hệ thống Medical AI',
            trang_thai='Cho_xac_nhan'
        )

        return JsonResponse({
            'status': 'success',
            'message': 'Đặt lịch khám thành công!',
            'appointment': {
                'id': appointment.id,
                'ma_lich_kham': appointment.ma_lich_kham,
                'benh_vien': hospital.ten_benh_vien,
                'chuyen_khoa': specialty.ten_chuyen_khoa,
                'bac_si': doctor.ho_ten,
                'chuc_danh': doctor.chuc_danh,
                'ngay_kham': appointment.ngay_kham.strftime('%d/%m/%Y'),
                'gio_kham': appointment.gio_kham.strftime('%H:%M'),
                'ten_benh_nhan': appointment.ten_benh_nhan,
                'so_dien_thoai': appointment.so_dien_thoai,
                'trang_thai': appointment.get_trang_thai_display(),
            }
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
