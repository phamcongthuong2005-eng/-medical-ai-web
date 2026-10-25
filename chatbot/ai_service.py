import re
import json
import os
import urllib.request
import urllib.error
try:
    import requests
except ImportError:
    requests = None
from datetime import datetime, timedelta
from hospitals.models import TinhThanh, BenhVien, ChuyenKhoa
from doctors.models import BacSi, LichLamViec
from django.utils import timezone

# Load .env file nếu có
try:
    from pathlib import Path
    env_path = Path(__file__).resolve().parent.parent / '.env'
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
except Exception:
    pass

DISCLAIMER_TEXT = "💡 *Lưu ý y khoa: Thông tin do AI cung cấp mang tính chất tham khảo ban đầu. Khi triệu chứng nặng hoặc kéo dài, bạn nên thăm khám trực tiếp tại cơ sở y tế.*"


# ================= 1. GỌI EXTERNAL LLM (GOOGLE GEMINI & OPENAI) =================
def _http_post_json(url, headers, payload, timeout=12):
    """Gửi HTTP POST JSON hỗ trợ cả requests và urllib chuẩn của Python"""
    try:
        if requests is not None:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
        else:
            req_data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=req_data, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode('utf-8'))
    except Exception:
        pass
    return None


def call_external_llm(user_message, history=None):
    """
    Gọi Google Gemini API hoặc OpenAI API nếu có API key trong biến môi trường.
    Hỗ trợ sinh câu trả lời tự nhiên, ân cần như bác sĩ thực thụ.
    """
    system_prompt = (
        "Bạn là Bác Sĩ Trợ Lý Y Tế AI (Medical AI) - đóng vai trò là Bác sĩ Gia đình tận tâm, giàu kinh nghiệm, "
        "tư vấn cho người bệnh (đặc biệt là các cô chú bác lớn tuổi và người dân bình thường).\n\n"
        "ĐẶC ĐIỂM NGƯỜI BỆNH:\n"
        "- Người bệnh và người lớn tuổi KHÔNG BIẾT viết prompt hay thuật ngữ y khoa. Họ 'đau sao nói vậy', "
        "dùng ngôn từ đời thường, tiếng địa phương, từ tượng thanh tượng hình ('nhức cái lưng cúi không nổi', "
        "'xây xẩm mặt mày chao đảo', 'bụng ấm ách ăn vô muốn ói', 'đầu gối lục cục đau điếng', 'ngực nặng trịch thở không ra hơi', "
        "'cổ họng vướng như có hột cơm mắc', 'hâm hấp sốt gai lạnh trong xương', 'chuột rút vọp bẻ đau điếng'...). \n"
        "- Bạn phải lập tức hiểu đúng bản chất cơn đau và cơ quan bị bệnh đằng sau những câu nói mộc mạc đó.\n\n"
        "PHONG CÁCH TƯ VẤN CỦA BÁC SĨ:\n"
        "1. Lễ phép, ân cần, gần gũi: Mở đầu bằng 'Dạ, Bác sĩ chào bác/cô/chú ạ!', xưng 'Bác sĩ' hoặc 'mình', gọi người bệnh là 'bác/cô/chú/bạn'. Lắng nghe và trấn an tinh thần người bệnh trước tiên.\n"
        "2. Giải thích bình dị, dễ hiểu: Tránh từ ngữ chuyên môn hàn lâm. Dùng hình ảnh đời thường để giải thích nguyên nhân gây đau.\n"
        "3. Hướng dẫn việc cần làm ngay tại nhà: Những việc đơn giản, an toàn làm được ngay bằng đồ dùng sẵn có (nước ấm, chườm ấm/mát, xoa bóp, tư thế nằm/ngồi, món ăn dễ tiêu...).\n"
        "4. Cảnh báo dấu hiệu nguy hiểm (Cờ đỏ): Dặn dò các triệu chứng nguy kịch cần người nhà hoặc con cháu đưa đến bệnh viện cấp cứu ngay.\n"
        "5. Hỏi thăm 1-2 câu ngắn gọn, dễ trả lời: Để tìm hiểu thêm diễn tiến bệnh (bị mấy ngày rồi, có đo huyết áp/nhiệt độ chưa...).\n"
        "6. Hướng dẫn thăm khám ân cần: Gợi ý đúng chuyên khoa, dặn dò người bệnh có thể nhờ con cháu chọn bác sĩ đặt lịch giúp trên màn hình.\n"
        "7. Trình bày thoáng, dễ đọc cho người lớn tuổi: Chia đoạn rõ ràng, in đậm các ý chính, dùng emoji sinh động, cỡ chữ dễ nhìn."
    )

    # 1. Thử gọi Google Gemini API nếu có GEMINI_API_KEY hoặc GOOGLE_API_KEY
    gemini_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY', '').strip()
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            headers = {'Content-Type': 'application/json'}
            
            contents = []
            if history:
                for h in history[-4:]:
                    role = 'user' if h.get('role') == 'user' else 'model'
                    contents.append({
                        'role': role,
                        'parts': [{'text': h.get('content', '')}]
                    })
            contents.append({
                'role': 'user',
                'parts': [{'text': f"[Chỉ dẫn hệ thống: {system_prompt}]\n\nCâu hỏi/Triệu chứng của người bệnh: {user_message}"}]
            })

            payload = {
                'contents': contents,
                'generationConfig': {
                    'temperature': 0.7,
                    'maxOutputTokens': 1200
                }
            }
            res_data = _http_post_json(url, headers, payload, timeout=12)
            if res_data:
                candidates = res_data.get('candidates', [])
                if candidates and 'content' in candidates[0]:
                    parts = candidates[0]['content'].get('parts', [])
                    if parts and 'text' in parts[0]:
                        return parts[0]['text'].strip()
        except Exception:
            pass

    # 2. Thử gọi OpenAI API nếu có OPENAI_API_KEY
    openai_key = os.environ.get('OPENAI_API_KEY', '').strip()
    if openai_key:
        try:
            headers = {
                'Authorization': f"Bearer {openai_key}",
                'Content-Type': 'application/json'
            }
            messages = [{'role': 'system', 'content': system_prompt}]
            if history:
                for h in history[-4:]:
                    messages.append({'role': h.get('role', 'user'), 'content': h.get('content', '')})
            messages.append({'role': 'user', 'content': user_message})

            payload = {
                'model': 'gpt-4o-mini',
                'messages': messages,
                'temperature': 0.7,
                'max_tokens': 1200
            }
            res_json = _http_post_json('https://api.openai.com/v1/chat/completions', headers, payload, timeout=12)
            if res_json and 'choices' in res_json:
                return res_json['choices'][0]['message']['content'].strip()
        except Exception:
            pass

    return None


# ================= 2. BỘ TRI THỨC Y TẾ & DINH DƯỠNG SỐNG KHỎE =================
HEALTH_KNOWLEDGE_BASE = [
    {
        'category': 'nutrition_stomach',
        'keywords': [
            'đau dạ dày nên ăn gì', 'đau dạ dày ăn gì', 'bị đau dạ dày nên ăn gì', 'người bị đau dạ dày nên ăn gì',
            'ăn gì tốt cho dạ dày', 'trào ngược dạ dày nên ăn gì', 'trào ngược dạ dày ăn gì', 'dạ dày nên ăn gì',
            'dạ dày ăn gì', 'dạ dày kiêng gì', 'đau dạ dày kiêng gì', 'trào ngược ăn gì', 'loét dạ dày nên ăn',
            'viêm dạ dày kiêng gì', 'đau bao tử nên ăn gì', 'đau bao tử ăn gì', 'trào ngược thực quản ăn gì'
        ],
        'title': '🍲 Chế Độ Ăn Cho Người Bị Dạ Dày & Trào Ngược',
        'response': (
            "Chào bạn! Khi dạ dày đang bị viêm hoặc có hiện tượng trào ngược axit, niêm mạc đang rất nhạy cảm nên chế độ ăn đóng vai trò then chốt giúp làm lành vết thương bạn nhé.\n\n"
            "✅ **Những món nên ăn giúp êm bụng, lành dạ dày:**\n"
            "- **Món bao bọc niêm mạc:** Bột yến mạch ấm, cháo hạt sen, khoai lang hấp, chuối chín (chuối tiêu chín kỹ hoặc chuối ngự), bí đỏ nấu nhừ.\n"
            "- **Đạm dễ tiêu:** Cá nạc hấp gừng, ức gà luộc xé nhỏ, trứng hấp mềm, đậu hũ non.\n"
            "- **Rau củ chứa vitamin U (lành vết loét):** Bắp cải luộc, bông cải xanh, canh rau ngót hoặc mồng tơi nấu thịt nạc.\n"
            "- **Mẹo dân gian hiệu quả:** 1 ly nước ấm pha 1 thìa tinh bột nghệ + 1 thìa mật ong nguyên chất vào buổi sáng trước khi ăn 30 phút.\n\n"
            "❌ **Cần kiêng tuyệt đối trong giai đoạn này:**\n"
            "- Đồ chua có tính axit cao (chanh, quất, xoài xanh, giấm, dưa muối, cà muối).\n"
            "- Đồ cay nóng (ớt, tiêu, mù tạt, tỏi sống) gây kích ứng xuất huyết niêm mạc.\n"
            "- Bia rượu, cà phê đậm đặc, trà đặc, nước ngọt có ga và khói thuốc lá."
        )
    },
    {
        'category': 'nutrition_diabetes',
        'keywords': [
            'tiểu đường nên ăn gì', 'tiểu đường ăn gì', 'người bị tiểu đường nên ăn gì',
            'đường huyết cao nên ăn gì', 'đường huyết cao ăn gì', 'chế độ ăn tiểu đường',
            'hạ đường huyết ăn gì', 'tiểu đường kiêng gì'
        ],
        'title': '🩸 Dinh Dưỡng Cho Người Bị Tiểu Đường / Đường Huyết Cao',
        'response': (
            "Chào bạn! Nguyên tắc cốt lõi trong dinh dưỡng của người tiểu đường không phải là nhịn ăn khắt khe, mà là kiểm soát chỉ số đường huyết ổn định, tránh để đường huyết tăng vọt sau ăn hay tụt dốc lúc đói.\n\n"
            "🩸 **Nguyên tắc thực đơn kiểm soát đường huyết:**\n"
            "1. **Chọn tinh bột có chỉ số GI thấp (< 55):** Gạo lứt, yến mạch nguyên cám, đậu đen, đậu đỏ, khoai lang luộc.\n"
            "2. **Thứ tự ăn thông minh:** Luôn ăn một bát canh rau xanh hoặc đĩa rau luộc trước tiên -> sau đó đến phần thịt/cá (chất đạm) -> và cuối cùng mới ăn cơm/tinh bột. Cách này giúp chất xơ làm chậm quá trình hấp thu glucose vào máu cực kỳ hiệu quả.\n"
            "3. **Tăng cường chất béo tốt:** Dầu ô liu, quả bơ, hạt óc chó, hạnh nhân, cá béo giàu Omega-3 giúp bảo vệ thành mạch tim mạch.\n"
            "4. **Kiêng khem:** Cắt bỏ nước ngọt có ga, bánh kẹo ngọt, chè, hoa quả sấy khô ngào đường và các loại nước ép trái cây đóng hộp."
        )
    },
    {
        'category': 'nutrition_weight_loss',
        'keywords': ['giảm cân', 'ăn kiêng', 'thực đơn giảm cân', 'giảm mỡ bụng', 'eat clean', 'nhịn ăn gián đoạn', 'keto', 'giảm béo'],
        'title': '🏃 Bí Quyết Ăn Uống Giảm Cân & Giảm Mỡ An Toàn',
        'response': (
            "Chào bạn! Để giảm mỡ hiệu quả và bền vững mà không bị mệt mỏi hay mất cơ bắp, bạn nên áp dụng nguyên tắc thâm hụt calo khoa học thay vì nhịn đói cực đoan nhé.\n\n"
            "🏃 **3 Nguyên tắc giảm mỡ chuẩn y khoa:**\n"
            "1. **Thâm hụt calo vừa phải (300 - 500 kcal/ngày):** Giúp bạn giảm khoảng 0.5kg mỡ/tuần một cách an toàn mà cơ thể vẫn tràn đầy năng lượng.\n"
            "2. **Tăng cường Protein nạc:** Nạp đủ 1.5 - 2g protein/kg cân nặng từ ức gà, trứng luộc, cá, đậu phụ. Protein giúp giữ khối cơ, đốt nhiều calo hơn khi tiêu hóa và giữ cảm giác no lâu, chống thèm ăn vặt.\n"
            "3. **Uống nước trước bữa ăn:** Uống 1 ly nước ấm lớn trước bữa ăn 15 phút giúp kích hoạt trao đổi chất và kiểm soát khẩu phần tốt hơn.\n"
            "4. **Cắt giảm calo rỗng:** Nói không với trà sữa, bánh ngọt, snack, sốt béo ngậy và đồ chiên ngập dầu."
        )
    },
    {
        'category': 'nutrition_general',
        'keywords': [
            'chế độ ăn uống', 'dinh dưỡng khoa học', 'ăn gì tốt cho sức khỏe',
            'thực đơn tốt cho sức khỏe', 'chế độ ăn lành mạnh', 'ăn gì khỏe',
            'ăn gì', 'chế độ ăn', 'dinh dưỡng', 'thực đơn', 'thực phẩm tốt', 'thực phẩm nên kiêng', 'nên ăn gì', 'kiêng ăn gì', 'uống gì'
        ],
        'title': '🥗 Tư Vấn Dinh Dưỡng & Ăn Uống Khoa Học',
        'response': (
            "Chào bạn nhé! Một chế độ dinh dưỡng cân bằng chính là nền tảng quan trọng nhất để cơ thể dẻo dai và phòng ngừa bệnh tật.\n\n"
            "🥗 **Nguyên tắc đĩa thức ăn vàng từ chuyên gia:**\n"
            "1. **1/2 Đĩa thức ăn (Rau củ & Trái cây tươi):** Ưu tiên rau xanh đậm (cải bó xôi, súp lơ, mồng tơi) và quả ít ngọt (táo, ổi, bưởi, việt quất) để cung cấp chất xơ, vitamin C, E và chất chống oxy hóa.\n"
            "2. **1/4 Đĩa thức ăn (Chất đạm chất lượng cao):** Ức gà nạc, cá biển sâu (cá hồi, cá thu giàu Omega-3), trứng gà, đậu phụ non và các loại hạt.\n"
            "3. **1/4 Đĩa thức ăn (Tinh bột chuyển hóa chậm):** Gạo lứt, yến mạch nguyên cám, khoai lang hấp, hạt quinoa giúp giải phóng năng lượng từ từ, không làm tăng vọt đường huyết.\n\n"
            "💧 **Thói quen vàng cần duy trì mỗi ngày:**\n"
            "- Uống đủ 1.5 - 2 lít nước ấm, uống rải rác từng ngụm nhỏ.\n"
            "- Giảm bớt muối và đồ ngọt đóng chai; ưu tiên cách chế biến luộc, hấp, áp chảo nhẹ.\n"
            "- Ăn tối nhẹ bụng và cách giờ đi ngủ ít nhất 2 - 3 tiếng để dạ dày được nghỉ ngơi."
        )
    },
    {
        'category': 'sleep_wellness',
        'keywords': ['mất ngủ', 'khó ngủ', 'ngủ ngon', 'ngủ sâu giấc', 'mệt mỏi khi ngủ dậy', 'thức khuya'],
        'title': '🌙 Bí Quyết Cải Thiện Giấc Ngủ Sâu & Trị Mất Ngủ',
        'response': (
            "Chào bạn! Giấc ngủ sâu là liều thuốc kỳ diệu nhất để não bộ và các tế bào cơ thể tự sửa chữa và phục hồi sau ngày dài.\n\n"
            "🌙 **Cách thiết lập giấc ngủ ngon tự nhiên:**\n"
            "1. **Quy tắc vệ sinh giấc ngủ (Sleep Hygiene):**\n"
            "   - Đi ngủ và thức dậy vào một khung giờ cố định mỗi ngày.\n"
            "   - Tắt điện thoại, máy tính ít nhất 45 phút trước khi ngủ (ánh sáng xanh ức chế hormone gây ngủ Melatonin).\n"
            "   - Phòng ngủ nên tối hoàn toàn, yên tĩnh và nhiệt độ mát mẻ (khoảng 24 - 26°C).\n"
            "2. **Thức uống hỗ trợ giấc ngủ:** Uống 1 tách trà hoa cúc ấm, trà tâm sen hoặc 1 ly sữa hạt ấm trước khi lên giường 30 phút.\n"
            "3. **Thư giãn cơ thể:** Ngâm chân nước ấm với chút gừng tươi và muối hạt trong 15 phút, kết hợp tập thở nhịp 4-7-8 giúp xoa dịu hệ thần kinh rất nhanh."
        )
    },
    {
        'category': 'water_intake',
        'keywords': ['uống nước', 'bao nhiêu lít nước', 'uống nước đúng cách', 'uống trà', 'uống nước ấm'],
        'title': '💧 Hướng Dẫn Uống Nước Đúng Cách Cho Cơ Thể Khỏe Mạnh',
        'response': (
            "Chào bạn! Nước chiếm hơn 70% cơ thể chúng ta, nhưng uống thế nào cho đúng và hấp thu tối đa thì không phải ai cũng biết đâu nhé.\n\n"
            "💧 **Công thức lượng nước chuẩn mỗi ngày:** `Cân nặng (kg) x 40ml` (Ví dụ bạn 55kg thì cần khoảng 2.2 lít nước/ngày).\n\n"
            "⏰ **4 Khung giờ vàng để uống nước:**\n"
            "1. **Ngay sau khi thức dậy:** 1 ly nước ấm khoảng 300ml giúp thanh lọc đường tiêu hóa và đánh thức các cơ quan.\n"
            "2. **Trước bữa ăn 30 phút:** 1 ly nước nhỏ giúp chuẩn bị dịch vị tiêu hóa.\n"
            "3. **Trước khi đi tắm:** 1 ly nước ấm giúp ổn định huyết áp và điều hòa nhiệt độ cơ thể.\n"
            "4. **Trước khi ngủ 30 - 45 phút:** 1 ngụm nước ấm nhỏ giúp phòng ngừa cô đặc máu ban đêm.\n\n"
            "👉 *Mẹo nhỏ: Hãy ngồi uống từng ngụm nhỏ thay vì đứng uống ừng ực cả cốc lớn bạn nhé!*"
        )
    }
]


# ================= 3. BỘ XỬ LÝ CÁC HOÀN CẢNH ĐỜI SỐNG THỰC TẾ =================

def handle_alcohol_throat_context(msg_clean):
    """
    Kịch bản chuyên sâu: Tối uống bia/rượu/nhậu -> Sáng dậy rát họng, khô họng, khàn tiếng, nuốt đau.
    Đây chính là tình huống người dùng đặc biệt yêu cầu: nch tự nhiên như người với người!
    """
    has_alcohol = any(w in msg_clean for w in [
        'bia', 'rượu', 'ruou', 'nhậu', 'nhau', 'ún bia', 'un bia', 'uống bia', 'uong bia',
        'uống rượu', 'uong ruou', 'chè chén', 'say', 'say xỉn', 'bàn nhậu', 'chầu bia', 'quá chén'
    ])
    has_throat = any(w in msg_clean for w in [
        'rát họng', 'rat hong', 'đau họng', 'dau hong', 'rát cổ', 'rat co', 'khô họng', 'kho hong',
        'khô cổ', 'kho co', 'khàn giọng', 'khan giong', 'khàn tiếng', 'khan tieng', 'mất giọng',
        'nuốt đau', 'nuot dau', 'khé cổ', 'khe co', 'rát', 'đắng họng', 'đắng miệng', 'chua miệng'
    ])

    if has_alcohol and has_throat:
        reply = (
            "Chào bạn nhé! Nghe bạn kể là mình hiểu ngay cảm giác khó chịu này rồi. Tình trạng tối hôm trước uống bia rượu (đặc biệt là bia ướp lạnh, uống nhiều đá) rồi sáng ngủ dậy thấy cổ họng khô khốc, rát buốt, nuốt nước bọt thấy cộm đau là phản ứng cực kỳ phổ biến luôn bạn ạ!\n\n"
            "🩺 **Tại sao tối uống bia mà sáng dậy lại bị rát họng?**\n"
            "Thực ra có 4 nguyên nhân chính kết hợp lại:\n"
            "1. 💧 **Cơ thể bị mất nước nghiêm trọng qua đêm:** Cồn trong bia là chất lợi tiểu mạnh, khiến bạn đi tiểu nhiều và rút bớt nước trong các mô tế bào. Khi ngủ qua đêm suốt 6 - 8 tiếng không uống nước lọc, niêm mạc vùng hầu họng bị khô khốc, mất đi lớp màng nhầy ẩm tự nhiên vốn có để bảo vệ họng.\n"
            "2. 🧊 **Nhiệt độ bia quá lạnh:** Uống nhiều bia lạnh hoặc bia kèm đá làm co thắt đột ngột các vi mạch máu nuôi dưỡng niêm mạc họng, làm giảm tuần hoàn máu và suy giảm tạm thời hàng rào miễn dịch tại chỗ của đường hô hấp trên.\n"
            "3. 🗣️ **Nói chuyện to, cười đùa, hò hét khi nhậu:** Trong các buổi tiệc nhậu vui vẻ và ồn ào, chúng ta thường có xu hướng nói lớn tiếng, cười đùa hoặc hò hét cụng ly liên tục. Điều này khiến dây thanh quản và niêm mạc họng bị cọ xát cơ học gây phù nề, khàn giọng và đau rát.\n"
            "4. 🔥 **Trào ngược axit dạ dày ban đêm (Acid Reflux):** Cồn làm giãn cơ thắt thực quản dưới và kích thích dạ dày tiết nhiều axit. Khi bạn đi ngủ trong trạng thái bụng đầy bia và thức ăn, axit dạ dày rất dễ trào ngược lên tận vòm họng gây bỏng rát niêm mạc, sáng dậy thường kèm cảm giác đắng ngắt hoặc chua ở cuống họng.\n\n"
            "---\n\n"
            "👉 **Những việc bạn nên làm ngay sáng nay để dịu họng tức thì:**\n"
            "- 💧 **Uống ngay 1 cốc nước ấm lớn (khoảng 350 - 400ml):** Uống từng ngụm nhỏ từ từ để cấp nước bù lại cho cơ thể và làm ẩm lại niêm mạc cổ họng đang bị khô rát.\n"
            "- 🍯 **Nước ấm pha mật ong + vài giọt chanh hoặc gừng:** Mật ong có tính kháng khuẩn tự nhiên, tạo lớp màng bọc làm dịu vết xước niêm mạc họng rất êm; vài lát gừng tươi giúp làm ấm họng, kích thích lưu thông máu và hỗ trợ tiêu hóa.\n"
            "- 🧂 **Súc họng sâu bằng nước muối sinh lý ấm (0.9%):** Ngửa cổ khò sâu xuống họng 30 giây rồi nhổ ra, thực hiện 3 - 4 lần trong ngày. Nước muối giúp sát trùng, giảm sưng nề và rửa trôi axit trào ngược đọng ở cuống họng.\n"
            "- 🍲 **Bữa sáng nhẹ nhàng, mềm ấm:** Bạn nên ăn một tô cháo hành tía tô nóng, súp gà hoặc phở ấm để làm ấm họng và bồi hoàn năng lượng; tránh các món chiên xào nhiều dầu mỡ hay đồ cay nóng.\n"
            "- 🚫 **Những điều hôm nay cần tránh:** Tuyệt đối không tiếp tục uống nước đá lạnh, không hút thuốc lá, kiêng cà phê đặc và hạn chế nói lớn tiếng để họng có thời gian hồi phục.\n\n"
            "---\n\n"
            "⚠️ **Dấu hiệu bạn cần lưu ý:**\n"
            "Thông thường nếu chỉ do bia lạnh và khô rát cơ học, họng sẽ êm dịu dần sau 1 - 2 ngày khi bạn nghỉ ngơi và bù đủ nước. Tuy nhiên, nếu bạn xuất hiện thêm các dấu hiệu sau thì có thể vi khuẩn cơ hội đã xâm nhập gây viêm nhiễm:\n"
            "- Sốt cao trên 38.5°C, người ớn lạnh, đau mỏi toàn thân.\n"
            "- Nuốt đau nhói buốt lan lên mang tai, nuốt nghẹn khó thở.\n"
            "- Amidan hai bên sưng to đỏ, có chấm mủ trắng hoặc nổi hạch đau ở góc hàm.\n"
            "- Đau rát kéo dài quá 3 ngày không có dấu hiệu thuyên giảm.\n\n"
            "---\n\n"
            "💬 *Hiện tại bạn chỉ thấy khô rát nhẹ hay có bị sốt, khàn tiếng hoặc nuốt đau buốt nhiều không? Bạn cứ chia sẻ thêm với mình nhé, mình ở đây để đồng hành cùng bạn!*"
        )
        return {
            'reply': reply,
            'stage': 'lifestyle_alcohol_throat',
            'suggested_specialty': 'Tai Mũi Họng',
            'quick_replies': [
                'Chỉ rát nhẹ, không sốt',
                'Có sốt và nuốt đau nhiều',
                'Uống thuốc gì cho đỡ rát họng?',
                'Tôi muốn đặt lịch khám Tai Mũi Họng'
            ]
        }
    return None


def handle_alcohol_headache_hangover(msg_clean):
    """
    Kịch bản: Uống bia/rượu -> Say, đau đầu, buồn nôn, mệt mỏi, giải rượu, say nguội.
    """
    has_alcohol = any(w in msg_clean for w in [
        'bia', 'rượu', 'ruou', 'nhậu', 'nhau', 'uống bia', 'uong bia', 'uống rượu',
        'say', 'say rượu', 'say bia', 'say xỉn', 'giải rượu', 'giai ruou', 'say nguội'
    ])
    has_hangover = any(w in msg_clean for w in [
        'đau đầu', 'dau dau', 'nhức đầu', 'nhuc dau', 'buồn nôn', 'buon non', 'nôn nao',
        'non nao', 'chóng mặt', 'chong mat', 'oải người', 'mệt mỏi', 'met moi', 'cồn cào', 'nóng ruột'
    ])

    if has_alcohol and has_hangover:
        reply = (
            "Chào bạn! Cảm giác đầu óc bưng bưng, nôn nao và mệt mỏi rã rời sau một đêm quá chén quả thực rất khó chịu...\n\n"
            "🩺 **Vì sao bạn bị đau đầu và mệt mỏi sau khi uống rượu bia?**\n"
            "- Khi gan phân giải cồn, nó tạo ra một hợp chất trung gian gọi là **Acetaldehyde** - chất này có độc tính cao gấp nhiều lần cồn, gây giãn mạch máu não (tạo ra cơn đau đầu bưng bưng) và kích ứng trung tâm buồn nôn ở não bộ.\n"
            "- Ngoài ra, cơ thể bị mất nước và cạn kiệt các chất điện giải (Kali, Natri) kèm hạ đường huyết nhẹ sau một giấc ngủ dài.\n\n"
            "---\n\n"
            "👉 **Các bước giúp bạn hồi phục và tỉnh táo nhanh nhất:**\n"
            "1. 🥥 **Bù nước và khoáng chất:** Uống ngay 1 ly nước dừa tươi, nước chanh muối ấm hoặc 1 gói Oresol pha đúng tỉ lệ. Đây là cách giải rượu và giảm đau đầu tự nhiên hiệu quả nhất.\n"
            "2. 🫚 **Trà gừng mật ong ấm:** Vài lát gừng tươi đập dập hãm nước sôi cùng 1 thìa mật ong giúp làm ấm bụng, chống co thắt dạ dày và dứt nhanh cơn buồn nôn.\n"
            "3. 🥣 **Ăn một bát cháo hành tía tô hoặc cháo đậu xanh nóng:** Giúp cung cấp lại lượng tinh bột làm ấm dạ dày và hỗ trợ gan thải độc tố cồn ra ngoài.\n"
            "4. 🚫 **LƯU Ý CỰC KỲ QUAN TRỌNG:** Tuyệt đối **KHÔNG tự ý uống thuốc giảm đau Paracetamol (Panadol)** ngay lúc này để trị đau đầu do rượu bia! Khi gan đang phải quá tải lọc cồn, Paracetamol sẽ kết hợp gây tổn thương gan cấp tính nguy hiểm.\n\n"
            "💬 *Hiện tại bạn có bị nôn ói nhiều không hay chỉ đau đầu và mệt mỏi? Bạn hãy uống nhiều nước ấm và nghỉ ngơi thêm ở phòng thoáng khí nhé!*"
        )
        return {
            'reply': reply,
            'stage': 'general',
            'suggested_specialty': 'Nội tổng quát',
            'quick_replies': [
                'Uống nước gì giải rượu nhanh?',
                'Ăn gì cho đỡ cồn cào ruột?',
                'Tôi muốn nghỉ ngơi thêm'
            ]
        }
    return None


def handle_cold_air_conditioning(msg_clean):
    """
    Kịch bản: Nằm điều hòa / Máy lạnh / Gió lạnh -> Rát họng, ngạt mũi, cảm lạnh.
    """
    has_cold_trigger = any(w in msg_clean for w in [
        'điều hòa', 'dieu hoa', 'máy lạnh', 'may lanh', 'quạt thốc', 'nhiễm lạnh',
        'trở trời', 'mắc mưa', 'dầm mưa', 'trời lạnh'
    ])
    has_cold_symptom = any(w in msg_clean for w in [
        'rát họng', 'rat hong', 'đau họng', 'dau hong', 'nghẹt mũi', 'nghat mui',
        'ngạt mũi', 'sổ mũi', 'so mui', 'chảy nước mũi', 'hắt hơi', 'hat hoi'
    ])

    if has_cold_trigger and has_cold_symptom:
        reply = (
            "Chào bạn nhé! Ngủ trong phòng máy lạnh hoặc điều hòa để nhiệt độ quá thấp rất thường xuyên gây ra tình trạng khô rát họng và nghẹt mũi vào sáng hôm sau.\n\n"
            "🩺 **Nguyên nhân chính:**\n"
            "- Máy lạnh hút ẩm rất mạnh, làm độ ẩm không khí trong phòng tụt xuống dưới 40% (mức lý tưởng là 55 - 65%). Không khí khô và lạnh khiến lớp dịch nhầy bảo vệ niêm mạc mũi họng bị bốc hơi hết, làm họng khô rát và kích hoạt phản xạ cuốn mũi phình to gây nghẹt thở.\n\n"
            "👉 **Cách khắc phục ngay hôm nay:**\n"
            "1. **Uống ngay một cốc nước ấm:** Cấp ẩm tức thì cho niêm mạc họng.\n"
            "2. **Vệ sinh mũi họng bằng nước muối sinh lý 0.9%:** Xịt rửa mũi và súc họng sâu để làm sạch chất nhầy và giữ ấm niêm mạc.\n"
            "3. **Điều chỉnh lại điều hòa cho những đêm tới:**\n"
            "   - Cài đặt nhiệt độ từ **26 - 28°C** (tránh để dưới 24°C).\n"
            "   - Đặt thêm một chậu nước nhỏ hoặc bật máy phun sương tạo ẩm trong phòng.\n"
            "   - Tránh để luồng gió điều hòa hoặc quạt phả thẳng trực diện vào vùng mặt và cổ khi ngủ.\n\n"
            "💬 *Bạn có bị sổ mũi nhiều hay kèm theo sốt không? Bạn chia sẻ thêm nhé!*"
        )
        return {
            'reply': reply,
            'stage': 'general',
            'suggested_specialty': 'Tai Mũi Họng',
            'quick_replies': [
                'Chỉ bị nghẹt mũi nhẹ',
                'Có sốt và ho nữa',
                'Tôi muốn đặt lịch khám Tai Mũi Họng'
            ]
        }
    return None


def handle_late_night_screen_strain(msg_clean):
    """
    Kịch bản: Thức khuya / Làm việc máy tính nhiều -> Đau đầu, mỏi mắt, choáng váng.
    """
    has_strain = any(w in msg_clean for w in [
        'thức khuya', 'thuc khuya', 'ngủ muộn', 'ngu muon', 'thiếu ngủ', 'thieu ngu',
        'máy tính', 'may tinh', 'nhìn màn hình', 'căng thẳng', 'stress', 'cày đêm'
    ])
    has_symptom = any(w in msg_clean for w in [
        'đau đầu', 'dau dau', 'mỏi mắt', 'moi mat', 'nhức mắt', 'chóng mặt', 'chong mat', 'choáng váng', 'uể oải'
    ])

    if has_strain and has_symptom:
        reply = (
            "Chào bạn! Cơ thể và hệ thần kinh sau một đêm thức khuya hoặc dán mắt vào màn hình máy tính quá lâu thường bị suy giảm tưới máu não và căng cứng các cơ vùng cổ vai gáy.\n\n"
            "🩺 **Lời khuyên giúp bạn giải tỏa căng thẳng và phục hồi:**\n"
            "1. 👁️ **Thư giãn đôi mắt (Quy tắc 20-20-20):** Cứ sau 20 phút nhìn màn hình, hãy nhìn xa ra khoảng 6 mét trong 20 giây; có thể nhỏ thêm nước mắt nhân tạo để chống khô mắt.\n"
            "2. 💆 **Massage giải tỏa cơ:** Dùng các đầu ngón tay xoa bóp nhẹ nhàng hai bên thái dương, ấn nhẹ huyệt phong trì (sau gáy) và vươn vai thư giãn cột sống cổ.\n"
            "3. 💧 **Bù nước và dinh dưỡng:** Uống 1 ly nước ấm lớn, có thể uống một tách trà hoa cúc hoặc nước ép hoa quả giàu vitamin C để tăng cường tỉnh táo.\n"
            "4. 😴 **Chợp mắt ngắn buổi trưa:** Dành khoảng 15 - 20 phút ngủ trưa để não bộ được tái tạo năng lượng, tránh ngủ quá dài buổi trưa gây mệt mỏi thêm.\n\n"
            "💬 *Bạn bị đau âm ỉ toàn đầu hay đau nhói nửa đầu? Bạn chia sẻ thêm để mình hỗ trợ nhé!*"
        )
        return {
            'reply': reply,
            'stage': 'general',
            'suggested_specialty': 'Thần kinh',
            'quick_replies': [
                'Đau âm ỉ hai bên thái dương',
                'Mỏi mắt và nhức vai gáy',
                'Cách ngủ ngon tối nay'
            ]
        }
    return None


def handle_followup_turns(msg_clean, session):
    """
    Xử lý các lượt hội thoại nối tiếp tự nhiên khi người dùng phản hồi lại câu hỏi trước của bot.
    """
    # 1. Người dùng phản hồi là chỉ rát nhẹ, không sốt, đã đỡ
    mild_keywords = [
        'chỉ rát nhẹ', 'chi rat nhe', 'rát nhẹ', 'rat nhe', 'hơi rát', 'hoi rat',
        'không sốt', 'khong sot', 'đỡ hơn rồi', 'do hon roi', 'đã đỡ', 'bớt rồi',
        'không đau lắm', 'chỉ bị khô cổ', 'chỉ bị khàn tiếng nhẹ', 'bình thường thôi'
    ]
    if any(k in msg_clean for k in mild_keywords):
        reply = (
            "Nghe bạn nói chỉ bị rát nhẹ và không sốt là mình an tâm nhiều rồi nè! 👍\n\n"
            "Như vậy khả năng rất cao là niêm mạc họng của bạn chỉ bị khô rát và kích ứng cơ học do cồn với nước đá lạnh thôi, chưa có dấu hiệu nhiễm khuẩn đâu bạn ạ.\n\n"
            "👉 **Kế hoạch chăm sóc hôm nay để họng nhanh êm:**\n"
            "1. Tiếp tục nhấp từng ngụm nước ấm rải rác trong ngày (cứ 20 - 30 phút uống một ngụm nhỏ).\n"
            "2. Duy trì uống 1 - 2 tách nước ấm mật ong chanh/gừng và súc họng bằng nước muối sinh lý ấm sau mỗi bữa ăn.\n"
            "3. Nếu ở trong phòng điều hòa, bạn nhớ chỉnh nhiệt độ từ 26°C trở lên và đặt thêm một cốc nước gần chỗ ngồi để giữ độ ẩm nhé.\n"
            "4. Trưa và tối nay ưu tiên các món canh ấm, cháo hoặc súp mềm, dễ nuốt để họng không phải cọ xát nhiều.\n\n"
            "Chỉ cần chăm sóc đúng cách vậy thì tầm chiều tối nay hoặc sang ngày mai là cổ họng sẽ êm dịu và hết rát hoàn toàn thôi bạn nha! Nếu có gì băn khoăn thêm, bạn cứ thoải mái nhắn cho mình bất cứ lúc nào nhé! Chúc bạn một ngày thật khỏe khoắn! 🌿"
        )
        return {
            'reply': reply,
            'stage': 'general',
            'quick_replies': [
                'Ăn gì tốt cho họng hôm nay?',
                'Uống nước thế nào đúng cách',
                'Cảm ơn bạn nhiều nhé'
            ]
        }

    # 2. Người dùng phản hồi có sốt, nuốt đau buốt nhiều, bệnh nặng lên
    severe_keywords = [
        'có sốt', 'co sot', 'bị sốt', 'bi sot', 'sốt cao', 'sot cao', 'sốt 38', 'sốt 39',
        'nuốt đau buốt', 'nuot dau buot', 'đau buốt lên tai', 'đau nhiều', 'rất đau',
        'nuốt nghẹn', 'rát nhiều', 'có đờm xanh', 'đờm vàng', 'sốt rét'
    ]
    if any(k in msg_clean for k in severe_keywords):
        reply = (
            "Ồ, nếu đã xuất hiện sốt và nuốt đau buốt nhiều như vậy thì bạn cần hết sức lưu ý rồi nhé! ⚠️\n\n"
            "Dấu hiệu này cho thấy vùng hầu họng của bạn không chỉ đơn thuần là khô rát do bia lạnh nữa, mà khả năng vi khuẩn hoặc virus cơ hội đã xâm nhập gây **viêm họng cấp** hoặc **viêm amidan cấp** sau khi sức đề kháng bị suy giảm tạm thời.\n\n"
            "🩺 **Những việc cần làm ngay lúc này:**\n"
            "1. 🌡️ **Kiểm tra nhiệt độ cơ thể:** Nếu sốt từ 38.5°C trở lên, bạn có thể uống 1 viên Paracetamol 500mg để hạ sốt và giảm đau buốt (cách nhau 4 - 6 tiếng nếu còn sốt). Lưu ý uống cách xa bữa bia rượu tối qua ít nhất 6 tiếng để bảo vệ gan.\n"
            "2. 💧 **Bù nước liên tục:** Uống nhiều nước ấm từng ngụm nhỏ, có thể uống thêm nước oresol hoặc nước cam ấm để bổ sung vitamin C.\n"
            "3. 🏥 **Thăm khám chuyên khoa Tai Mũi Họng:** Vì tình trạng đã có sốt và nuốt đau buốt, bạn rất nên đến cơ sở y tế để bác sĩ nội soi vòm họng và kê đơn thuốc kháng viêm/kháng sinh phù hợp, tránh để viêm nhiễm lan xuống phế quản hoặc tạo ổ áp-xe quanh amidan.\n\n"
            "---\n\n"
            "👉 **Bạn có muốn mình hỗ trợ tìm bệnh viện và đặt lịch khám với Bác sĩ chuyên khoa Tai Mũi Họng gần bạn nhất không?**"
        )
        return {
            'reply': reply,
            'stage': 'ask_booking_confirmation',
            'suggested_specialty': 'Tai Mũi Họng',
            'quick_replies': [
                'Có, tôi muốn đặt lịch khám',
                'Khám ở Đà Nẵng',
                'Khám ở Hà Nội',
                'Khám ở TP. Hồ Chí Minh',
                'Chưa, tôi muốn hỏi thêm'
            ]
        }

    # 3. Người dùng hỏi về thuốc uống tại nhà
    med_keywords = [
        'uống thuốc gì', 'uong thuoc gi', 'mua thuốc gì', 'mua thuoc gi',
        'thuốc gì', 'thuoc gi', 'uống thuốc nào', 'uống kháng sinh không', 'dùng thuốc gì'
    ]
    if any(k in msg_clean for k in med_keywords):
        reply = (
            "Về việc dùng thuốc khi bị rát họng, mình xin chia sẻ với bạn những hướng dẫn y khoa an toàn và chuẩn xác này nhé:\n\n"
            "✅ **1. Các giải pháp thảo dược & không kê đơn an toàn có thể dùng ngay:**\n"
            "- 🍬 **Viên ngậm thảo dược:** Các loại viên ngậm chứa tinh dầu bạc hà, khuynh diệp, cam thảo, chanh mật ong hoặc keo ong (như Strepsils, Prospan, viên ngậm quất mật ong...) giúp làm dịu cảm giác đau rát, sát trùng nhẹ và kích thích tiết nước bọt giữ ẩm cho niêm mạc họng.\n"
            "- 🌿 **Xịt họng keo ong / thảo dược:** Xịt trực tiếp 2 - 3 nhát vào sâu vòm họng, ngày 3 - 4 lần. Keo ong là kháng sinh tự nhiên giúp kháng khuẩn và làm lành niêm mạc họng rất hiệu quả.\n"
            "- 🧂 **Dung dịch súc họng sát khuẩn:** Nước muối sinh lý ấm 0.9% hoặc nước súc họng chuyên dụng chứa Povidone-iodine (như Betadine súc họng 1%) dùng 2 - 3 lần/ngày.\n\n"
            "💊 **2. Thuốc giảm đau hạ sốt (khi cần thiết):**\n"
            "- Nếu họng đau buốt nhiều hoặc người hâm hấp sốt, bạn có thể uống **Paracetamol 500mg** (1 viên/lần, cách nhau 4 - 6 tiếng). *Lưu ý: Không uống Paracetamol ngay lúc đang say rượu bia.*\n\n"
            "❌ **3. LƯU Ý ĐẶC BIỆT QUAN TRỌNG:**\n"
            "- **Tuyệt đối KHÔNG tự ý mua thuốc kháng sinh** (như Amoxicillin, Augmentin, Cephalexin...) để tự uống. Đa số các đợt rát họng ban đầu là do kích ứng cơ học hoặc virus, kháng sinh không có tác dụng với virus và kích ứng mà còn gây hại men gan, rối loạn tiêu hóa và kháng thuốc!\n"
            "- Chỉ dùng kháng sinh khi có chỉ định trực tiếp từ bác sĩ sau khi thăm khám.\n\n"
            "Nếu sau 2 - 3 ngày tình trạng rát họng không đỡ hoặc xuất hiện sốt, bạn nên đi khám chuyên khoa Tai Mũi Họng nhé!"
        )
        return {
            'reply': reply,
            'stage': 'general',
            'suggested_specialty': 'Tai Mũi Họng',
            'quick_replies': [
                'Viên ngậm loại nào tốt?',
                'Khi nào cần đi khám?',
                'Tôi muốn đặt lịch khám'
            ]
        }

    # 4. Người dùng cảm ơn, chào hỏi thân mật
    thanks_keywords = ['cảm ơn', 'cam on', 'thank', 'thanks', 'cám ơn', 'tuyệt vời', 'ok bạn', 'cảm ơn bác sĩ']
    if any(k in msg_clean for k in thanks_keywords):
        reply = (
            "Dạ không có gì bạn nhé! Được đồng hành và hỗ trợ bạn chăm sóc sức khỏe là niềm vui lớn của mình. 🌸\n\n"
            "Bạn nhớ chú ý nghỉ ngơi, uống đủ nước ấm và giữ gìn sức khỏe hôm nay nhé. Bất cứ khi nào bạn có thắc mắc về ăn uống, dinh dưỡng hay sức khỏe, cứ nhắn cho mình nhé!\n\n"
            "Chúc bạn một ngày tràn đầy năng lượng và thật nhiều niềm vui! ✨"
        )
        return {
            'reply': reply,
            'stage': 'general',
            'quick_replies': [
                'Ăn gì tốt cho sức khỏe?',
                'Tư vấn dinh dưỡng dạ dày',
                'Đặt lịch khám bệnh'
            ]
        }

    return None


# ================= 4. BỘ ÁNH XẠ TRIỆU CHỨNG LÂM SÀNG VỚI LỜI VĂN TỰ NHIÊN =================
SYMPTOM_CLINICAL_MAP = {
    'tai mũi họng': {
        'keywords': ['đau họng', 'rát họng', 'khàn tiếng', 'mất tiếng', 'viêm xoang', 'nghẹt mũi', 'ngạt mũi', 'sổ mũi', 'ù tai', 'chảy máu cam', 'viêm amidan', 'ho khan', 'ho có đờm', 'viêm họng', 'rát cổ'],
        'specialty_name': 'Tai Mũi Họng',
        'greeting': 'Chào bạn nhé! Nghe bạn chia sẻ về các triệu chứng ở vùng tai mũi họng, mình rất hiểu cảm giác vướng víu, khó chịu mà bạn đang trải qua.',
        'clinical_cause': 'Các biểu hiện như đau họng, nghẹt mũi hoặc ho thường do kích ứng niêm mạc, viêm đường hô hấp trên hoặc viêm xoang dị ứng khi thời tiết thay đổi hay do tiếp xúc với khói bụi, đồ uống lạnh.',
        'home_care': 'Bạn nên súc miệng và họng sâu bằng nước muối sinh lý ấm (0.9%) 3-4 lần/ngày, uống nhiều nước ấm pha mật ong gừng, giữ ấm vùng cổ ngực và tránh uống nước đá lạnh.',
        'red_flags': 'Nếu bạn có dấu hiệu sốt cao khó hạ, nuốt đau buốt lan lên tai, khạc đờm đặc màu xanh vàng hoặc khó thở, bạn nên thăm khám bác sĩ sớm để tránh biến chứng viêm phế quản hoặc viêm phổi nhé.'
    },
    'tiêu hóa': {
        'keywords': ['đau bụng', 'đau dạ dày', 'đau thượng vị', 'ợ chua', 'ợ hơi', 'trào ngược', 'tiêu chảy', 'táo bón', 'nôn mửa', 'buồn nôn', 'khó tiêu', 'đầy bụng', 'viêm loét', 'đại tràng', 'trĩ', 'đi ngoài'],
        'specialty_name': 'Tiêu hóa',
        'greeting': 'Chào bạn nhé! Đau dạ dày hay các rối loạn tiêu hóa luôn khiến cơ thể mệt mỏi và ăn uống mất ngon.',
        'clinical_cause': 'Các biểu hiện như đau âm ỉ thượng vị, ợ hơi, ợ chua hay đầy chướng bụng thường liên quan đến viêm loét dạ dày - tá tràng hoặc trào ngược dạ dày thực quản (GERD), thường bùng phát do căng thẳng, ăn uống thất thường hoặc đồ cay nóng.',
        'home_care': 'Bạn nên ăn các món lỏng ấm như cháo, súp; uống nước ấm tinh bột nghệ mật ong; chia nhỏ bữa ăn và tuyệt đối không để bụng quá đói hay ăn quá no; kiêng đồ chua cay, dầu mỡ và đồ uống có cồn.',
        'red_flags': 'Nếu xuất hiện cơn đau quặn dữ dội, nôn ra máu, đi ngoài phân đen như bã cà phê hoặc nôn liên tục không dứt, bạn cần đến bệnh viện cấp cứu ngay!'
    },
    'thần kinh': {
        'keywords': ['đau đầu', 'nhức đầu', 'chóng mặt', 'hoa mắt', 'mất ngủ', 'tiền đình', 'đột quỵ', 'tê tay chân', 'tê bì', 'co giật', 'nửa đầu', 'tai biến', 'choáng váng'],
        'specialty_name': 'Thần kinh',
        'greeting': 'Chào bạn! Cơn đau đầu hay cảm giác chóng mặt hoa mắt thực sự làm ảnh hưởng rất nhiều đến công việc và sinh hoạt hàng ngày.',
        'clinical_cause': 'Đau đầu, chóng mặt thường do căng thẳng thần kinh (stress), thiếu máu lên não, đau nửa đầu Migraine hoặc rối loạn tiền đình. Thức khuya hay làm việc trước máy tính liên tục cũng là tác nhân kích hoạt phổ biến.',
        'home_care': 'Bạn nên dành thời gian nghỉ ngơi ở nơi yên tĩnh, thoáng khí, mát mẻ; xoa bóp nhẹ nhàng vùng thái dương và cổ gáy; uống đủ nước ấm và tránh tiếp xúc với ánh sáng màn hình điện tử.',
        'red_flags': 'CẢNH BÁO NGUY HIỂM: Nếu cơn đau đầu dữ dội đột ngột, kèm theo méo miệng, nói ngọng, nhìn mờ hoặc yếu liệt một bên tay chân, đây có thể là dấu hiệu đột quỵ tai biến - phải gọi cấp cứu 115 ngay lập tức!'
    },
    'tim mạch': {
        'keywords': ['đau ngực', 'tức ngực', 'khó thở', 'hồi hộp', 'tim đập nhanh', 'huyết áp cao', 'tăng huyết áp', 'hạ huyết áp', 'nhói tim', 'mạch vành', 'đánh trống ngực'],
        'specialty_name': 'Tim mạch',
        'greeting': 'Chào bạn! Các triệu chứng liên quan đến lồng ngực và nhịp tim luôn cần được quan tâm và theo dõi hết sức cẩn trọng.',
        'clinical_cause': 'Cảm giác tức ngực, hồi hộp, tim đập nhanh có thể liên quan đến rối loạn thần kinh tim do lo âu, rối loạn nhịp tim hoặc các bệnh lý tim mạch như tăng huyết áp, thiếu máu cơ tim cục bộ.',
        'home_care': 'Bạn nên ngồi nghỉ ngơi ở tư thế nửa nằm nửa ngồi, nới lỏng cổ áo, thở chậm và sâu để giữ tinh thần thật bình tĩnh, hạn chế vận động gắng sức.',
        'red_flags': 'KHẨN CẤP: Nếu xuất hiện cơn đau thắt nghẹn như đá đè sau xương ức, lan lên cằm, vai hoặc cánh tay trái kéo dài trên 10-15 phút kèm toát mồ hôi lạnh, bạn cần đến cơ sở cấp cứu tim mạch gần nhất ngay!'
    },
    'cơ xương khớp': {
        'keywords': ['đau lưng', 'thoát vị', 'đau khớp', 'khớp gối', 'thoái hóa', 'mỏi vai gáy', 'đau nhức xương', 'gút', 'acid uric', 'viêm khớp', 'đau cổ', 'cứng khớp'],
        'specialty_name': 'Cơ xương khớp',
        'greeting': 'Chào bạn nhé! Những cơn đau mỏi xương khớp hay cột sống luôn gây cảm giác bức bối, cản trở việc đi lại và vận động.',
        'clinical_cause': 'Đau mỏi vai gáy hay đau lưng thường bắt nguồn từ sai tư thế khi ngồi làm việc lâu, thoái hóa đốt sống hoặc thoát vị đĩa đệm. Viêm khớp hoặc gút cũng gây sưng đau các khớp ngón chân, cổ chân.',
        'home_care': 'Bạn có thể chườm ấm vùng đau mỏi 15-20 phút, xoa bóp nhẹ nhàng, thực hiện các bài tập kéo giãn cơ nhẹ và điều chỉnh lại tư thế ngồi thẳng lưng.',
        'red_flags': 'Nếu khớp sưng to, nóng đỏ cấp tính hoặc có dấu hiệu tê bì mất cảm giác lan xuống bàn chân, bạn nên đi khám chuyên khoa Cơ Xương Khớp sớm.'
    },
    'da liễu': {
        'keywords': ['ngứa da', 'dị ứng', 'mẩn đỏ', 'mụn trứng cá', 'chàm', 'vảy nến', 'rụng tóc', 'nổi mề đay', 'phát ban', 'nấm da', 'viêm da', 'mẩn ngứa'],
        'specialty_name': 'Da liễu',
        'greeting': 'Chào bạn nhé! Ngứa ngáy hay nổi mẩn đỏ trên da luôn mang lại cảm giác vô cùng khó chịu và bứt rứt.',
        'clinical_cause': 'Nổi mẩn ngứa thường là phản ứng của viêm da tiếp xúc, dị ứng thức ăn (hải sản, trứng, sữa) hoặc nổi mề đay do thời tiết thay đổi, côn trùng cắn.',
        'home_care': 'Bạn nên tắm bằng nước mát hoặc ấm vừa, dùng sữa tắm dịu nhẹ; tránh cào gãi làm trầy xước nhiễm trùng da; có thể chườm mát nhẹ để giảm cơn ngứa.',
        'red_flags': 'CẢNH BÁO PHẢN VỆ: Nếu nổi mề đay lan nhanh khắp người kèm theo sưng phù môi, mí mắt, khó thở, nghẹn họng hoặc tụt huyết áp, phải đến phòng cấp cứu ngay lập tức!'
    },
    'nhi khoa': {
        'keywords': ['trẻ em', 'em bé', 'trẻ sơ sinh', 'bé sốt', 'bé quấy khóc', 'biếng ăn', 'bé nôn', 'sởi', 'thủy đậu', 'chân tay miệng', 'tiêm chủng', 'con tôi'],
        'specialty_name': 'Nhi khoa',
        'greeting': 'Chào bạn! Chăm sóc bé khi con bị ốm quả thực làm cha mẹ rất xót ruột và lo lắng.',
        'clinical_cause': 'Hệ miễn dịch của trẻ nhỏ còn non nớt nên rất dễ bị sốt do virus, viêm họng hoặc rối loạn tiêu hóa khi thời tiết chuyển mùa.',
        'home_care': 'Cho bé mặc quần áo mỏng thoáng mát; chườm ấm các vùng nách, bẹn khi sốt; cho bé bú nhiều cữ hoặc uống bù nước Oresol theo đúng tỉ lệ; dùng Paracetamol hạ sốt cho trẻ đúng liều (10-15mg/kg cân nặng) khi sốt >= 38.5°C.',
        'red_flags': 'ĐƯA BÉ ĐI VIỆN NGAY NẾU: Bé sốt cao co giật, thở rút lõm lồng ngực, bỏ bú, ngủ li bì khó đánh thức, nôn ói tất cả mọi thứ hoặc có ban xuất huyết dưới da!'
    },
    'mắt': {
        'keywords': ['đau mắt', 'đỏ mắt', 'mờ mắt', 'cận thị', 'chảy nước mắt', 'cộm mắt', 'nhức mắt', 'loạn thị', 'viêm kết mạc', 'đau mắt đỏ'],
        'specialty_name': 'Mắt (Nhãn khoa)',
        'greeting': 'Chào bạn! Đôi mắt là cửa sổ tâm hồn, khi mắt bị đau cộm hay mờ đi sẽ ảnh hưởng rất lớn đến mọi sinh hoạt.',
        'clinical_cause': 'Đau mắt, đỏ mắt, cộm xốn thường do viêm kết mạc (đau mắt đỏ), dị vật bay vào mắt hoặc hội chứng thị giác màn hình do dùng thiết bị điện tử quá lâu.',
        'home_care': 'Rửa mắt bằng nước muối sinh lý NaCl 0.9% chuyên dùng cho mắt; nhỏ nước mắt nhân tạo; cho mắt nghỉ ngơi hoàn toàn và tránh dụi mắt làm xước giác mạc.',
        'red_flags': 'Nếu nhìn mờ đột ngột, thấy quầng sáng quanh đèn kèm đau nhức buốt sâu trong hốc mắt, bạn cần đến khám chuyên khoa Mắt ngay.'
    },
    'nội tổng quát': {
        'keywords': ['sốt', 'mệt mỏi', 'sụt cân', 'khám tổng quát', 'kiểm tra sức khỏe', 'khám định kỳ', 'ốm', 'sức khỏe', 'người yếu'],
        'specialty_name': 'Nội tổng quát',
        'greeting': 'Chào bạn nhé! Khi cơ thể cảm thấy mệt mỏi, uể oải hay có dấu hiệu bất thường, việc lắng nghe sức khỏe bản thân là điều vô cùng đúng đắn.',
        'clinical_cause': 'Cảm giác mệt mỏi, sụt cân hay người ốm yếu có thể xuất phát từ suy nhược cơ thể, thiếu máu, rối loạn chức năng tuyến giáp hoặc cần kiểm tra các chỉ số đường huyết, men gan.',
        'home_care': 'Bạn nên chú ý ăn uống đủ chất, bổ sung vitamin, ngủ đủ giấc và uống nhiều nước ấm để cơ thể hồi phục.',
        'red_flags': 'Nếu tình trạng mệt mỏi kéo dài không rõ nguyên nhân, bạn nên làm xét nghiệm tổng quát để bác sĩ tầm soát chính xác.'
    }
}


# ================= 4B. BỘ TỪ ĐIỂN TRIỆU CHỨNG ĐỜI THƯỜNG / DÂN GIAN CHO NGƯỜI LỚN TUỔI =================
# Người lớn tuổi và bệnh nhân bình dân không biết viết prompt, họ "đau sao nói vậy"
ELDERLY_COLLOQUIAL_CLINICAL_MAP = [
    {
        'category': 'back_spine',
        'keywords': [
            'nhức cái lưng', 'đau cái lưng', 'cúi xuống không được', 'cúi không nổi',
            'đứng lên ngồi xuống đau', 'nhức buốt từ lưng', 'đau dọc xuống chân', 'cụp lưng',
            'khom lưng', 'cúi xuống nhức', 'cúi lưng không được', 'nhức thắt lưng', 'mỏi lưng quá',
            'đau thắt lưng', 'đau ngang thắt lưng', 'đau dọc xuống mông'
        ],
        'compound_check': lambda msg: 'lưng' in msg and any(w in msg for w in ['cúi', 'nhức', 'buốt', 'khom', 'cụp', 'không nổi', 'không được', 'điếng', 'rên']),
        'specialty': 'Cơ xương khớp',
        'reply': (
            "Dạ, Bác sĩ chào bác/cô ạ! Nghe bác/cô kể bị đau nhức vùng lưng, cúi xuống không nổi là bác sĩ hiểu ngay cảm giác bức bối, đi đứng khó khăn của bác rồi ạ.\n\n"
            "🩺 **Bác sĩ giải thích nguyên nhân:**\n"
            "Ở người lớn tuổi, các đĩa đệm và cột sống thắt lưng theo năm tháng thường bị thoái hóa, giảm độ đàn hồi. Khi mình cúi gập người, xoay người đột ngột hoặc ngồi lâu, các dải cơ quanh cột sống sẽ bị co thắt dữ dội để 'bảo vệ' cột sống, gây ra cơn đau nhức buốt điếng, khiến mình không thể cúi hay đứng thẳng người được.\n\n"
            "👉 **Những việc bác/cô cần làm ngay tại nhà:**\n"
            "1. 🛏️ **Nằm nghỉ ngơi đúng tư thế:** Bác nằm nghỉ trên giường có đệm cứng hoặc chiếu phẳng, kê một chiếc gối mỏng dưới khoeo chân (đầu gối hơi co nhẹ) để giảm hoàn toàn áp lực đè lên cột sống lưng.\n"
            "2. ♨️ **Chườm ấm thắt lưng:** Dùng khăn ấm, túi chườm ấm hoặc ngải cứu sao nóng với muối hạt chườm lên vùng lưng đau khoảng 15 - 20 phút để các cơ được giãn mềm ra.\n"
            "3. 🚫 **Tuyệt đối tránh:** Không ráng cúi khom người xách đồ nặng, không xoay vặn lưng hay bẻ khớp lưng đột ngột.\n\n"
            "⚠️ **Dấu hiệu nguy hiểm cần con cháu đưa đi khám ngay:**\n"
            "Nếu cơn đau nhức buốt lan dọc xuống mông, cẳng chân, hoặc chân có cảm giác tê bì, mất cảm giác, đi tiểu tiện khó khăn, bác cần nhờ người nhà đưa đến bệnh viện kiểm tra ngay để tránh chèn ép dây thần kinh tọa nặng.\n\n"
            "💬 *Bác/cô bị đau lưng mấy ngày nay rồi ạ? Cơn đau có lan xuống chân hay chỉ đau ngang vùng thắt lưng thôi ạ?*"
        ),
        'quick_replies': [
            'Chỉ đau ngang thắt lưng',
            'Đau lan xuống mông và chân',
            'Tôi muốn đặt lịch khám Cơ Xương Khớp',
            'Chưa, tôi muốn hỏi thêm'
        ]
    },
    {
        'category': 'knee_joints',
        'keywords': [
            'đầu gối lục cục', 'khớp gối lục cục', 'đau hai cái đầu gối', 'nhức đầu gối',
            'bước cầu thang đau', 'lục cục lạo xạo', 'lạo xạo', 'cứng khớp gối',
            'đau điếng đầu gối', 'sưng đầu gối', 'khớp gối đau', 'khớp kêu lục cục', 'đầu gối'
        ],
        'compound_check': lambda msg: any(k in msg for k in ['đầu gối', 'khớp gối']) and any(w in msg for w in ['lục cục', 'lạo xạo', 'cầu thang', 'đau điếng', 'nhức', 'đau', 'sưng', 'cứng']),
        'specialty': 'Cơ xương khớp',
        'reply': (
            "Dạ, Bác sĩ chào bác/cô ạ! Khớp gối kêu lục cục, lạo xạo và đau buốt khi bước lên cầu thang hay đứng lên ngồi xuống là nỗi khổ rất lớn của các cô bác lớn tuổi mà bác sĩ gặp hàng ngày ở phòng khám.\n\n"
            "🩺 **Bác sĩ giải thích vì sao gối lại kêu và đau:**\n"
            "Lớp sụn bọc ở hai đầu xương khớp gối của mình giống như một lớp đệm cao su êm ái. Qua nhiều năm đi lại, lớp sụn này bị bào mòn mỏng đi, kèm theo lượng dịch nhờn bôi trơn khớp bị khô cạn. Khi bác co duỗi gối, hai đầu xương cọ xát trực tiếp vào nhau phát ra tiếng 'lục cục' và gây đau nhức buốt điếng.\n\n"
            "👉 **Lời khuyên bác sĩ dặn bác chăm sóc gối tại nhà:**\n"
            "1. 🪜 **Hạn chế leo cầu thang & ngồi xổm:** Tuyệt đối không ngồi xổm, không ngồi xếp bằng dưới đất hay leo trèo cầu thang nhiều, vì mỗi lần gập gối như vậy tải trọng đè lên khớp gối gấp 4 - 5 lần trọng lượng cơ thể.\n"
            "2. ♨️ **Chườm ấm và xoa bóp:** Mỗi sáng thức dậy, bác dùng hai lòng bàn tay xoa xát nhẹ nhàng quanh hai đầu gối 5 - 10 phút cho nóng ấm lên trước khi bước chân xuống giường để tránh bị cứng khớp.\n"
            "3. 🚴 **Vận động nhẹ:** Bác có thể nằm trên giường tập động tác đạp xe đạp trên không hoặc đi bộ nhẹ nhàng trên đường bằng phẳng (không đi bộ quá 30 phút một lần).\n\n"
            "⚠️ **Khi nào cần đi khám:**\n"
            "Nếu khớp gối sưng to, nóng đỏ, sờ vào thấy bùng nhùng (tràn dịch khớp) hoặc đau đến mức không thể đặt chân xuống đất bước đi, bác cần đi khám chuyên khoa Cơ Xương Khớp sớm để bác sĩ kiểm tra và hút dịch/tiêm dưỡng chất khớp nhé.\n\n"
            "💬 *Bác bị đau một bên hay cả hai bên gối ạ? Bác có thể nhờ con cháu chọn bác sĩ bên dưới để đặt lịch khám giúp bác nhé!*"
        ),
        'quick_replies': [
            'Đau cả hai đầu gối',
            'Đầu gối có sưng nhẹ',
            'Tôi muốn đặt lịch khám Cơ Xương Khớp',
            'Chưa, tôi muốn hỏi thêm'
        ]
    },
    {
        'category': 'dizziness_vertigo',
        'keywords': [
            'xây xẩm mặt mày', 'chao đảo', 'nhà cửa quay cuồng', 'chóng mặt như chong chóng',
            'bước xuống giường thấy quay cuồng', 'váng đầu', 'bủn rủn tay chân', 'hoa mắt tối sầm',
            'quay cuồng đầu óc', 'xây xẩm'
        ],
        'compound_check': lambda msg: any(w in msg for w in ['xây xẩm', 'chao đảo', 'quay cuồng', 'nhà cửa quay']),
        'specialty': 'Thần kinh',
        'reply': (
            "Dạ, Bác sĩ chào bác/cô ạ! Triệu chứng ngủ dậy bước xuống giường thấy xây xẩm mặt mày, nhà cửa chao đảo quay cuồng như chong chóng là một tình trạng làm người bệnh rất sợ hãi và dễ bị ngã.\n\n"
            "🩺 **Bác sĩ giải thích nguyên nhân:**\n"
            "Ở người lớn tuổi, phần lớn các cơn chóng mặt quay cuồng kiểu này xuất phát từ 2 nguyên nhân chính:\n"
            "1. **Rối loạn tiền đình ốc tai:** Cơ quan giữ thăng bằng ở tai trong bị thiếu máu nuôi hoặc các tinh thể thạch nhĩ bị xô lệch vị trí khi bác xoay trở đầu.\n"
            "2. **Hạ huyết áp tư thế hoặc thiếu máu não:** Khi bác đang nằm mà ngồi bật dậy hoặc đứng lên quá nhanh, máu chưa kịp bơm đủ lên não bộ, gây hoa mắt, tối sầm mặt mày.\n\n"
            "👉 **Những việc bác/cô cần làm ngay lúc này:**\n"
            "1. 🛏️ **Nằm yên ngay lập tức:** Bác nằm yên trên giường ở tư thế nghiêng sang bên đỡ chóng mặt hơn, nhắm mắt lại, phòng ốc thoáng gió và yên tĩnh, không quay đầu qua lại đột ngột.\n"
            "2. 🫚 **Uống nước ấm hoặc trà gừng ấm:** Uống một ly nước ấm pha chút gừng tươi đập dập giúp làm ấm cơ thể, kích thích máu lưu thông lên não và giảm cảm giác nôn nao.\n"
            "3. 🩸 **Đo huyết áp:** Bác nhờ con cháu lấy máy đo huyết áp tại nhà đo xem huyết áp đang cao hay thấp để xử lý kịp thời.\n\n"
            "⚠️ **DẤU HIỆU CẢNH BÁO ĐỘT QUỴ - CẦN CẤP CỨU 115 NGAY:**\n"
            "Nếu chóng mặt kèm theo: **méo miệng, nói ngọng khó phát âm, nhìn một thành hai, hoặc yếu liệt một bên tay chân**, gia đình phải đưa bác vào phòng cấp cứu bệnh viện ngay lập tức trong khung giờ vàng!\n\n"
            "💬 *Hiện tại bác đã nằm nghỉ chưa ạ? Bác có bị buồn nôn hay nôn ói gì không ạ?*"
        ),
        'quick_replies': [
            'Hiện tại đang nằm nghỉ',
            'Có buồn nôn và nôn ói',
            'Tôi muốn đặt lịch khám Thần kinh',
            'Chưa, tôi muốn hỏi thêm'
        ]
    },
    {
        'category': 'stomach_indigestion',
        'keywords': [
            'ấm ách cái bụng', 'ấm ách', 'ăn vô muốn ói', 'ăn vô là muốn ói', 'mắc ói',
            'lợm giọng', 'ợ chua lợm', 'bụng cứ râm ran', 'bụng chướng phình', 'ăn không tiêu',
            'ăn vô tức bụng', 'cồn cào ruột gan', 'đau quặn bụng', 'lợm cổ'
        ],
        'compound_check': lambda msg: any(w in msg for w in ['ấm ách', 'muốn ói', 'mắc ói', 'lợm giọng', 'râm ran']) and any(k in msg for k in ['bụng', 'dạ dày', 'ăn', 'ruột']),
        'specialty': 'Tiêu hóa',
        'reply': (
            "Dạ, Bác sĩ chào bác/cô ạ! Cảm giác bụng cứ ấm ách, râm ran khó chịu, ăn vào là muốn ói và ợ chua lợm giọng làm cho người bệnh ăn không ngon, ngủ không yên, sụt cân và rất mệt mỏi.\n\n"
            "🩺 **Bác sĩ giải thích vì sao lại bị như vậy:**\n"
            "Tình trạng này cho thấy niêm mạc dạ dày đang bị viêm tấy, co bóp kém và tăng tiết nhiều axit dịch vị. Axit dư thừa cùng thức ăn chưa kịp tiêu hóa bị ứ đọng lại, sinh hơi làm chướng bụng rồi trào ngược lên thực quản, gây cảm giác lợm giọng buồn nôn và đắng chát ở cuống họng.\n\n"
            "👉 **Những việc bác nên làm để bụng êm lại:**\n"
            "1. 🥣 **Ăn cháo loãng hoặc súp ấm:** Tạm thời hôm nay bác nên ăn các món cháo hạt sen, súp gà hoặc bột yến mạch nấu mềm, chia thành 4 - 5 bữa nhỏ trong ngày để dạ dày không phải co bóp nhọc nhằn.\n"
            "2. 🍯 **Tinh bột nghệ mật ong ấm:** Buổi sáng trước khi ăn 30 phút, bác uống 1 ly nước ấm pha 1 thìa tinh bột nghệ và 1 thìa mật ong. Tinh bột nghệ giúp làm lành vết trợt niêm mạc, mật ong giúp giảm viêm và êm bụng rất nhanh.\n"
            "3. 🚫 **Những thứ cần kiêng:** Tuyệt đối không ăn đồ chua (chanh, cam chua, dưa cà muối), đồ cay nóng, đồ chiên ngập dầu và không nằm ngay sau khi vừa ăn xong.\n\n"
            "⚠️ **Dấu hiệu nguy hiểm cần đi viện ngay:**\n"
            "Nếu bác nôn ra chất màu đen như bã cà phê, đi ngoài phân đen có mùi tanh, hoặc đau quặn dữ dội bụng cứng như gỗ, gia đình cần đưa bác đi bệnh viện cấp cứu ngay lập tức!\n\n"
            "💬 *Bác bị ấm ách bụng mấy ngày rồi ạ? Cơn đau có xuất hiện lúc đói hay lúc vừa ăn no xong ạ?*"
        ),
        'quick_replies': [
            'Đau lúc đói cồn cào',
            'Ăn no xong tức bụng khó thở',
            'Tôi muốn đặt lịch khám Tiêu hóa',
            'Chưa, tôi muốn hỏi thêm'
        ]
    },
    {
        'category': 'chest_heart',
        'keywords': [
            'nặng ngực như đá đè', 'thở không ra hơi', 'hụt hơi', 'tức ngực thở dốc',
            'nặng trịch ở ngực', 'nhói nhói ở tim', 'tim đập thình thịch', 'ngộp thở', 'thở hụt hơi'
        ],
        'compound_check': lambda msg: any(w in msg for w in ['đá đè', 'không ra hơi', 'hụt hơi', 'thở dốc', 'ngộp thở']) and any(k in msg for k in ['ngực', 'tim', 'thở']),
        'specialty': 'Tim mạch',
        'reply': (
            "Dạ, Bác sĩ chào bác ạ! Triệu chứng nặng ngực như có đá đè và thở không ra hơi là một dấu hiệu tim mạch - hô hấp hết sức quan trọng mà chúng ta không được phép chủ quan bác nhé!\n\n"
            "🩺 **Bác sĩ dặn dò y khoa:**\n"
            "Cảm giác tức nghẹn lồng ngực có thể xuất phát từ việc các nhánh mạch máu nuôi tim (mạch vành) bị co thắt hoặc xơ vữa làm giảm lượng máu nuôi cơ tim, hoặc do chức năng tim và phổi đang bị quá tải.\n\n"
            "👉 **Việc bác cần làm ngay lúc này:**\n"
            "1. 🪑 **Ngồi nghỉ ngơi ngay lập tức:** Bác dừng mọi hoạt động, ngồi tựa lưng vào ghế hoặc nằm nửa nằm nửa ngồi ở nơi thoáng gió, nới lỏng cúc áo cổ và dây thắt lưng.\n"
            "2. 🫁 **Hít thở chậm và sâu:** Hít vào từ từ bằng mũi, thở nhẹ nhàng bằng miệng để ổn định nhịp thở và nhịp tim.\n"
            "3. 👥 **Báo ngay cho người nhà:** Bác gọi ngay người thân trong nhà lại ngồi cạnh để theo dõi sát tình trạng.\n\n"
            "⚠️ **CẢNH BÁO CẤP CỨU TIM MẠCH KHẨN CẤP:**\n"
            "Nếu cơn đau tức ngực kéo dài trên **10 - 15 phút**, đau lan lên hàm, cổ, vai hoặc xuống cánh tay trái, kèm theo **vã mồ hôi lạnh, hoa mắt, choáng váng**, gia đình phải **gọi cấp cứu 115 hoặc đưa bác đến bệnh viện có khoa Tim mạch gần nhất ngay lập tức**!\n\n"
            "💬 *Hiện tại cơn tức ngực của bác đã đỡ chưa ạ? Bác có tiền sử tăng huyết áp hay bệnh tim từ trước không ạ?*"
        ),
        'quick_replies': [
            'Có tiền sử tăng huyết áp',
            'Đang ngồi nghỉ ngơi',
            'Tôi muốn đặt lịch khám Tim mạch',
            'Chưa, tôi muốn hỏi thêm'
        ]
    },
    {
        'category': 'throat_globus',
        'keywords': [
            'vướng cổ họng', 'như có hột cơm', 'hột cơm mắc', 'khạc hoài không ra',
            'nuốt vướng', 'nghẹn nghẹn ở cổ', 'khô khé cổ', 'vướng họng', 'vướng ở cổ', 'nuốt nghẹn'
        ],
        'compound_check': lambda msg: any(w in msg for w in ['hột cơm', 'khạc hoài', 'nuốt vướng', 'nghèn nghẹn', 'vướng víu']) and any(k in msg for k in ['họng', 'cổ']),
        'specialty': 'Tai Mũi Họng',
        'reply': (
            "Dạ, Bác sĩ chào bác/cô ạ! Cảm giác cổ họng cứ vướng víu như có hột cơm hay sợi tóc mắc ở trỏng, khạc hoài không ra nuốt cũng không trôi là triệu chứng mà các cô bác lớn tuổi đến phòng khám của bác sĩ than phiền rất nhiều.\n\n"
            "🩺 **Bác sĩ giải thích nguyên nhân:**\n"
            "Y học gọi đây là chứng **'Loạn cảm họng'**. Hơn 80% trường hợp không phải là có dị vật thật mắc trong họng, mà là do **axit dịch vị dạ dày ban đêm trào ngược lên vòm họng** làm niêm mạc vùng đáy họng và sụn phễu bị sưng phù nề nhẹ. Khi nuốt, vùng niêm mạc phù này cọ xát tạo ra cảm giác cộm nghẹn y như có hột cơm mắc ở đó.\n\n"
            "👉 **Cách điều trị và chăm sóc tại nhà:**\n"
            "1. 🧂 **Súc họng nước muối sinh lý ấm:** Ngửa cổ khò sâu bằng nước muối ấm 0.9% ngày 3 lần để làm sạch axit trào ngược bám ở họng.\n"
            "2. 🛌 **Kê cao đầu giường:** Khi ngủ, bác kê cao đầu và vai khoảng 15cm (dùng gối chống trào ngược) để trọng lực giữ axit không trào lên họng lúc ban đêm.\n"
            "3. ⏰ **Ăn tối sớm:** Bác nhớ ăn tối trước giờ đi ngủ ít nhất 3 tiếng và không ăn vặt hay uống sữa no sát giờ ngủ nhé.\n\n"
            "💬 *Bác bị vướng họng lâu chưa ạ? Sáng dậy bác có hay bị ợ hơi, đắng miệng hay chua cổ không ạ?*"
        ),
        'quick_replies': [
            'Bị vướng họng nhiều ngày nay',
            'Sáng dậy hay đắng miệng',
            'Tôi muốn đặt lịch khám Tai Mũi Họng',
            'Chưa, tôi muốn hỏi thêm'
        ]
    },
    {
        'category': 'night_urination',
        'keywords': [
            'tiểu đêm nhiều', 'đêm đi tiểu miết', 'tiểu 4 5 lần', 'tiểu 3 4 lần',
            'tiểu rắt', 'tiểu buốt', 'đái dắt', 'tiểu không hết', 'rặn tiểu khó', 'đêm thức dậy đi tiểu'
        ],
        'compound_check': lambda msg: any(w in msg for w in ['tiểu đêm', 'đêm đi tiểu', 'tiểu miết', 'tiểu rắt', 'tiểu buốt', 'đái dắt']),
        'specialty': 'Nội tổng quát',
        'reply': (
            "Dạ, Bác sĩ chào bác ạ! Ban đêm cứ phải thức dậy đi tiểu 3 - 4 lần khiến giấc ngủ bị gián đoạn, ban ngày người uể oải mệt mỏi là nỗi khổ của rất nhiều cô bác lớn tuổi.\n\n"
            "🩺 **Bác sĩ giải thích nguyên nhân:**\n"
            "- Ở các bác nam giới lớn tuổi: Nguyên nhân hàng đầu là do **phì đại tuyến tiền liệt lành tính** (tuyến tiền liệt to ra chèn ép vào cổ bàng quang, khiến nước tiểu không thoát hết được, gây tiểu nhiều lần, dòng tiểu yếu, tiểu rắt).\n"
            "- Ở các bác nữ: Thường do bàng quang tăng hoạt, sa sàn chậu hoặc viêm đường tiết niệu nhẹ.\n"
            "- Ngoài ra, bệnh tiểu đường (đường huyết cao) cũng kích thích bàng quang đi tiểu liên tục.\n\n"
            "👉 **Những lời khuyên giúp bác hạn chế tiểu đêm:**\n"
            "1. 💧 **Giảm uống nước sau 7 giờ tối:** Ban ngày bác uống đủ nước, nhưng sau 7h tối hạn chế uống canh nhiều nước, không uống trà đặc hay cà phê buổi tối.\n"
            "2. 🚹 **Đi tiểu 2 lần trước khi ngủ:** Trước khi lên giường bác đi tiểu một lần, nằm đọc sách hay nghe radio 15 phút rồi trước khi ngủ hẳn đi tiểu thêm một lần nữa để xả cạn bàng quang.\n"
            "3. 🏥 **Nên đi siêu âm kiểm tra:** Bác nên nhờ con cháu đưa đi khám chuyên khoa để siêu âm tuyến tiền liệt và xét nghiệm nước tiểu, bác sĩ sẽ kê thuốc giúp co nhỏ tiền liệt tuyến hoặc ổn định bàng quang, bác sẽ ngủ ngon giấc suốt đêm.\n\n"
            "💬 *Bác đi tiểu dòng nước tiểu có mạnh không ạ? Có bị buốt rát hay són tiểu không ạ?*"
        ),
        'quick_replies': [
            'Tiểu đêm 3 - 4 lần',
            'Có cảm giác tiểu không hết bãi',
            'Tôi muốn đặt lịch khám',
            'Chưa, tôi muốn hỏi thêm'
        ]
    },
    {
        'category': 'leg_cramps',
        'keywords': [
            'chuột rút', 'vọp bẻ', 'bắp chân rút cứng', 'rút bắp chân',
            'chuột rút ban đêm', 'co rút bắp chân', 'đau thắt bắp chuối'
        ],
        'compound_check': lambda msg: any(w in msg for w in ['chuột rút', 'vọp bẻ', 'rút cứng']) and any(k in msg for k in ['chân', 'bắp chân', 'đêm']),
        'specialty': 'Cơ xương khớp',
        'reply': (
            "Dạ, Bác sĩ chào bác ạ! Đang ngủ ngon giấc ban đêm mà bắp chân bị giật rút cứng đờ, đau điếng không duỗi chân ra được (dân gian mình hay gọi là vọp bẻ hay chuột rút) là tình trạng rất hay gặp ở người lớn tuổi.\n\n"
            "🩺 **Bác sĩ giải thích nguyên nhân:**\n"
            "Hiện tượng này xảy ra do cơ bắp chân bị thiếu hụt khoáng chất (Canxi, Magie, Kali), hoặc do suy giãn tĩnh mạch chi dưới làm máu ứ trệ, hoặc đơn giản là do ban đêm bị lạnh chân làm co mạch máu đột ngột.\n\n"
            "👉 **Mẹo xử lý ngay lập tức khi bị chuột rút:**\n"
            "1. 🦶 **Kéo ngược mũi chân về phía đầu gối:** Khi bắp chân vừa bị rút cứng, bác ráng giữ thẳng chân và dùng tay kéo mạnh mũi bàn chân ngửa ngược về phía đầu gối. Làm như vậy cơ bắp chân sẽ bị kéo giãn ra và cơn chuột rút sẽ nhả ngay trong vòng 15 - 30 giây!\n"
            "2. ♨️ **Xoa bóp và giữ ấm:** Sau khi nhả cơ, bác xoa bóp nhẹ nhàng từ cổ chân lên bắp chuối bằng dầu gừng ấm.\n"
            "3. 🧦 **Cách phòng ngừa ban đêm:** Bác nên ngâm chân bằng nước ấm với chút muối gừng trước khi ngủ 15 phút, khi ngủ nên mang tất (vớ) mỏng để giữ ấm hai bàn chân và kê chân cao hơn mình khoảng 10cm.\n\n"
            "💬 *Bác có hay bị chuột rút thường xuyên không ạ? Bác có cảm giác tê bì hay nổi gân xanh ngoằn ngoèo ở bắp chân không ạ?*"
        ),
        'quick_replies': [
            'Hay bị chuột rút lúc gần sáng',
            'Có cảm giác tê bì chân',
            'Tôi muốn đặt lịch khám Cơ Xương Khớp',
            'Chưa, tôi muốn hỏi thêm'
        ]
    },
    {
        'category': 'eye_vision',
        'keywords': [
            'mắt kèm nhèm', 'chảy nước mắt sống', 'mắt mờ', 'nhìn mờ mờ',
            'mắt khô cộm', 'mắt đỏ hoe', 'cộm xốn mắt', 'mắt mờ đi'
        ],
        'compound_check': lambda msg: any(w in msg for w in ['kèm nhèm', 'nước mắt sống', 'cộm xốn', 'mờ mờ']) and 'mắt' in msg,
        'specialty': 'Mắt (Nhãn khoa)',
        'reply': (
            "Dạ, Bác sĩ chào bác/cô ạ! Mắt bị kèm nhèm, cộm xốn và hay bị chảy nước mắt sống (nước mắt cứ tự trào ra khi ra gió hoặc nhìn lâu) là bệnh lý tuổi già rất phổ biến.\n\n"
            "🩺 **Bác sĩ giải thích nguyên nhân:**\n"
            "- Khi có tuổi, tuyến lệ giảm tiết nước mắt tự nhiên gây ra bệnh **khô mắt tuổi già**. Mắt bị khô sẽ phản xạ bằng cách kích thích chảy tràn nước mắt sống nhưng chất lượng nước mắt loãng, không bôi trơn được giác mạc.\n"
            "- Ngoài ra, nhìn mờ mờ như có màng sương che phủ thường là dấu hiệu ban đầu của **đục thủy tinh thể (cườm khô)**.\n\n"
            "👉 **Cách chăm sóc mắt tại nhà:**\n"
            "1. 💧 **Nhỏ nước mắt nhân tạo:** Bác mua loại nước mắt nhân tạo không chất bảo quản (như Sanlein hoặc Systane Ultra) nhỏ mỗi ngày 3 - 4 lần để giữ ẩm và làm dịu mắt.\n"
            "2. 🕶️ **Đeo kính râm khi ra đường:** Giúp chắn gió, bụi bẩn và tia cực tím kích ứng mắt.\n"
            "3. 🚫 **Không dụi mắt:** Tuyệt đối không dùng tay hay vạt áo dụi mắt vì rất dễ làm trầy xước giác mạc và gây nhiễm trùng.\n\n"
            "💬 *Bác nhìn mờ cả hai mắt hay một mắt ạ? Mắt có bị đau nhức sâu trong hốc mắt hay nhìn thấy quầng sáng màu sắc không ạ?*"
        ),
        'quick_replies': [
            'Hay chảy nước mắt sống khi ra gió',
            'Nhìn mờ như có màng sương',
            'Tôi muốn đặt lịch khám Mắt',
            'Chưa, tôi muốn hỏi thêm'
        ]
    },
    {
        'category': 'children_care',
        'keywords': [
            'cháu tôi nó sốt', 'cháu tôi ho', 'ho sù sụ', 'em bé quấy khóc',
            'con bé nôn ói', 'sổ mũi lòng thòng', 'cháu tôi bị sốt', 'cháu tôi bị ho'
        ],
        'compound_check': lambda msg: any(w in msg for w in ['cháu tôi', 'con bé', 'thằng bé', 'em bé']) and any(k in msg for k in ['sốt', 'ho', 'quấy', 'khóc', 'ói', 'sổ mũi']),
        'specialty': 'Nhi khoa',
        'reply': (
            "Dạ, Bác sĩ chào ông/bà ạ! Chăm cháu nhỏ khi con bị ốm, ho sù sụ cả đêm quấy khóc quả thực làm ông bà, cha mẹ xót ruột và lo lắng vô cùng.\n\n"
            "🩺 **Lời khuyên bác sĩ nhi khoa hướng dẫn ông bà chăm cháu:**\n"
            "1. 🌡️ **Cặp nhiệt độ cho cháu:** Bác dùng nhiệt kế kẹp nách hoặc đo trán cho cháu. Nếu cháu sốt dưới 38.5°C thì chưa cần cho uống thuốc hạ sốt, chỉ cần cởi bớt quần áo ấm, cho bé mặc đồ mỏng thoáng.\n"
            "2. 🧽 **Lau ấm cho bé:** Dùng 5 chiếc khăn mềm thấm nước ấm (ấm như nước tắm bé, khoảng 37 độ) đắp vào trán, 2 nách và 2 bên bẹn của cháu để hạ nhiệt an toàn. *Tuyệt đối không dùng nước đá lạnh hay chanh chà vào người bé nhé.*\n"
            "3. 💧 **Uống thuốc hạ sốt khi sốt cao >= 38.5°C:** Cho bé uống thuốc Paracetamol (dạng gói Hapacol hoặc siro) theo đúng cân nặng của bé: **10 - 15mg cho mỗi kg cân nặng** (ví dụ bé 10kg thì uống gói 150mg), cách nhau ít nhất 4 - 6 tiếng nếu còn sốt.\n"
            "4. 👃 **Nhỏ mũi nước muối sinh lý:** Nhỏ vài giọt nước muối ấm vào mũi để dịch mũi loãng ra, giúp bé dễ thở và đỡ ho sù sụ khi ngủ.\n\n"
            "⚠️ **DẤU HIỆU CẦN ĐƯA CHÁU ĐI VIỆN CẤP CỨU NGAY:**\n"
            "- Bé sốt cao co giật, mắt nhìn ngược.\n"
            "- Bé thở nhanh, rút lõm lồng ngực (khi hít vào ngực và sườn lõm sâu vào).\n"
            "- Bé ngủ li bì khó đánh thức, bỏ bú, hoặc nôn ói tất cả mọi thứ vừa ăn.\n\n"
            "💬 *Cháu nhà mình được mấy tuổi và nặng bao nhiêu kg rồi ạ? Bé sốt bao nhiêu độ rồi bác ơi?*"
        ),
        'quick_replies': [
            'Bé sốt 38.5 độ',
            'Bé ho nhiều về đêm',
            'Tôi muốn đặt lịch khám Nhi khoa',
            'Chưa, tôi muốn hỏi thêm'
        ]
    }
]


def handle_colloquial_patient_complaints(msg_clean, user_message):
    """
    Xử lý các câu nói bình dân, từ ngữ địa phương, nôm na 'đau sao nói vậy' của người lớn tuổi
    """
    for item in ELDERLY_COLLOQUIAL_CLINICAL_MAP:
        for kw in item['keywords']:
            if kw in msg_clean:
                return {
                    'reply': item['reply'] + f"\n\n{DISCLAIMER_TEXT}",
                    'stage': 'ask_booking_confirmation',
                    'suggested_specialty': item['specialty'],
                    'quick_replies': item['quick_replies']
                }
        if 'compound_check' in item and item['compound_check'](msg_clean):
            return {
                'reply': item['reply'] + f"\n\n{DISCLAIMER_TEXT}",
                'stage': 'ask_booking_confirmation',
                'suggested_specialty': item['specialty'],
                'quick_replies': item['quick_replies']
            }
    return None


def get_doctor_active_slots(doctor, max_slots=8):
    """
    Lấy danh sách các khung giờ khám còn trống của bác sĩ.
    Nếu DB chưa có sẵn, tự động sinh các khung giờ chuẩn cho các ngày tới.
    """
    today = timezone.now().date()
    slots_qs = LichLamViec.objects.filter(bac_si=doctor, ngay__gte=today, trang_thai=True).order_by('ngay', 'gio_bat_dau')[:max_slots]
    slots_list = []
    for s in slots_qs:
        slots_list.append({
            'date': s.ngay.strftime('%Y-%m-%d'),
            'date_display': s.ngay.strftime('%d/%m'),
            'start_time': s.gio_bat_dau.strftime('%H:%M'),
            'time_slot': f"{s.gio_bat_dau.strftime('%H:%M')} - {s.gio_ket_thuc.strftime('%H:%M')}"
        })

    if not slots_list:
        next_date = today + timedelta(days=1)
        if next_date.weekday() == 6:
            next_date = next_date + timedelta(days=1)
        for t in ['08:00', '09:00', '10:00', '14:00', '15:00', '16:00']:
            slots_list.append({
                'date': next_date.strftime('%Y-%m-%d'),
                'date_display': next_date.strftime('%d/%m'),
                'start_time': t,
                'time_slot': f"{t} - {int(t[:2])+1:02d}:00"
            })
    return slots_list


# ================= 5. HÀM XỬ LÝ CHÍNH (PROCESS_MEDICAL_CHAT) =================

def process_medical_chat(user_message, session=None):
    """
    Hàm xử lý tin nhắn trung tâm:
    - Trả lời tự nhiên, ân cần, giàu cảm xúc thấu cảm như người với người.
    - Xử lý mượt mà ngữ cảnh thực tế (Uống bia tối qua sáng nay rát họng, thức khuya đau đầu, nằm điều hòa cảm...).
    - Hỏi han ân cần, không chèn ép đặt lịch thô bạo.
    - Kết nối Google Gemini API / OpenAI API khi có key, hoặc dùng bộ Clinical AI Engine thông minh offline.
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

    all_provinces = list(TinhThanh.objects.all())

    # Lấy ngữ cảnh hội thoại trước đó từ session
    prev_specialty = None
    last_stage = None
    conversation_history = []
    if session:
        recent_messages = list(session.messages.all().order_by('-created_at')[:6])
        recent_messages.reverse()
        for m in recent_messages:
            conversation_history.append({
                'role': 'assistant' if m.sender == 'ai' else 'user',
                'content': m.message
            })
        last_ai_msg = session.messages.filter(sender='ai').order_by('-created_at').first()
        if last_ai_msg and last_ai_msg.data_json:
            prev_specialty = last_ai_msg.data_json.get('suggested_specialty')
            last_stage = last_ai_msg.data_json.get('stage')

    # ================= BƯỚC 1: KIỂM TRA ĐỒNG Ý / TỪ CHỐI ĐẶT LỊCH CHÍNH XÁC =================
    booking_affirmative_exact = [
        'có', 'co', 'ok', 'yes', 'được', 'duoc', 'đặt', 'dat',
        'đặt lịch', 'dat lich', 'đặt khám', 'dat kham', 'đồng ý', 'dong y',
        'có nhé', 'co nhe', 'có nha', 'co nha', 'có ạ', 'co a', 'có chứ', 'co chu',
        'có bạn ơi', 'có giúp tôi', 'hỗ trợ tôi đặt', 'đặt luôn', 'dat luon',
        'có đặt', 'co dat', 'có tôi muốn đặt', 'muốn đặt', 'muon dat'
    ]
    booking_affirmative_phrases = [
        'muốn đặt lịch', 'muon dat lich', 'có đặt lịch', 'co dat lich',
        'có, tôi muốn đặt lịch khám', 'tôi muốn đặt lịch', 'muốn khám', 'muon kham',
        'hỗ trợ đặt lịch', 'xem bác sĩ', 'xem bac si', 'chọn bác sĩ', 'chon bac si',
        'đặt hẹn', 'dat hen', 'đặt lịch khám', 'dat lich kham', 'muốn đi khám', 'muon di kham',
        'giúp tôi đặt lịch', 'đặt lịch cho tôi'
    ]

    is_affirming_booking = False
    if msg_clean in booking_affirmative_exact:
        is_affirming_booking = True
    elif any(phrase in msg_clean for phrase in booking_affirmative_phrases):
        is_affirming_booking = True
    elif last_stage == 'ask_booking_confirmation':
        # Phải bắt đầu bằng từ khẳng định và không phải là câu mô tả triệu chứng 'có bị...', 'có sốt...'
        if re.match(r'^(có|co|ok|yes|được|duoc)\b', msg_clean) and not any(w in msg_clean for w in ['có bị', 'có rát', 'có đau', 'có sốt', 'có mỏi', 'có đờm', 'có nôn']):
            is_affirming_booking = True
        elif any(w in msg_clean for w in ['đặt lịch', 'đặt khám', 'muốn khám', 'chọn bác sĩ']):
            is_affirming_booking = True

    # Người dùng từ chối đặt lịch
    booking_declining_exact = ['chưa', 'chua', 'không', 'khong', 'thôi', 'thoi', 'no', 'chưa cần', 'không cần']
    booking_declining_phrases = [
        'chưa cần', 'chua can', 'chưa muốn', 'chua muon', 'không cần', 'khong can',
        'chưa, tôi muốn hỏi thêm', 'tôi muốn hỏi thêm', 'chưa muốn đặt', 'để sau', 'de sau', 'hỏi thêm đã'
    ]
    is_declining_booking = (
        msg_clean in booking_declining_exact or
        any(phrase in msg_clean for phrase in booking_declining_phrases)
    )

    if is_declining_booking and last_stage in ['ask_booking_confirmation', 'lifestyle_alcohol_throat']:
        response_data['stage'] = 'general'
        response_data['reply'] = (
            "Dạ vâng, hoàn toàn không sao bạn nhé! Bạn hãy dành thời gian nghỉ ngơi, theo dõi thêm các phản ứng của cơ thể và áp dụng các hướng dẫn làm dịu họng tại nhà nhé.\n\n"
            "Nếu bạn có bất kỳ câu hỏi nào về ăn uống, cách chăm sóc hay cần tư vấn thêm triệu chứng gì, bạn cứ nhắn cho mình bất kỳ lúc nào nhé! Chúc bạn mau khỏe và có một ngày thật tốt lành! 🌸"
        )
        response_data['quick_replies'] = [
            'Ăn gì tốt cho sức khỏe?',
            'Uống nước thế nào đúng cách',
            'Khi nào cần đi khám bác sĩ?'
        ]
        return response_data

    # Người dùng đồng ý đặt lịch khám
    if is_affirming_booking and (prev_specialty or last_stage == 'ask_booking_confirmation' or 'đặt lịch' in msg_clean or 'khám' in msg_clean):
        target_specialty = prev_specialty or 'Tai Mũi Họng'
        specialty_doctors = BacSi.objects.filter(
            chuyen_khoa__ten_chuyen_khoa=target_specialty,
            trang_thai=True
        ).select_related('benh_vien', 'chuyen_khoa', 'user')[:4]

        doc_list = []
        for d in specialty_doctors:
            slots_list = get_doctor_active_slots(d, max_slots=8)
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

        response_data['stage'] = 'booking_confirmed'
        response_data['suggested_specialty'] = target_specialty
        response_data['suggested_doctors'] = doc_list
        response_data['suggested_provinces'] = [p.ten_tinh for p in all_provinces]
        response_data['quick_replies'] = [p.ten_tinh for p in all_provinces]
        response_data['reply'] = (
            f"Dạ vâng! Mình rất sẵn lòng hỗ trợ bạn kết nối và đặt lịch khám với Bác sĩ chuyên khoa **{target_specialty}**. 🩺\n\n"
            f"👉 Bạn có thể bấm chọn **Tỉnh/Thành phố** bên dưới để tìm bệnh viện gần bạn nhất, "
            f"hoặc bấm nút **'Chọn bác sĩ này'** ở danh sách bên dưới để xem khung giờ trống và đặt lịch trực tiếp nhé:"
        )
        return response_data

    # ================= BƯỚC 2: NGƯỜI DÙNG CHỦ ĐỘNG CHỌN TỈNH / BỆNH VIỆN =================
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
            f"Hệ thống tìm thấy **{len(hospital_list)} bệnh viện** tiếp nhận đặt lịch trực tuyến. "
            f"Bạn muốn đặt lịch khám tại bệnh viện nào dưới đây?"
        )
        response_data['quick_replies'] = [h['ten'] for h in hospital_list]
        return response_data

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
            slots_list = get_doctor_active_slots(d, max_slots=8)
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
            f"Dưới đây là danh sách **bác sĩ chuyên khoa** đang trực tiếp nhận lịch. "
            f"Bạn vui lòng chọn một bác sĩ bên dưới để xem khung giờ trống và tiến hành đặt lịch khám:"
        )
        return response_data

    # ================= BƯỚC 3: XỬ LÝ LƯỢT HỘI THOẠI NỐI TIẾP (FOLLOW-UP TURNS) =================
    followup_res = handle_followup_turns(msg_clean, session)
    if followup_res:
        response_data.update(followup_res)
        return response_data

    # ================= BƯỚC 4: XỬ LÝ HOÀN CẢNH ĐỜI SỐNG THỰC TẾ (LIFESTYLE TRIGGERS) =================
    # 4.1 Bia rượu / Nhậu + Rát họng / Khô họng (Kịch bản người dùng yêu cầu!)
    throat_alcohol_res = handle_alcohol_throat_context(msg_clean)
    if throat_alcohol_res:
        llm_reply = call_external_llm(user_message, conversation_history)
        if llm_reply:
            throat_alcohol_res['reply'] = llm_reply + f"\n\n{DISCLAIMER_TEXT}"
        response_data.update(throat_alcohol_res)
        return response_data

    # 4.2 Bia rượu + Say / Đau đầu / Buồn nôn / Nôn nao / Giải rượu
    headache_alcohol_res = handle_alcohol_headache_hangover(msg_clean)
    if headache_alcohol_res:
        llm_reply = call_external_llm(user_message, conversation_history)
        if llm_reply:
            headache_alcohol_res['reply'] = llm_reply + f"\n\n{DISCLAIMER_TEXT}"
        response_data.update(headache_alcohol_res)
        return response_data

    # 4.3 Máy lạnh / Điều hòa / Nhiễm lạnh + Rát họng / Sổ mũi
    cold_ac_res = handle_cold_air_conditioning(msg_clean)
    if cold_ac_res:
        llm_reply = call_external_llm(user_message, conversation_history)
        if llm_reply:
            cold_ac_res['reply'] = llm_reply + f"\n\n{DISCLAIMER_TEXT}"
        response_data.update(cold_ac_res)
        return response_data

    # 4.4 Thức khuya / Làm việc máy tính + Đau đầu / Mỏi mắt
    screen_strain_res = handle_late_night_screen_strain(msg_clean)
    if screen_strain_res:
        llm_reply = call_external_llm(user_message, conversation_history)
        if llm_reply:
            screen_strain_res['reply'] = llm_reply + f"\n\n{DISCLAIMER_TEXT}"
        response_data.update(screen_strain_res)
        return response_data

    # 4.5 Xử lý tiếng nói mộc mạc đời thường của người bệnh & người lớn tuổi (Không biết gõ prompt, đau sao nói vậy)
    colloquial_res = handle_colloquial_patient_complaints(msg_clean, user_message)
    if colloquial_res:
        llm_reply = call_external_llm(user_message, conversation_history)
        if llm_reply:
            colloquial_res['reply'] = llm_reply + f"\n\n{DISCLAIMER_TEXT}"
        response_data.update(colloquial_res)
        return response_data

    # ================= BƯỚC 5: HỎI ĐÁP DINH DƯỠNG, ĂN UỐNG & SỐNG KHỎE =================
    best_health_topic = None
    longest_health_kw = 0
    for topic in HEALTH_KNOWLEDGE_BASE:
        for kw in topic['keywords']:
            if kw in msg_clean and len(kw) > longest_health_kw:
                best_health_topic = topic
                longest_health_kw = len(kw)

    if best_health_topic:
        llm_reply = call_external_llm(user_message, conversation_history)
        if llm_reply:
            response_data['reply'] = llm_reply + f"\n\n{DISCLAIMER_TEXT}"
        else:
            response_data['reply'] = (
                f"{best_health_topic['response']}\n\n"
                f"{DISCLAIMER_TEXT}\n\n"
                f"💬 *Bạn có thể hỏi thêm về bất kỳ món ăn, thực phẩm hay vấn đề sức khỏe nào khác nhé!*"
            )

        response_data['stage'] = 'general'
        response_data['quick_replies'] = [
            'Ăn gì tốt cho dạ dày',
            'Chế độ ăn cho người tiểu đường',
            'Cách giảm cân an toàn',
            'Uống nước thế nào đúng cách',
            'Bí quyết ngủ ngon sâu giấc'
        ]
        return response_data

    # ================= BƯỚC 6: PHÂN TÍCH TRIỆU CHỨNG LÂM SÀNG TỰ NHIÊN =================
    detected_specialty_key = None
    longest_symptom_kw = 0
    for spec_key, spec_info in SYMPTOM_CLINICAL_MAP.items():
        for kw in spec_info['keywords']:
            if kw in msg_clean and len(kw) > longest_symptom_kw:
                detected_specialty_key = spec_key
                longest_symptom_kw = len(kw)

    if detected_specialty_key:
        spec_info = SYMPTOM_CLINICAL_MAP[detected_specialty_key]
        specialty_name = spec_info['specialty_name']

        explicitly_booking = any(w in msg_clean for w in ['đặt lịch', 'muốn khám', 'đặt khám', 'hẹn khám', 'tìm bác sĩ', 'xem bác sĩ'])

        if explicitly_booking:
            specialty_doctors = BacSi.objects.filter(
                chuyen_khoa__ten_chuyen_khoa=specialty_name,
                trang_thai=True
            ).select_related('benh_vien', 'chuyen_khoa', 'user')[:4]

            doc_list = []
            for d in specialty_doctors:
                slots_list = get_doctor_active_slots(d, max_slots=8)
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

            response_data['stage'] = 'booking_confirmed'
            response_data['suggested_specialty'] = specialty_name
            response_data['suggested_doctors'] = doc_list
            response_data['suggested_provinces'] = [p.ten_tinh for p in all_provinces]
            response_data['quick_replies'] = [p.ten_tinh for p in all_provinces]
            response_data['reply'] = (
                f"Dạ vâng! Với các biểu hiện bạn vừa chia sẻ, chuyên khoa phù hợp nhất để thăm khám là **{specialty_name}**.\n\n"
                f"🩺 **Lời khuyên chăm sóc ban đầu:**\n{spec_info['home_care']}\n\n"
                f"⚠️ **Lưu ý:** {spec_info['red_flags']}\n\n"
                f"{DISCLAIMER_TEXT}\n\n"
                f"👨‍⚕️ **Đội ngũ bác sĩ chuyên khoa {specialty_name} sẵn sàng nhận lịch khám:**\n"
                f"Bạn có thể chọn bác sĩ bên dưới hoặc chọn **Tỉnh/Thành phố** để xem bệnh viện tiếp nhận:"
            )
            return response_data
        else:
            llm_reply = call_external_llm(user_message, conversation_history)
            if llm_reply:
                reply_text = llm_reply + f"\n\n{DISCLAIMER_TEXT}"
            else:
                reply_text = (
                    f"{spec_info['greeting']}\n\n"
                    f"🩺 **Về nguyên nhân có thể gặp:**\n"
                    f"{spec_info['clinical_cause']}\n\n"
                    f"👉 **Những việc bạn nên làm để chăm sóc tại nhà:**\n"
                    f"{spec_info['home_care']}\n\n"
                    f"⚠️ **Khi nào cần đi khám bác sĩ:**\n"
                    f"{spec_info['red_flags']}\n\n"
                    f"💡 **Định hướng chuyên khoa:**\n"
                    f"Nếu tình trạng kéo dài hoặc không thuyên giảm sau 2-3 ngày, bạn nên thăm khám tại chuyên khoa **{specialty_name}** để được bác sĩ kiểm tra và kê đơn thuốc chính xác nhé.\n\n"
                    f"{DISCLAIMER_TEXT}\n\n"
                    f"---\n"
                    f"💬 *Tình trạng này bạn bị mấy ngày rồi? Hiện tại bạn có bị sốt hay xuất hiện thêm triệu chứng khó chịu nào khác không?*"
                )

            response_data['stage'] = 'ask_booking_confirmation'
            response_data['suggested_specialty'] = specialty_name
            response_data['suggested_doctors'] = []
            response_data['suggested_provinces'] = []
            response_data['reply'] = reply_text
            response_data['quick_replies'] = [
                'Có, tôi muốn đặt lịch khám',
                'Tôi bị 1-2 ngày nay',
                'Chưa, tôi muốn hỏi thêm'
            ]
            return response_data

    # ================= BƯỚC 7: CÂU HỎI MỞ / TỰ DO -> GỌI LLM HOẶC TRẢ LỜI MỞ =================
    llm_reply = call_external_llm(user_message, conversation_history)
    if llm_reply:
        response_data['reply'] = llm_reply + f"\n\n{DISCLAIMER_TEXT}"
        response_data['quick_replies'] = ['Tư vấn dinh dưỡng', 'Khám tại Đà Nẵng', 'Khám tại Hà Nội', 'Khám tại TP.HCM']
        return response_data

    # Chào hỏi hoặc giới thiệu năng lực
    greetings = ['xin chào', 'chào bạn', 'hello', 'hi', 'bạn là ai', 'có ai ở đây không', 'giúp tôi', 'alo']
    if any(g in msg_clean for g in greetings):
        response_data['reply'] = (
            "👋 **Xin chào bạn! Mình là Trợ lý Y tế AI của Medical AI.**\n\n"
            "Mình luôn ở đây để lắng nghe và hỗ trợ bạn 24/7 về mọi vấn đề sức khỏe:\n"
            "1. 🩺 **Tư vấn triệu chứng & hoàn cảnh bệnh:** Phân tích cụ thể tình trạng khó chịu (như tối uống bia sáng rát họng, thức khuya đau đầu, nằm điều hòa cảm lạnh...).\n"
            "2. 🥗 **Chế độ ăn uống & dinh dưỡng:** Tư vấn thực đơn cho người đau dạ dày, tiểu đường, giảm mỡ, tăng cơ, ăn uống lành mạnh...\n"
            "3. 🌿 **Mẹo sống khỏe & Chăm sóc tại nhà:** Cách cải thiện giấc ngủ, giảm căng thẳng, mẹo sơ cứu ban đầu an toàn.\n"
            "4. 🏥 **Kết nối bác sĩ & Đặt lịch khám:** Tìm bệnh viện uy tín tại 5 tỉnh thành và đặt lịch với bác sĩ chuyên khoa phù hợp.\n\n"
            "👉 *Bạn đang cảm thấy không khỏe ở đâu hay muốn tìm hiểu về chế độ ăn uống gì? Cứ thoải mái chia sẻ với mình nhé!*"
        )
        response_data['quick_replies'] = [
            'Tối qua tôi uống bia sáng nay rát họng',
            'Ăn gì tốt cho dạ dày?',
            'Tôi bị đau đầu, chóng mặt',
            'Cách giảm cân an toàn',
            'Đặt lịch tại Đà Nẵng'
        ]
        return response_data

    # Phản hồi thông minh mặc định
    response_data['reply'] = (
        "Cảm ơn câu hỏi của bạn. Mình có thể hỗ trợ bạn tư vấn cặn kẽ về **các triệu chứng khó chịu thường gặp, chế độ dinh dưỡng ăn uống cho từng bệnh lý, mẹo chăm sóc sức khỏe tại nhà** hoặc **hỗ trợ kết nối bác sĩ chuyên khoa**.\n\n"
        "Bạn hãy chia sẻ chi tiết hơn về tình trạng của mình nhé (Ví dụ: *'Tối qua tôi uống bia sáng nay rát họng'*, *'Người đau dạ dày nên ăn gì?'*, *'Tôi bị đau nửa đầu 2 ngày nay'*)."
    )
    response_data['quick_replies'] = [
        'Tối qua tôi uống bia sáng nay rát họng',
        'Dinh dưỡng cho dạ dày',
        'Cách ngủ ngon sâu giấc',
        'Đặt lịch khám tại Đà Nẵng'
    ]
    return response_data
