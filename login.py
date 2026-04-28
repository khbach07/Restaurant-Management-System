import sys
import os
import pymysql
import pymysql.cursors
from PyQt5.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QFrame, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QCursor, QPainter, QPixmap, QColor

# =========================================================
# ROLE MAPPING: MySQL username → role
# Thêm user mới vào đây nếu cần
# =========================================================
ROLE_MAP = {
    'john_admin':   'admin',
    'mary_cashier': 'cashier',
    # Thêm waiter accounts ở đây, ví dụ:
    'peter_waiter': 'waiter',
}

# =========================================================
# MAISON DES RÊVES - LUXURY STAFF PORTAL
# DESIGN: MINIMALIST FLOAT UI (BASED ON REFERENCE IMAGE 2)
# =========================================================
class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        # 1. Tải ảnh nền trực tiếp vào bộ nhớ (Cách này chống lỗi 100%)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(current_dir, 'fine_dining1.jpg')
        self.bg_pixmap = QPixmap(image_path)
        
        self.initUI()

    # KỸ THUẬT VẼ ẢNH NỀN TUYỆT ĐỐI (Vượt qua mọi lỗi CSS)
    def paintEvent(self, event):
        painter = QPainter(self)

        if not self.bg_pixmap.isNull():
            scaled = self.bg_pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )

            # Cắt ảnh ra giữa (center crop)
            x = (scaled.width() - self.width()) // 2
            y = (scaled.height() - self.height()) // 2

            painter.drawPixmap(0, 0, scaled, x, y, self.width(), self.height())
            painter.fillRect(self.rect(), QColor(0, 0, 0, 120))  # overlay đen mờ
        else:
            painter.fillRect(self.rect(), QColor("#121212"))

    def initUI(self):
        # 1. Window Configuration
        self.setWindowTitle('Maison de Rêve - Staff Access')
        
        # Enable Fullscreen and remove window borders
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.showFullScreen() 

        # ---------------------------------------------------------
        # MAIN LAYOUT: 60-40 SPLIT SCREEN VỚI LỀ PHẢI
        # ---------------------------------------------------------
        main_layout = QHBoxLayout(self)
        
        # ĐÂY CHÍNH LÀ ĐIỂM NHẤN: Chừa lề phải 60px, lề trên/dưới 30px 
        # Để khung Login lơ lửng, hở nền ảnh ra ngoài rìa!
        main_layout.setContentsMargins(0, 30, 60, 30) 
        main_layout.setSpacing(0)

        # LEFT SIDE: Không gian trống 65% để nhìn thấy ảnh
        left_space = QWidget()
        left_space.setStyleSheet("background: transparent;")
        main_layout.addWidget(left_space, stretch=65) 

        # RIGHT SIDE: Khung Login nổi 35%
        right_panel = QFrame()
        right_panel.setObjectName("LoginPanel")
        
        # 90% Opacity White Background + Bo góc Floating
        right_panel.setStyleSheet("""
            QFrame#LoginPanel {
                background-color: rgba(255, 255, 255, 230); 
                border-radius: 20px; /* Bo góc mềm mại cho Floating Panel */
            }
        """)
        main_layout.addWidget(right_panel, stretch=35) 

        # ---------------------------------------------------------
        # LOGIN FORM LAYOUT (LEFT-ALIGNED, VERTICALLY CENTERED)
        # ---------------------------------------------------------
        form_layout = QVBoxLayout()
        # Dãn cách 2 bên để form không bị chạm viền khung trắng
        form_layout.setContentsMargins(70, 0, 70, 0) 
        right_panel.setLayout(form_layout)

        # Ép nội dung ra giữa chiều dọc
        form_layout.addStretch()

        # --- 1. TITLE & SUBTITLE ---
        lbl_brand = QLabel("Maison des Rêves")
        lbl_brand.setFont(QFont('Montserrat', 38, QFont.Bold))
        lbl_brand.setStyleSheet("color: #D32F2F; background: transparent;") # Đỏ sậm luxury
        lbl_brand.setAlignment(Qt.AlignLeft)

        lbl_subtitle = QLabel("Please login to your account")
        lbl_subtitle.setFont(QFont('Segoe UI', 12, QFont.Bold))
        lbl_subtitle.setStyleSheet("color: #666666; background: transparent; margin-top: 5px;") 
        lbl_subtitle.setAlignment(Qt.AlignLeft)

        form_layout.addWidget(lbl_brand)
        form_layout.addWidget(lbl_subtitle)
        
        form_layout.addSpacing(85) 

        # --- 2. INPUT FIELDS (AIRY UNDERLINE STYLE) ---
        input_style = """
            QLineEdit {
                background-color: transparent;
                border: none;
                border-bottom: 2px solid #DDDDDD; /* Đường kẻ Xám nhạt tinh tế */
                padding: 5px 0px 10px 0px; 
                font-family: 'Segoe UI', Arial;
                font-size: 16px;
                color: #333333;
            }
            QLineEdit:focus {
                border-bottom: 2px solid #D32F2F; /* Đỏ khi click vào */
            }
        """

        label_style = "color: #999999; font-family: 'Segoe UI'; font-weight: bold; font-size: 16px; background: transparent;"

        # USERNAME FIELD
        lbl_user = QLabel("User Name")
        lbl_user.setStyleSheet(label_style)
        self.txt_username = QLineEdit()
        self.txt_username.setStyleSheet(input_style)

        form_layout.addWidget(lbl_user)
        form_layout.addSpacing(10)
        form_layout.addWidget(self.txt_username)
        
        form_layout.addSpacing(35) 

        # PASSWORD FIELD
        lbl_pass = QLabel("Password")
        lbl_pass.setStyleSheet(label_style)
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setStyleSheet(input_style)

        form_layout.addWidget(lbl_pass)
        form_layout.addSpacing(10)
        form_layout.addWidget(self.txt_password)

        form_layout.addSpacing(75) 

        # --- 3. LOGIN BUTTON (STRETCHY PILL-SHAPE) ---
        self.btn_login = QPushButton("Login")
        self.btn_login.setCursor(QCursor(Qt.PointingHandCursor))
        
        self.btn_login.setFixedHeight(52) 
        self.btn_login.setStyleSheet("""
            QPushButton {
                background-color: #D32F2F; 
                color: #FFFFFF;
                border: none;
                border-radius: 26px; /* Bo góc viên thuốc */
                font-family: 'Montserrat', 'Segoe UI';
                font-size: 16px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background-color: #B71C1C; 
            }
        """)
        self.btn_login.clicked.connect(self.handle_login)

        # Nút tự động Stretch dãn ngang bằng ô nhập liệu
        form_layout.addWidget(self.btn_login)

        # Ép nội dung ra giữa chiều dọc
        form_layout.addStretch()

    # ---------------------------------------------------------
    # DATABASE AUTHENTICATION LOGIC
    # ---------------------------------------------------------
    def handle_login(self):
        user = self.txt_username.text().strip()
        pwd  = self.txt_password.text().strip()

        if not user or not pwd:
            QMessageBox.warning(self, "Validation Error", "Please enter both staff credentials.")
            return

        # Xác định role từ username trước khi thử kết nối DB
        role = ROLE_MAP.get(user)
        if role is None:
            QMessageBox.critical(self, "Access Denied",
                                 f"Username '{user}' is not registered in the system.")
            return

        try:
            conn = pymysql.connect(
                host='localhost',
                database='restaurant_db',
                user=user,
                password=pwd,
                connect_timeout=5
            )
            conn.close()

            # -----------------------------------------------
            # ROUTING: Mở đúng cửa sổ dựa theo role
            # -----------------------------------------------
            if role == 'admin':
                from manager import ManagerDashboard, db_manager as mgr_db
                self.next_window = ManagerDashboard()
                self.next_window.showMaximized()
            else:
                # cashier hoặc waiter đều vào DashboardWindow
                from dashboard import DashboardWindow, db_manager as dash_db
                self.next_window = DashboardWindow()
                self.next_window.showFullScreen()

            self.close()

        except pymysql.err.OperationalError as err:
            QMessageBox.critical(self, "Access Denied",
                                 f"Invalid credentials or connection error.\n{err}")

    # NHẤN NÚT ESC ĐỂ THOÁT APP
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

# =========================================================
# APPLICATION ENTRY POINT
# =========================================================
if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True) 
    
    app = QApplication(sys.argv)
    login_screen = LoginWindow()
    login_screen.show()
    sys.exit(app.exec_())