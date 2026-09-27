import re
import json
import os
import requests
from datetime import datetime, timedelta
from hospitals.models import TinhThanh, BenhVien, ChuyenKhoa
from doctors.models import BacSi, LichLamViec
from django.utils import timezone

# ================= 1. BỘ TRI THỨC Y TẾ, DINH DƯỠNG, SỨC KHỎE & ĂN UỐNG ĐA DẠNG =================
HEALTH_KNOWLEDGE_BASE = [
    # --- DINH DƯỠNG & ĂN UỐNG CHO SỨC KHỎE ---
    {
        'category': 'nutrition_general',
        'keywords': ['ăn gì', 'chế độ ăn', 'dinh dưỡng', 'thực đơn', 'thực phẩm tốt', 'thực phẩm nên kiêng', 'nên ăn gì', 'kiêng ăn gì', 'uống gì'],
        'title': '🥗 Tư Vấn Dinh Dưỡng & Ăn Uống Khoa Học',
        'response': (
            "🥗 **Lời khuyên dinh dưỡng & ăn uống lành mạnh từ Bác sĩ AI:**\n\n"
            "1. **Nguyên tắc đĩa thức ăn cân bằng (MyPlate):**\n"
            "   - **1/2 đĩa:** Rau xanh đa màu sắc và trái cây tươi (cung cấp chất xơ, vitamin A, C, E, kẽm).\n"
            "   - **1/4 đĩa:** Chất đạm nạc chất lượng cao (ức gà, cá biển sâu, trứng, đậu hũ, thịt bò nạc).\n"
            "   - **1/4 đĩa:** Tinh bột hấp thu chậm (gạo lứt, yến mạch, khoai lang, quinoa) giúp ổn định đường huyết.\n\n"
            "2. **Thói quen ăn uống khoa học:**\n"
            "   - 💧 **Uống đủ nước:** 1.5 - 2.5 lít nước lọc mỗi ngày (tương đương 40ml / kg cân nặng).\n"
            "   - 🧂 **Giảm muối & đường:** Ăn nhạt giúp bảo vệ tim mạch, huyết áp và thận; hạn chế nước ngọt đóng chai.\n"
            "   - 🍳 **Chế biến lành mạnh:** Ưu tiên hấp, luộc, áp chảo nhẹ; hạn chế đồ chiên xào ngập dầu mỡ.\n"
            "   - ⏰ **Ăn đúng giờ:** Không bỏ bữa sáng, ăn tối trước khi đi ngủ ít nhất 2 - 3 tiếng để dạ dày kịp tiêu hóa."
        )
    },
    {
        'category': 'nutrition_stomach',
        'keywords': ['ăn gì tốt cho dạ dày', 'đau dạ dày ăn gì', 'trào ngược ăn gì', 'loét dạ dày nên ăn', 'viêm dạ dày kiêng gì'],
        'title': '🍲 Chế Độ Ăn Cho Người Bị Dạ Dày & Trào Ngược',
        'response': (
            "🍲 **Thực đơn vàng cho người bị đau dạ dày & trào ngược thực quản:**\n\n"
            "✅ **NÊN ĂN:**\n"
            "   - **Thực phẩm bao bọc niêm mạc:** Bột yến mạch, cháo hạt sen, khoai lang, chuối chín, bí đỏ hấp.\n"
            "   - **Đạm dễ tiêu hóa:** Cá nạc, thịt ức gà hấp/luộc, đậu phụ non, trứng gà luộc chín mềm.\n"
            "   - **Rau củ giàu chất chống viêm:** Bắp cải (chứa nhiều Vitamin U giúp làm lành vết loét), bông cải xanh, rau mồng tơi.\n"
            "   - **Nước nghệ mật ong ấm:** Uống vào buổi sáng giúp kháng viêm và bảo vệ lớp niêm mạc dạ dày.\n\n"
            "❌ **CẦN KIÊNG:**\n"
            "   - Đồ chua có tính axit cao (chanh, quất, xoài xanh, giấm, dưa muối cà muối).\n"
            "   - Đồ cay nóng (ớt, hạt tiêu, mù tạt, tỏi sống).\n"
            "   - Rượu bia, cà phê đậm đặc, đồ uống có ga và thuốc lá."
        )
    },
    {
        'category': 'nutrition_diabetes',
        'keywords': ['tiểu đường ăn gì', 'đường huyết cao', 'chế độ ăn tiểu đường', 'hạ đường huyết ăn gì'],
        'title': '🩸 Dinh Dưỡng Cho Người Bị Tiểu Đường / Đường Huyết Cao',
        'response': (
            "🩸 **Chế độ ăn kiểm soát đường huyết ổn định:**\n\n"
            "1. **Chọn thực phẩm có chỉ số đường huyết thấp (GI < 55):**\n"
            "   - Gạo lứt, yến mạch nguyên cám, các loại đậu (đậu đen, đậu đỏ, đậu xanh).\n"
            "   - Các loại rau củ nhiều chất xơ hòa tan: súp lơ, cải bó xôi, mướp đắng (khổ qua), cà rốt luộc.\n\n"
            "2. **Bổ sung chất béo tốt & Protein:**\n"
            "   - Cá hồi, cá thu (giàu Omega-3), các loại hạt (hạnh nhân, óc chó, hạt chia).\n\n"
            "3. **Lưu ý đặc biệt:**\n"
            "   - Ăn rau xanh trước bữa ăn để làm chậm quá trình hấp thu glucose vào máu.\n"
            "   - Tránh xa bánh kẹo ngọt, nước ép trái cây cô đặc, chè, sữa đặc có đường.\n"
            "   - Chia nhỏ các bữa ăn (4 - 5 bữa/ngày) để tránh đỉnh tăng vọt đường huyết sau ăn."
        )
    },
    {
        'category': 'nutrition_weight_loss',
        'keywords': ['giảm cân', 'ăn kiêng', 'thực đơn giảm cân', 'giảm mỡ bụng', 'eat clean', 'nhịn ăn gián đoạn', 'keto'],
        'title': '🏃 Bí Quyết Ăn Uống Giảm Cân & Giảm Mỡ An Toàn',
        'response': (
            "🏃 **Nguyên tắc giảm mỡ an toàn & bền vững (Khoa học & Không hại sức khỏe):**\n\n"
            "1. **Thâm hụt Calo nhẹ nhàng (Calorie Deficit):**\n"
            "   - Nạp ít hơn mức cơ thể tiêu hao khoảng 300 - 500 kcal/ngày (tương đương giảm 0.5kg mỡ/tuần).\n"
            "   - Tuyệt đối **không nhịn đói cực đoan** vì sẽ làm suy giảm cơ bắp và rối loạn trao đổi chất.\n\n"
            "2. **Tăng cường Protein & Chất xơ:**\n"
            "   - Protein (1.5 - 2g/kg thể trọng) giúp duy trì cơ và no lâu, giảm cảm giác thèm ăn vặt.\n"
            "   - Ăn nhiều rau xanh, dưa chuột, cần tây, táo, bưởi để hỗ trợ hệ tiêu hóa.\n\n"
            "3. **Uống nước trước bữa ăn:**\n"
            "   - Uống 1 ly nước ấm trước bữa ăn 15 phút giúp kích hoạt tiêu hóa và kiểm soát khẩu phần.\n\n"
            "4. **Cắt giảm Calo rỗng:**\n"
            "   - Cắt bỏ trà sữa, đồ ngọt, snack, sốt mayonnaise và thức ăn nhanh chiên rán."
        )
    },
    {
        'category': 'nutrition_gym',
        'keywords': ['tập gym ăn gì', 'tăng cơ', 'whey protein', 'trước khi tập', 'sau khi tập', 'thực đơn thể hình'],
        'title': '💪 Dinh Dưỡng Cho Người Tập Luyện Thể Thao & Tăng Cơ',
        'response': (
            "💪 **Chiến lược dinh dưỡng tối ưu hóa cơ bắp & phục hồi năng lượng:**\n\n"
            "1. **Trước khi tập (30 - 60 phút):**\n"
            "   - Bổ sung tinh bột hấp thu vừa + chút protein nhẹ: 1 quả chuối + 1 lát bánh mì đen hoặc 1 ly sữa chua hạt.\n\n"
            "2. **Sau khi tập (trong vòng 45 phút - Cửa sổ đồng hóa):**\n"
            "   - Cung cấp Protein nạc hấp thu nhanh (ức gà, trứng luộc, whey protein) + Carb nhanh (cơm trắng, khoai lang) để phục hồi sợi cơ bị tổn thương.\n\n"
            "3. **Bù nước & Điện giải:**\n"
            "   - Uống từng ngụm nhỏ trong suốt buổi tập, bổ sung khoáng chất nếu ra nhiều mồ hôi."
        )
    },
    {
        'category': 'water_intake',
        'keywords': ['uống nước', 'bao nhiêu lít nước', 'uống nước đúng cách', 'uống trà', 'uống nước ấm'],
        'title': '💧 Hướng Dẫn Uống Nước Đúng Cách Cho Cơ Thể Khỏe Mạnh',
        'response': (
            "💧 **Công thức và thời điểm vàng uống nước cho cơ thể:**\n\n"
            "1. **Lượng nước cần thiết:**\n"
            "   - Công thức chuẩn: `Cân nặng (kg) x 40ml` (Ví dụ: 50kg cần khoảng 2.0 lít nước/ngày).\n\n"
            "2. **4 Thời điểm vàng để uống nước:**\n"
            "   - ⏰ **Ngay sau khi thức dậy (6:00 - 7:00):** 1 ly nước ấm giúp thanh lọc đường ruột và đánh thức các cơ quan.\n"
            "   - ⏰ **Trước bữa ăn 30 phút:** Giúp dịch vị tiêu hóa tiết ra sẵn sàng.\n"
            "   - ⏰ **Trước khi tắm:** Giúp cân bằng huyết áp và điều hòa thân nhiệt.\n"
            "   - ⏰ **Trước khi đi ngủ 30 - 45 phút:** 1 ngụm nước nhỏ giúp ngăn ngừa nguy cơ đông máu và tai biến ban đêm.\n\n"
            "3. **Lưu ý:** Uống từng ngụm nhỏ, ngồi uống thay vì đứng, hạn chế uống nhiều nước lạnh buốt."
        )
    },

    # --- SỨC KHỎE ĐỜI SỐNG & LỐI SỐNG LÀNH MẠNH ---
    {
        'category': 'sleep_wellness',
        'keywords': ['mất ngủ', 'khó ngủ', 'ngủ ngon', 'ngủ sâu giấc', 'mệt mỏi khi ngủ dậy', 'thức khuya'],
        'title': '🌙 Bí Quyết Cải Thiện Giấc Ngủ Sâu & Trị Mất Ngủ',
        'response': (
            "🌙 **Phương pháp khoa học để có giấc ngủ sâu và tái tạo năng lượng:**\n\n"
            "1. **Quy tắc vệ sinh giấc ngủ (Sleep Hygiene):**\n"
            "   - Đi ngủ và thức dậy vào một khung giờ cố định mỗi ngày (kể cả cuối tuần).\n"
            "   - Tắt ánh sáng xanh (điện thoại, máy tính, tivi) ít nhất 45 phút trước khi lên giường.\n"
            "   - Giữ phòng ngủ thoáng mát, nhiệt độ lý tưởng khoảng 24 - 26°C và tối hoàn toàn.\n\n"
            "2. **Đồ uống & Thực phẩm hỗ trợ giấc ngủ:**\n"
            "   - Uống 1 tách trà hoa cúc, trà tim sen hoặc 1 ly sữa ấm trước khi ngủ.\n"
            "   - Hạt sen, chuối, hạnh nhân chứa nhiều Melatonin và Magie tự nhiên giúp thư giãn thần kinh.\n\n"
            "3. **Thư giãn trước khi ngủ:**\n"
            "   - Ngâm chân bằng nước ấm với chút gừng/muối 15 phút, tập thở sâu theo nhịp 4-7-8."
        )
    },
    {
        'category': 'stress_mental',
        'keywords': ['stress', 'căng thẳng', 'lo âu', 'áp lực', 'mệt mỏi tinh thần', 'trầm cảm'],
        'title': '🌿 Giải Tỏa Căng Thẳng & Cân Bằng Tâm Trí',
        'response': (
            "🌿 **Cách giải tỏa căng thẳng và chăm sóc sức khỏe tinh thần:**\n\n"
            "1. **Kỹ thuật thở sâu 4-7-8:** Hít vào bằng mũi trong 4 giây, giữ hơi 7 giây, thở ra từ từ bằng miệng trong 8 giây (lặp lại 4 lần).\n"
            "2. **Vận động nhẹ giải phóng Endorphin:** Đi bộ nhanh 20 phút ngoài trời hoặc tập Yoga giúp xoa dịu hệ thần kinh trung ương.\n"
            "3. **Giảm kích thích thần kinh:** Giảm bớt trà đậm, cà phê và các chất kích thích; tăng cường vitamin nhóm B và Magie.\n"
            "4. **Chia sẻ và giải bày:** Tâm sự với người thân, bạn bè hoặc tìm đến chuyên gia tâm lý khi cảm xúc quá tải."
        )
    },
    {
        'category': 'office_ergonomics',
        'keywords': ['đau mỏi vai gáy', 'đau lưng văn phòng', 'ngồi nhiều', 'mỏi cổ', 'mỏi mắt máy tính'],
        'title': '💻 Chăm Sóc Sức Khỏe Cho Dân Văn Phòng',
        'response': (
            "💻 **Bí quyết bảo vệ cột sống và đôi mắt cho người ngồi máy tính nhiều:**\n\n"
            "1. **Quy tắc 20-20-20 cho mắt:** Cứ sau 20 phút nhìn màn hình, hãy nhìn vào một vật cách xa 20 feet (khoảng 6 mét) trong 20 giây.\n"
            "2. **Tư thế ngồi chuẩn y khoa:**\n"
            "   - Mắt ngang tầm với cạnh trên của màn hình máy tính.\n"
            "   - Lưng thẳng tựa vào đệm tựa, đùi song song mặt đất, bàn chân đặt phẳng trên sàn.\n"
            "   - Khuỷu tay gập góc 90 độ khi gõ bàn phím.\n"
            "3. **Đứng dậy vận động:** Cứ mỗi 45 - 60 phút, đứng lên vươn vai, xoay khớp cổ và đi lấy nước để máu lưu thông đều."
        )
    },

    # --- SƠ CỨU & CHĂM SÓC BAN ĐẦU TẠI NHÀ ---
    {
        'category': 'fever_care',
        'keywords': ['hạ sốt', 'cách hạ sốt', 'sốt cao', 'uống thuốc hạ sốt', 'chườm ấm', 'chườm lạnh'],
        'title': '🌡️ Hướng Dẫn Hạ Sốt Nhanh & An Toàn Tại Nhà',
        'response': (
            "🌡️ **Quy trình xử lý khi bị sốt an toàn theo khuyến cáo y khoa:**\n\n"
            "1. **Chăm sóc cơ thể:**\n"
            "   - Mặc quần áo mỏng, rộng rãi, thoáng mát, phòng ốc thông thoáng.\n"
            "   - Dùng khăn mềm thấm **nước ấm** (nhiệt độ nước thấp hơn thân nhiệt 2 độ) để lau chườm tại trán, 2 nách và 2 bẹn. *(Tuyệt đối không chườm đá lạnh vì gây co mạch)*.\n\n"
            "2. **Bù nước & Điện giải:**\n"
            "   - Uống nhiều nước lọc, nước oresol (pha đúng tỉ lệ hướng dẫn), nước cam, nước dừa.\n\n"
            "3. **Dùng thuốc hạ sốt (khi sốt $\ge 38.5^\circ C$):**\n"
            "   - Paracetamol liều $10 - 15mg / kg$ cân nặng mỗi lần, cách nhau $4 - 6$ tiếng (không quá 4 lần/ngày).\n\n"
            "⚠️ **Cần đến bệnh viện ngay nếu:** Sốt cao trên $39.5^\circ C$ không hạ, co giật, khó thở, nôn ói liên tục hoặc phát ban li bì."
        )
    },
    {
        'category': 'burn_care',
        'keywords': ['bị bỏng', 'sơ cứu bỏng', 'bỏng nước sôi', 'bỏng bô xe', 'bỏng dầu mỡ'],
        'title': '🔥 Sơ Cứu Bỏng Đúng Cách (Không Để Lại Sẹo)',
        'response': (
            "🔥 **5 Bước sơ cứu bỏng chuẩn y khoa ngay tức thì:**\n\n"
            "1. **Làm mát vết bỏng lập tức:** Ngâm hoặc xả nhẹ vết bỏng dưới vòi **nước sạch mát** (15 - 20°C) liên tục trong 15 - 20 phút để hạ nhiệt mô tế bào.\n"
            "2. **Tháo bỏ trang sức, đồ chật** quanh vùng bỏng trước khi bị sưng phù nề.\n"
            "3. **Bảo vệ vết bỏng:** Che phủ nhẹ nhàng bằng gạc y tế vô trùng hoặc vải sạch.\n"
            "4. ❌ **TUYỆT ĐỐI KHÔNG:** Bôi kem đánh răng, nước mắm, mỡ trăn, trứng sống hay chườm đá lạnh vì sẽ gây nhiễm trùng hoại tử!\n"
            "5. **Đến cơ sở y tế:** Nếu vết bỏng diện tích rộng, có bóng nước to hoặc ở các vị trí nhạy cảm (mặt, khớp, bộ phận sinh dục)."
        )
    }
]

# Bộ quy tắc ánh xạ Triệu chứng -> Chuyên khoa & Lời khuyên y tế lâm sàng
SYMPTOM_KNOWLEDGE_BASE = {
    'thần kinh': {
        'keywords': ['đau đầu', 'nhức đầu', 'chóng mặt', 'hoa mắt', 'mất ngủ', 'tiền đình', 'đột quỵ', 'tê tay chân', 'co giật', 'nửa đầu', 'tai biến'],
        'specialty_name': 'Thần kinh',
        'advice': 'Triệu chứng đau đầu, chóng mặt hoặc mất ngủ có thể xuất phát từ căng thẳng (stress), thiếu máu não, đau nửa đầu Migraine hoặc rối loạn tiền đình. Bạn nên nghỉ ngơi ở nơi thoáng mát, uống đủ nước và tránh làm việc quá sức trước màn hình.',
        'urgent': 'Nếu có dấu hiệu méo miệng, yếu liệt nửa người, nói ngọng hoặc đau đầu dữ dội đột ngột, vui lòng đến ngay cơ sở cấp cứu gần nhất!'
    },
    'tim mạch': {
        'keywords': ['đau ngực', 'tức ngực', 'khó thở', 'hồi hộp', 'tim đập nhanh', 'huyết áp cao', 'tăng huyết áp', 'hạ huyết áp', 'nhói tim', 'mạch vành'],
        'specialty_name': 'Tim mạch',
        'advice': 'Triệu chứng đau tức ngực hoặc hồi hộp đánh trống ngực cần được thăm khám cẩn thận để tầm soát bệnh lý mạch vành, rối loạn nhịp tim hoặc huyết áp. Bạn nên hạn chế gắng sức và giữ tinh thần thư giãn.',
        'urgent': 'Cơn đau thắt ngực lan ra cánh tay trái, cổ hoặc hàm kéo dài trên 15 phút là dấu hiệu cảnh báo khẩn cấp!'
    },
    'tiêu hóa': {
        'keywords': ['đau bụng', 'đau dạ dày', 'ợ chua', 'ợ hơi', 'trào ngược', 'tiêu chảy', 'táo bón', 'nôn mửa', 'buồn nôn', 'khó tiêu', 'đầy bụng', 'viêm loét', 'đại tràng', 'trĩ'],
        'specialty_name': 'Tiêu hóa',
        'advice': 'Các triệu chứng như đau thượng vị, ợ chua hay đầy hơi thường liên quan đến viêm loét dạ dày tá tràng hoặc trào ngược dạ dày thực quản (GERD). Nên ăn đúng bữa, kiêng đồ chua cay, dầu mỡ và đồ uống có cồn.',
        'urgent': 'Nếu nôn ra máu, đi ngoài phân đen hoặc đau quặn dữ dội, cần đi viện cấp cứu ngay.'
    },
    'tai mũi họng': {
        'keywords': ['đau họng', 'rát họng', 'viêm xoang', 'nghẹt mũi', 'sổ mũi', 'ù tai', 'chảy máu cam', 'khàn tiếng', 'viêm amidan', 'ho khan', 'ho có đờm', 'viêm họng'],
        'specialty_name': 'Tai Mũi Họng',
        'advice': 'Đau họng, nghẹt mũi thường do viêm đường hô hấp trên hoặc viêm xoang dị ứng khi thời tiết thay đổi. Bạn có thể súc họng bằng nước muối sinh lý ấm, giữ ấm cổ họng.',
        'urgent': 'Nếu sốt cao khó hạ kèm khó thở nặng, cần đến gặp bác sĩ kiểm tra trực tiếp.'
    },
    'nhi khoa': {
        'keywords': ['trẻ em', 'em bé', 'trẻ sơ sinh', 'bé sốt', 'bé quấy khóc', 'biếng ăn', 'bé nôn', 'sởi', 'thủy đậu', 'chân tay miệng', 'tiêm chủng'],
        'specialty_name': 'Nhi khoa',
        'advice': 'Sức đề kháng của trẻ còn non nớt. Khi bé sốt cần cho mặc quần áo thoáng mát, chườm ấm và bù nước oresol đúng cách. Tuyệt đối không tự ý cho trẻ dùng kháng sinh khi chưa có chỉ định.',
        'urgent': 'Bé sốt cao co giật, bỏ bú, ngủ li bì hoặc thở rút lõm lồng ngực là dấu hiệu cần cấp cứu ngay!'
    },
    'da liễu': {
        'keywords': ['ngứa da', 'dị ứng', 'mẩn đỏ', 'mụn trứng cá', 'chàm', 'vảy nến', 'rụng tóc', 'nổi mề đay', 'phát ban', 'nấm da', 'viêm da'],
        'specialty_name': 'Da liễu',
        'advice': 'Nổi mẩn ngứa hoặc phát ban có thể do viêm da tiếp xúc, dị ứng thời tiết hoặc thức ăn. Tránh cào gãi làm trầy xước nhiễm trùng và giữ da luôn sạch sẽ.',
        'urgent': 'Nếu phát ban kèm phù môi, mí mắt hoặc khó thở, đây có thể là phản vệ khẩn cấp.'
    },
    'cơ xương khớp': {
        'keywords': ['đau lưng', 'thoát vị', 'đau khớp', 'khớp gối', 'thoái hóa', 'mỏi vai gáy', 'đau nhức xương', 'gút', 'acid uric', 'viêm khớp'],
        'specialty_name': 'Cơ xương khớp',
        'advice': 'Đau mỏi vai gáy hoặc đau khớp gối thường gặp ở người làm việc văn phòng hoặc người cao tuổi do thoái hóa. Nên duy trì vận động nhẹ nhàng, điều chỉnh tư thế ngồi thẳng.',
        'urgent': 'Nếu khớp sưng to nóng đỏ cấp tính hoặc không cử động được, cần thăm khám sớm.'
    },
    'mắt': {
        'keywords': ['đau mắt', 'đỏ mắt', 'mờ mắt', 'cận thị', 'chảy nước mắt', 'cộm mắt', 'mắt nhức', 'loạn thị', 'viêm kết mạc'],
        'specialty_name': 'Mắt (Nhãn khoa)',
        'advice': 'Đau mắt, cộm xốn có thể do viêm kết mạc hoặc hội chứng thị giác màn hình. Nhỏ nước mắt nhân tạo, cho mắt nghỉ ngơi theo quy tắc 20-20-20.',
        'urgent': 'Nếu nhìn mờ đột ngột hoặc thấy chớp sáng kèm đau nhức sâu trong hốc mắt, cần khám mắt ngay.'
    },
    'sản phụ khoa': {
        'keywords': ['mang thai', 'mẹ bầu', 'kinh nguyệt', 'chậm kinh', 'ốm nghén', 'phụ khoa', 'khám thai', 'sinh con'],
        'specialty_name': 'Sản - Phụ khoa',
        'advice': 'Trong thai kỳ, phụ nữ cần khám định kỳ theo mốc, bổ sung Sắt, Axit Folic và Canxi đầy đủ theo chỉ dẫn y khoa.',
        'urgent': 'Nếu đau bụng dữ dội hoặc xuất huyết âm đạo bất thường trong thai kỳ, phải đến viện ngay.'
    },
    'nội tổng quát': {
        'keywords': ['sốt', 'mệt mỏi', 'sụt cân', 'khám tổng quát', 'kiểm tra sức khỏe', 'khám định kỳ', 'ốm', 'sức khỏe'],
        'specialty_name': 'Nội tổng quát',
        'advice': 'Khám Nội tổng quát là bước đầu tiên tối ưu giúp bạn kiểm tra các chỉ số sức khỏe tổng thể, thực hiện xét nghiệm cơ bản và được bác sĩ định hướng điều trị.',
        'urgent': ''
    }
}

DISCLAIMER_TEXT = "💡 *Lưu ý y khoa: Thông tin do AI cung cấp chỉ mang tính chất tham khảo, không thay thế chẩn đoán hoặc đơn thuốc chuyên môn của bác sĩ.*"


def call_openai_medical_chat(user_message):
    """
    Gọi OpenAI API (khi có OPENAI_API_KEY) để trả lời mọi thắc mắc y tế, dinh dưỡng, sức khỏe, lối sống
    """
    api_key = os.environ.get('OPENAI_API_KEY', '').strip()
    if not api_key:
        return None

    system_prompt = (
        "Bạn là Bác sĩ Trợ lý Y tế AI (Medical AI Assistant) - chuyên gia tận tâm tư vấn về y tế, sức khỏe, "
        "chế độ ăn uống, dinh dưỡng khoa học, lối sống lành mạnh, chăm sóc gia đình và sơ cứu ban đầu.\n"
        "- Trả lời bằng tiếng Việt tự nhiên, ân cần, định dạng rõ ràng bằng gạch đầu dòng và emoji sinh động.\n"
        "- Đưa ra các hướng dẫn khoa học, chi tiết về thực phẩm nên ăn, nên kiêng, cách chế biến, cách sinh hoạt.\n"
        "- Luôn kèm lưu ý y khoa khi cần thiết và cảnh báo dấu hiệu nguy hiểm nếu có.\n"
        "- Không phán đoán độc đoán mà tư vấn trên góc độ y học chứng cứ."
    )

    try:
        headers = {
            'Authorization': f"Bearer {api_key}",
            'Content-Type': 'application/json'
        }
        payload = {
            'model': 'gpt-4o-mini',
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_message}
            ],
            'temperature': 0.7,
            'max_tokens': 900
        }
        resp = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=payload, timeout=12)
        if resp.status_code == 200:
            res_json = resp.json()
            ai_text = res_json['choices'][0]['message']['content'].strip()
            return ai_text
    except Exception:
        pass
    return None


def process_medical_chat(user_message, session=None):
    """
    Hàm xử lý tin nhắn trung tâm:
    - Trả lời thông minh mọi câu hỏi về dinh dưỡng, ăn uống, sức khỏe, lối sống, sơ cứu, y học.
    - Phân biệt rõ giữa:
      1) Hỏi đáp kiến thức sức khỏe/ăn uống -> Trả lời chi tiết, KHÔNG ép nút đặt lịch.
      2) Yêu cầu đặt lịch khám / Hỏi bệnh viện / Mô tả bệnh lý muốn đi khám -> Kích hoạt quy trình gợi ý bác sĩ và đặt lịch.
    """
    msg_clean = user_message.lower().strip()

    response_data = {
        'reply': '',
        'stage': 'general',
        'suggested_specialty': None,
        'suggested_provinces': [],
        'suggested_hospitals': [],
        'suggested_doctors': [],
        'quick_replies': []
    }

    # ================= 1. KIỂM TRA INTENT ĐẶT LỊCH / CHỌN TỈNH / BỆNH VIỆN =================
    all_provinces = list(TinhThanh.objects.all())
    
    # 1.1 Người dùng chủ động chọn Tỉnh/Thành phố
    matched_province = None
    for prov in all_provinces:
        if prov.ten_tinh.lower() in msg_clean:
            matched_province = prov
            break

    if matched_province:
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

    # 1.2 Người dùng chủ động chọn Bệnh viện
    matched_hospital = None
    for h in BenhVien.objects.all():
        if h.ten_benh_vien.lower() in msg_clean:
            matched_hospital = h
            break

    if matched_hospital:
        doctors = list(BacSi.objects.filter(benh_vien=matched_hospital, trang_thai=True).select_related('chuyen_khoa', 'user'))
        if len(doctors) < 4:
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

    # ================= 2. KIỂM TRA HỎI ĐÁP DINH DƯỠNG, ĂN UỐNG & SỨC KHỎE ĐỜI SỐNG =================
    # Kiểm tra xem có khớp các chủ đề dinh dưỡng / ăn uống / lối sống / sơ cứu không
    matched_health_topics = []
    for topic in HEALTH_KNOWLEDGE_BASE:
        for kw in topic['keywords']:
            if kw in msg_clean:
                matched_health_topics.append(topic)
                break

    if matched_health_topics:
        # Người dùng đang hỏi về Dinh dưỡng, Chế độ ăn hoặc Sức khỏe lối sống!
        primary_topic = matched_health_topics[0]
        
        # Thử gọi OpenAI nếu có cấu hình để trả lời phong phú hơn
        openai_reply = call_openai_medical_chat(user_message)
        if openai_reply:
            response_data['reply'] = openai_reply + f"\n\n{DISCLAIMER_TEXT}"
        else:
            response_data['reply'] = (
                f"{primary_topic['response']}\n\n"
                f"{DISCLAIMER_TEXT}\n\n"
                f"💬 *Bạn có thể hỏi thêm về bất kỳ thực phẩm, chế độ dinh dưỡng hoặc vấn đề sức khỏe nào khác!*"
            )

        response_data['stage'] = 'general'
        response_data['quick_replies'] = [
            'Ăn gì tốt cho dạ dày',
            'Chế độ ăn cho người tiểu đường',
            'Cách giảm cân an toàn',
            'Uống nước thế nào đúng cách',
            'Bí quyết ngủ ngon'
        ]
        return response_data

    # ================= 3. PHÂN TÍCH TRIỆU CHỨNG BỆNH LÝ & ĐIỀU HƯỚNG CHUYÊN KHOA =================
    detected_specialties = []
    matched_advice = []
    matched_urgent = []

    for cat_name, cat_info in SYMPTOM_KNOWLEDGE_BASE.items():
        for kw in cat_info['keywords']:
            if kw in msg_clean:
                detected_specialties.append(cat_info['specialty_name'])
                matched_advice.append(cat_info['advice'])
                if cat_info['urgent']:
                    matched_urgent.append(cat_info['urgent'])
                break

    if detected_specialties:
        # Tìm thấy chuyên khoa phù hợp với triệu chứng bệnh nhân!
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
            f"🤖 **Phân tích của Bác sĩ AI:**\n"
            f"Dựa trên các triệu chứng bạn vừa chia sẻ, hệ thống đề xuất bạn nên khám chuyên khoa {specialty_text}.\n\n"
            f"🩺 **Tư vấn y khoa tham khảo:**\n{advice_text}{urgent_text}\n\n"
            f"{DISCLAIMER_TEXT}\n\n"
            f"👨‍⚕️ **Đội ngũ bác sĩ chuyên khoa {primary_specialty} sẵn sàng nhận lịch (cả bác sĩ nam & nữ):**\n"
            f"Bạn có thể chọn trực tiếp bác sĩ bên dưới để đặt lịch khám, hoặc chọn **Tỉnh/Thành phố** để xem bệnh viện gần bạn nhất:"
        )
        return response_data

    # ================= 4. THỬ GỌI OPENAI CHO CÂU HỎI MỞ BẤT KỲ =================
    openai_reply = call_openai_medical_chat(user_message)
    if openai_reply:
        response_data['reply'] = openai_reply + f"\n\n{DISCLAIMER_TEXT}"
        response_data['quick_replies'] = ['Tư vấn dinh dưỡng', 'Khám tại Đà Nẵng', 'Khám tại Hà Nội', 'Khám tại TP.HCM']
        return response_data

    # ================= 5. CHÀO HỎI HOẶC TRẢ LỜI MỞ RỘNG =================
    greetings = ['xin chào', 'chào bạn', 'hello', 'hi', 'bạn là ai', 'có ai ở đây không', 'giúp tôi']
    if any(g in msg_clean for g in greetings):
        response_data['reply'] = (
            "👋 **Xin chào bạn! Tôi là Bác sĩ Trợ lý AI của Medical AI.**\n\n"
            "Tôi luôn sẵn sàng hỗ trợ bạn 24/7 về mọi vấn đề sức khỏe:\n"
            "1. 🥗 **Tư vấn dinh dưỡng & ăn uống lành mạnh:** Ăn gì tốt cho dạ dày, tiểu đường, tim mạch, giảm cân, tăng cơ...\n"
            "2. 🌿 **Lối sống & Chăm sóc sức khỏe:** Cách cải thiện giấc ngủ, giảm căng thẳng, chăm sóc mắt, sơ cứu tại nhà...\n"
            "3. 🩺 **Phân tích triệu chứng y khoa:** Định hướng đúng chuyên khoa khi bạn cảm thấy không khỏe.\n"
            "4. 🏥 **Đặt lịch khám bệnh thông minh:** Tìm bệnh viện uy tín tại 5 tỉnh thành và đặt lịch với bác sĩ chuyên khoa (nam & nữ).\n\n"
            "👉 **Bạn có thể hỏi tôi bất kỳ điều gì!** *(Ví dụ: 'Ăn gì tốt cho tiêu hóa?', 'Uống nước thế nào đúng cách?', 'Tôi bị đau nửa đầu 2 ngày nay')*"
        )
        response_data['quick_replies'] = [
            'Ăn gì tốt cho dạ dày?',
            'Chế độ ăn cho người tiểu đường',
            'Cách giảm cân an toàn',
            'Tôi bị đau đầu, chóng mặt',
            'Đặt lịch tại Đà Nẵng'
        ]
        return response_data

    # 6. Phản hồi thông minh mặc định khi câu hỏi quá trừu tượng
    response_data['reply'] = (
        "Cảm ơn câu hỏi của bạn. Tôi có thể giải đáp cho bạn về **chế độ dinh dưỡng, ăn uống cho từng bệnh lý, mẹo sống khỏe, sơ cứu tại nhà** hoặc **phân tích triệu chứng để đặt lịch khám**.\n\n"
        "Bạn hãy nhập chi tiết hơn câu hỏi của mình nhé (Ví dụ: *'Người bị cao huyết áp nên ăn gì?'*, *'Cách hạ sốt nhanh tại nhà'*, *'Tôi bị đau nhức khớp gối'*)."
    )
    response_data['quick_replies'] = [
        'Dinh dưỡng cho dạ dày',
        'Thực đơn giảm mỡ an toàn',
        'Cách ngủ ngon sâu giấc',
        'Đặt lịch khám tại Đà Nẵng'
    ]
    return response_data

