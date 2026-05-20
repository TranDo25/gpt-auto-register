"""
Mô-đun tải cấu hình
Tải cấu hình từ tệp config.yaml, hỗ trợ cập nhật động

Cách sử dụng:
    from config import cfg

    # Truy cập các mục cấu hình
    total = cfg.registration.total_accounts
    email_domain = cfg.email.domain

    # Hoặc nhập trực tiếp các hằng số (tương thích với mã cũ)
    from config import TOTAL_ACCOUNTS, EMAIL_DOMAIN
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

# Cố gắng nhập yaml, nếu chưa cài đặt thì hiển thị thông báo
try:
    import yaml
except ImportError:
    print("❌ Thiếu phụ thuộc PyYAML, vui lòng cài đặt trước:")
    print("   pip install pyyaml")
    sys.exit(1)


# ==============================================================
# Định nghĩa các lớp dữ liệu cấu hình
# ==============================================================

@dataclass
class RegistrationConfig:
    """Cấu hình đăng ký"""
    total_accounts: int = 1
    min_age: int = 20
    max_age: int = 40


@dataclass
class EmailConfig:
    """Cấu hình dịch vụ email"""
    worker_url: str = ""
    domain: str = ""
    prefix_length: int = 10
    wait_timeout: int = 120
    poll_interval: int = 3
    admin_password: str = ""


@dataclass
class BrowserConfig:
    """Cấu hình trình duyệt"""
    max_wait_time: int = 600
    short_wait_time: int = 120
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


@dataclass
class PasswordConfig:
    """Cấu hình mật khẩu"""
    length: int = 16
    charset: str = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%"


@dataclass
class RetryConfig:
    """Cấu hình thử lại"""
    http_max_retries: int = 5
    http_timeout: int = 30
    error_page_max_retries: int = 5
    button_click_max_retries: int = 3


@dataclass
class BatchConfig:
    """Cấu hình đăng ký hàng loạt"""
    interval_min: int = 5
    interval_max: int = 15


@dataclass
class FilesConfig:
    """Cấu hình đường dẫn tệp"""
    accounts_file: str = "registered_accounts.txt"


@dataclass
class CreditCardConfig:
    """Cấu hình thẻ tín dụng"""
    number: str = ""
    expiry: str = ""
    expiry_month: str = ""
    expiry_year: str = ""
    cvc: str = ""


@dataclass
class PaymentConfig:
    """Cấu hình thanh toán"""
    credit_card: CreditCardConfig = field(default_factory=CreditCardConfig)


@dataclass
class AppConfig:
    """Cấu hình hoàn chỉnh của ứng dụng"""
    registration: RegistrationConfig = field(default_factory=RegistrationConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    password: PasswordConfig = field(default_factory=PasswordConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    batch: BatchConfig = field(default_factory=BatchConfig)
    files: FilesConfig = field(default_factory=FilesConfig)
    payment: PaymentConfig = field(default_factory=PaymentConfig)


# ==============================================================
# Trình tải cấu hình
# ==============================================================

class ConfigLoader:
    """
    Trình tải cấu hình
    Hỗ trợ tải cấu hình từ tệp YAML và hợp nhất các giá trị mặc định
    """

    # Đường dẫn tìm kiếm tệp cấu hình (theo thứ tự ưu tiên)
    CONFIG_FILES = [
        "config.yaml",
        "config.yml",
        "config.local.yaml",
        "config.local.yml",
    ]

    def __init__(self, config_path: Optional[str] = None):
        """
        Khởi tạo trình tải cấu hình

        Tham số:
            config_path: Chỉ định đường dẫn tệp cấu hình, nếu là None thì tự động tìm kiếm
        """
        self.config_path = config_path
        self.raw_config: Dict[str, Any] = {}
        self.config = AppConfig()

        self._load_config()

    def _find_config_file(self) -> Optional[Path]:
        """Tìm kiếm tệp cấu hình"""
        # Lấy thư mục chứa script
        base_dir = Path(__file__).parent

        for filename in self.CONFIG_FILES:
            config_file = base_dir / filename
            if config_file.exists():
                return config_file

        return None

    def _load_config(self) -> None:
        """Tải tệp cấu hình"""
        if self.config_path:
            config_file = Path(self.config_path)
        else:
            config_file = self._find_config_file()

        if config_file is None or not config_file.exists():
            print("⚠️ Không tìm thấy tệp cấu hình config.yaml")
            print("   Vui lòng sao chép config.example.yaml thành config.yaml và sửa đổi cấu hình")
            print("   Tiếp tục chạy với cấu hình mặc định...")
            return

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self.raw_config = yaml.safe_load(f) or {}

            self.config_path = str(config_file)
            print(f"📄 Đã tải tệp cấu hình: {config_file.name}")

            # Phân tích cấu hình thành các lớp dữ liệu
            self._parse_config()

        except yaml.YAMLError as e:
            print(f"❌ Lỗi định dạng tệp cấu hình: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Lỗi tải tệp cấu hình: {e}")
            sys.exit(1)

    def _parse_config(self) -> None:
        """Phân tích cấu hình thô thành các lớp dữ liệu"""
        # Cấu hình đăng ký
        if 'registration' in self.raw_config:
            reg = self.raw_config['registration']
            self.config.registration = RegistrationConfig(
                total_accounts=reg.get('total_accounts', 1),
                min_age=reg.get('min_age', 20),
                max_age=reg.get('max_age', 40)
            )

        # Cấu hình email
        if 'email' in self.raw_config:
            email = self.raw_config['email']
            self.config.email = EmailConfig(
                worker_url=email.get('worker_url', ''),
                domain=email.get('domain', ''),
                prefix_length=email.get('prefix_length', 10),
                wait_timeout=email.get('wait_timeout', 120),
                poll_interval=email.get('poll_interval', 3),
                admin_password=email.get('admin_password', '')
            )

        # Cấu hình trình duyệt
        if 'browser' in self.raw_config:
            browser = self.raw_config['browser']
            self.config.browser = BrowserConfig(
                max_wait_time=browser.get('max_wait_time', 600),
                short_wait_time=browser.get('short_wait_time', 120),
                user_agent=browser.get('user_agent', '')
            )

        # Cấu hình mật khẩu
        if 'password' in self.raw_config:
            pwd = self.raw_config['password']
            self.config.password = PasswordConfig(
                length=pwd.get('length', 16),
                charset=pwd.get('charset', '')
            )

        # Cấu hình thử lại
        if 'retry' in self.raw_config:
            retry = self.raw_config['retry']
            self.config.retry = RetryConfig(
                http_max_retries=retry.get('http_max_retries', 5),
                http_timeout=retry.get('http_timeout', 30),
                error_page_max_retries=retry.get('error_page_max_retries', 5),
                button_click_max_retries=retry.get('button_click_max_retries', 3)
            )

        # Cấu hình hàng loạt
        if 'batch' in self.raw_config:
            batch = self.raw_config['batch']
            self.config.batch = BatchConfig(
                interval_min=batch.get('interval_min', 5),
                interval_max=batch.get('interval_max', 15)
            )

        # Cấu hình tệp
        if 'files' in self.raw_config:
            files = self.raw_config['files']
            self.config.files = FilesConfig(
                accounts_file=files.get('accounts_file', 'registered_accounts.txt')
            )

        # Cấu hình thanh toán
        if 'payment' in self.raw_config:
            payment = self.raw_config['payment']
            self.config.payment = PaymentConfig(
                credit_card=CreditCardConfig(
                    number=payment.get('credit_card', {}).get('number', ''),
                    expiry=payment.get('credit_card', {}).get('expiry', ''),
                    expiry_month=payment.get('credit_card', {}).get('expiry_month', ''),
                    expiry_year=payment.get('credit_card', {}).get('expiry_year', ''),
                    cvc=payment.get('credit_card', {}).get('cvc', '')
                )
            )

    def reload(self) -> None:
        """Tải lại tệp cấu hình"""
        self._load_config()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Lấy giá trị cấu hình thô (hỗ trợ đường dẫn dấu chấm)

        Tham số:
            key: Khóa cấu hình, hỗ trợ đường dẫn được phân tách bằng dấu chấm, ví dụ: 'email.domain'
            default: Giá trị mặc định

        Trả về:
            Giá trị cấu hình hoặc giá trị mặc định
        """
        keys = key.split('.')
        value = self.raw_config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value


# ==============================================================
# Thực thể cấu hình toàn cục
# ==============================================================

# Tạo trình tải cấu hình toàn cục
_loader = ConfigLoader()

# Đối tượng cấu hình (khuyến nghị sử dụng)
cfg = _loader.config


# ==============================================================
# Xuất tương thích (giữ mã cũ tương thích)
# ==============================================================

# Cấu hình đăng ký
TOTAL_ACCOUNTS = cfg.registration.total_accounts
MIN_AGE = cfg.registration.min_age
MAX_AGE = cfg.registration.max_age

# Cấu hình email
EMAIL_WORKER_URL = cfg.email.worker_url
EMAIL_DOMAIN = cfg.email.domain
EMAIL_PREFIX_LENGTH = cfg.email.prefix_length
EMAIL_WAIT_TIMEOUT = cfg.email.wait_timeout
EMAIL_POLL_INTERVAL = cfg.email.poll_interval
EMAIL_ADMIN_PASSWORD = cfg.email.admin_password

# Cấu hình trình duyệt
MAX_WAIT_TIME = cfg.browser.max_wait_time
SHORT_WAIT_TIME = cfg.browser.short_wait_time
USER_AGENT = cfg.browser.user_agent

# Cấu hình mật khẩu
PASSWORD_LENGTH = cfg.password.length
PASSWORD_CHARS = cfg.password.charset

# Cấu hình thử lại
HTTP_MAX_RETRIES = cfg.retry.http_max_retries
HTTP_TIMEOUT = cfg.retry.http_timeout
ERROR_PAGE_MAX_RETRIES = cfg.retry.error_page_max_retries
BUTTON_CLICK_MAX_RETRIES = cfg.retry.button_click_max_retries

# Cấu hình hàng loạt
BATCH_INTERVAL_MIN = cfg.batch.interval_min
BATCH_INTERVAL_MAX = cfg.batch.interval_max

# Cấu hình tệp
TXT_FILE = cfg.files.accounts_file

# Cấu hình thanh toán (định dạng từ điển, tương thích với mã cũ)
CREDIT_CARD_INFO = {
    "number": cfg.payment.credit_card.number,
    "expiry": cfg.payment.credit_card.expiry,
    "expiry_month": cfg.payment.credit_card.expiry_month,
    "expiry_year": cfg.payment.credit_card.expiry_year,
    "cvc": cfg.payment.credit_card.cvc
}


# ==============================================================
# Hàm tiện ích
# ==============================================================

def reload_config() -> None:
    """
    Tải lại tệp cấu hình
    Lưu ý: Điều này sẽ không cập nhật các hằng số đã nhập, chỉ cập nhật đối tượng cfg
    """
    global cfg
    _loader.reload()
    cfg = _loader.config


def get_config() -> AppConfig:
    """Lấy đối tượng cấu hình hiện tại"""
    return cfg


def print_config_summary() -> None:
    """In tóm tắt cấu hình"""
    print("\n" + "=" * 50)
    print("📋 Tóm tắt cấu hình hiện tại")
    print("=" * 50)
    print(f"  Số lượng tài khoản đăng ký: {cfg.registration.total_accounts}")
    print(f"  Tên miền email: {cfg.email.domain}")
    print(f"  URL Worker: {cfg.email.worker_url[:30]}...")
    print(f"  Tệp lưu tài khoản: {cfg.files.accounts_file}")
    print(f"  Khoảng thời gian hàng loạt: {cfg.batch.interval_min}-{cfg.batch.interval_max}s")
    print("=" * 50 + "\n")


# In thông tin cấu hình một lần khi mô-đun được tải (tùy chọn)
if __name__ == "__main__":
    print_config_summary()
