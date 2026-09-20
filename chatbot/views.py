from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import uuid

from .models import ChatSession, ChatMessage
from .ai_service import process_medical_chat
from hospitals.models import TinhThanh

def chat_page_view(request):
    """
    Trang giao diện trò chuyện toàn màn hình với Chatbox AI
    """
    provinces = TinhThanh.objects.all()
    return render(request, 'chatbot/chat_page.html', {'provinces': provinces})


def api_send_message(request):
    """
    API tiếp nhận tin nhắn từ giao diện (Web Chatbox hoặc Floating Widget)
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Chỉ chấp nhận POST'}, status=405)

    try:
        if request.content_type == 'application/json':
            body = json.loads(request.body)
        else:
            body = request.POST

        user_text = body.get('message', '').strip()
        session_key = body.get('session_key', '').strip()

        if not user_text:
            return JsonResponse({'status': 'error', 'message': 'Nội dung tin nhắn không được để trống'}, status=400)

        # Lấy hoặc tạo ChatSession
        if not session_key:
            session_key = str(uuid.uuid4())

        user = request.user if request.user.is_authenticated else None
        session_obj, _ = ChatSession.objects.get_or_create(
            session_key=session_key,
            defaults={'user': user}
        )
        if user and not session_obj.user:
            session_obj.user = user
            session_obj.save()

        # Lưu tin nhắn của Người dùng
        ChatMessage.objects.create(
            session=session_obj,
            sender='user',
            message=user_text
        )

        # Gọi AI Service phân tích triệu chứng / tỉnh / bệnh viện / bác sĩ
        ai_res = process_medical_chat(user_text, session=session_obj)

        # Lưu phản hồi của AI
        ChatMessage.objects.create(
            session=session_obj,
            sender='ai',
            message=ai_res['reply'],
            data_json=ai_res
        )

        return JsonResponse({
            'status': 'success',
            'session_key': session_key,
            'reply': ai_res['reply'],
            'data': ai_res
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def api_get_history(request):
    """
    Lấy lịch sử hội thoại của phiên chat
    """
    session_key = request.GET.get('session_key', '').strip()
    if not session_key:
        return JsonResponse({'status': 'success', 'messages': []})

    session_obj = ChatSession.objects.filter(session_key=session_key).first()
    if not session_obj:
        return JsonResponse({'status': 'success', 'messages': []})

    messages_data = []
    for m in session_obj.messages.all():
        messages_data.append({
            'sender': m.sender,
            'message': m.message,
            'data': m.data_json,
            'time': m.created_at.strftime('%H:%M')
        })

    return JsonResponse({'status': 'success', 'messages': messages_data})
