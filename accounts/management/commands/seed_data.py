import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta, time
from accounts.models import User
from hospitals.models import TinhThanh, ChuyenKhoa, BenhVien
from doctors.models import BacSi, LichLamViec
from appointments.models import LichKham

class Command(BaseCommand):
    help = 'Khởi tạo dữ liệu mẫu cho Website Y tế AI: Tỉnh thành, Bệnh viện, Chuyên khoa, Bác sĩ (mỗi khoa 4 bác sĩ nam nữ), Lịch khám'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE('=== BẮT ĐẦU NẠP DỮ LIỆU MẪU TOÀN DIỆN ==='))

        # 1. Tạo Tài khoản Admin
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@medicalai.vn',
                'full_name': 'Quản Trị Viên Hệ Thống',
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(' Đã tạo Admin: admin / admin123'))

        # 2. Tạo Bệnh nhân mẫu
        patient_user, created = User.objects.get_or_create(
            username='benhnhan',
            defaults={
                'email': 'benhnhan@gmail.com',
                'full_name': 'Nguyễn Văn An',
                'phone': '0905123456',
                'address': '12 Hải Châu, TP. Đà Nẵng',
                'gender': 'nam',
                'role': 'patient',
            }
        )
        if created:
            patient_user.set_password('patient123')
            patient_user.save()
            self.stdout.write(self.style.SUCCESS(' Đã tạo Bệnh nhân: benhnhan / patient123'))

        # 3. Tạo Tỉnh / Thành phố
        tinh_data = ['Đà Nẵng', 'Hà Nội', 'TP. Hồ Chí Minh', 'Thừa Thiên Huế', 'Cần Thơ']
        tinh_objs = {}
        for t_name in tinh_data:
            obj, _ = TinhThanh.objects.get_or_create(ten_tinh=t_name)
            tinh_objs[t_name] = obj
        self.stdout.write(self.style.SUCCESS(f' Đã nạp {len(tinh_objs)} Tỉnh/Thành phố.'))

        # 4. Tạo 9 Chuyên khoa y tế
        chuyen_khoa_data = [
            ('Nội tổng quát', 'Khám chữa các bệnh lý nội khoa thông thường, sốt, ho, mệt mỏi, kiểm tra sức khỏe định kỳ.', 'bi-capsule'),
            ('Thần kinh', 'Chuyên khám và điều trị đau đầu, chóng mặt, mất ngủ, rối loạn tiền đình, thần kinh cơ, đột quỵ.', 'bi-cpu'),
            ('Tim mạch', 'Chẩn đoán và điều trị tăng huyết áp, suy tim, bệnh mạch vành, rối loạn nhịp tim.', 'bi-heart-pulse'),
            ('Tai Mũi Họng', 'Khám điều trị viêm xoang, viêm họng, viêm amidan, ù tai, khó thở.', 'bi-headset'),
            ('Da liễu', 'Điều trị dị ứng da, mụn trứng cá, chàm, vảy nến, rụng tóc và bệnh lý da liễu.', 'bi-flower1'),
            ('Nhi khoa', 'Chăm sóc sức khỏe, tiêm chủng, điều trị bệnh lý sơ sinh và trẻ em.', 'bi-person-heart'),
            ('Tiêu hóa', 'Điều trị đau dạ dày, viêm đại tràng, trào ngược dạ dày thực quản, gan mật.', 'bi-droplet-half'),
            ('Cơ xương khớp', 'Thoái hóa khớp, đau lưng, thoát vị đĩa đệm, đau khớp gối, loãng xương.', 'bi-activity'),
            ('Mắt (Nhãn khoa)', 'Đo thị lực, đau mắt đỏ, cận thị, loạn thị, đục thủy tinh thể.', 'bi-eye'),
        ]
        ck_objs = {}
        for name, desc, icon in chuyen_khoa_data:
            obj, _ = ChuyenKhoa.objects.get_or_create(
                ten_chuyen_khoa=name,
                defaults={'mo_ta': desc, 'bieu_tuong': icon}
            )
            ck_objs[name] = obj
        self.stdout.write(self.style.SUCCESS(f' Đã nạp {len(ck_objs)} Chuyên khoa y tế.'))

        # 5. Tạo Bệnh viện theo từng Tỉnh
        bv_data = [
            # Đà Nẵng
            {
                'ten': 'Bệnh viện Đa khoa Đà Nẵng',
                'tinh': 'Đà Nẵng',
                'dia_chi': '124 Hải Phòng, Thạch Thang, Hải Châu, Đà Nẵng',
                'sdt': '0236 3821 118',
                'email': 'bvdanang@danang.gov.vn',
                'website': 'https://dananghospital.org.vn',
                'hinh_anh': 'https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?w=800',
                'mo_ta': 'Bệnh viện hạng I tuyến cuối tại miền Trung với đầy đủ các chuyên khoa mũi nhọn.',
            },
            {
                'ten': 'Bệnh viện Hoàn Mỹ Đà Nẵng',
                'tinh': 'Đà Nẵng',
                'dia_chi': '291 Nguyễn Văn Linh, Thạc Gián, Thanh Khê, Đà Nẵng',
                'sdt': '0236 3650 676',
                'email': 'contactus.danang@hoanmy.com',
                'website': 'https://hoanmydanang.com',
                'hinh_anh': 'https://images.unsplash.com/photo-1586773860418-d37222d8fce3?w=800',
                'mo_ta': 'Dịch vụ y tế chất lượng cao, đặt lịch nhanh chóng, chăm sóc chuẩn quốc tế.',
            },
            {
                'ten': 'Bệnh viện Phụ Sản - Nhi Đà Nẵng',
                'tinh': 'Đà Nẵng',
                'dia_chi': '402 Lê Văn Hiến, Khuê Mỹ, Ngũ Hành Sơn, Đà Nẵng',
                'sdt': '0236 3957 777',
                'email': 'psndanang@gmail.com',
                'website': 'https://phusannhidanang.org.vn',
                'hinh_anh': 'https://images.unsplash.com/photo-1538108149393-fbbd81895907?w=800',
                'mo_ta': 'Bệnh viện chuyên khoa Sản - Nhi hàng đầu khu vực miền Trung.',
            },
            # Hà Nội
            {
                'ten': 'Bệnh viện Bạch Mai',
                'tinh': 'Hà Nội',
                'dia_chi': '78 Đường Giải Phóng, Phương Mai, Đống Đa, Hà Nội',
                'sdt': '024 3869 3731',
                'email': 'benhvienbachmai@bachmai.edu.vn',
                'website': 'http://bachmai.gov.vn',
                'hinh_anh': 'https://images.unsplash.com/photo-1587351021759-3e566b6af7cc?w=800',
                'mo_ta': 'Bệnh viện đa khoa hạng đặc biệt đầu tiên của cả nước.',
            },
            {
                'ten': 'Bệnh viện Hữu nghị Việt Đức',
                'tinh': 'Hà Nội',
                'dia_chi': '40 Tràng Thi, Hàng Bông, Hoàn Kiếm, Hà Nội',
                'sdt': '024 3825 3531',
                'email': 'bvvd@vietduchospital.edu.vn',
                'website': 'http://benhvienvietduc.org',
                'hinh_anh': 'https://images.unsplash.com/photo-1516549655169-df83a0774514?w=800',
                'mo_ta': 'Trung tâm ngoại khoa và cơ xương khớp hàng đầu Việt Nam.',
            },
            {
                'ten': 'Bệnh viện Đại học Y Hà Nội',
                'tinh': 'Hà Nội',
                'dia_chi': 'Số 1 Tôn Thất Tùng, Kim Liên, Đống Đa, Hà Nội',
                'sdt': '024 3574 7788',
                'email': 'benhviendhyhn@hmu.edu.vn',
                'website': 'http://benhviendaihocyhanoi.com',
                'hinh_anh': 'https://images.unsplash.com/photo-1579684385127-1ef15d508118?w=800',
                'mo_ta': 'Mô hình viện - trường hiện đại, tiện nghi, điều trị kỹ thuật cao.',
            },
            # TP. Hồ Chí Minh
            {
                'ten': 'Bệnh viện Chợ Rẫy',
                'tinh': 'TP. Hồ Chí Minh',
                'dia_chi': '201B Nguyễn Chí Thanh, Phường 12, Quận 5, TP. Hồ Chí Minh',
                'sdt': '028 3855 4137',
                'email': 'bvchoray@choray.vn',
                'website': 'http://choray.vn',
                'hinh_anh': 'https://images.unsplash.com/photo-1582750433449-648ed127bb54?w=800',
                'mo_ta': 'Bệnh viện đa khoa trung ương tuyến cuối lớn nhất miền Nam.',
            },
            {
                'ten': 'Bệnh viện Đại học Y Dược TP.HCM',
                'tinh': 'TP. Hồ Chí Minh',
                'dia_chi': '215 Hồng Bàng, Phường 11, Quận 5, TP. Hồ Chí Minh',
                'sdt': '028 3855 4269',
                'email': 'bvdhyd@umc.edu.vn',
                'website': 'https://bvdaihoc.com.vn',
                'hinh_anh': 'https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?w=800',
                'mo_ta': 'Hệ thống khám chữa bệnh chuẩn mực, tận tâm và đa chuyên khoa.',
            },
            {
                'ten': 'Bệnh viện Từ Dũ',
                'tinh': 'TP. Hồ Chí Minh',
                'dia_chi': '284 Cống Quỳnh, Phạm Ngũ Lão, Quận 1, TP. Hồ Chí Minh',
                'sdt': '028 5404 2829',
                'email': 'tudu@tudu.vn',
                'website': 'https://tudu.com.vn',
                'hinh_anh': 'https://images.unsplash.com/photo-1538108149393-fbbd81895907?w=800',
                'mo_ta': 'Bệnh viện chuyên khoa Sản - Phụ - Nhi tuyến đầu phía Nam.',
            },
            # Huế & Cần Thơ
            {
                'ten': 'Bệnh viện Trung ương Huế',
                'tinh': 'Thừa Thiên Huế',
                'dia_chi': '16 Lê Lợi, Vĩnh Ninh, Thành phố Huế',
                'sdt': '0234 3822 325',
                'email': 'bvtwhue@bvtwhue.com.vn',
                'website': 'https://bvtwhue.com.vn',
                'hinh_anh': 'https://images.unsplash.com/photo-1587351021759-3e566b6af7cc?w=800',
                'mo_ta': 'Bệnh viện hạng đặc biệt với trang thiết bị y khoa tiên tiến.',
            },
            {
                'ten': 'Bệnh viện Đa khoa Trung ương Cần Thơ',
                'tinh': 'Cần Thơ',
                'dia_chi': '315 Nguyễn Văn Linh, Ninh Kiều, Cần Thơ',
                'sdt': '0292 3820 071',
                'email': 'bvdktwct@gmail.com',
                'website': 'http://bvtwct.vn',
                'hinh_anh': 'https://images.unsplash.com/photo-1586773860418-d37222d8fce3?w=800',
                'mo_ta': 'Bệnh viện tuyến trung ương lớn nhất miền Tây Nam Bộ.',
            },
        ]

        bv_objs = {}
        for b_data in bv_data:
            tinh_obj = tinh_objs[b_data['tinh']]
            bv, _ = BenhVien.objects.get_or_create(
                ten_benh_vien=b_data['ten'],
                defaults={
                    'tinh': tinh_obj,
                    'dia_chi': b_data['dia_chi'],
                    'so_dien_thoai': b_data['sdt'],
                    'email': b_data['email'],
                    'website': b_data['website'],
                    'hinh_anh': b_data['hinh_anh'],
                    'mo_ta': b_data['mo_ta'],
                    'trang_thai': True,
                }
            )
            # Gán tất cả 9 chuyên khoa cho các bệnh viện đa khoa
            for ck_obj in ck_objs.values():
                bv.chuyen_khoas.add(ck_obj)
            bv_objs[b_data['ten']] = bv

        self.stdout.write(self.style.SUCCESS(f' Đã nạp {len(bv_objs)} Bệnh viện.'))

        # 6. DANH SÁCH BÁC SĨ TOÀN DIỆN (MỖI CHUYÊN KHOA CÓ 4 BÁC SĨ CẢ NAM LẪN NỮ)
        # Các hình ảnh avatar bác sĩ chất lượng cao
        IMG_MALE_1 = 'https://images.unsplash.com/photo-1622253692010-333f2da6031d?w=600'
        IMG_MALE_2 = 'https://images.unsplash.com/photo-1537368910025-700350fe46c7?w=600'
        IMG_MALE_3 = 'https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?w=600'
        IMG_MALE_4 = 'https://images.unsplash.com/photo-1582750433449-648ed127bb54?w=600'

        IMG_FEMALE_1 = 'https://images.unsplash.com/photo-1594824813689-f538573ef841?w=600'
        IMG_FEMALE_2 = 'https://images.unsplash.com/photo-1651008376811-b90baee60c1f?w=600'
        IMG_FEMALE_3 = 'https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=600'
        IMG_FEMALE_4 = 'https://images.unsplash.com/photo-1527613426441-4da17471b66d?w=600'

        doctor_roster = [
            # 1. THẦN KINH (2 Nam, 2 Nữ)
            {
                'username': 'bs_nam_tk', 'ho_ten': 'Nguyễn Văn Nam', 'chuc_danh': 'BS. CKII', 'gender': 'nam',
                'chuyen_khoa': 'Thần kinh', 'benh_vien': 'Bệnh viện Đa khoa Đà Nẵng', 'exp': 15, 'fee': 250000,
                'anh': IMG_MALE_1, 'mo_ta': 'Chuyên gia đầu ngành điều trị đau nửa đầu Migraine, mất ngủ, chóng mặt tiền đình và tai biến mạch máu não.'
            },
            {
                'username': 'bs_lan_tk', 'ho_ten': 'Hoàng Ngọc Lan', 'chuc_danh': 'ThS. BS', 'gender': 'nu',
                'chuyen_khoa': 'Thần kinh', 'benh_vien': 'Bệnh viện Chợ Rẫy', 'exp': 12, 'fee': 300000,
                'anh': IMG_FEMALE_1, 'mo_ta': 'Chuyên sâu chẩn đoán động kinh, đau dây thần kinh tọa, rối loạn giấc ngủ và suy nhược thần kinh.'
            },
            {
                'username': 'bs_bao_tk', 'ho_ten': 'Trần Quốc Bảo', 'chuc_danh': 'TS. BS', 'gender': 'nam',
                'chuyen_khoa': 'Thần kinh', 'benh_vien': 'Bệnh viện Bạch Mai', 'exp': 18, 'fee': 350000,
                'anh': IMG_MALE_2, 'mo_ta': 'Nhiều năm nghiên cứu bệnh Parkinson, Alzheimer sa sút trí tuệ và các bệnh lý thần kinh cơ.'
            },
            {
                'username': 'bs_maianh_tk', 'ho_ten': 'Lê Thị Mai Anh', 'chuc_danh': 'BS. CKI', 'gender': 'nu',
                'chuyen_khoa': 'Thần kinh', 'benh_vien': 'Bệnh viện Hoàn Mỹ Đà Nẵng', 'exp': 8, 'fee': 220000,
                'anh': IMG_FEMALE_2, 'mo_ta': 'Điều trị hiệu quả chứng đau đầu căng thẳng do áp lực công việc, hội chứng tiền đình ở người trẻ.'
            },

            # 2. TIM MẠCH (2 Nam, 2 Nữ)
            {
                'username': 'bs_huong_tm', 'ho_ten': 'Trần Thị Thu Hương', 'chuc_danh': 'ThS. BS', 'gender': 'nu',
                'chuyen_khoa': 'Tim mạch', 'benh_vien': 'Bệnh viện Hoàn Mỹ Đà Nẵng', 'exp': 10, 'fee': 300000,
                'anh': IMG_FEMALE_3, 'mo_ta': 'Chuyên sâu tầm soát tăng huyết áp, suy tim, bệnh mạch vành và can thiệp mạch máu.'
            },
            {
                'username': 'bs_cuong_tm', 'ho_ten': 'Đặng Hùng Cường', 'chuc_danh': 'PGS. TS', 'gender': 'nam',
                'chuyen_khoa': 'Tim mạch', 'benh_vien': 'Bệnh viện Bạch Mai', 'exp': 24, 'fee': 400000,
                'anh': IMG_MALE_3, 'mo_ta': 'Chuyên gia tim mạch hàng đầu, giàu kinh nghiệm điều trị rối loạn nhịp tim và bệnh van tim phức tạp.'
            },
            {
                'username': 'bs_hung_tm', 'ho_ten': 'Phạm Văn Hưng', 'chuc_danh': 'BS. CKII', 'gender': 'nam',
                'chuyen_khoa': 'Tim mạch', 'benh_vien': 'Bệnh viện Đa khoa Đà Nẵng', 'exp': 16, 'fee': 280000,
                'anh': IMG_MALE_4, 'mo_ta': 'Khám và tư vấn phục hồi chức năng tim sau nhồi máu, kiểm soát mỡ máu và huyết áp cao.'
            },
            {
                'username': 'bs_phuong_tm', 'ho_ten': 'Nguyễn Mai Phương', 'chuc_danh': 'BS. CKI', 'gender': 'nu',
                'chuyen_khoa': 'Tim mạch', 'benh_vien': 'Bệnh viện Chợ Rẫy', 'exp': 9, 'fee': 250000,
                'anh': IMG_FEMALE_4, 'mo_ta': 'Chẩn đoán hình ảnh tim mạch, siêu âm Doppler tim, theo dõi bệnh lý tim bẩm sinh người lớn.'
            },

            # 3. TIÊU HÓA (2 Nam, 2 Nữ)
            {
                'username': 'bs_minh_th', 'ho_ten': 'Đỗ Quang Minh', 'chuc_danh': 'TS. BS', 'gender': 'nam',
                'chuyen_khoa': 'Tiêu hóa', 'benh_vien': 'Bệnh viện Bạch Mai', 'exp': 17, 'fee': 350000,
                'anh': IMG_MALE_1, 'mo_ta': 'Chuyên gia nội soi can thiệp, điều trị dứt điểm viêm loét dạ dày tá tràng, vi khuẩn HP, trào ngược dạ dày.'
            },
            {
                'username': 'bs_ngoc_th', 'ho_ten': 'Vũ Bích Ngọc', 'chuc_danh': 'ThS. BS', 'gender': 'nu',
                'chuyen_khoa': 'Tiêu hóa', 'benh_vien': 'Bệnh viện Đa khoa Đà Nẵng', 'exp': 11, 'fee': 260000,
                'anh': IMG_FEMALE_1, 'mo_ta': 'Khám điều trị viêm đại tràng co thắt, hội chứng ruột kích thích, bệnh lý gan nhiễm mỡ.'
            },
            {
                'username': 'bs_dat_th', 'ho_ten': 'Võ Thành Đạt', 'chuc_danh': 'BS. CKII', 'gender': 'nam',
                'chuyen_khoa': 'Tiêu hóa', 'benh_vien': 'Bệnh viện Đại học Y Dược TP.HCM', 'exp': 19, 'fee': 320000,
                'anh': IMG_MALE_2, 'mo_ta': 'Kinh nghiệm phong phú trong phẫu thuật nội soi đường tiêu hóa và điều trị viêm tụy, sỏi mật.'
            },
            {
                'username': 'bs_thao_th', 'ho_ten': 'Nguyễn Thị Thu Thảo', 'chuc_danh': 'BS. CKI', 'gender': 'nu',
                'chuyen_khoa': 'Tiêu hóa', 'benh_vien': 'Bệnh viện Hoàn Mỹ Đà Nẵng', 'exp': 7, 'fee': 200000,
                'anh': IMG_FEMALE_2, 'mo_ta': 'Tận tâm tư vấn chế độ ăn uống, điều trị chứng khó tiêu, đầy bụng, ợ hơi ợ chua mãn tính.'
            },

            # 4. NỘI TỔNG QUÁT (2 Nam, 2 Nữ)
            {
                'username': 'bs_tuan_ntq', 'ho_ten': 'Lê Anh Tuấn', 'chuc_danh': 'PGS. TS', 'gender': 'nam',
                'chuyen_khoa': 'Nội tổng quát', 'benh_vien': 'Bệnh viện Đa khoa Đà Nẵng', 'exp': 22, 'fee': 350000,
                'anh': IMG_MALE_3, 'mo_ta': 'Nguyên trưởng khoa Nội, chuyên gia kiểm tra sức khỏe tổng thể và các bệnh lý nội khoa đa cơ quan.'
            },
            {
                'username': 'bs_truc_ntq', 'ho_ten': 'Phan Thị Thanh Trúc', 'chuc_danh': 'BS. CKII', 'gender': 'nu',
                'chuyen_khoa': 'Nội tổng quát', 'benh_vien': 'Bệnh viện Bạch Mai', 'exp': 15, 'fee': 280000,
                'anh': IMG_FEMALE_3, 'mo_ta': 'Điều trị sốt kéo dài chưa rõ nguyên nhân, mệt mỏi suy kiệt, quản lý bệnh đái tháo đường và nội tiết.'
            },
            {
                'username': 'bs_duc_ntq', 'ho_ten': 'Bùi Minh Đức', 'chuc_danh': 'ThS. BS', 'gender': 'nam',
                'chuyen_khoa': 'Nội tổng quát', 'benh_vien': 'Bệnh viện Chợ Rẫy', 'exp': 13, 'fee': 260000,
                'anh': IMG_MALE_4, 'mo_ta': 'Khám sức khỏe tổng quát định kỳ, tầm soát bệnh mạn tính ở người cao tuổi.'
            },
            {
                'username': 'bs_ngan_ntq', 'ho_ten': 'Đỗ Hoàng Kim Ngân', 'chuc_danh': 'BS. CKI', 'gender': 'nu',
                'chuyen_khoa': 'Nội tổng quát', 'benh_vien': 'Bệnh viện Hoàn Mỹ Đà Nẵng', 'exp': 8, 'fee': 200000,
                'anh': IMG_FEMALE_4, 'mo_ta': 'Tư vấn tiêm chủng người lớn, điều trị cảm cúm, viêm họng sốt siêu vi và rối loạn chuyển hóa.'
            },

            # 5. TAI MŨI HỌNG (2 Nam, 2 Nữ)
            {
                'username': 'bs_vinh_tmh', 'ho_ten': 'Trương Quang Vinh', 'chuc_danh': 'BS. CKII', 'gender': 'nam',
                'chuyen_khoa': 'Tai Mũi Họng', 'benh_vien': 'Bệnh viện Đa khoa Đà Nẵng', 'exp': 18, 'fee': 280000,
                'anh': IMG_MALE_1, 'mo_ta': 'Chuyên gia nội soi tai mũi họng, nạo VA, cắt amidan, điều trị viêm xoang hàm, xoang trán mạn tính.'
            },
            {
                'username': 'bs_duyen_tmh', 'ho_ten': 'Nguyễn Thị Mỹ Duyên', 'chuc_danh': 'ThS. BS', 'gender': 'nu',
                'chuyen_khoa': 'Tai Mũi Họng', 'benh_vien': 'Bệnh viện Bạch Mai', 'exp': 11, 'fee': 250000,
                'anh': IMG_FEMALE_1, 'mo_ta': 'Điều trị viêm mũi xoang dị ứng thời tiết, khàn tiếng hạt xơ dây thanh, mất thính lực ở người lớn.'
            },
            {
                'username': 'bs_huy_tmh', 'ho_ten': 'Đinh Quốc Huy', 'chuc_danh': 'BS. CKI', 'gender': 'nam',
                'chuyen_khoa': 'Tai Mũi Họng', 'benh_vien': 'Bệnh viện Chợ Rẫy', 'exp': 9, 'fee': 220000,
                'anh': IMG_MALE_2, 'mo_ta': 'Khám điều trị ù tai, thủng màng nhĩ, viêm tai giữa chảy mủ và các dị vật đường thở.'
            },
            {
                'username': 'bs_hang_tmh', 'ho_ten': 'Lê Thị Thúy Hằng', 'chuc_danh': 'BS. CKI', 'gender': 'nu',
                'chuyen_khoa': 'Tai Mũi Họng', 'benh_vien': 'Bệnh viện Đại học Y Hà Nội', 'exp': 7, 'fee': 200000,
                'anh': IMG_FEMALE_2, 'mo_ta': 'Tận tình chu đáo trong khám chữa viêm tai mũi họng cho cả người lớn và trẻ em.'
            },

            # 6. DA LIỄU (2 Nam, 2 Nữ)
            {
                'username': 'bs_hanh_dl', 'ho_ten': 'Phạm Thị Bích Hạnh', 'chuc_danh': 'ThS. BS', 'gender': 'nu',
                'chuyen_khoa': 'Da liễu', 'benh_vien': 'Bệnh viện Hoàn Mỹ Đà Nẵng', 'exp': 13, 'fee': 250000,
                'anh': IMG_FEMALE_3, 'mo_ta': 'Chuyên gia điều trị viêm da cơ địa, mề đay dị ứng, mụn trứng cá nặng, sẹo rỗ và nám da.'
            },
            {
                'username': 'bs_triet_dl', 'ho_ten': 'Ngô Minh Triết', 'chuc_danh': 'BS. CKII', 'gender': 'nam',
                'chuyen_khoa': 'Da liễu', 'benh_vien': 'Bệnh viện Bạch Mai', 'exp': 20, 'fee': 320000,
                'anh': IMG_MALE_3, 'mo_ta': 'Bác sĩ đầu ngành về các bệnh da tự miễn như vảy nến, lupus ban đỏ, zona thần kinh, rụng tóc từng mảng.'
            },
            {
                'username': 'bs_linh_dl', 'ho_ten': 'Trần Thảo Linh', 'chuc_danh': 'BS. CKI', 'gender': 'nu',
                'chuyen_khoa': 'Da liễu', 'benh_vien': 'Bệnh viện Đại học Y Dược TP.HCM', 'exp': 8, 'fee': 220000,
                'anh': IMG_FEMALE_4, 'mo_ta': 'Khám chữa các bệnh lý nấm da, chàm tiếp xúc và tư vấn quy trình phục hồi da kích ứng.'
            },
            {
                'username': 'bs_nghia_dl', 'ho_ten': 'Huỳnh Trọng Nghĩa', 'chuc_danh': 'BS. CKI', 'gender': 'nam',
                'chuyen_khoa': 'Da liễu', 'benh_vien': 'Bệnh viện Đa khoa Đà Nẵng', 'exp': 10, 'fee': 240000,
                'anh': IMG_MALE_4, 'mo_ta': 'Ứng dụng laser và công nghệ thẩm mỹ y khoa trong điều trị sẹo lồi, mụn cóc và bớt sắc tố.'
            },

            # 7. NHI KHOA (2 Nam, 2 Nữ)
            {
                'username': 'bs_ha_nk', 'ho_ten': 'Phạm Thị Thu Hà', 'chuc_danh': 'BS. CKI', 'gender': 'nu',
                'chuyen_khoa': 'Nhi khoa', 'benh_vien': 'Bệnh viện Phụ Sản - Nhi Đà Nẵng', 'exp': 10, 'fee': 220000,
                'anh': IMG_FEMALE_1, 'mo_ta': 'Chuyên điều trị bệnh đường hô hấp ở trẻ, viêm tiểu phế quản, viêm tai giữa, tư vấn dinh dưỡng biếng ăn.'
            },
            {
                'username': 'bs_thinh_nk', 'ho_ten': 'Nguyễn Đức Thịnh', 'chuc_danh': 'ThS. BS', 'gender': 'nam',
                'chuyen_khoa': 'Nhi khoa', 'benh_vien': 'Bệnh viện Phụ Sản - Nhi Đà Nẵng', 'exp': 14, 'fee': 260000,
                'anh': IMG_MALE_1, 'mo_ta': 'Kinh nghiệm sâu sắc trong cấp cứu nhi khoa, điều trị sốt xuất huyết, tay chân miệng và sởi ở trẻ nhỏ.'
            },
            {
                'username': 'bs_uyen_nk', 'ho_ten': 'Vũ Thị Thục Uyên', 'chuc_danh': 'BS. CKII', 'gender': 'nu',
                'chuyen_khoa': 'Nhi khoa', 'benh_vien': 'Bệnh viện Từ Dũ', 'exp': 19, 'fee': 300000,
                'anh': IMG_FEMALE_2, 'mo_ta': 'Chuyên gia hồi sức sơ sinh, chăm sóc trẻ sinh non và tư vấn tiêm chủng vắc xin trọn gói.'
            },
            {
                'username': 'bs_nam_nk', 'ho_ten': 'Lê Hải Nam', 'chuc_danh': 'TS. BS', 'gender': 'nam',
                'chuyen_khoa': 'Nhi khoa', 'benh_vien': 'Bệnh viện Bạch Mai', 'exp': 16, 'fee': 350000,
                'anh': IMG_MALE_2, 'mo_ta': 'Chuyên khám và điều trị các rối loạn phát triển tâm thần vận động, chậm nói và hen suyễn ở trẻ em.'
            },

            # 8. CƠ XƯƠNG KHỚP (2 Nam, 2 Nữ)
            {
                'username': 'bs_khoi_cxk', 'ho_ten': 'Nguyễn Trọng Khôi', 'chuc_danh': 'TS. BS', 'gender': 'nam',
                'chuyen_khoa': 'Cơ xương khớp', 'benh_vien': 'Bệnh viện Đa khoa Đà Nẵng', 'exp': 17, 'fee': 300000,
                'anh': IMG_MALE_3, 'mo_ta': 'Chuyên gia điều trị thoái hóa khớp gối, khớp háng, thoát vị đĩa đệm cột sống cổ và thắt lưng.'
            },
            {
                'username': 'bs_diep_cxk', 'ho_ten': 'Lê Ngọc Diệp', 'chuc_danh': 'BS. CKII', 'gender': 'nu',
                'chuyen_khoa': 'Cơ xương khớp', 'benh_vien': 'Bệnh viện Hữu nghị Việt Đức', 'exp': 21, 'fee': 380000,
                'anh': IMG_FEMALE_3, 'mo_ta': 'Kinh nghiệm hàng đầu về điều trị viêm khớp dạng thấp, bệnh gút cấp và mạn tính, loãng xương.'
            },
            {
                'username': 'bs_hai_cxk', 'ho_ten': 'Cao Minh Hải', 'chuc_danh': 'BS. CKI', 'gender': 'nam',
                'chuyen_khoa': 'Cơ xương khớp', 'benh_vien': 'Bệnh viện Chợ Rẫy', 'exp': 12, 'fee': 260000,
                'anh': IMG_MALE_4, 'mo_ta': 'Tiêm huyết tương giàu tiểu cầu (PRP) khớp gối, điều trị chấn thương thể thao và đứt dây chằng.'
            },
            {
                'username': 'bs_nhung_cxk', 'ho_ten': 'Đặng Thị Hồng Nhung', 'chuc_danh': 'ThS. BS', 'gender': 'nu',
                'chuyen_khoa': 'Cơ xương khớp', 'benh_vien': 'Bệnh viện Bạch Mai', 'exp': 9, 'fee': 240000,
                'anh': IMG_FEMALE_4, 'mo_ta': 'Tư vấn vật lý trị liệu, phục hồi chức năng sau mổ xương và điều trị đau mỏi vai gáy văn phòng.'
            },

            # 9. MẮT / NHÃN KHOA (2 Nam, 2 Nữ)
            {
                'username': 'bs_nga_mat', 'ho_ten': 'Nguyễn Thị Phương Nga', 'chuc_danh': 'ThS. BS', 'gender': 'nu',
                'chuyen_khoa': 'Mắt (Nhãn khoa)', 'benh_vien': 'Bệnh viện Hoàn Mỹ Đà Nẵng', 'exp': 11, 'fee': 240000,
                'anh': IMG_FEMALE_1, 'mo_ta': 'Khám đo thị lực chuyên sâu, điều trị viêm giác mạc, khô mắt, kiểm soát tiến triển cận thị học đường.'
            },
            {
                'username': 'bs_tan_mat', 'ho_ten': 'Đoàn Nhật Tân', 'chuc_danh': 'BS. CKII', 'gender': 'nam',
                'chuyen_khoa': 'Mắt (Nhãn khoa)', 'benh_vien': 'Bệnh viện Đại học Y Hà Nội', 'exp': 18, 'fee': 320000,
                'anh': IMG_MALE_1, 'mo_ta': 'Chuyên gia phẫu thuật Phaco đục thủy tinh thể, điều trị Glaucoma cườm nước và bệnh võng mạc.'
            },
            {
                'username': 'bs_quynh_mat', 'ho_ten': 'Võ Ngọc Quỳnh', 'chuc_danh': 'BS. CKI', 'gender': 'nu',
                'chuyen_khoa': 'Mắt (Nhãn khoa)', 'benh_vien': 'Bệnh viện Chợ Rẫy', 'exp': 8, 'fee': 220000,
                'anh': IMG_FEMALE_2, 'mo_ta': 'Điều trị các bệnh lý đau mắt đỏ, dị ứng kết mạc, mộng thịt và phục hồi thị lực.'
            },
            {
                'username': 'bs_long_mat', 'ho_ten': 'Phan Đình Long', 'chuc_danh': 'BS. CKI', 'gender': 'nam',
                'chuyen_khoa': 'Mắt (Nhãn khoa)', 'benh_vien': 'Bệnh viện Đa khoa Đà Nẵng', 'exp': 13, 'fee': 250000,
                'anh': IMG_MALE_2, 'mo_ta': 'Phẫu thuật khúc xạ Lasik, Smile điều trị cận - loạn thị và chăm sóc mắt người cao tuổi.'
            },

            # 10. BỔ SUNG CHO HUẾ & CẦN THƠ
            {
                'username': 'bs_tri_hue', 'ho_ten': 'Hồ Đăng Trí', 'chuc_danh': 'BS. CKII', 'gender': 'nam',
                'chuyen_khoa': 'Tim mạch', 'benh_vien': 'Bệnh viện Trung ương Huế', 'exp': 19, 'fee': 300000,
                'anh': IMG_MALE_3, 'mo_ta': 'Chuyên gia tim mạch Bệnh viện Trung ương Huế, can thiệp nong mạch vành và phẫu thuật tim hở.'
            },
            {
                'username': 'bs_tram_hue', 'ho_ten': 'Tôn Nữ Bích Trâm', 'chuc_danh': 'ThS. BS', 'gender': 'nu',
                'chuyen_khoa': 'Thần kinh', 'benh_vien': 'Bệnh viện Trung ương Huế', 'exp': 12, 'fee': 250000,
                'anh': IMG_FEMALE_3, 'mo_ta': 'Điều trị bệnh lý thần kinh cơ, suy giảm trí nhớ, rối loạn vận động và đau dây thần kinh.'
            },
            {
                'username': 'bs_thong_ct', 'ho_ten': 'Dương Minh Thông', 'chuc_danh': 'TS. BS', 'gender': 'nam',
                'chuyen_khoa': 'Tiêu hóa', 'benh_vien': 'Bệnh viện Đa khoa Trung ương Cần Thơ', 'exp': 16, 'fee': 280000,
                'anh': IMG_MALE_4, 'mo_ta': 'Chuyên gia tiêu hóa hàng đầu miền Tây, nội soi cắt polyp đường tiêu hóa và điều trị viêm gan B, C.'
            },
            {
                'username': 'bs_oanh_ct', 'ho_ten': 'Lâm Thị Kiều Oanh', 'chuc_danh': 'BS. CKI', 'gender': 'nu',
                'chuyen_khoa': 'Nội tổng quát', 'benh_vien': 'Bệnh viện Đa khoa Trung ương Cần Thơ', 'exp': 10, 'fee': 200000,
                'anh': IMG_FEMALE_4, 'mo_ta': 'Khám chữa các bệnh nội tiết, đái tháo đường, mỡ máu và kiểm tra sức khỏe tổng thể.'
            },
        ]

        today = timezone.now().date()
        time_slots = [
            (time(8, 0), time(9, 0)),
            (time(9, 0), time(10, 0)),
            (time(10, 0), time(11, 0)),
            (time(14, 0), time(15, 0)),
            (time(15, 0), time(16, 0)),
            (time(16, 0), time(17, 0)),
        ]

        created_doctors_count = 0
        for d in doctor_roster:
            # Tạo user
            u, u_created = User.objects.get_or_create(
                username=d['username'],
                defaults={
                    'email': f"{d['username']}@medicalai.vn",
                    'full_name': f"{d['chuc_danh']} {d['ho_ten']}",
                    'phone': '0905' + str(created_doctors_count).zfill(6),
                    'gender': d.get('gender', 'nam'),
                    'role': 'doctor',
                }
            )
            if u_created:
                u.set_password('doctor123')
                u.save()

            # Tạo hồ sơ bác sĩ
            bv = bv_objs.get(d['benh_vien'])
            ck = ck_objs.get(d['chuyen_khoa'])
            if bv and ck:
                bacsi, b_created = BacSi.objects.get_or_create(
                    user=u,
                    defaults={
                        'benh_vien': bv,
                        'chuyen_khoa': ck,
                        'ho_ten': d['ho_ten'],
                        'chuc_danh': d['chuc_danh'],
                        'so_nam_kinh_nghiem': d['exp'],
                        'mo_ta': d['mo_ta'],
                        'anh_dai_dien': d['anh'],
                        'gia_kham': d['fee'],
                        'trang_thai': True,
                    }
                )
                if not b_created:
                    # Cập nhật nếu đã có
                    bacsi.benh_vien = bv
                    bacsi.chuyen_khoa = ck
                    bacsi.gia_kham = d['fee']
                    bacsi.anh_dai_dien = d['anh']
                    bacsi.save()

                # Tạo Lịch làm việc 14 ngày tới cho mỗi bác sĩ
                for day_offset in range(0, 14):
                    slot_date = today + timedelta(days=day_offset)
                    # Tránh chủ nhật
                    if slot_date.weekday() == 6:
                        continue

                    for start_t, end_t in time_slots:
                        LichLamViec.objects.get_or_create(
                            bac_si=bacsi,
                            ngay=slot_date,
                            gio_bat_dau=start_t,
                            gio_ket_thuc=end_t,
                            defaults={
                                'so_luong_benh_nhan': 4,
                                'trang_thai': True,
                            }
                        )
                created_doctors_count += 1

        self.stdout.write(self.style.SUCCESS(f' Đã nạp {created_doctors_count} Bác sĩ (cả nam lẫn nữ, mỗi chuyên khoa 4 bác sĩ) kèm lịch làm việc 14 ngày tới.'))

        self.stdout.write(self.style.SUCCESS('=== NẠP DỮ LIỆU MẪU TOÀN DIỆN THÀNH CÔNG! ==='))
