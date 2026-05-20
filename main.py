"""
Script tự động đăng ký tài khoản ChatGPT
Điểm vào chương trình chính

Cách sử dụng:
    1. Sửa đổi cấu hình trong config.py
    2. Chạy: python main.py

Cài đặt phụ thuộc:
    pip install undetected-chromedriver selenium requests

Chức năng:
    - Tự động tạo email tạm thời (dựa trên cloudflare_temp_email)
    - Tự động hoàn thành quy trình đăng ký ChatGPT
    - Tự động trích xuất mã xác minh
    - Hỗ trợ đăng ký hàng loạt
"""

import time
import random

from config import (
    TOTAL_ACCOUNTS,
    BATCH_INTERVAL_MIN,
    BATCH_INTERVAL_MAX
)
from utils import generate_random_password, save_to_txt, update_account_status
from email_service import create_temp_email, wait_for_verification_email
from browser import (
    create_driver,
    fill_signup_form,
    enter_verification_code,
    fill_profile_info,
    subscribe_plus_trial,
    cancel_subscription
)


def register_one_account(monitor_callback=None):
    """
    Đăng ký một tài khoản
    :param monitor_callback: Hàm gọi lại func(driver, step_name), dùng để chụp ảnh màn hình và kiểm tra gián đoạn

    Trả về:
        tuple: (email, mật khẩu, có thành công không)
    """
    driver = None
    email = None
    password = None
    success = False

    # Hàm trợ giúp: thực hiện gọi lại
    def _report(step_name):
        if monitor_callback and driver:
            monitor_callback(driver, step_name)

    try:
        # 1. Tạo email tạm thời
        print("📧 Đang tạo email tạm thời...")
        email, jwt_token = create_temp_email()
        if not email:
            print("❌ Lỗi tạo email, dừng đăng ký")
            return None, None, False

        # 2. Tạo mật khẩu ngẫu nhiên
        password = generate_random_password()

        # 3. Khởi tạo trình duyệt
        driver = create_driver(headless=False)
        _report("init_browser")

        # 4. Mở trang đăng ký
        url = "https://chat.openai.com/chat"
        print(f"🌐 Đang mở {url}...")
        driver.get(url)
        time.sleep(3)
        _report("open_page")

        # 5. Điền biểu mẫu đăng ký (email và mật khẩu)
        if not fill_signup_form(driver, email, password):
            print("❌ Lỗi điền biểu mẫu đăng ký")
            return email, password, False
        _report("fill_form")

        # 6. Chờ email xác minh
        time.sleep(5)
        verification_code = wait_for_verification_email(jwt_token)

        # Nếu không tự động nhận được mã xác minh, yêu cầu nhập thủ công
        if not verification_code:
            print("⚠️ Không tự động nhận được mã xác minh, cố gắng yêu cầu người dùng nhập...")
            # Có thể mở rộng gọi lại nhập thủ công ở đây, tạm thời bỏ qua

        if not verification_code:
            print("❌ Không nhận được mã xác minh, dừng đăng ký")
            return email, password, False

        # 7. Nhập mã xác minh
        if not enter_verification_code(driver, verification_code):
            print("❌ Lỗi nhập mã xác minh")
            return email, password, False
        _report("enter_code")

        # 8. Điền thông tin cá nhân
        if not fill_profile_info(driver):
            print("❌ Lỗi điền thông tin cá nhân")
            return email, password, False
        _report("fill_profile")

        # 9. Lưu thông tin tài khoản (đăng ký thành công)
        save_to_txt(email, password, "Đã đăng ký")

        # 10. Hoàn thành đăng ký
        print("\n" + "=" * 50)
        print("🎉 Đăng ký thành công!")
        print(f"   Email: {email}")
        print(f"   Mật khẩu: {password}")
        print("=" * 50)

        success = True
        print("⏳ Chờ trang ổn định...")
        time.sleep(5)
        _report("registered")

        # # 11. Kích hoạt Plus trial (đã vô hiệu hóa - chỉ đăng ký tài khoản thường)
        # print("\n" + "-" * 30)
        # print("🚀 Bắt đầu kích hoạt Plus trial")
        # print("-" * 30)
        #
        # if subscribe_plus_trial(driver):
        #     print("🎉 Plus trial kích hoạt thành công!")
        #     update_account_status(email, "Đã kích hoạt Plus")
        #     _report("plus_subscribed")
        #
        #     # 12. Hủy đăng ký (ngăn chặn bị trừ tiền)
        #     print("\n" + "-" * 30)
        #     print("🛑 Đang hủy đăng ký...")
        #     print("-" * 30)
        #
        #     time.sleep(5)
        #     if cancel_subscription(driver):
        #         print("🎉 Đăng ký đã hủy thành công, quy trình hoàn hảo!")
        #         update_account_status(email, "Đã hủy đăng ký")
        #         _report("subscription_cancelled")
        #     else:
        #         print("⚠️ Lỗi hủy đăng ký, vui lòng hủy thủ công!")
        #         update_account_status(email, "Lỗi hủy đăng ký")
        #         _report("cancel_failed")
        # else:
        #     print("⚠️ Lỗi kích hoạt Plus trial")
        #     update_account_status(email, "Lỗi kích hoạt Plus")
        #     _report("plus_failed")
        #
        # success = True
        # time.sleep(5)
        
    except InterruptedError:
        print("🛑 Tác vụ đã bị người dùng gián đoạn")
        if email: update_account_status(email, "Người dùng gián đoạn")
        return email, password, False

    except Exception as e:
        print(f"❌ Lỗi xảy ra: {e}")
        # Ngay cả khi có lỗi cũng lưu thông tin tài khoản đã có (để dễ dàng kiểm tra)
        if email and password:
            update_account_status(email, f"Lỗi: {str(e)[:50]}")

    finally:
        if driver:
            print("🔒 Đang đóng trình duyệt...")
            driver.quit()

    return email, password, success
    



def run_batch():
    """
    Đăng ký hàng loạt tài khoản
    """
    print("\n" + "=" * 60)
    print(f"🚀 Bắt đầu đăng ký hàng loạt, mục tiêu: {TOTAL_ACCOUNTS}")
    print("=" * 60 + "\n")

    print("\n⚠️  Tuyên bố miễn trừ: Dự án này chỉ dùng cho mục đích học tập và nghiên cứu. Vui lòng không sử dụng cho mục đích thương mại hoặc hoạt động vi phạm.")
    print("⚠️  Người sử dụng cần tự chịu trách nhiệm về mọi hậu quả do sử dụng không đúng cách.\n")
    time.sleep(2)

    success_count = 0
    fail_count = 0
    registered_accounts = []

    for i in range(TOTAL_ACCOUNTS):
        print("\n" + "#" * 60)
        print(f"📝 Đang đăng ký tài khoản thứ {i + 1}/{TOTAL_ACCOUNTS}")
        print("#" * 60 + "\n")

        email, password, success = register_one_account()

        if success:
            success_count += 1
            registered_accounts.append((email, password))
        else:
            fail_count += 1

        # Hiển thị tiến trình
        print("\n" + "-" * 40)
        print(f"📊 Tiến trình hiện tại: {i + 1}/{TOTAL_ACCOUNTS}")
        print(f"   ✅ Thành công: {success_count}")
        print(f"   ❌ Thất bại: {fail_count}")
        print("-" * 40)

        # Nếu còn tài khoản tiếp theo, chờ thời gian ngẫu nhiên
        if i < TOTAL_ACCOUNTS - 1:
            wait_time = random.randint(BATCH_INTERVAL_MIN, BATCH_INTERVAL_MAX)
            print(f"\n⏳ Chờ {wait_time} giây trước khi đăng ký tiếp theo...")
            time.sleep(wait_time)

    # Thống kê cuối cùng
    print("\n" + "=" * 60)
    print("🏁 Đăng ký hàng loạt hoàn thành")
    print("=" * 60)
    print(f"   Tổng cộng: {TOTAL_ACCOUNTS}")
    print(f"   ✅ Thành công: {success_count}")
    print(f"   ❌ Thất bại: {fail_count}")

    if registered_accounts:
        print("\n📋 Các tài khoản đã đăng ký thành công:")
        for email, password in registered_accounts:
            print(f"   - {email}")

    print("=" * 60)


if __name__ == "__main__":
    run_batch()
