"""
Mô-đun dịch vụ email
Dựa trên dự án cloudflare_temp_email để triển khai chức năng email tạm thời
Địa chỉ dự án: https://github.com/dreamhunter2333/cloudflare_temp_email
"""

import random
import string
import time
import email
from email import policy

from config import (
    EMAIL_WORKER_URL,
    EMAIL_DOMAIN,
    EMAIL_PREFIX_LENGTH,
    EMAIL_WAIT_TIMEOUT,
    EMAIL_POLL_INTERVAL,
    HTTP_TIMEOUT
)
from utils import http_session, get_user_agent, extract_verification_code


def create_temp_email():
    """
    Tạo email tạm thời
    Gọi giao diện /api/new_address của cloudflare_temp_email

    Lưu ý: Máy chủ sẽ tự động thêm tiền tố 'tmp' vào tên email,
    do đó nên sử dụng trường address được máy chủ trả về làm địa chỉ email thực tế

    Trả về:
        tuple: (địa chỉ email, mã thông báo JWT), thất bại trả về (None, None)
    """
    print("📧 Đang tạo email tạm thời...")

    # Tạo tiền tố email ngẫu nhiên (máy chủ sẽ tự động thêm tiền tố tmp)
    prefix = ''.join(random.choices(
        string.ascii_lowercase + string.digits,
        k=EMAIL_PREFIX_LENGTH
    ))

    headers = {
        "Content-Type": "application/json",
        "User-Agent": get_user_agent()
    }

    try:
        # Gọi giao diện tạo email
        response = http_session.post(
            f"{EMAIL_WORKER_URL}/api/new_address",
            headers=headers,
            json={"name": prefix},
            timeout=HTTP_TIMEOUT
        )

        if response.status_code == 200:
            result = response.json()
            jwt_token = result.get('jwt')
            # Sử dụng địa chỉ email thực tế được máy chủ trả về (bao gồm tiền tố tmp)
            actual_email = result.get('address')

            if jwt_token and actual_email:
                print(f"✅ Email tạo thành công: {actual_email}")
                return actual_email, jwt_token
            elif jwt_token:
                # Tương thích: nếu máy chủ không trả về address, tự ghép nối
                fallback_email = f"tmp{prefix}@{EMAIL_DOMAIN}"
                print(f"✅ Email tạo thành công: {fallback_email}")
                return fallback_email, jwt_token
            else:
                print(f"⚠️ Phản hồi không chứa JWT: {result}")
        else:
            print(f"❌ Lỗi API: HTTP {response.status_code}")
            print(f"   Nội dung phản hồi: {response.text[:200]}")

    except Exception as e:
        print(f"❌ Lỗi tạo email: {e}")

    return None, None


def fetch_emails(jwt_token: str):
    """
    Lấy danh sách email

    Tham số:
        jwt_token: Mã thông báo JWT nhận được khi tạo email

    Trả về:
        list: Danh sách email, thất bại trả về None
    """
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "User-Agent": get_user_agent()
    }

    try:
        # API cần các tham số limit và offset
        response = http_session.get(
            f"{EMAIL_WORKER_URL}/api/mails?limit=20&offset=0",
            headers=headers,
            timeout=HTTP_TIMEOUT
        )

        if response.status_code == 200:
            result = response.json()

            # Xử lý các định dạng phản hồi khác nhau
            if isinstance(result, list):
                return result
            elif isinstance(result, dict):
                return result.get('results', result.get('mails', []))
        else:
            print(f"  Lỗi lấy email: HTTP {response.status_code}")

    except Exception as e:
        print(f"  Lỗi lấy email: {e}")

    return None


def get_email_detail(jwt_token: str, email_id: str):
    """
    Lấy chi tiết email

    Tham số:
        jwt_token: Mã thông báo JWT
        email_id: ID email

    Trả về:
        dict: Chi tiết email, thất bại trả về None
    """
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "User-Agent": get_user_agent()
    }

    try:
        response = http_session.get(
            f"{EMAIL_WORKER_URL}/api/mails/{email_id}",
            headers=headers,
            timeout=HTTP_TIMEOUT
        )

        if response.status_code == 200:
            return response.json()

    except Exception as e:
        print(f"  Lỗi lấy chi tiết email: {e}")

    return None


def parse_raw_email(raw_content: str):
    """
    Phân tích nội dung email thô

    Tham số:
        raw_content: Chuỗi email thô

    Trả về:
        dict: Từ điển chứa subject, body, sender
    """
    result = {'subject': '', 'body': '', 'sender': ''}

    if not raw_content:
        return result

    try:
        msg = email.message_from_string(raw_content, policy=policy.default)

        result['subject'] = msg.get('Subject', '')
        result['sender'] = msg.get('From', '')

        # Lấy nội dung
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type in ['text/plain', 'text/html']:
                    payload = part.get_payload(decode=True)
                    if payload:
                        result['body'] = payload.decode('utf-8', errors='ignore')
                        break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                result['body'] = payload.decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"  Lỗi phân tích email: {e}")

    return result


def wait_for_verification_email(jwt_token: str, timeout: int = None):
    """
    Chờ và trích xuất mã xác minh OpenAI
    Sẽ liên tục thăm dò hộp thư cho đến khi nhận được email xác minh hoặc hết thời gian chờ

    Tham số:
        jwt_token: Mã thông báo JWT
        timeout: Thời gian chờ tối đa (giây), mặc định sử dụng giá trị trong tệp cấu hình

    Trả về:
        str: Mã xác minh, không tìm thấy trả về None
    """
    if timeout is None:
        timeout = EMAIL_WAIT_TIMEOUT

    print(f"⏳ Đang chờ email xác minh (tối đa {timeout} giây)...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        emails = fetch_emails(jwt_token)

        if emails and len(emails) > 0:
            for email_item in emails:
                # Cố gắng phân tích trường raw (nếu tồn tại)
                raw_content = email_item.get('raw', '')
                if raw_content:
                    parsed = parse_raw_email(raw_content)
                    subject = parsed['subject']
                    sender = parsed['sender'].lower()
                    body = parsed['body']
                else:
                    # Quay lại các trường cũ
                    sender = str(email_item.get('from') or email_item.get('source', '')).lower()
                    subject = email_item.get('subject', '') or ''
                    body = ''

                # Kiểm tra xem có phải email xác minh OpenAI không
                if 'openai' in sender or 'chatgpt' in subject.lower():
                    print(f"\n📧 Nhận được email xác minh OpenAI!")
                    print(f"   Chủ đề: {subject}")

                    # Trước tiên cố gắng trích xuất mã xác minh từ chủ đề
                    code = extract_verification_code(subject)
                    if code:
                        return code

                    # Nếu không có trong chủ đề, trích xuất từ nội dung
                    if body:
                        code = extract_verification_code(body)
                        if code:
                            return code

                    # Nếu vẫn chưa có, cố gắng lấy chi tiết email
                    email_id = email_item.get('id')
                    if email_id:
                        detail = get_email_detail(jwt_token, email_id)
                        if detail:
                            # Phân tích raw trong chi tiết
                            detail_raw = detail.get('raw', '')
                            if detail_raw:
                                parsed_detail = parse_raw_email(detail_raw)
                                code = extract_verification_code(parsed_detail['subject'])
                                if code:
                                    return code
                                code = extract_verification_code(parsed_detail['body'])
                                if code:
                                    return code

                            # Thử các trường khác
                            content = (
                                detail.get('html') or
                                detail.get('html_content') or
                                detail.get('text') or
                                detail.get('content', '')
                            )
                            if content:
                                code = extract_verification_code(content)
                                if code:
                                    return code

        # Hiển thị tiến trình chờ
        elapsed = int(time.time() - start_time)
        print(f"  Đang chờ... ({elapsed}s)", end='\r')
        time.sleep(EMAIL_POLL_INTERVAL)

    print("\n⏰ Hết thời gian chờ email xác minh")
    return None
