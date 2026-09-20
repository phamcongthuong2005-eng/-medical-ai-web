// Medical AI Chatbot & In-Chat Booking Engine

// Global in-chat booking state
window.chatBookingState = {
  symptom: '',
  specialtyId: null,
  specialtyName: '',
  tinhId: null,
  tinhName: '',
  hospitalId: null,
  hospitalName: '',
  doctorId: null,
  doctorName: '',
  doctorFee: 0,
  date: '',
  time: '',
  fullName: '',
  phone: ''
};

document.addEventListener('DOMContentLoaded', () => {
  initFloatingChat();

  // Khởi tạo thông tin người dùng nếu đã đăng nhập
  if (window.CURRENT_USER && window.CURRENT_USER.is_authenticated) {
    chatBookingState.fullName = window.CURRENT_USER.full_name || window.CURRENT_USER.username;
    chatBookingState.phone = window.CURRENT_USER.phone || '';
  }
});

function initFloatingChat() {
  const trigger = document.getElementById('chatTrigger');
  const box = document.getElementById('chatBox');
  const closeBtn = document.getElementById('closeChatBtn');
  const chatForm = document.getElementById('chatForm');
  const chatInput = document.getElementById('chatInput');
  const messagesContainer = document.getElementById('chatMessages');

  if (!trigger || !box) return;

  // Khóa phiên chat
  let sessionKey = localStorage.getItem('medical_ai_session_key');
  if (!sessionKey) {
    sessionKey = 'sess_' + Math.random().toString(36).substring(2, 15);
    localStorage.setItem('medical_ai_session_key', sessionKey);
  }

  // Mở / Đóng khung chat nổi
  trigger.addEventListener('click', () => {
    box.classList.toggle('open');
    if (box.classList.contains('open')) {
      chatInput.focus();
      if (messagesContainer.children.length === 0) {
        addAiMessageToContainer(messagesContainer, {
          reply: '👋 Xin chào bạn! Tôi là **Trợ lý Y tế AI** của Medical AI.\n\nTôi có thể hỗ trợ bạn:\n1. 🩺 **Phân tích triệu chứng** và tư vấn thông tin y tế tham khảo.\n2. 🏥 **Chọn bệnh viện theo từng Tỉnh/Thành phố**.\n3. 👨‍⚕️ **Tự động điền bảng thông tin và đặt lịch khám ngay tại đây!**\n\nBạn đang có triệu chứng gì hay muốn khám ở tỉnh/thành phố nào?',
          quick_replies: ['Tôi bị đau đầu, chóng mặt', 'Tôi bị đau dạ dày', 'Đà Nẵng', 'Hà Nội', 'TP. Hồ Chí Minh']
        });
      }
    }
  });

  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      box.classList.remove('open');
    });
  }

  // Gửi tin nhắn
  if (chatForm) {
    chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = chatInput.value.trim();
      if (!text) return;

      addUserMessageToContainer(messagesContainer, text);
      chatInput.value = '';
      sendChatMessage(messagesContainer, text, sessionKey);
    });
  }

  window.sendQuickMessage = function(text) {
    // Mở hộp chat nếu đang đóng
    if (!box.classList.contains('open')) {
      box.classList.add('open');
    }
    addUserMessageToContainer(messagesContainer, text);
    sendChatMessage(messagesContainer, text, sessionKey);
  };
}

// Thêm tin nhắn của User
function addUserMessageToContainer(container, text) {
  const bubble = document.createElement('div');
  bubble.className = 'message-bubble message-user';
  bubble.textContent = text;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

// Gửi tin nhắn đến Django Backend API
async function sendChatMessage(container, message, sessionKey) {
  // Ghi nhận triệu chứng nếu là tin nhắn đầu tiên
  if (!chatBookingState.symptom && message.length > 5 && !message.includes('khám ở')) {
    chatBookingState.symptom = message;
  }

  const typingElem = document.createElement('div');
  typingElem.className = 'message-bubble message-ai text-muted typing-indicator';
  typingElem.innerHTML = '<span class="spinner-grow spinner-grow-sm me-1"></span> AI đang phân tích dữ liệu...';
  container.appendChild(typingElem);
  container.scrollTop = container.scrollHeight;

  try {
    const res = await fetch('/chatbot/api/send/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      },
      body: JSON.stringify({ message, session_key: sessionKey })
    });

    const data = await res.json();
    typingElem.remove();

    if (data.status === 'success') {
      addAiMessageToContainer(container, data.data);
    } else {
      addAiMessageToContainer(container, { reply: 'Xin lỗi, đã có lỗi: ' + (data.message || 'Lỗi xử lý') });
    }
  } catch (err) {
    typingElem.remove();
    addAiMessageToContainer(container, { reply: 'Không thể kết nối máy chủ. Vui lòng kiểm tra lại mạng.' });
  }
}

// Hiển thị tin nhắn AI kèm các nút hành động tương tác trong Chat
function addAiMessageToContainer(container, data) {
  const bubble = document.createElement('div');
  bubble.className = 'message-bubble message-ai';

  // Lưu specialty gợi ý nếu có
  if (data.suggested_specialty) {
    chatBookingState.specialtyName = data.suggested_specialty;
  }
  if (data.selected_province) {
    chatBookingState.tinhName = data.selected_province;
  }

  // Format văn bản
  let formattedText = data.reply || '';
  formattedText = formattedText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  formattedText = formattedText.replace(/\n/g, '<br>');

  let html = `<div>${formattedText}</div>`;

  // 1. Nếu có BỆNH VIỆN THUỘC TỈNH: Hiển thị dạng Card có nút "CHỌN BỆNH VIỆN NÀY" ngay trong chat
  if (data.suggested_hospitals && data.suggested_hospitals.length > 0) {
    html += `<div class="mt-3 d-flex flex-column gap-2">`;
    data.suggested_hospitals.forEach(h => {
      html += `
        <div class="card p-2 border shadow-sm bg-white" style="font-size: 0.85rem; border-radius: 12px;">
          <div class="d-flex gap-2 align-items-center">
            <img src="${h.hinh_anh}" alt="${h.ten}" style="width: 55px; height: 55px; object-fit: cover; border-radius: 8px;">
            <div class="flex-grow-1">
              <strong class="text-dark d-block">${h.ten}</strong>
              <div class="text-muted small"><i class="bi bi-geo-alt text-danger"></i> ${h.dia_chi}</div>
            </div>
          </div>
          <div class="mt-2 pt-2 border-top d-flex justify-content-between align-items-center">
            <span class="text-primary small"><i class="bi bi-telephone"></i> ${h.sdt}</span>
            <button type="button" class="btn btn-sm btn-primary-custom" style="font-size: 0.78rem;" 
                    onclick="chatSelectHospital(${h.id}, '${h.ten}')">
              <i class="bi bi-check2-circle me-1"></i> Chọn bệnh viện này
            </button>
          </div>
        </div>
      `;
    });
    html += `</div>`;
  }

  // 2. Nếu có BÁC SĨ: Hiển thị dạng Card có nút "CHỌN BÁC SĨ NÀY" ngay trong chat
  if (data.suggested_doctors && data.suggested_doctors.length > 0) {
    html += `<div class="mt-3 d-flex flex-column gap-2">`;
    data.suggested_doctors.forEach(d => {
      const slotsJson = JSON.stringify(d.slots || []).replace(/"/g, '&quot;');
      const isFemale = (d.gender && d.gender.toLowerCase().includes('nữ')) || d.ho_ten.includes('Thị') || d.ho_ten.includes('Lan') || d.ho_ten.includes('Hương') || d.ho_ten.includes('Nga') || d.ho_ten.includes('Hà') || d.ho_ten.includes('Ngọc') || d.ho_ten.includes('Hạnh') || d.ho_ten.includes('Diệp') || d.ho_ten.includes('Nhung') || d.ho_ten.includes('Quỳnh');
      const genderBadge = isFemale 
        ? '<span class="badge bg-danger-subtle text-danger border border-danger-subtle px-2 py-1"><i class="bi bi-gender-female"></i> Bác sĩ Nữ</span>'
        : '<span class="badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-1"><i class="bi bi-gender-male"></i> Bác sĩ Nam</span>';

      html += `
        <div class="card p-2 border shadow-sm bg-white text-center" style="font-size: 0.85rem; border-radius: 12px;">
          <div class="d-flex justify-content-between align-items-center mb-1">
            ${genderBadge}
            <span class="badge bg-light text-muted border" style="font-size: 0.72rem;"><i class="bi bi-hospital"></i> ${d.benh_vien || ''}</span>
          </div>
          <img src="${d.anh}" alt="${d.ho_ten}" class="rounded-circle mx-auto my-1 shadow-sm" style="width: 55px; height: 55px; object-fit: cover;">
          <strong class="text-dark d-block">${d.chuc_danh} ${d.ho_ten}</strong>
          <span class="badge bg-primary text-white my-1" style="font-size: 0.75rem;">${d.chuyen_khoa}</span>
          <div class="text-success small fw-bold mb-2">Phí khám: ${d.gia_kham.toLocaleString()} đ</div>
          <button type="button" class="btn btn-sm btn-success w-100 fw-bold" style="font-size: 0.8rem;"
                  onclick="chatSelectDoctor(${d.id}, '${d.chuc_danh} ${d.ho_ten}', ${d.chuyen_khoa_id || 1}, '${d.chuyen_khoa}', ${d.gia_kham}, ${slotsJson})">
            <i class="bi bi-calendar2-check me-1"></i> Chọn bác sĩ này
          </button>
        </div>
      `;
    });
    html += `</div>`;
  }

  // 3. Quick replies / Chips (Tỉnh thành, triệu chứng)
  if (data.quick_replies && data.quick_replies.length > 0) {
    html += `<div class="mt-2 pt-2 border-top">`;
    data.quick_replies.forEach(chip => {
      html += `<span class="quick-chip" onclick="window.sendQuickMessage('${chip}')">${chip}</span>`;
    });
    html += `</div>`;
  }

  bubble.innerHTML = html;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

// ================= CÁC BƯỚC TỰ ĐỘNG ĐIỀN THÔNG TIN TRONG CHAT =================

// Bước A: Người dùng chọn Bệnh viện
window.chatSelectHospital = function(hospitalId, hospitalName) {
  chatBookingState.hospitalId = hospitalId;
  chatBookingState.hospitalName = hospitalName;

  const container = getActiveMessagesContainer();
  addUserMessageToContainer(container, `Tôi chọn khám tại ${hospitalName}`);

  // Tải danh sách bác sĩ của viện qua API
  const typingElem = document.createElement('div');
  typingElem.className = 'message-bubble message-ai text-muted';
  typingElem.innerHTML = '<span class="spinner-grow spinner-grow-sm me-1"></span> Đang tải danh sách bác sĩ chuyên khoa...';
  container.appendChild(typingElem);
  container.scrollTop = container.scrollHeight;

  fetch(`/doctors/api/by-criteria/?hospital_id=${hospitalId}`)
    .then(res => res.json())
    .then(data => {
      typingElem.remove();
      if (data.status === 'success' && data.data.length > 0) {
        addAiMessageToContainer(container, {
          reply: `🏥 Bạn đã chọn: **${hospitalName}**\n\nDưới đây là danh sách **bác sĩ chuyên khoa** đang trực tiếp nhận lịch khám tại viện. Bạn vui lòng chọn bác sĩ mong muốn:`,
          suggested_doctors: data.data.map(d => ({
            id: d.id,
            ho_ten: d.ho_ten,
            chuc_danh: d.chuc_danh,
            chuyen_khoa_id: d.chuyen_khoa_id || 1,
            chuyen_khoa: d.chuyen_khoa,
            gia_kham: d.gia_kham,
            anh: d.anh_dai_dien,
            slots: []
          }))
        });
      } else {
        addAiMessageToContainer(container, { reply: `Hiện chưa có lịch bác sĩ trực tuyến tại ${hospitalName}. Vui lòng chọn bệnh viện khác.` });
      }
    });
};

// Bước B: Người dùng chọn Bác sĩ
window.chatSelectDoctor = function(doctorId, doctorName, specialtyId, specialtyName, doctorFee, slots) {
  chatBookingState.doctorId = doctorId;
  chatBookingState.doctorName = doctorName;
  chatBookingState.specialtyId = specialtyId;
  chatBookingState.specialtyName = specialtyName;
  chatBookingState.doctorFee = doctorFee;

  const container = getActiveMessagesContainer();
  addUserMessageToContainer(container, `Tôi chọn bác sĩ ${doctorName}`);

  const typingElem = document.createElement('div');
  typingElem.className = 'message-bubble message-ai text-muted';
  typingElem.innerHTML = '<span class="spinner-grow spinner-grow-sm me-1"></span> Đang kiểm tra các khung giờ trống của bác sĩ...';
  container.appendChild(typingElem);
  container.scrollTop = container.scrollHeight;

  // Lấy các khung giờ trống của bác sĩ
  fetch(`/doctors/api/${doctorId}/slots/`)
    .then(res => res.json())
    .then(data => {
      typingElem.remove();
      const slotsList = data.data || [];
      renderDoctorSlotsInChat(container, doctorName, slotsList);
    });
};

// Hiển thị ngày và khung giờ còn trống trong chat
function renderDoctorSlotsInChat(container, doctorName, slotsList) {
  const bubble = document.createElement('div');
  bubble.className = 'message-bubble message-ai';

  let html = `
    <div>
      👨‍⚕️ Bác sĩ: <strong>${doctorName}</strong><br>
      Dưới đây là các <strong>khung giờ khám còn trống</strong>. Bạn vui lòng bấm chọn khung giờ thuận tiện nhất:
    </div>
    <div class="d-flex flex-wrap gap-2 mt-3">
  `;

  if (slotsList.length > 0) {
    slotsList.slice(0, 8).forEach(s => {
      html += `
        <button type="button" class="btn btn-sm btn-outline-primary" style="font-size: 0.78rem;"
                onclick="chatSelectSlot('${s.date}', '${s.start_time}', '${s.date_display}')">
          <i class="bi bi-clock me-1"></i> ${s.date_display} (${s.start_time})
        </button>
      `;
    });
  } else {
    // Tạo tạm một số slot chuẩn nếu data rỗng
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const dStr = tomorrow.toISOString().split('T')[0];
    const dDisplay = tomorrow.toLocaleDateString('vi-VN');
    ['08:00', '09:00', '10:00', '14:00', '15:00'].forEach(t => {
      html += `
        <button type="button" class="btn btn-sm btn-outline-primary" style="font-size: 0.78rem;"
                onclick="chatSelectSlot('${dStr}', '${t}', '${dDisplay}')">
          <i class="bi bi-clock me-1"></i> ${dDisplay} (${t})
        </button>
      `;
    });
  }

  html += `</div>`;
  bubble.innerHTML = html;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

// Bước C: Người dùng chọn Khung giờ khám
window.chatSelectSlot = function(dateStr, timeStr, dateDisplay) {
  chatBookingState.date = dateStr;
  chatBookingState.time = timeStr;

  const container = getActiveMessagesContainer();
  addUserMessageToContainer(container, `Tôi chọn khám lúc ${timeStr} ngày ${dateDisplay || dateStr}`);

  // Kiểm tra xem đã có Họ tên & SĐT chưa
  if (chatBookingState.fullName && chatBookingState.phone) {
    // Đã có thông tin -> Hiển thị ngay BẢNG THÔNG TIN ĐẶT LỊCH
    renderBookingSummaryTable(container);
  } else {
    // Chưa có thông tin -> Hiển thị form điền nhanh trong chat
    renderPatientInfoFormInChat(container);
  }
};

// Form điền nhanh thông tin trong chat nếu chưa đăng nhập
function renderPatientInfoFormInChat(container) {
  const bubble = document.createElement('div');
  bubble.className = 'message-bubble message-ai';
  bubble.innerHTML = `
    <div>
      📝 Để hoàn tất đặt lịch, bạn vui lòng cung cấp <strong>Họ tên</strong> và <strong>Số điện thoại</strong> liên hệ:
    </div>
    <div class="card p-3 bg-light border mt-2 rounded-3 text-start">
      <div class="mb-2">
        <label class="form-label small fw-semibold mb-1">Họ và tên người khám:</label>
        <input type="text" id="chatInputPatientName" class="form-control form-control-sm" placeholder="VD: Nguyễn Văn An" value="${chatBookingState.fullName || ''}">
      </div>
      <div class="mb-2">
        <label class="form-label small fw-semibold mb-1">Số điện thoại nhận tin nhắn xác nhận:</label>
        <input type="tel" id="chatInputPatientPhone" class="form-control form-control-sm" placeholder="VD: 0905123456" value="${chatBookingState.phone || ''}">
      </div>
      <button type="button" class="btn btn-sm btn-primary w-100 fw-bold mt-1" onclick="chatSubmitPatientInfo()">
        <i class="bi bi-arrow-right-circle me-1"></i> Xem Bảng Thông Tin Đặt Lịch
      </button>
    </div>
  `;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

window.chatSubmitPatientInfo = function() {
  const nameInput = document.getElementById('chatInputPatientName');
  const phoneInput = document.getElementById('chatInputPatientPhone');

  const name = nameInput ? nameInput.value.trim() : '';
  const phone = phoneInput ? phoneInput.value.trim() : '';

  if (!name || !phone) {
    alert('Vui lòng nhập đầy đủ Họ tên và Số điện thoại liên hệ!');
    return;
  }

  chatBookingState.fullName = name;
  chatBookingState.phone = phone;

  const container = getActiveMessagesContainer();
  addUserMessageToContainer(container, `Thông tin của tôi: ${name} - ${phone}`);
  renderBookingSummaryTable(container);
};

// Bước D: HIỂN THỊ BẢNG THÔNG TIN ĐẶT LỊCH ĐỂ KHÁCH HÀNG XÁC NHẬN "ĐỒNG Ý ĐẶT LỊCH"
function renderBookingSummaryTable(container) {
  const bubble = document.createElement('div');
  bubble.className = 'message-bubble message-ai w-100';

  const feeFormatted = (chatBookingState.doctorFee || 250000).toLocaleString() + ' VNĐ';

  bubble.innerHTML = `
    <div class="card p-3 border-2 border-primary bg-white shadow-sm rounded-4 text-start">
      <div class="d-flex align-items-center gap-2 mb-2 pb-2 border-bottom">
        <i class="bi bi-calendar2-check-fill text-primary fs-4"></i>
        <div>
          <strong class="text-primary fs-6 d-block">BẢNG THÔNG TIN ĐẶT LỊCH KHÁM</strong>
          <small class="text-muted">Vui lòng kiểm tra lại thông tin trước khi xác nhận</small>
        </div>
      </div>

      <div class="table-responsive">
        <table class="table table-sm table-borderless mb-2 small">
          <tbody>
            <tr>
              <td class="text-muted" style="width: 130px;">Tỉnh/Thành phố:</td>
              <td><strong>${chatBookingState.tinhName || 'Đà Nẵng'}</strong></td>
            </tr>
            <tr>
              <td class="text-muted">Bệnh viện:</td>
              <td><strong class="text-dark">${chatBookingState.hospitalName}</strong></td>
            </tr>
            <tr>
              <td class="text-muted">Chuyên khoa:</td>
              <td><span class="badge bg-primary-subtle text-primary">${chatBookingState.specialtyName || 'Nội tổng quát'}</span></td>
            </tr>
            <tr>
              <td class="text-muted">Bác sĩ:</td>
              <td><strong>${chatBookingState.doctorName}</strong></td>
            </tr>
            <tr>
              <td class="text-muted">Thời gian khám:</td>
              <td><strong class="text-success"><i class="bi bi-clock me-1"></i>${chatBookingState.time} - Ngày ${chatBookingState.date}</strong></td>
            </tr>
            <tr>
              <td class="text-muted">Bệnh nhân:</td>
              <td><strong>${chatBookingState.fullName}</strong></td>
            </tr>
            <tr>
              <td class="text-muted">Số điện thoại:</td>
              <td><strong>${chatBookingState.phone}</strong></td>
            </tr>
            <tr>
              <td class="text-muted">Triệu chứng:</td>
              <td class="fst-italic text-secondary">${chatBookingState.symptom || 'Khám tổng quát / theo tư vấn AI'}</td>
            </tr>
            <tr>
              <td class="text-muted">Phí khám dự kiến:</td>
              <td><strong class="text-danger">${feeFormatted}</strong></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="pt-3 border-top d-flex gap-2" id="chatConfirmBtnGroup">
        <button type="button" class="btn btn-success flex-grow-1 fw-bold py-2 shadow-sm" onclick="chatConfirmBooking(this)">
          <i class="bi bi-check-circle-fill me-1"></i> ĐỒNG Ý ĐẶT LỊCH
        </button>
        <button type="button" class="btn btn-outline-secondary btn-sm" onclick="chatRestartBooking()">
          <i class="bi bi-arrow-clockwise"></i> Chọn lại
        </button>
      </div>
    </div>
  `;

  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

// Bước E: Khách hàng click "ĐỒNG Ý ĐẶT LỊCH" ➔ Lưu vào MySQL
window.chatConfirmBooking = function(buttonElement) {
  if (buttonElement) {
    buttonElement.disabled = true;
    buttonElement.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Đang lưu vào hệ thống...';
  }

  const container = getActiveMessagesContainer();

  const payload = {
    hospital_id: chatBookingState.hospitalId,
    specialty_id: chatBookingState.specialtyId || 1,
    doctor_id: chatBookingState.doctorId,
    date: chatBookingState.date,
    time: chatBookingState.time,
    full_name: chatBookingState.fullName,
    phone: chatBookingState.phone,
    symptom: chatBookingState.symptom || 'Đặt lịch qua Trợ lý Chatbox AI',
    reason: 'Đặt lịch qua AI Chatbox'
  };

  fetch('/appointments/api/create/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify(payload)
  })
  .then(res => res.json())
  .then(data => {
    if (data.status === 'success') {
      const app = data.appointment;
      renderBookingSuccessInChat(container, app);
    } else {
      alert('Không thể hoàn tất đặt lịch: ' + (data.message || 'Lỗi'));
      if (buttonElement) {
        buttonElement.disabled = false;
        buttonElement.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i> ĐỒNG Ý ĐẶT LỊCH';
      }
    }
  })
  .catch(() => {
    alert('Lỗi kết nối máy chủ!');
    if (buttonElement) {
      buttonElement.disabled = false;
      buttonElement.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i> ĐỒNG Ý ĐẶT LỊCH';
    }
  });
};

// Hiển thị Thẻ Đặt Lịch Thành Công ngay trong chat
function renderBookingSuccessInChat(container, app) {
  const bubble = document.createElement('div');
  bubble.className = 'message-bubble message-ai w-100';

  bubble.innerHTML = `
    <div class="alert alert-success border-2 border-success rounded-4 p-3 shadow-sm mb-0 text-start">
      <div class="d-flex align-items-center gap-2 mb-2">
        <i class="bi bi-check-circle-fill text-success fs-3"></i>
        <div>
          <strong class="fs-6 text-success d-block">🎉 ĐẶT LỊCH KHÁM THÀNH CÔNG!</strong>
          <small class="text-muted">Thông tin cuộc hẹn đã được lưu an toàn vào cơ sở dữ liệu MySQL</small>
        </div>
      </div>

      <div class="bg-white p-3 rounded-3 border mb-3 small">
        <div class="mb-1">Mã đặt lịch: <strong class="text-primary font-monospace fs-6">${app.ma_lich_kham}</strong></div>
        <div class="mb-1">Bệnh viện: <strong>${app.benh_vien}</strong></div>
        <div class="mb-1">Bác sĩ phụ trách: <strong>${app.chuc_danh} ${app.bac_si}</strong></div>
        <div class="mb-1">Thời gian hẹn: <strong class="text-success"><i class="bi bi-calendar-event me-1"></i>${app.gio_kham} ngày ${app.ngay_kham}</strong></div>
        <div class="mb-1">Bệnh nhân: <strong>${app.ten_benh_nhan}</strong> (${app.so_dien_thoai})</div>
        <div>Trạng thái: <span class="badge bg-warning text-dark">${app.trang_thai}</span></div>
      </div>

      <p class="small text-muted mb-3">
        Bệnh viện sẽ gửi tin nhắn/gọi điện xác nhận trước giờ khám. Quý khách vui lòng đến trước 15 phút để làm thủ tục tiếp đón.
      </p>

      <div class="d-flex gap-2">
        <a href="/appointments/my-appointments/" class="btn btn-sm btn-primary flex-grow-1">
          <i class="bi bi-calendar-check me-1"></i> Lịch Khám Của Tôi
        </a>
        <a href="/appointments/${app.id}/success/" class="btn btn-sm btn-outline-success">
          <i class="bi bi-receipt me-1"></i> Xem Phiếu Khám
        </a>
      </div>
    </div>
  `;

  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

window.chatRestartBooking = function() {
  const container = getActiveMessagesContainer();
  addUserMessageToContainer(container, 'Tôi muốn chọn lại thông tin đặt lịch');
  addAiMessageToContainer(container, {
    reply: 'Dạ, bạn muốn khám ở Tỉnh/Thành phố nào để tôi hỗ trợ tìm bệnh viện và bác sĩ nhé?',
    quick_replies: ['Đà Nẵng', 'Hà Nội', 'TP. Hồ Chí Minh', 'Thừa Thiên Huế', 'Cần Thơ']
  });
};

function getActiveMessagesContainer() {
  const pageMessages = document.getElementById('pageChatMessages');
  if (pageMessages) return pageMessages;
  return document.getElementById('chatMessages') || document.body;
}

// Lấy CSRF token từ cookie
function getCsrfToken() {
  const cookieValue = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];
  return cookieValue || '';
}
