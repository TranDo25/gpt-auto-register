let isRunning = false;
let logIndex = 0;
let pollInterval = null;

// Khởi tạo
document.addEventListener('DOMContentLoaded', () => {
    switchTab('dashboard');
    startPolling();
});

// Chuyển đổi tab
function switchTab(tabName) {
    document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

    document.getElementById(`view-${tabName}`).classList.add('active');

    // Tìm nav item tương ứng để highlight
    const navIndex = tabName === 'dashboard' ? 0 : 1;
    document.querySelectorAll('.nav-item')[navIndex].classList.add('active');

    if (tabName === 'accounts') {
        loadAccounts();
    }
}

// Kiểm tra trạng thái định kỳ
function startPolling() {
    pollStatus(); // Thực hiện ngay lập tức
    pollInterval = setInterval(pollStatus, 1000);
}

async function pollStatus() {
    try {
        const res = await fetch(`/api/status?log_index=${logIndex}`);
        const data = await res.json();

        updateUI(data);
    } catch (e) {
        console.error("Lỗi kiểm tra:", e);
    }
}

function updateUI(data) {
    // 1. Cập nhật các chỉ số cơ bản
    document.getElementById('valAction').textContent = data.current_action;
    document.getElementById('valSuccess').textContent = data.success;
    document.getElementById('valFail').textContent = data.fail;
    document.getElementById('valInventory').textContent = data.total_inventory;
    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();

    // 2. Cập nhật trạng thái chạy (nút và đèn chỉ báo)
    isRunning = data.is_running;
    const btnStart = document.getElementById('btnStart');
    const btnStop = document.getElementById('btnStop');
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');

    if (isRunning) {
        btnStart.classList.add('hidden');
        btnStop.classList.remove('hidden');
        statusDot.classList.add('running');
        statusText.textContent = "Đang Chạy";
    } else {
        btnStart.classList.remove('hidden');
        btnStop.classList.add('hidden');
        statusDot.classList.remove('running');
        statusText.textContent = "Hệ Thống Rảnh";
    }

    // 4. Cập nhật màn hình giám sát
    const monitorImg = document.getElementById('liveMonitor');
    const noSignal = document.getElementById('noSignal');
    const monitorStatus = document.getElementById('monitorStatus');

    if (isRunning) {
        monitorImg.classList.remove('hidden');
        noSignal.classList.add('hidden');

        // Chỉ gán src nếu nó trống hoặc không chứa /video_feed, tránh làm mới lặp lại gây nhấp nháy
        if (!monitorImg.src || monitorImg.src.indexOf('/video_feed') === -1) {
            monitorImg.src = "/video_feed";
        }

        monitorStatus.textContent = "LIVE";
        monitorStatus.classList.remove('neutral');
        monitorStatus.classList.add('success');
    } else {
        monitorStatus.textContent = "OFFLINE";
        monitorStatus.classList.remove('success');
        monitorStatus.classList.add('neutral');
        // Tác vụ kết thúc, nhưng không nhất thiết phải ngắt luồng vì có thể còn khung hình cuối cùng
        // Nếu muốn ngắt: monitorImg.src = "";
    }

    // 5. Thêm nhật ký
    if (data.logs && data.logs.length > 0) {
        const container = document.getElementById('logContainer');

        // Xóa placeholder
        const placeholder = container.querySelector('.log-placeholder');
        if (placeholder) placeholder.remove();

        data.logs.forEach(logLine => {
            const div = document.createElement('div');
            div.className = 'log-entry';
            div.textContent = logLine;
            container.appendChild(div);
        });

        // Tự động cuộn xuống dưới cùng
        container.scrollTop = container.scrollHeight;

        // Cập nhật chỉ số, tránh lấy lại dữ liệu cũ
        logIndex += data.logs.length;
    }
}

// Bắt đầu tác vụ
async function startTask() {
    const count = parseInt(document.getElementById('targetCount').value) || 1;

    // Xóa nhật ký cũ
    clearLogs();

    try {
        const res = await fetch('/api/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ count: count })
        });

        if (!res.ok) {
            alert("Bắt đầu thất bại: " + await res.text());
        }
    } catch (e) {
        alert("Yêu cầu thất bại: " + e);
    }
}

// Dừng tác vụ
async function stopTask() {
    if (!confirm("Bạn có chắc chắn muốn dừng tác vụ hiện tại không?")) return;

    try {
        await fetch('/api/stop', { method: 'POST' });
    } catch (e) {
        console.error(e);
    }
}

// Xóa nhật ký
function clearLogs() {
    document.getElementById('logContainer').innerHTML = '<div class="log-placeholder">Chờ tác vụ bắt đầu...</div>';
    logIndex = 0;
}

// Tải danh sách tài khoản
async function loadAccounts() {
    const tbody = document.getElementById('accountTableBody');
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center">Đang Tải...</td></tr>';

    try {
        const res = await fetch('/api/accounts');
        const accounts = await res.json();

        renderAccounts(accounts);
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;color:red">Tải Thất Bại: ${e}</td></tr>`;
    }
}

function renderAccounts(accounts) {
    const tbody = document.getElementById('accountTableBody');
    tbody.innerHTML = '';

    if (accounts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#666">Không Có Dữ Liệu</td></tr>';
        return;
    }

    accounts.forEach(acc => {
        let statusClass = '';
        if (acc.status.includes('Thành Công') || acc.status.includes('Đã Đăng Ký')) statusClass = 'success';
        if (acc.status.includes('Thất Bại')) statusClass = 'fail';

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${acc.email}</td>
            <td style="font-family:monospace">${acc.password}</td>
            <td><span class="status-tag ${statusClass}">${acc.status}</span></td>
            <td>${acc.time}</td>
        `;
        tbody.appendChild(tr);
    });

    // Lưu vào global để tìm kiếm
    window.allAccounts = accounts;
}

// Tìm kiếm tài khoản
function filterAccounts() {
    const term = document.getElementById('searchInput').value.toLowerCase();
    if (!window.allAccounts) return;

    const filtered = window.allAccounts.filter(acc =>
        acc.email.toLowerCase().includes(term)
    );
    renderAccounts(filtered);
}
