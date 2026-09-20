import re
import json
import os
from datetime import datetime, timedelta
from hospitals.models import TinhThanh, BenhVien, ChuyenKhoa
from doctors.models import BacSi, LichLamViec

from django.utils import timezone

# Bộ quy tắc ánh xạ Triệu chứng -> Chuyên khoa & Lời khuyên y tế tham khảo
SYMPTOM_KNOWLEDGE_BASE = {
    'thần kinh': {
        'keywords': ['đau đầu', 'nhức đầu', 'chóng mặt', 'hoa mắt', 'mất ngủ', 'tiền đình', 'đột quỵ', 'tê tay chân', 'co giật', 'nửa đầu'],
        'specialty_name': 'Thần kinh',
        'advice': 'Triệu chứng đau đầu, chóng mặt hoặc mất ngủ có thể xuất phát từ căng thẳng (stress), thiếu máu não, đau nửa đầu Migraine hoặc rối loạn tiền đình. Bạn nên nghỉ ngơi ở nơi thoáng mát, uống đủ nước và tránh làm việc quá sức trước màn hình.',
        'urgent': 'Nếu có dấu hiệu méo miệng, yếu liệt nửa người, nói ngọng hoặc đau đầu dữ dội đột ngột, vui lòng đến ngay cơ sở cấp cứu gần nhất!'
    },
    'tim mạch': {
        'keywords': ['đau ngực', 'tức ngực', 'khó thở', 'hồi hộp', 'tim đập nhanh', 'huyết áp cao', 'tăng huyết áp', 'hạ huyết áp', 'nhói tim'],
        'specialty_name': 'Tim mạch',
        'advice': 'Triệu chứng đau tức ngực hoặc hồi hộp đánh trống ngực cần được thăm khám cẩn thận để tầm soát bệnh lý mạch vành, rối loạn nhịp tim hoặc huyết áp. Bạn nên hạn chế gắng sức và giữ tinh thần thư giãn.',
        'urgent': 'Cơn đau thắt ngực lan ra cánh tay trái, cổ hoặc hàm kéo dài trên 15 phút là dấu hiệu cảnh báo khẩn cấp!'
    },
    'tiêu hóa': {
        'keywords': ['đau bụng', 'đau dạ dày', 'ợ chua', 'ợ hơi', 'trào ngược', 'tiêu chảy', 'táo bón', 'nôn mửa', 'buồn nôn', 'khó tiêu', 'đầy bụng', 'viêm loét'],
        'specialty_name': 'Tiêu hóa',
        'advice': 'Các triệu chứng như đau thượng vị, ợ chua hay đầy hơi thường liên quan đến viêm loét dạ dày tá tràng hoặc trào ngược dạ dày thực quản (GERD). Nên ăn đúng bữa, kiêng đồ chua cay, dầu mỡ và đồ uống có cồn.',
        'urgent': 'Nếu nôn ra máu, đi ngoài phân đen hoặc đau quặn dữ dội, cần đi viện cấp cứu ngay.'
    },
    'tai mũi họng': {
        'keywords': ['đau họng', 'rát họng', 'viêm xoang', 'nghẹt mũi', 'sổ mũi', 'ù tai', 'chảy máu cam', 'khàn tiếng', 'viêm amidan', 'ho khan', 'ho có đờm'],
        'specialty_name': 'Tai Mũi Họng',
        'advice': 'Đau họng, nghẹt mũi thường do viêm đường hô hấp trên hoặc viêm xoang dị ứng khi thời tiết thay đổi. Bạn có thể súc họng bằng nước muối sinh lý ấm, giữ ấm cổ họng.',
        'urgent': 'Nếu sốt cao khó hạ kèm khó thở nặng, cần đến gặp bác sĩ kiểm tra trực tiếp.'
    },
    'nhi khoa': {
        'keywords': ['trẻ em', 'em bé', 'trẻ sơ sinh', 'bé sốt', 'bé quấy khóc', 'biếng ăn', 'bé nôn', 'sởi', 'thủy đậu'],
        'specialty_name': 'Nhi khoa',
        'advice': 'Sức đề kháng của trẻ còn non nớt. Khi bé sốt cần cho mặc quần áo thoáng mát, chườm ấm và bù nước oresol đúng cách. Tuyệt đối không tự ý cho trẻ dùng kháng sinh khi chưa có chỉ định.',
        'urgent': 'Bé sốt cao co giật, bỏ bú, ngủ li bì hoặc thở rút lõm lồng ngực là dấu hiệu cần cấp cứu ngay!'
    },
    'da liễu': {
        'keywords': ['ngứa da', 'dị ứng', 'mẩn đỏ', 'mụn trứng cá', 'chàm', 'vảy nến', 'rụng tóc', 'nổi mề đay', 'phát ban'],
        'specialty_name': 'Da liễu',
        'advice': 'Nổi mẩn ngứa hoặc phát ban có thể do viêm da tiếp xúc, dị ứng thời tiết hoặc thức ăn. Tránh cào gãi làm trầy xước nhiễm trùng và giữ da luôn sạch sẽ.',
        'urgent': 'Nếu phát ban kèm phù môi, mí mắt hoặc khó thở, đây có thể là phản vệ khẩn cấp.'
    },
    'cơ xương khớp': {
        'keywords': ['đau lưng', 'thoát vị', 'đau khớp', 'khớp gối', 'thoái hóa', 'mỏi vai gáy', 'đau nhức xương', 'gút', 'acid uric'],
        'specialty_name': 'Cơ xương khớp',
        'advice': 'Đau mỏi vai gáy hoặc đau khớp gối thường gặp ở người làm việc văn phòng hoặc người cao tuổi do thoái hóa. Nên duy trì vận động nhẹ nhàng, điều chỉnh tư thế ngồi thẳng.',
        'urgent': 'Nếu khớp sưng to nóng đỏ cấp tính hoặc không cử động được, cần thăm khám sớm.'
    },
    'mắt': {
        'keywords': ['đau mắt', 'đỏ mắt', 'mờ mắt', 'cận thị', 'chảy nước mắt', 'cộm mắt', 'mắt nhức'],
        'specialty_name': 'Mắt (Nhãn khoa)',
        'advice': 'Đau mắt, cộm xốn có thể do viêm kết mạc hoặc hội chứng thị giác màn hình. Nhỏ nước mắt nhân tạo, cho mắt nghỉ ngơi theo quy tắc 20-20-20.',
        'urgent': 'Nếu nhìn mờ đột ngột hoặc thấy chớp sáng kèm đau nhức sâu trong hốc mắt, cần khám mắt ngay.'
    },
    'nội tổng quát': {
        'keywords': ['sốt', 'mệt mỏi', 'sụt cân', 'khám tổng quát', 'kiểm tra sức khỏe', 'khám định kỳ', 'ốm'],
        'specialty_name': 'Nội tổng quát',
        'advice': 'Khám Nội tổng quát là bước đầu tiên tối ưu giúp bạn kiểm tra các chỉ số sức khỏe tổng thể, thực hiện xét nghiệm cơ bản và được bác sĩ định hướng điều trị.',
        'urgent': ''
    }
}

DISCLAIMER_TEXT = "💡 *Lưu ý y khoa: Thông tin do AI cung cấp chỉ mang tính chất tham khảo, không thay thế chẩn đoán hoặc đơn thuốc chuyên môn của bác sĩ.*"


def process_medical_chat(user_message, session=None):
    """
    Xử lý tin nhắn của người dùng và trả về phản hồi theo đúng luồng:
    Triệu chứng -> AI phân tích & gợi ý chuyên khoa -> Hỏi Tỉnh -> Gợi ý Bệnh viện thuộc tỉnh -> Gợi ý Bác sĩ -> Hỗ trợ đặt lịch
    """
    msg_clean = user_message.lower().strip()

    response_data = {
        'reply': '',
        'stage': 'general',  # 'symptom_matched', 'province_selected', 'hospital_selected', 'general'
        'suggested_specialty': None,
        'suggested_provinces': [],
        'suggested_hospitals': [],
        'suggested_doctors': [],
        'quick_replies': []
    }

    # 1. Kiểm tra xem người dùng có đang chọn hoặc hỏi về một Tỉnh/Thành phố cụ thể không
    all_provinces = list(TinhThanh.objects.all())
    matched_province = None
    for prov in all_provinces:
        if prov.ten_tinh.lower() in msg_clean:
            matched_province = prov
            break

    if matched_province:
        # Người dùng vừa chọn Tỉnh/Thành phố!
        # Truy vấn danh sách BỆNH VIỆN THUỘC TỈNH ĐÓ
        hospitals_in_province = BenhVien.objects.filter(tinh=matched_province, trang_thai=True).prefetch_related('chuyen_khoas')
        
        hospital_list = []
        for h in hospitals_in_province:
            hospital_list.append({
                'id': h.id,
                'ten': h.ten_benh_vien,
                'dia_chi': h.dia_chi,
                'sdt': h.so_dien_thoai,
                'hinh_anh': h.hinh_anh,
                'chuyen_khoas': [ck.ten_chuyen_khoa for ck in h.chuyen_khoas.all()[:4]]
            })

        response_data['stage'] = 'province_selected'
        response_data['selected_province'] = matched_province.ten_tinh
        response_data['suggested_hospitals'] = hospital_list
        response_data['reply'] = (
            f"📍 **Các bệnh viện uy tín tại {matched_province.ten_tinh}**:\n\n"
            f"Hệ thống tìm thấy **{len(hospital_list)} bệnh viện** tại địa phương này. "
            f"Bạn muốn đặt lịch khám tại bệnh viện nào dưới đây?"
        )
        response_data['quick_replies'] = [h['ten'] for h in hospital_list]
        return response_data

    # 2. Kiểm tra xem người dùng có nhắc đến tên Bệnh viện cụ thể không
    matched_hospital = None
    for h in BenhVien.objects.all():
        if h.ten_benh_vien.lower() in msg_clean:
            matched_hospital = h
            break

    if matched_hospital:
        # Người dùng chọn bệnh viện -> Lấy các bác sĩ làm việc tại bệnh viện đó
        doctors = list(BacSi.objects.filter(benh_vien=matched_hospital, trang_thai=True).select_related('chuyen_khoa', 'user'))
        if len(doctors) < 4:
            # Bổ sung thêm bác sĩ cùng tỉnh để luôn có ít nhất 4 bác sĩ cả nam lẫn nữ
            more_docs = list(BacSi.objects.filter(benh_vien__tinh=matched_hospital.tinh, trang_thai=True).exclude(id__in=[d.id for d in doctors]).select_related('chuyen_khoa', 'user')[:4 - len(doctors)])
            doctors.extend(more_docs)

        doc_list = []
        for d in doctors:
            today = timezone.now().date()
            slots_qs = LichLamViec.objects.filter(bac_si=d, ngay__gte=today, trang_thai=True).order_by('ngay', 'gio_bat_dau')[:8]
            slots_list = []
            for s in slots_qs:
                slots_list.append({
                    'date': s.ngay.strftime('%Y-%m-%d'),
                    'date_display': s.ngay.strftime('%d/%m'),
                    'start_time': s.gio_bat_dau.strftime('%H:%M'),
                    'time_slot': f"{s.gio_bat_dau.strftime('%H:%M')} - {s.gio_ket_thuc.strftime('%H:%M')}"
                })

            gender_label = 'Bác sĩ Nam' if getattr(d.user, 'gender', 'nam') == 'nam' else 'Bác sĩ Nữ'
            doc_list.append({
                'id': d.id,
                'ho_ten': d.ho_ten,
                'chuc_danh': d.chuc_danh,
                'gender': gender_label,
                'chuyen_khoa_id': d.chuyen_khoa.id,
                'chuyen_khoa': d.chuyen_khoa.ten_chuyen_khoa,
                'gia_kham': float(d.gia_kham),
                'anh': d.anh_dai_dien,
                'benh_vien_id': d.benh_vien.id,
                'benh_vien': d.benh_vien.ten_benh_vien,
                'slots': slots_list
            })

        response_data['stage'] = 'hospital_selected'
        response_data['selected_hospital'] = matched_hospital.ten_benh_vien
        response_data['selected_hospital_id'] = matched_hospital.id
        response_data['suggested_doctors'] = doc_list
        response_data['reply'] = (
            f"🏥 Bạn đã chọn: **{matched_hospital.ten_benh_vien}**\n"
            f"📍 Địa chỉ: {matched_hospital.dia_chi}\n"
            f"📞 Hotline: {matched_hospital.so_dien_thoai}\n\n"
            f"Dưới đây là danh sách **bác sĩ chuyên khoa** (gồm cả bác sĩ nam và nữ) đang trực tiếp nhận lịch khám. "
            f"Bạn vui lòng chọn một bác sĩ bên dưới để xem khung giờ trống và tiến hành đặt lịch:"
        )
        return response_data

    # 2b. Kiểm tra xem người dùng có nhắc đến tên Bác sĩ cụ thể không
    matched_doctor = None
    for d in BacSi.objects.filter(trang_thai=True).select_related('benh_vien', 'chuyen_khoa'):
        if d.ho_ten.lower() in msg_clean:
            matched_doctor = d
            break

    if matched_doctor:
        today = timezone.now().date()
        schedules = LichLamViec.objects.filter(bac_si=matched_doctor, ngay__gte=today, trang_thai=True).order_by('ngay', 'gio_bat_dau')[:12]
        slots_list = []
        for s in schedules:
            slots_list.append({
                'date': s.ngay.strftime('%Y-%m-%d'),
                'date_display': s.ngay.strftime('%d/%m/%Y'),
                'start_time': s.gio_bat_dau.strftime('%H:%M'),
                'time_slot': f"{s.gio_bat_dau.strftime('%H:%M')} - {s.gio_ket_thuc.strftime('%H:%M')}"
            })

        response_data['stage'] = 'doctor_selected'
        response_data['selected_doctor'] = {
            'id': matched_doctor.id,
            'ho_ten': matched_doctor.ho_ten,
            'chuc_danh': matched_doctor.chuc_danh,
            'chuyen_khoa_id': matched_doctor.chuyen_khoa.id,
            'chuyen_khoa': matched_doctor.chuyen_khoa.ten_chuyen_khoa,
            'benh_vien_id': matched_doctor.benh_vien.id,
            'benh_vien': matched_doctor.benh_vien.ten_benh_vien,
            'gia_kham': float(matched_doctor.gia_kham),
            'slots': slots_list
        }
        response_data['reply'] = (
            f"👨‍⚕️ Bạn đã chọn: **{matched_doctor.chuc_danh} {matched_doctor.ho_ten}**\n"
            f"🩺 Chuyên khoa: {matched_doctor.chuyen_khoa.ten_chuyen_khoa} • Bệnh viện: {matched_doctor.benh_vien.ten_benh_vien}\n"
            f"💰 Phí khám: {matched_doctor.gia_kham:,.0f} VNĐ\n\n"
            f"Dưới đây là các **ngày và khung giờ khám còn trống** của bác sĩ. Bạn muốn chọn khung giờ nào?"
        )
        return response_data

    # 3. Phân tích triệu chứng người dùng nhập vào
    detected_specialties = []
    matched_advice = []
    matched_urgent = []

    for cat_name, cat_info in SYMPTOM_KNOWLEDGE_BASE.items():
        found = False
        for kw in cat_info['keywords']:
            if kw in msg_clean:
                found = True
                break
        if found:
            detected_specialties.append(cat_info['specialty_name'])
            matched_advice.append(cat_info['advice'])
            if cat_info['urgent']:
                matched_urgent.append(cat_info['urgent'])

    if detected_specialties:
        # Tìm thấy chuyên khoa phù hợp!
        primary_specialty = detected_specialties[0]
        response_data['stage'] = 'symptom_matched'
        response_data['suggested_specialty'] = primary_specialty
        response_data['suggested_provinces'] = [p.ten_tinh for p in all_provinces]
        response_data['quick_replies'] = [p.ten_tinh for p in all_provinces]

        # Lấy 4 bác sĩ (cả nam lẫn nữ) của chuyên khoa này
        specialty_doctors = BacSi.objects.filter(
            chuyen_khoa__ten_chuyen_khoa=primary_specialty,
            trang_thai=True
        ).select_related('benh_vien', 'chuyen_khoa', 'user')[:4]

        doc_list = []
        for d in specialty_doctors:
            today = timezone.now().date()
            slots_qs = LichLamViec.objects.filter(bac_si=d, ngay__gte=today, trang_thai=True).order_by('ngay', 'gio_bat_dau')[:8]
            slots_list = []
            for s in slots_qs:
                slots_list.append({
                    'date': s.ngay.strftime('%Y-%m-%d'),
                    'date_display': s.ngay.strftime('%d/%m'),
                    'start_time': s.gio_bat_dau.strftime('%H:%M'),
                    'time_slot': f"{s.gio_bat_dau.strftime('%H:%M')} - {s.gio_ket_thuc.strftime('%H:%M')}"
                })

            gender_label = 'Bác sĩ Nam' if getattr(d.user, 'gender', 'nam') == 'nam' else 'Bác sĩ Nữ'
            doc_list.append({
                'id': d.id,
                'ho_ten': d.ho_ten,
                'chuc_danh': d.chuc_danh,
                'gender': gender_label,
                'chuyen_khoa_id': d.chuyen_khoa.id,
                'chuyen_khoa': d.chuyen_khoa.ten_chuyen_khoa,
                'gia_kham': float(d.gia_kham),
                'anh': d.anh_dai_dien,
                'benh_vien_id': d.benh_vien.id,
                'benh_vien': d.benh_vien.ten_benh_vien,
                'slots': slots_list
            })
        response_data['suggested_doctors'] = doc_list

        specialty_text = " hoặc ".join([f"**{s}**" for s in detected_specialties[:2]])
        advice_text = " ".join(matched_advice[:1])
        urgent_text = f"\n\n⚠️ **Lưu ý khẩn:** {matched_urgent[0]}" if matched_urgent else ""

        response_data['reply'] = (
            f"🤖 **Phân tích của AI:**\n"
            f"Dựa trên các triệu chứng bạn vừa chia sẻ, hệ thống đề xuất bạn nên khám chuyên khoa {specialty_text}.\n\n"
            f"🩺 **Tư vấn tham khảo:**\n{advice_text}{urgent_text}\n\n"
            f"{DISCLAIMER_TEXT}\n\n"
            f"👨‍⚕️ **Đội ngũ bác sĩ chuyên khoa {primary_specialty} sẵn sàng nhận lịch (cả bác sĩ nam & nữ):**\n"
            f"Bạn có thể bấm **'Chọn bác sĩ này'** bên dưới để đặt lịch trực tiếp, hoặc chọn **Tỉnh/Thành phố** để xem bệnh viện gần bạn nhất:"
        )
        return response_data

    # 4. Người dùng chào hỏi hoặc hỏi chung
    greetings = ['xin chào', 'chào bạn', 'hello', 'hi', 'bạn là ai', 'có ai ở đây không']
    if any(g in msg_clean for g in greetings):
        response_data['reply'] = (
            "👋 Xin chào bạn! Tôi là **Trợ lý Y tế AI** của Medical AI.\n\n"
            "Tôi có thể hỗ trợ bạn:\n"
            "1. 💬 **Phân tích triệu chứng** và tư vấn thông tin y tế tham khảo.\n"
            "2. 🩺 **Gợi ý chuyên khoa** phù hợp với vấn đề sức khỏe của bạn.\n"
            "3. 🏥 **Tìm bệnh viện theo tỉnh/thành phố** (Đà Nẵng, Hà Nội, TP.HCM,...).\n"
            "4. 👨‍⚕️ **Xem lịch bác sĩ và đặt lịch khám** trực tuyến nhanh chóng.\n\n"
            "👉 Hãy cho tôi biết bạn đang gặp phải triệu chứng gì? *(Ví dụ: 'Tôi bị đau đầu chóng mặt', 'Tôi bị đau dạ dày và ợ chua', 'Tôi muốn khám ở Đà Nẵng')*"
        )
        response_data['quick_replies'] = ['Tôi bị đau đầu, chóng mặt', 'Tôi bị đau tức ngực', 'Tôi bị đau dạ dày', 'Khám tại Đà Nẵng']
        return response_data

    # 5. Phản hồi mặc định thông minh
    response_data['reply'] = (
        "Cảm ơn bạn đã nhắn tin. Để tôi có thể hỗ trợ tư vấn và định hướng chuyên khoa chính xác nhất, "
        "bạn vui lòng mô tả cụ thể hơn về các triệu chứng bạn đang gặp phải (ví dụ: bị đau ở đâu, kéo dài bao lâu, có kèm sốt hay khó chịu khác không?).\n\n"
        "Hoặc bạn có thể chọn Tỉnh/Thành phố bên dưới để xem danh sách bệnh viện và đặt lịch khám trực tiếp:"
    )
    response_data['suggested_provinces'] = [p.ten_tinh for p in all_provinces]
    response_data['quick_replies'] = [p.ten_tinh for p in all_provinces]
    return response_data
