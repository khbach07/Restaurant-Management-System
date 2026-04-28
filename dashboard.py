print("1. Bắt đầu khởi động App...")
import sys
import os
import re
import datetime

print("2. Đang nạp PyQt5...")
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect,
                             QScrollArea, QGridLayout, QStackedWidget, QMessageBox,
                             QLineEdit, QFormLayout, QSpinBox, QComboBox, QCalendarWidget,
                             QSpacerItem, QSizePolicy, QDialog, QMenu)
from PyQt5.QtCore import Qt, pyqtSignal, QDate, QSize
from PyQt5.QtGui import QFont, QCursor, QColor, QPixmap, QTextCharFormat, QPainter, QPainterPath
from dotenv import load_dotenv
print("3. Đang nạp QtAwesome (Icon)...")
import qtawesome as qta

print("4. Đang nạp PyMySQL (Giải pháp chống Crash)...")
import pymysql
import pymysql.cursors

print("5. Tuyệt vời! Mọi thứ an toàn. Đang dựng giao diện...")

MODERN_FONT = "'Nunito', 'Segoe UI', sans-serif"

# ==========================================
# GIAO DIỆN SCROLLBAR HIỆN ĐẠI
# ==========================================
MODERN_SCROLL = """
QScrollArea { border: none; background-color: transparent; }
QScrollBar:vertical {
    border: none; background: #F3F4F6; width: 10px; margin: 0px; border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #D1D5DB; min-height: 30px; border-radius: 5px;
}
QScrollBar::handle:vertical:hover { background: #9CA3AF; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
"""

load_dotenv()

# ==========================================
# 0. DATABASE MANAGER 
# ==========================================
class DatabaseManager:
    def __init__(self):
        self.config = {
            'host':     os.getenv('DB_HOST',     'localhost'),
            'user':     os.getenv('DB_USER',     'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME',     'restaurant_db')
        }
        self.aes_key = 'RestaurantSecretKey2026'

    def connect(self):
        return pymysql.connect(**self.config)

    def get_tables_status(self):
        try:
            conn = self.connect()
            cursor = conn.cursor(pymysql.cursors.DictCursor) 
            cursor.execute("SELECT TableID, Status FROM DiningTables")
            statuses = {row['TableID']: row['Status'] for row in cursor.fetchall()}
            conn.close()
            return statuses
        except Exception as e: return {}

    def get_customer_from_reservation(self, table_id):
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT CustomerID FROM Reservations WHERE TableID = %s ORDER BY DateTime DESC LIMIT 1", (table_id,))
            res = cursor.fetchone()
            conn.close()
            return res[0] if res else None
        except: return None

    def update_table_status(self, table_id, status):
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("UPDATE DiningTables SET Status = %s WHERE TableID = %s", (status, table_id))
            conn.commit()
            conn.close()
            return True
        except: return False

    # THÊM: LẤY THÔNG TIN RESERVATION
    def get_reservation_details(self, table_id):
        try:
            conn = self.connect()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            query = f"""
                SELECT r.ReservationID, c.CustomerName, 
                       CAST(AES_DECRYPT(UNHEX(c.PhoneNumber), '{self.aes_key}') AS CHAR) as Phone, 
                       c.Address, r.DateTime, r.GuestCount
                FROM Reservations r
                JOIN Customers c ON r.CustomerID = c.CustomerID
                WHERE r.TableID = %s ORDER BY r.DateTime DESC LIMIT 1
            """
            cursor.execute(query, (table_id,))
            res = cursor.fetchone()
            conn.close()
            return res
        except: return None

    # THÊM: LẤY THÔNG TIN KHÁCH HÀNG BẰNG SĐT (AUTO-FILL)
    def get_customer_by_phone(self, phone):
        try:
            conn = self.connect()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            query = f"SELECT CustomerName, Address FROM Customers WHERE CAST(AES_DECRYPT(UNHEX(PhoneNumber), '{self.aes_key}') AS CHAR) = %s"
            cursor.execute(query, (phone,))
            res = cursor.fetchone()
            conn.close()
            return res
        except: return None

    # THÊM: XÓA RESERVATION
    def cancel_reservation(self, table_id):
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Reservations WHERE TableID = %s", (table_id,))
            cursor.execute("UPDATE DiningTables SET Status = 'Available' WHERE TableID = %s", (table_id,))
            conn.commit()
            conn.close()
            return True
        except: return False

    # THÊM: CẬP NHẬT RESERVATION (EDIT)
    def update_reservation_details(self, res_id, name, phone, address, date_time_str, guest_count):
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT CustomerID FROM Reservations WHERE ReservationID = %s", (res_id,))
            cust_id = cursor.fetchone()[0]
            cursor.execute(f"UPDATE Customers SET CustomerName=%s, PhoneNumber=HEX(AES_ENCRYPT(%s, '{self.aes_key}')), Address=%s WHERE CustomerID=%s", 
                           (name, phone, address, cust_id))
            cursor.execute("UPDATE Reservations SET DateTime=%s, GuestCount=%s WHERE ReservationID=%s", 
                           (date_time_str, guest_count, res_id))
            conn.commit()
            conn.close()
            return True
        except: return False

    # THÊM: SEARCH KHÁCH BẰNG SĐT
    def smart_search_reservation(self, keyword):
        try:
            conn = self.connect()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Kỹ thuật tìm kiếm LIKE: Thêm % ở 2 đầu để tìm 1, 2 chữ bất kỳ trong tên
            search_term = f"%{keyword}%"
            
            query = f"""
                SELECT r.TableID, c.CustomerName, 
                       CAST(AES_DECRYPT(UNHEX(c.PhoneNumber), '{self.aes_key}') AS CHAR) as Phone
                FROM Reservations r
                JOIN Customers c ON r.CustomerID = c.CustomerID
                WHERE CAST(AES_DECRYPT(UNHEX(c.PhoneNumber), '{self.aes_key}') AS CHAR) LIKE %s
                   OR c.CustomerName LIKE %s
                ORDER BY r.DateTime DESC
            """
            cursor.execute(query, (search_term, search_term))
            res = cursor.fetchall()
            conn.close()
            return res # Trả về 1 mảng danh sách các kết quả tìm được
        except Exception as e:
            print("DB Lỗi (smart_search):", e)
            return []

    def save_reservation(self, name, phone, address, date_time_str, guest_count, table_id):
        try:
            conn = self.connect()
            cursor = conn.cursor()
            query_check = f"SELECT CustomerID FROM Customers WHERE CAST(AES_DECRYPT(UNHEX(PhoneNumber), '{self.aes_key}') AS CHAR) = %s"
            cursor.execute(query_check, (phone,))
            result = cursor.fetchone()
            if result:
                cust_id = result[0]
                if address.strip() != "":
                    cursor.execute("UPDATE Customers SET Address = %s WHERE CustomerID = %s", (address, cust_id))
            else:
                query_insert_cust = f"INSERT INTO Customers (CustomerName, PhoneNumber, Address) VALUES (%s, HEX(AES_ENCRYPT(%s, '{self.aes_key}')), %s)"
                cursor.execute(query_insert_cust, (name, phone, address))
                cust_id = cursor.lastrowid
            cursor.execute("CALL ConfirmReservation(%s, %s, %s, %s)", (cust_id, table_id, date_time_str, guest_count))
            conn.commit()
            conn.close()
            return True
        except: return False

    def load_table_order(self, table_id):
        try:
            conn = self.connect()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT InvoiceID FROM Invoices WHERE TableID = %s AND PaymentDate IS NULL", (table_id,))
            inv = cursor.fetchone()
            if not inv: 
                conn.close()
                return {}
            cursor.execute("SELECT m.DishName, m.Category, od.Quantity, od.UnitPrice FROM OrderDetails od JOIN MenuItems m ON od.DishID = m.DishID WHERE od.InvoiceID = %s", (inv['InvoiceID'],))
            items = {}
            for row in cursor.fetchall():
                img = "default.jpg"
                if "Steak" in row['DishName']: img = "wagyu.jpg"
                elif "Bisque" in row['DishName']: img = "lobster.jpg"
                elif "Pasta" in row['DishName']: img = "truffle.jpg"
                elif "Cheesecake" in row['DishName']: img = "cheesecake.jpg"
                elif "Wine" in row['DishName']: img = "wine.jpg"
                elif "Foie Gras" in row['DishName']: img = "foie_gras.jpg"
                elif "Wellington" in row['DishName']: img = "wellington.jpg"
                elif "Salmon" in row['DishName']: img = "salmon.jpg"
                elif "Tiramisu" in row['DishName']: img = "tiramisu.jpg"
                elif "Water" in row['DishName']: img = "water.jpg"
                
                items[row['DishName']] = {
                    'qty': row['Quantity'], 
                    'price': float(row['UnitPrice']), # FIX LỖI Ở ĐÂY: Ép kiểu Decimal thành Float
                    'img': img, 
                    'cat': row['Category']
                }
            conn.close()
            return items
        except Exception as e:
            print("DB Lỗi (load_table_order):", e)
            return {}

    def save_order_to_db(self, table_id, ordered_items):
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT InvoiceID FROM Invoices WHERE TableID = %s AND PaymentDate IS NULL", (table_id,))
            inv = cursor.fetchone()
            if inv:
                inv_id = inv[0]
                cursor.execute("DELETE FROM OrderDetails WHERE InvoiceID = %s", (inv_id,)) 
            else:
                cust_id = self.get_customer_from_reservation(table_id)
                if not cust_id:
                    cursor.execute("SELECT CustomerID FROM Customers LIMIT 1")
                    res = cursor.fetchone()
                    cust_id = res[0] if res else None
                cursor.execute("INSERT INTO Invoices (TotalAmount, PaymentDate, CustomerID, TableID) VALUES (0, NULL, %s, %s)", (cust_id, table_id))
                inv_id = cursor.lastrowid
            for dish_name, data in ordered_items.items():
                cursor.execute("SELECT DishID FROM MenuItems WHERE DishName = %s", (dish_name,))
                dish_id = cursor.fetchone()[0]
                cursor.execute("INSERT INTO OrderDetails (Quantity, UnitPrice, InvoiceID, DishID) VALUES (%s, %s, %s, %s)", (data['qty'], data['price'], inv_id, dish_id))
            cursor.execute("CALL GenerateBill(%s)", (inv_id,))
            conn.commit()
            conn.close()
            return True
        except: return False

    def process_checkout(self, table_id, ordered_items):
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT InvoiceID FROM Invoices WHERE TableID = %s AND PaymentDate IS NULL", (table_id,))
            inv_id = cursor.fetchone()[0]
            cursor.execute("UPDATE Invoices SET PaymentDate = NOW() WHERE InvoiceID = %s", (inv_id,))
            conn.commit()
            conn.close()
            return True
        except: return False
    
    
db_manager = DatabaseManager()

# ==========================================
# WIDGET POPUP HIỆN ĐẠI 
# ==========================================
class ModernPopup(QDialog):
    def __init__(self, title, message, icon_name="fa5s.check-circle", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 200)
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0)
        frame = QFrame(); frame.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 15px; border: 1px solid #E5E7EB; }")
        shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(20); shadow.setColor(QColor(0, 0, 0, 40)); shadow.setOffset(0, 5)
        frame.setGraphicsEffect(shadow)
        f_layout = QVBoxLayout(frame); f_layout.setContentsMargins(25, 25, 25, 25); f_layout.setSpacing(15)
        
        h_head = QHBoxLayout(); icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon(icon_name, color="#EF4444").pixmap(24, 24))
        icon_lbl.setStyleSheet("border: none; background: transparent;") # FIX VIỀN ICON Ở ĐÂY
        title_lbl = QLabel(title); title_lbl.setFont(QFont('Nunito', 16, QFont.Bold)); title_lbl.setStyleSheet("color: #111827; border: none;")
        
        h_head.addWidget(icon_lbl); h_head.addWidget(title_lbl); h_head.addStretch()
        msg_lbl = QLabel(message); msg_lbl.setWordWrap(True); msg_lbl.setFont(QFont('Nunito', 11)); msg_lbl.setStyleSheet("color: #4B5563; border: none;")
        btn_ok = QPushButton("Got it"); btn_ok.setCursor(QCursor(Qt.PointingHandCursor)); btn_ok.setFixedSize(100, 40)
        btn_ok.setStyleSheet("QPushButton { background-color: #EF4444; color: #FFFFFF; border: none; border-radius: 8px; font-weight: bold; font-family: 'Nunito'; font-size: 14px; } QPushButton:hover { background-color: #DC2626; }")
        btn_ok.clicked.connect(self.accept)
        
        f_layout.addLayout(h_head); f_layout.addWidget(msg_lbl); f_layout.addWidget(btn_ok, alignment=Qt.AlignRight)
        layout.addWidget(frame)

class ModernConfirmPopup(QDialog):
    def __init__(self, title, message, icon_name="fa5s.exclamation-triangle", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 200)
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0)
        frame = QFrame(); frame.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 15px; border: 1px solid #E5E7EB; }")
        shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(20); shadow.setColor(QColor(0, 0, 0, 40)); shadow.setOffset(0, 5)
        frame.setGraphicsEffect(shadow)
        f_layout = QVBoxLayout(frame); f_layout.setContentsMargins(25, 25, 25, 25); f_layout.setSpacing(15)
        
        h_head = QHBoxLayout(); icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon(icon_name, color="#EF4444").pixmap(24, 24))
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        title_lbl = QLabel(title); title_lbl.setFont(QFont('Nunito', 16, QFont.Bold)); title_lbl.setStyleSheet("color: #111827; border: none;")
        
        h_head.addWidget(icon_lbl); h_head.addWidget(title_lbl); h_head.addStretch()
        msg_lbl = QLabel(message); msg_lbl.setWordWrap(True); msg_lbl.setFont(QFont('Nunito', 11)); msg_lbl.setStyleSheet("color: #4B5563; border: none;")
        
        btn_layout = QHBoxLayout()
        btn_no = QPushButton("No"); btn_no.setCursor(QCursor(Qt.PointingHandCursor)); btn_no.setFixedSize(100, 40)
        btn_no.setStyleSheet("QPushButton { background-color: transparent; color: #4B5563; border: 1px solid #D1D5DB; border-radius: 8px; font-weight: bold; font-family: 'Nunito'; font-size: 14px; } QPushButton:hover { background-color: #F3F4F6; }")
        btn_no.clicked.connect(self.reject)
        
        btn_yes = QPushButton("Yes"); btn_yes.setCursor(QCursor(Qt.PointingHandCursor)); btn_yes.setFixedSize(100, 40)
        btn_yes.setStyleSheet("QPushButton { background-color: #EF4444; color: #FFFFFF; border: none; border-radius: 8px; font-weight: bold; font-family: 'Nunito'; font-size: 14px; } QPushButton:hover { background-color: #DC2626; }")
        btn_yes.clicked.connect(self.accept)
        
        btn_layout.addStretch(); btn_layout.addWidget(btn_no); btn_layout.addWidget(btn_yes)
        f_layout.addLayout(h_head); f_layout.addWidget(msg_lbl); f_layout.addLayout(btn_layout)
        layout.addWidget(frame)

# ==========================================
# 1. MENU CARD WIDGET
# ==========================================
class MenuCard(QFrame):
    quantityChanged = pyqtSignal(str, int, float, str, str) 
    def __init__(self, name, price, image_filename, cat="Fine Dining"):
        super().__init__()
        self.dish_name = name; self.dish_price = float(price); self.image_filename = image_filename; self.cat = cat; self.quantity = 0
        self.setFixedSize(260, 380); self.setObjectName("MenuCard")
        shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(25); shadow.setColor(QColor(0, 0, 0, 20)); shadow.setOffset(0, 8); self.setGraphicsEffect(shadow)
        layout = QVBoxLayout(); layout.setContentsMargins(15, 15, 15, 25); layout.setSpacing(15)
        self.top_stack = QStackedWidget(); self.top_stack.setFixedSize(230, 230)
        self.img_label = QLabel(); self.img_label.setStyleSheet("background-color: #F5F5F5; border-radius: 12px;"); self.img_label.setAlignment(Qt.AlignCenter)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        pixmap = QPixmap(os.path.join(current_dir, 'menu_images', image_filename))
        if not pixmap.isNull(): self.img_label.setPixmap(pixmap.scaled(230, 230, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        self.top_stack.addWidget(self.img_label)
        self.counter_container = QFrame(); self.counter_container.setStyleSheet("background-color: transparent;")
        counter_layout = QVBoxLayout(); counter_layout.setAlignment(Qt.AlignCenter)
        self.pill_frame = QFrame(); self.pill_frame.setFixedSize(160, 50); self.pill_frame.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 25px; }")
        pill_layout = QHBoxLayout(self.pill_frame); pill_layout.setContentsMargins(10, 0, 10, 0)
        self.btn_minus = QPushButton(qta.icon("fa5s.minus", color="#333"), ""); self.btn_minus.setFixedSize(30, 30); self.btn_minus.setStyleSheet("border: none; font-weight: bold; font-size: 18px;"); self.btn_minus.setCursor(QCursor(Qt.PointingHandCursor)); self.btn_minus.clicked.connect(self.decrease_qty)
        self.lbl_qty = QLabel("1"); self.lbl_qty.setFont(QFont('Nunito', 16, QFont.Bold)); self.lbl_qty.setStyleSheet(f"color: #333333; font-family: {MODERN_FONT};"); self.lbl_qty.setAlignment(Qt.AlignCenter)
        self.btn_plus = QPushButton(qta.icon("fa5s.plus", color="#333"), ""); self.btn_plus.setFixedSize(30, 30); self.btn_plus.setStyleSheet("border: none; font-weight: bold; font-size: 18px;"); self.btn_plus.setCursor(QCursor(Qt.PointingHandCursor)); self.btn_plus.clicked.connect(self.increase_qty)
        pill_layout.addWidget(self.btn_minus); pill_layout.addWidget(self.lbl_qty); pill_layout.addWidget(self.btn_plus)
        counter_layout.addWidget(self.pill_frame); self.counter_container.setLayout(counter_layout); self.top_stack.addWidget(self.counter_container)
        self.name_lbl = QLabel(self.dish_name); self.name_lbl.setFont(QFont('Nunito', 13, QFont.Bold)); self.name_lbl.setAlignment(Qt.AlignCenter); self.name_lbl.setWordWrap(True)
        self.price_lbl = QLabel(f"{self.dish_price:,.0f} VND"); self.price_lbl.setFont(QFont('Nunito', 11, QFont.Bold)); self.price_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.top_stack); layout.addStretch(); layout.addWidget(self.name_lbl); layout.addWidget(self.price_lbl); self.setLayout(layout)
        self.update_theme()

    def set_quantity(self, qty): self.quantity = qty; self.update_theme()
    def update_theme(self):
        if self.quantity > 0:
            self.setStyleSheet("QFrame#MenuCard { background-color: #3B3B3B; border-radius: 15px; }"); self.name_lbl.setStyleSheet(f"color: #FFFFFF; font-family: {MODERN_FONT};"); self.price_lbl.setStyleSheet(f"color: #BDBDBD; font-family: {MODERN_FONT};"); self.top_stack.setCurrentIndex(1); self.lbl_qty.setText(str(self.quantity))
        else:
            self.setStyleSheet("QFrame#MenuCard { background-color: #FFFFFF; border-radius: 15px; }"); self.name_lbl.setStyleSheet(f"color: #333333; font-family: {MODERN_FONT};"); self.price_lbl.setStyleSheet(f"color: #EF4444; font-family: {MODERN_FONT};"); self.top_stack.setCurrentIndex(0)
    def mousePressEvent(self, event):
        if self.quantity == 0: self.quantity = 1; self.update_theme(); self.quantityChanged.emit(self.dish_name, self.quantity, self.dish_price, self.image_filename, self.cat)
    def increase_qty(self): self.quantity += 1; self.update_theme(); self.quantityChanged.emit(self.dish_name, self.quantity, self.dish_price, self.image_filename, self.cat)
    def decrease_qty(self):
        if self.quantity > 0: self.quantity -= 1; self.update_theme(); self.quantityChanged.emit(self.dish_name, self.quantity, self.dish_price, self.image_filename, self.cat)

# ==========================================
# 2. MENU WINDOW (ORDERING)
# ==========================================
class MenuWindow(QWidget):
    def __init__(self, table_id, dashboard_parent):
        super().__init__()
        self.table_id = table_id; self.dashboard_parent = dashboard_parent
        self.ordered_items = db_manager.load_table_order(self.table_id) 
        self.initUI()

    def round_pixmap(self, pixmap, radius):
        rounded = QPixmap(pixmap.size()); rounded.fill(Qt.transparent)
        painter = QPainter(rounded); painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath(); path.addRoundedRect(0, 0, pixmap.width(), pixmap.height(), radius, radius)
        painter.setClipPath(path); painter.drawPixmap(0, 0, pixmap); painter.end()
        return rounded

    def initUI(self):
        self.setStyleSheet("background-color: #F8F9FA;")
        main_h_layout = QHBoxLayout(self); main_h_layout.setContentsMargins(0, 0, 0, 0); main_h_layout.setSpacing(0)

        left_widget = QWidget(); left_layout = QVBoxLayout(left_widget); left_layout.setContentsMargins(50, 40, 50, 40)
        header_layout = QHBoxLayout(); self.btn_back = QPushButton(qta.icon('fa5s.arrow-left', color='#EF4444'), "")
        self.btn_back.setIconSize(QSize(24, 24)); self.btn_back.setFixedSize(50, 50); self.btn_back.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_back.setStyleSheet("border: none; background: transparent;"); self.btn_back.clicked.connect(self.go_back)
        lbl_title = QLabel(f"<span style='color: #BDBDBD;'>Dining Areas &nbsp;&nbsp;&gt;&nbsp;&nbsp;</span> <span style='color: #333333;'>Table {self.table_id:02d}</span>")
        lbl_title.setFont(QFont('Nunito', 22, QFont.Bold)); lbl_title.setStyleSheet(f"font-family: {MODERN_FONT};")
        header_layout.addWidget(self.btn_back); header_layout.addSpacing(20); header_layout.addWidget(lbl_title); header_layout.addStretch()
        left_layout.addLayout(header_layout); left_layout.addSpacing(30)

        menu_items = [
            {'name': 'Wagyu Ribeye Steak', 'price': 1500000, 'img': 'wagyu.jpg', 'cat': 'Main Course'}, {'name': 'Lobster Bisque', 'price': 450000, 'img': 'lobster.jpg', 'cat': 'Appetizer'},
            {'name': 'Truffle Pasta', 'price': 650000, 'img': 'truffle.jpg', 'cat': 'Main Course'}, {'name': 'Basque Burnt Cheesecake', 'price': 250000, 'img': 'cheesecake.jpg', 'cat': 'Dessert'},
            {'name': 'Bordeaux Red Wine', 'price': 1200000, 'img': 'wine.jpg', 'cat': 'Beverage'}, {'name': 'Pan-Seared Foie Gras', 'price': 850000, 'img': 'foie_gras.jpg', 'cat': 'Appetizer'},
            {'name': 'Beef Wellington', 'price': 1800000, 'img': 'wellington.jpg', 'cat': 'Main Course'}, {'name': 'Grilled Salmon', 'price': 180000, 'img': 'salmon.jpg', 'cat': 'Main Course'},
            {'name': 'Classic Tiramisu', 'price': 150000, 'img': 'tiramisu.jpg', 'cat': 'Dessert'}, {'name': 'Sparkling Water', 'price': 100000, 'img': 'water.jpg', 'cat': 'Beverage'}
        ]
        scroll_area = QScrollArea(); scroll_area.setWidgetResizable(True); scroll_area.setStyleSheet(MODERN_SCROLL)
        grid_widget = QWidget(); grid_widget.setStyleSheet("background-color: transparent;")
        grid_layout = QGridLayout(grid_widget); grid_layout.setSpacing(80); grid_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        row, col = 0, 0
        for item in menu_items:
            card = MenuCard(item['name'], item['price'], item['img'], item['cat'])
            if item['name'] in self.ordered_items: card.set_quantity(self.ordered_items[item['name']]['qty'])
            card.quantityChanged.connect(self.track_order); grid_layout.addWidget(card, row, col)
            col += 1
            if col > 3: col = 0; row += 1
        scroll_area.setWidget(grid_widget); left_layout.addWidget(scroll_area); main_h_layout.addWidget(left_widget, stretch=1)

        self.sidebar_widget = QFrame(); self.sidebar_widget.setObjectName("Sidebar")
        self.sidebar_widget.setStyleSheet("#Sidebar { background-color: #FFFFFF; border-left: 1px solid #E5E7EB; }"); self.sidebar_widget.setFixedWidth(460)
        self.sidebar_layout = QVBoxLayout(self.sidebar_widget); self.sidebar_layout.setContentsMargins(30, 40, 30, 40); self.sidebar_layout.setSpacing(15)
        s_header = QHBoxLayout(); s_title = QLabel("Order Details"); s_title.setFont(QFont('Nunito', 22, QFont.Bold)); s_title.setStyleSheet("color: #111827; border: none; background: transparent;")
        s_header.addWidget(s_title); s_header.addStretch(); self.sidebar_layout.addLayout(s_header)
        self.lbl_table_info = QLabel(f"Table {self.table_id:02d} - Dine In"); self.lbl_table_info.setFont(QFont('Nunito', 11, QFont.Bold)); self.lbl_table_info.setStyleSheet("color: #4B5563; border: none; background: transparent;")
        self.sidebar_layout.addWidget(self.lbl_table_info); self.sidebar_layout.addSpacing(10)

        self.cart_scroll = QScrollArea(); self.cart_scroll.setWidgetResizable(True); self.cart_scroll.setStyleSheet(MODERN_SCROLL + "background-color: transparent;")
        self.cart_container = QWidget(); self.cart_container.setStyleSheet("background-color: transparent;")
        self.cart_layout = QVBoxLayout(self.cart_container); self.cart_layout.setContentsMargins(0, 0, 0, 0); self.cart_layout.setSpacing(15); self.cart_layout.setAlignment(Qt.AlignTop)
        self.cart_scroll.setWidget(self.cart_container); self.sidebar_layout.addWidget(self.cart_scroll)

        self.totals_container = QWidget(); self.totals_container.setStyleSheet("background-color: transparent;")
        self.totals_layout = QVBoxLayout(self.totals_container); self.totals_layout.setContentsMargins(0,0,0,0)
        def create_fixed_total_row(label_text, is_bold=False):
            row = QHBoxLayout(); lbl_name = QLabel(label_text); lbl_val = QLabel("0 VND")
            font = QFont('Nunito', 16 if is_bold else 11, QFont.Bold if is_bold else QFont.Normal); color = "#111827" if is_bold else "#9CA3AF"
            lbl_name.setFont(font); lbl_name.setStyleSheet(f"color: {color}; border: none; background: transparent;")
            lbl_val.setFont(font); lbl_val.setStyleSheet(f"color: {color}; border: none; background: transparent;")
            row.addWidget(lbl_name); row.addStretch(); row.addWidget(lbl_val)
            return row, lbl_val

        row1, self.val_items_total = create_fixed_total_row("Items Total")
        row2, self.val_tax = create_fixed_total_row("Service Charge (10%)")
        row_disc, self.val_disc = create_fixed_total_row("Discount (5%)") # THÊM DÒNG DISCOUNT
        line = QFrame(); line.setFrameShape(QFrame.HLine); line.setStyleSheet("background-color: #E5E7EB; border: none; max-height: 1px;")
        row3, self.val_total = create_fixed_total_row("Total", is_bold=True)
        self.totals_layout.addSpacing(10); self.totals_layout.addLayout(row1); self.totals_layout.addLayout(row2); self.totals_layout.addLayout(row_disc); self.totals_layout.addSpacing(10); self.totals_layout.addWidget(line); self.totals_layout.addSpacing(10); self.totals_layout.addLayout(row3); self.totals_layout.addSpacing(10)
        self.sidebar_layout.addWidget(self.totals_container)

        btns_layout = QHBoxLayout()
        self.btn_save_order = QPushButton("Save Order"); self.btn_save_order.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_save_order.setStyleSheet("QPushButton { background-color: #F3F4F6; color: #4B5563; border: none; border-radius: 12px; padding: 15px; font-weight: bold; font-family: 'Nunito'; font-size: 15px; } QPushButton:hover { background-color: #E5E7EB; }")
        self.btn_save_order.clicked.connect(self.save_order_only)
        self.btn_pay = QPushButton("Print Bill & Pay"); self.btn_pay.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_pay.setStyleSheet("QPushButton { background-color: #EF4444; color: #FFFFFF; border: none; border-radius: 12px; padding: 15px; font-weight: bold; font-family: 'Nunito'; font-size: 15px; } QPushButton:hover { background-color: #DC2626; }")
        self.btn_pay.clicked.connect(self.checkout_order)
        btns_layout.addWidget(self.btn_save_order); btns_layout.addWidget(self.btn_pay); self.sidebar_layout.addLayout(btns_layout)
        main_h_layout.addWidget(self.sidebar_widget); self.refresh_sidebar()

    def track_order(self, name, qty, price, img, cat):
        if qty > 0: self.ordered_items[name] = {'qty': qty, 'price': price, 'img': img, 'cat': cat}
        elif name in self.ordered_items: del self.ordered_items[name]
        self.refresh_sidebar()

    def refresh_sidebar(self):
        for i in reversed(range(self.cart_layout.count())): 
            widget_to_remove = self.cart_layout.itemAt(i).widget()
            if widget_to_remove: widget_to_remove.setParent(None)
            
        total_base = 0
        items_list = list(self.ordered_items.items())
        
        for i, (dish_name, item) in enumerate(items_list):
            f = QFrame(); f.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E5E7EB; }")
            fl = QHBoxLayout(f); fl.setContentsMargins(15, 15, 15, 15); fl.setSpacing(15)
            img_lbl = QLabel(); img_lbl.setFixedSize(65, 65)
            pixmap = QPixmap(os.path.join(os.path.dirname(__file__), 'menu_images', item.get('img', '')))
            if not pixmap.isNull(): img_lbl.setPixmap(self.round_pixmap(pixmap.scaled(65, 65, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation), 12)) 
            else: img_lbl.setText("No Img"); img_lbl.setAlignment(Qt.AlignCenter); img_lbl.setStyleSheet("background-color: #F3F4F6; color: #9CA3AF; border-radius: 12px; border: none;")
            
            v_info = QVBoxLayout(); v_info.setSpacing(6); v_info.setAlignment(Qt.AlignVCenter)
            lbl_name = QLabel(dish_name); lbl_name.setFont(QFont('Nunito', 11, QFont.Bold)); lbl_name.setStyleSheet("color: #111827; border: none; background: transparent;")
            lbl_cat = QLabel(item.get('cat', 'Food')); lbl_cat.setFont(QFont('Nunito', 9)); lbl_cat.setStyleSheet("color: #9CA3AF; border: none; background: transparent;")
            lbl_price_qty = QLabel(f"{item['qty']}x {item['price']:,.0f} VND"); lbl_price_qty.setFont(QFont('Nunito', 10, QFont.Bold)); lbl_price_qty.setStyleSheet("color: #111827; border: none; background: transparent;")
            v_info.addWidget(lbl_name); v_info.addWidget(lbl_cat); v_info.addWidget(lbl_price_qty)
            fl.addWidget(img_lbl, alignment=Qt.AlignTop); fl.addLayout(v_info); fl.addStretch(); self.cart_layout.addWidget(f)
            if i < len(items_list) - 1:
                divider = QFrame(); divider.setFrameShape(QFrame.HLine); divider.setStyleSheet("background-color: #E5E7EB; border: none; max-height: 1px;"); self.cart_layout.addWidget(divider)
            total_base += item['qty'] * item['price']

        tax_amount = total_base * 0.10 
        discount_amount = total_base * 0.05 if total_base > 3000000 else 0
        final_total = total_base + tax_amount - discount_amount
        self.val_items_total.setText(f"{total_base:,.0f} VND")
        self.val_tax.setText(f"{tax_amount:,.0f} VND")
        self.val_disc.setText(f"-{discount_amount:,.0f} VND" if discount_amount > 0 else "0 VND")
        self.val_total.setText(f"{final_total:,.0f} VND")

        if total_base == 0:
            self.btn_save_order.setEnabled(False); self.btn_pay.setEnabled(False)
            self.btn_pay.setStyleSheet("QPushButton { background-color: #FCA5A5; color: #FFFFFF; border: none; border-radius: 12px; padding: 15px; font-weight: bold; font-family: 'Nunito'; font-size: 15px; }")
        else:
            self.btn_save_order.setEnabled(True); self.btn_pay.setEnabled(True)
            self.btn_pay.setStyleSheet("QPushButton { background-color: #EF4444; color: #FFFFFF; border: none; border-radius: 12px; padding: 15px; font-weight: bold; font-family: 'Nunito'; font-size: 15px; } QPushButton:hover { background-color: #DC2626; }")

    def save_order_only(self):
        db_manager.update_table_status(self.table_id, 'Occupied')
        if db_manager.save_order_to_db(self.table_id, self.ordered_items):
            ModernPopup("Saved", f"Order saved for Table {self.table_id}.", "fa5s.save", self).exec_()
            self.dashboard_parent.refresh_tables(); self.close(); self.dashboard_parent.showFullScreen()

    def checkout_order(self):
        db_manager.save_order_to_db(self.table_id, self.ordered_items) 
        if db_manager.process_checkout(self.table_id, self.ordered_items):
            db_manager.update_table_status(self.table_id, 'Available')
            ModernPopup("Success", f"Bill printed! Table {self.table_id} is free.", "fa5s.check-circle", self).exec_()
            self.dashboard_parent.refresh_tables(); self.close(); self.dashboard_parent.showFullScreen()

    def go_back(self):
        self.close(); self.dashboard_parent.showFullScreen()

# ==========================================
# 3. DINING TABLE WIDGET
# ==========================================
class DiningTable(QFrame):
    clicked = pyqtSignal(int)
    def __init__(self, table_id, capacity, status='Available'):
        super().__init__()
        self.table_id = table_id; self.capacity = capacity; self.status = status; self.is_selected = False
        self.colors = {'Available': {'bg': '#D1D5DB', 'text': '#4B5563', 'chair': '#D1D5DB', 'border_active': '#9CA3AF'},
                       'Reserved':  {'bg': '#FFCDD2', 'text': '#C62828', 'chair': '#FFCDD2', 'border_active': '#E53935'},
                       'Occupied':  {'bg': '#EF4444', 'text': '#FFFFFF', 'chair': '#F87171', 'border_active': '#B91C1C'}}
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout() if self.capacity == 6 else QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(8)
        self.table_core = QLabel(str(self.table_id)); self.table_core.setAlignment(Qt.AlignCenter); self.table_core.setFont(QFont('Nunito', 18, QFont.Bold))
        self.table_core.setFixedSize(200, 90) if self.capacity == 6 else self.table_core.setFixedSize(90, 160)
        def create_chair_group(num_chairs, is_horizontal):
            group = QHBoxLayout() if is_horizontal else QVBoxLayout(); group.setContentsMargins(0, 0, 0, 0); group.setSpacing(12); group.setAlignment(Qt.AlignCenter)
            for _ in range(num_chairs):
                chair = QFrame(); chair.setFixedSize(40, 18) if is_horizontal else chair.setFixedSize(18, 40)
                if not hasattr(self, 'chairs'): self.chairs = []
                self.chairs.append(chair); group.addWidget(chair)
            return group
        if self.capacity == 6: main_layout.addLayout(create_chair_group(3, True)); main_layout.addWidget(self.table_core, alignment=Qt.AlignCenter); main_layout.addLayout(create_chair_group(3, True))
        else: main_layout.addLayout(create_chair_group(2, False)); main_layout.addWidget(self.table_core, alignment=Qt.AlignCenter); main_layout.addLayout(create_chair_group(2, False))
        self.setLayout(main_layout); self.update_style()

    def update_style(self):
        theme = self.colors[self.status]; border_style = f"2px solid {theme['border_active']}" if self.is_selected else "none"
        self.table_core.setStyleSheet(f"QLabel {{ background-color: {theme['bg']}; color: {theme['text']}; border: {border_style}; border-radius: 20px; font-family: {MODERN_FONT}; }}")
        for chair in self.chairs: chair.setStyleSheet(f"QFrame {{ background-color: {theme['chair']}; border: {border_style}; border-radius: 8px; }}")

    def mousePressEvent(self, event): self.clicked.emit(self.table_id)

# ==========================================
# 4. RESERVATION PANE (CẬP NHẬT 2 CHẾ ĐỘ & X NÚT)
# ==========================================
class ReservationPane(QFrame):
    reservation_deleted = pyqtSignal(int)
    reservation_updated = pyqtSignal()
    reservation_created = pyqtSignal(dict)
    occupy_created = pyqtSignal(dict) # THÊM SIGNAL OCCUPY

    def __init__(self):
        super().__init__()
        self.table_id = None; self.res_data = None; self.res_id = None; self.mode = 'new'
        self.setFixedWidth(440) 
        self.setStyleSheet("QFrame { background-color: #FFFFFF; border-right: 1px solid #E5E7EB; }")
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Nút X (Close) và Tiêu đề
        header_lay = QHBoxLayout()
        self.lbl_main_title = QLabel("Reservation")
        self.lbl_main_title.setFont(QFont('Nunito', 22, QFont.Bold))
        self.lbl_main_title.setStyleSheet("color: #111827; border: none;") 
        
        self.btn_close = QPushButton(qta.icon('fa5s.times', color='#9CA3AF'), "")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setStyleSheet("background: transparent; border: none;")
        self.btn_close.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_close.clicked.connect(self.hide)

        header_lay.addWidget(self.lbl_main_title)
        header_lay.addStretch()
        header_lay.addWidget(self.btn_close)
        layout.addLayout(header_lay)

        self.input_style = f"""
            QLineEdit {{ background-color: #FFFFFF; border: 1px solid #D1D5DB; border-radius: 8px; padding: 12px 15px; font-family: {MODERN_FONT}; font-size: 14px; color: #111827; }}
            QLineEdit:focus {{ border: 1px solid #3B82F6; }}
        """
        
        # 1. Full name
        name_lay = QVBoxLayout(); name_lay.setContentsMargins(0, 0, 0, 0); name_lay.setSpacing(5)
        lbl_name = QLabel("Full name"); lbl_name.setStyleSheet(f"color: #6B7280; font-family: {MODERN_FONT}; font-weight: bold; border: none;")
        self.txt_name = QLineEdit(); self.txt_name.setPlaceholderText("Your name here"); self.txt_name.setStyleSheet(self.input_style); self.txt_name.textChanged.connect(self.validate_form)
        name_lay.addWidget(lbl_name); name_lay.addWidget(self.txt_name); layout.addLayout(name_lay)
        
        # 2. Phone number + Báo lỗi (ép margin âm để sát hơn nữa)
        phone_lay = QVBoxLayout(); phone_lay.setContentsMargins(0, 0, 0, 0); phone_lay.setSpacing(5)
        lbl_phone = QLabel("Phone number"); lbl_phone.setStyleSheet(f"color: #6B7280; font-family: {MODERN_FONT}; font-weight: bold; border: none;")
        self.txt_phone = QLineEdit(); self.txt_phone.setPlaceholderText("Enter a valid phone number"); self.txt_phone.setStyleSheet(self.input_style)
        phone_lay.addWidget(lbl_phone); phone_lay.addWidget(self.txt_phone)
        self.lbl_phone_error = QLabel("Please enter valid number"); self.lbl_phone_error.setFont(QFont('Nunito', 10))
        self.lbl_phone_error.setStyleSheet("color: #EF4444; padding-left: 2px; border: none; margin-top: -2px; margin-bottom: -5px;") 
        self.lbl_phone_error.setVisible(False)
        sp_phone = self.lbl_phone_error.sizePolicy()
        sp_phone.setRetainSizeWhenHidden(True)
        self.lbl_phone_error.setSizePolicy(sp_phone)
        phone_lay.addWidget(self.lbl_phone_error); self.txt_phone.textChanged.connect(self.auto_fill_customer) # ĐỔI SANG HÀM AUTO-FILL
        layout.addLayout(phone_lay)

        # 3. Address
        addr_lay = QVBoxLayout(); addr_lay.setContentsMargins(0, 0, 0, 0); addr_lay.setSpacing(5)
        lbl_address = QLabel("Address"); lbl_address.setStyleSheet(f"color: #6B7280; font-family: {MODERN_FONT}; font-weight: bold; border: none;")
        self.txt_address = QLineEdit(); self.txt_address.setPlaceholderText("Enter address (optional)"); self.txt_address.setStyleSheet(self.input_style)
        addr_lay.addWidget(lbl_address); addr_lay.addWidget(self.txt_address)
        layout.addLayout(addr_lay)

        cal_container = QFrame(); cal_container.setStyleSheet("border: 1px solid #D1D5DB; border-radius: 12px; background-color: #FFFFFF;")
        cal_layout = QVBoxLayout(); cal_layout.setContentsMargins(15, 15, 15, 15); cal_layout.setSpacing(5)
        lbl_date_title = QLabel("Date to come"); lbl_date_title.setStyleSheet(f"color: #6B7280; font-family: {MODERN_FONT}; font-weight: bold; border: none;"); layout.addWidget(lbl_date_title)
        self.txt_selected_date = QLineEdit(); self.txt_selected_date.setReadOnly(True); self.txt_selected_date.setStyleSheet(self.input_style); self.txt_selected_date.setText(QDate.currentDate().toString("yyyy-MM-dd")); cal_layout.addWidget(self.txt_selected_date); cal_layout.addSpacing(5)

        cal_nav_layout = QHBoxLayout()
        self.btn_prev_month = QPushButton(qta.icon('fa5s.angle-left', color='#6B7280'), ""); self.btn_prev_month.setFixedSize(30, 30); self.btn_prev_month.setCursor(QCursor(Qt.PointingHandCursor)); self.btn_prev_month.setStyleSheet("QPushButton { border: 1px solid #E5E7EB; border-radius: 15px; background-color: #F9FAFB; } QPushButton:hover { background-color: #E5E7EB; }")
        self.lbl_month_year = QLabel("2025 JUL"); self.lbl_month_year.setFont(QFont('Nunito', 12, QFont.Bold)); self.lbl_month_year.setStyleSheet("color: #111827; border: none;"); self.lbl_month_year.setAlignment(Qt.AlignCenter)
        self.btn_next_month = QPushButton(qta.icon('fa5s.angle-right', color='#6B7280'), ""); self.btn_next_month.setFixedSize(30, 30); self.btn_next_month.setCursor(QCursor(Qt.PointingHandCursor)); self.btn_next_month.setStyleSheet("QPushButton { border: 1px solid #E5E7EB; border-radius: 15px; background-color: #F9FAFB; } QPushButton:hover { background-color: #E5E7EB; }")

        cal_nav_layout.addWidget(self.btn_prev_month); cal_nav_layout.addWidget(self.lbl_month_year); cal_nav_layout.addWidget(self.btn_next_month); cal_layout.addLayout(cal_nav_layout)
        
        self.calendar = QCalendarWidget(); self.calendar.setNavigationBarVisible(False); self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader); self.calendar.setGridVisible(False); self.calendar.setFixedSize(310, 220)
        fmt = QTextCharFormat(); fmt.setBackground(Qt.transparent); fmt.setForeground(QColor('#9CA3AF')); fmt.setFontWeight(QFont.Bold); self.calendar.setHeaderTextFormat(fmt)
        self.calendar.setStyleSheet("""
            QCalendarWidget QTableView { background-color: #FFFFFF; border: none; selection-background-color: #EF4444; selection-color: white; outline: 0px; }
            QCalendarWidget QTableView::item { margin: 4px; border-radius: 12px; color: #374151; font-family: 'Nunito'; font-size: 13px; }
            QCalendarWidget QTableView::item:selected { background-color: #EF4444; border-radius: 12px; color: white; font-weight: bold; }
            QCalendarWidget QTableView::item:hover { background-color: #F3F4F6; border-radius: 12px; }
        """)
        cal_layout.addWidget(self.calendar, alignment=Qt.AlignCenter); cal_container.setLayout(cal_layout)

        self.btn_prev_month.clicked.connect(self.calendar.showPreviousMonth); self.btn_next_month.clicked.connect(self.calendar.showNextMonth)
        self.calendar.currentPageChanged.connect(self.update_calendar_header); self.calendar.clicked.connect(self.update_date_input)
        layout.addWidget(cal_container); self.update_calendar_header(self.calendar.yearShown(), self.calendar.monthShown())

        time_v_layout = QVBoxLayout(); time_v_layout.setContentsMargins(0, 0, 0, 0); time_v_layout.setSpacing(5); lbl_time = QLabel("Time to come"); lbl_time.setStyleSheet(f"color: #6B7280; font-family: {MODERN_FONT}; font-weight: bold; border: none;"); time_v_layout.addWidget(lbl_time)
        self.time_picker = QComboBox(); self.time_picker.setStyleSheet(f"QComboBox {{ background-color: #FFFFFF; border: 1px solid #D1D5DB; border-radius: 8px; padding: 12px 15px 12px 45px; font-family: {MODERN_FONT}; font-size: 14px; color: #111827; }} QComboBox::drop-down {{ border: none; width: 30px; }} QComboBox QAbstractItemView {{ border: 1px solid #E5E7EB; border-radius: 8px; background-color: #FFFFFF; outline: 0px; padding: 5px; }} QComboBox QAbstractItemView::item {{ min-height: 38px; padding-left: 10px; border-radius: 5px; color: #374151; }} QComboBox QAbstractItemView::item:selected {{ background-color: #EFF6FF; color: #1D4ED8; }}")
        lbl_icon_clock = QLabel(self.time_picker); lbl_icon_clock.setPixmap(qta.icon('fa5s.clock', color='#FA5A5A').pixmap(20, 20)); lbl_icon_clock.setStyleSheet("background: transparent; border: none;"); lbl_icon_clock.setFixedSize(20, 20); lbl_icon_clock.move(15, 12)
        fine_dining_times = ["18:00", "18:30", "19:00", "19:30", "20:00", "20:30", "21:00", "21:30", "22:00"]; self.time_picker.addItems(fine_dining_times); time_v_layout.addWidget(self.time_picker); layout.addLayout(time_v_layout)

        guest_v_layout = QVBoxLayout(); guest_v_layout.setContentsMargins(0, 0, 0, 0); guest_v_layout.setSpacing(5); lbl_guest = QLabel("Number of people"); lbl_guest.setStyleSheet(f"color: #6B7280; font-family: {MODERN_FONT}; font-weight: bold; border: none;"); guest_v_layout.addWidget(lbl_guest)
        self.txt_guests = QLineEdit(); self.txt_guests.setPlaceholderText("How many people will attend"); self.txt_guests.setStyleSheet(self.input_style.replace("padding: 12px 15px;", "padding: 12px 15px 12px 45px;")); lbl_icon_users = QLabel(self.txt_guests); lbl_icon_users.setPixmap(qta.icon('fa5s.users', color='#FA5A5A').pixmap(20, 20)); lbl_icon_users.setStyleSheet("background: transparent; border: none;"); lbl_icon_users.setFixedSize(20, 20); lbl_icon_users.move(15, 12); guest_v_layout.addWidget(self.txt_guests)
        self.lbl_guest_error = QLabel("Please enter a valid number (1-20)"); self.lbl_guest_error.setFont(QFont('Nunito', 10)); self.lbl_guest_error.setStyleSheet("color: #EF4444; padding-left: 2px; border: none; margin-top: -2px; margin-bottom: -5px;"); self.lbl_guest_error.setVisible(False); sp_guest = self.lbl_guest_error.sizePolicy(); sp_guest.setRetainSizeWhenHidden(True); self.lbl_guest_error.setSizePolicy(sp_guest); guest_v_layout.addWidget(self.lbl_guest_error); self.txt_guests.textChanged.connect(self.validate_form); layout.addLayout(guest_v_layout)

        layout.addStretch()
        layout.addSpacing(10)

        # NÚT BOTTOM MỚI (EDIT, CONTINUE/CANCEL)
        btn_layout = QHBoxLayout()
        self.btn_edit = QPushButton("Edit Info")
        self.btn_edit.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_edit.setStyleSheet("QPushButton { background-color: transparent; color: #4B5563; border: 1px solid #D1D5DB; border-radius: 8px; padding: 10px 25px; font-weight: bold; font-family: 'Nunito'; font-size: 14px; } QPushButton:hover { background-color: #F3F4F6; }")
        self.btn_edit.clicked.connect(self.toggle_edit_mode)

        self.btn_save = QPushButton("Continue") 
        self.btn_save.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_save.setStyleSheet("QPushButton { background-color: #EF4444; color: #FFFFFF; border: none; border-radius: 8px; padding: 10px 30px; font-weight: bold; font-family: 'Nunito'; font-size: 14px; } QPushButton:hover { background-color: #DC2626; } QPushButton:disabled { background-color: #FCA5A5; }")
        self.btn_save.clicked.connect(self.handle_action)

        btn_layout.addWidget(self.btn_edit); btn_layout.addStretch(); btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout); self.setLayout(layout)

    def set_fields_readonly(self, readonly):
        for w in [self.txt_name, self.txt_phone, self.txt_address, self.txt_guests]:
            w.setReadOnly(readonly)
            bg = "#F3F4F6" if readonly else "#FFFFFF"
            w.setStyleSheet(w.styleSheet().replace("background-color: #FFFFFF", f"background-color: {bg}").replace("background-color: #F3F4F6", f"background-color: {bg}"))
        self.calendar.setEnabled(not readonly)
        self.time_picker.setEnabled(not readonly)
        self.btn_next_month.setEnabled(not readonly)
        self.btn_prev_month.setEnabled(not readonly)

    def show_pane(self, table_id, res_data=None, is_occupy=False):
        self.table_id = table_id; self.res_data = res_data
        self.show()
        self.lbl_phone_error.setVisible(False)
        self.lbl_guest_error.setVisible(False)

        if is_occupy:
            # CHẾ ĐỘ OCCUPY (Giao diện y hệt, chỉ khóa chọn ngày giờ)
            self.mode = 'occupy'; self.res_id = None
            self.lbl_main_title.setText("Occupy Table")
            self.btn_edit.hide(); self.btn_save.setText("Occupy Now")
            self.btn_save.setStyleSheet("QPushButton { background-color: #EF4444; color: #FFFFFF; border: none; border-radius: 8px; padding: 10px 30px; font-weight: bold; font-family: 'Nunito'; font-size: 14px; } QPushButton:hover { background-color: #DC2626; } QPushButton:disabled { background-color: #FCA5A5; }")
            self.set_fields_readonly(False)
            # Khóa lịch và thời gian vì sẽ lấy thời gian thực (System Time)
            self.calendar.setEnabled(False); self.time_picker.setEnabled(False); self.btn_next_month.setEnabled(False); self.btn_prev_month.setEnabled(False)
            self.txt_name.clear(); self.txt_phone.clear(); self.txt_address.clear(); self.txt_guests.clear()
            self.txt_selected_date.setText(QDate.currentDate().toString("yyyy-MM-dd"))
            self.validate_form()
        elif res_data is None:
            # CHẾ ĐỘ MỚI (RESERVATION)
            self.mode = 'new'; self.res_id = None
            self.lbl_main_title.setText("Reservation")
            self.btn_edit.hide(); self.btn_save.setText("Continue")
            self.btn_save.setStyleSheet("QPushButton { background-color: #EF4444; color: #FFFFFF; border: none; border-radius: 8px; padding: 10px 30px; font-weight: bold; font-family: 'Nunito'; font-size: 14px; } QPushButton:hover { background-color: #DC2626; } QPushButton:disabled { background-color: #FCA5A5; }")
            self.set_fields_readonly(False)
            self.txt_name.clear(); self.txt_phone.clear(); self.txt_address.clear(); self.txt_guests.clear()
            self.calendar.setSelectedDate(QDate.currentDate()); self.txt_selected_date.setText(QDate.currentDate().toString("yyyy-MM-dd"))
            self.validate_form()
        else:
            # CHẾ ĐỘ VIEW (CÓ SẴN DỮ LIỆU)
            self.mode = 'view'; self.res_id = res_data['ReservationID']
            self.lbl_main_title.setText("Reservation Info")
            self.btn_edit.show(); self.btn_edit.setText("Edit Info")
            self.btn_save.setText("Cancel Reservation")
            self.btn_save.setStyleSheet("QPushButton { background-color: #EF4444; color: #FFFFFF; border: none; border-radius: 8px; padding: 10px 30px; font-weight: bold; font-family: 'Nunito'; font-size: 14px; } QPushButton:hover { background-color: #DC2626; }")
            self.btn_save.setEnabled(True)
            self.set_fields_readonly(True)
            
            # Đổ dữ liệu vào Form
            self.txt_name.setText(res_data['CustomerName'])
            self.txt_phone.setText(res_data['Phone'] if res_data['Phone'] else "")
            self.txt_address.setText(res_data['Address'] if res_data['Address'] else "")
            self.txt_guests.setText(str(res_data['GuestCount']))
            
            dt = res_data['DateTime']
            # FIX 1: Định dạng lại strftime chuẩn %Y-%m-%d
            self.txt_selected_date.setText(dt.strftime("%Y-%m-%d"))
            self.time_picker.setCurrentText(dt.strftime("%H:%M"))

    def toggle_edit_mode(self):
        if self.mode == 'view':
            self.mode = 'edit'; self.set_fields_readonly(False)
            self.btn_edit.setText("Discard")
            self.btn_save.setText("Save Changes")
            self.validate_form()
        elif self.mode == 'edit':
            self.show_pane(self.table_id, self.res_data) # Hủy bỏ thay đổi

    # HÀM MỚI: TỰ ĐỘNG ĐIỀN THÔNG TIN KHÁCH HÀNG KHI GÕ SĐT
    def auto_fill_customer(self):
        self.validate_form() # Vẫn giữ logic validate cũ
        if self.mode in ['new', 'occupy']:
            phone = self.txt_phone.text().strip()
            # Nếu gõ đủ định dạng SĐT (VD: 09... 10 số)
            if re.match(r"^(0)\d{9}$", phone):
                customer = db_manager.get_customer_by_phone(phone)
                if customer:
                    # Chỉ điền nếu ô tên/địa chỉ đang trống để tránh ghi đè nhầm
                    if not self.txt_name.text().strip(): self.txt_name.setText(customer['CustomerName'])
                    if customer['Address'] and not self.txt_address.text().strip(): self.txt_address.setText(customer['Address'])

    # TÌM HÀM NÀY VÀ DÁN ĐÈ BẰNG ĐOẠN SAU
    def handle_action(self):
        if self.mode == 'new':
            data = {'table_id': self.table_id, 'name': self.txt_name.text().strip(), 'phone': self.txt_phone.text().strip(), 'address': self.txt_address.text().strip(), 'date': self.txt_selected_date.text(), 'time': self.time_picker.currentText(), 'guests': int(self.txt_guests.text().strip())}
            self.reservation_created.emit(data); self.hide()
        elif self.mode == 'occupy':
            # Lấy thời gian hệ thống ngay lúc bấm Occupy Now
            dt_string = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:00")
            data = {'table_id': self.table_id, 'name': self.txt_name.text().strip(), 'phone': self.txt_phone.text().strip(), 'address': self.txt_address.text().strip(), 'date': dt_string.split()[0], 'time': dt_string.split()[1], 'guests': int(self.txt_guests.text().strip())}
            self.occupy_created.emit(data); self.hide()
        elif self.mode == 'view':
            # FIX LỖI: HIỆN POPUP HỎI YES/NO TRƯỚC KHI CANCEL
            confirm = ModernConfirmPopup("Cancel Reservation", "Are you sure you want to cancel this reservation?", "fa5s.exclamation-triangle", self.window())
            if confirm.exec_() == QDialog.Accepted:
                if db_manager.cancel_reservation(self.table_id):
                    self.reservation_deleted.emit(self.table_id)
                    self.hide()
        elif self.mode == 'edit':
            dt_string = f"{self.txt_selected_date.text()} {self.time_picker.currentText().split(' ')[0]}:00"
            if db_manager.update_reservation_details(self.res_id, self.txt_name.text().strip(), self.txt_phone.text().strip(), self.txt_address.text().strip(), dt_string, int(self.txt_guests.text().strip())):
                self.reservation_updated.emit(); self.hide()

    def update_calendar_header(self, year, month): self.lbl_month_year.setText(QDate(year, month, 1).toString("yyyy MMM").upper())
    def update_date_input(self, date): self.txt_selected_date.setText(date.toString("yyyy-MM-dd"))
    
    def validate_form(self):
        if self.mode == 'view': return
        phone = self.txt_phone.text().strip(); phone_valid = bool(re.match(r"^(0)\d{9}$", phone))
        if phone and not phone_valid: self.lbl_phone_error.setVisible(True); self.txt_phone.setStyleSheet(self.txt_phone.styleSheet().replace("1px solid #D1D5DB", "1px solid #EF4444"))
        else: self.lbl_phone_error.setVisible(False); self.txt_phone.setStyleSheet(self.txt_phone.styleSheet().replace("1px solid #EF4444", "1px solid #D1D5DB"))
        guests = self.txt_guests.text().strip(); guests_valid = guests.isdigit() and 0 < int(guests) <= 20
        if guests and not guests_valid: self.lbl_guest_error.setVisible(True); self.txt_guests.setStyleSheet(self.txt_guests.styleSheet().replace("1px solid #D1D5DB", "1px solid #EF4444"))
        else: self.lbl_guest_error.setVisible(False); self.txt_guests.setStyleSheet(self.txt_guests.styleSheet().replace("1px solid #EF4444", "1px solid #D1D5DB"))
        self.btn_save.setEnabled(phone_valid and guests_valid and self.txt_name.text().strip() != "")

# ==========================================
# 6. MAIN DASHBOARD WINDOW
# ==========================================
class DashboardWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_table_id = None
        self.tables = {}
        self.active_orders = {} 
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Le Veau - Seats Plan')
        self.setStyleSheet("background-color: #F3F4F6;")

        main_horizontal_layout = QHBoxLayout()
        main_horizontal_layout.setContentsMargins(0, 0, 0, 0); main_horizontal_layout.setSpacing(0)

        self.reserve_pane = ReservationPane()
        self.reserve_pane.hide()
        self.reserve_pane.reservation_created.connect(self.on_reservation_created)
        self.reserve_pane.reservation_deleted.connect(self.on_reservation_deleted)
        self.reserve_pane.reservation_updated.connect(self.on_reservation_updated)
        self.reserve_pane.occupy_created.connect(self.on_occupy_created) # KẾT NỐI TÍN HIỆU OCCUPY
        main_horizontal_layout.addWidget(self.reserve_pane)

        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(50, 40, 50, 40)

        # HEADER CÓ THANH TÌM KIẾM (GLOBAL SEARCH)
        header_layout = QHBoxLayout()
        lbl_title = QLabel("Choose table"); lbl_title.setFont(QFont('Nunito', 24, QFont.Bold)); lbl_title.setStyleSheet(f"color: #111827; font-family: {MODERN_FONT};")
        
        self.search_container = QFrame()
        self.search_container.setStyleSheet("background-color: #FFFFFF; border-radius: 20px; border: 1px solid #E5E7EB;")
        self.search_container.setFixedSize(300, 40)
        search_layout = QHBoxLayout(self.search_container); search_layout.setContentsMargins(15, 0, 15, 0)
        
        lbl_search_icon = QLabel()
        lbl_search_icon.setPixmap(qta.icon('fa5s.search', color='#9CA3AF').pixmap(16, 16))
        # FIX 2: Bỏ viền cho kính lúp
        lbl_search_icon.setStyleSheet("border: none; background: transparent;")
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search phone...")
        self.txt_search.setStyleSheet("border: none; background: transparent; font-family: 'Nunito'; font-size: 14px; color: #111827;")
        self.txt_search.returnPressed.connect(self.search_customer)
        search_layout.addWidget(lbl_search_icon); search_layout.addWidget(self.txt_search)

        btn_logout = QPushButton()
        btn_logout.setIcon(qta.icon('fa5s.sign-out-alt', color='#6B7280'))
        btn_logout.setIconSize(QSize(16, 16))
        btn_logout.setFixedSize(40, 40)
        btn_logout.setCursor(QCursor(Qt.PointingHandCursor))
        btn_logout.setToolTip("Logout")
        btn_logout.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #FEE2E2;
                border-color: #FECACA;
            }
            QPushButton:hover QIcon { color: #EF4444; }
        """)
        shadow_lo = QGraphicsDropShadowEffect(); shadow_lo.setBlurRadius(12); shadow_lo.setColor(QColor(0, 0, 0, 18)); shadow_lo.setOffset(0, 3); btn_logout.setGraphicsEffect(shadow_lo)
        btn_logout.clicked.connect(self.handle_logout)

        btn_exit = QPushButton(qta.icon('fa5s.power-off', color='#FFFFFF'), " Exit POS")
        btn_exit.setFixedSize(120, 40); btn_exit.setCursor(QCursor(Qt.PointingHandCursor))
        btn_exit.setStyleSheet("QPushButton { background-color: #374151; color: white; border-radius: 8px; font-weight: bold;} QPushButton:hover { background-color: #111827; }")
        btn_exit.clicked.connect(self.close)

        header_layout.addWidget(lbl_title); header_layout.addStretch(); header_layout.addWidget(self.search_container); header_layout.addSpacing(14); header_layout.addWidget(btn_logout); header_layout.addSpacing(10); header_layout.addWidget(btn_exit)
        right_layout.addLayout(header_layout)
        
        self.floor_layout = QVBoxLayout(); self.floor_layout.setSpacing(100); self.floor_layout.setAlignment(Qt.AlignCenter)
        self.refresh_tables()
        right_layout.addLayout(self.floor_layout)

        self.action_container = QWidget()
        action_layout = QHBoxLayout(); action_layout.setAlignment(Qt.AlignCenter); action_layout.setSpacing(40)

        self.btn_book = self.create_icon_action("fa5s.user-check", "Occupy")
        self.btn_reserve = self.create_icon_action("fa5s.clock", "Reservation")
        self.btn_order = self.create_icon_action("fa5s.plus", "Order")
        self.btn_cancel = self.create_icon_action("fa5s.times", "Cancel")
        
        self.btn_cancel.btn_reference.clicked.connect(self.deselect_table)
        self.btn_order.btn_reference.clicked.connect(self.open_menu)
        self.btn_book.btn_reference.clicked.connect(self.show_occupy_pane) # ĐỔI SANG MỞ FORM OCCUPY
        self.btn_reserve.btn_reference.clicked.connect(self.show_reservation_pane)
        
        action_layout.addWidget(self.btn_book); action_layout.addWidget(self.btn_reserve); action_layout.addWidget(self.btn_order); action_layout.addWidget(self.btn_cancel)
        self.action_container.setLayout(action_layout); self.action_container.setVisible(False)
        right_layout.addWidget(self.action_container)
        
        main_horizontal_layout.addWidget(right_container, stretch=1)
        self.setLayout(main_horizontal_layout)

    def search_customer(self):
        keyword = self.txt_search.text().strip()
        if not keyword: return
        
        results = db_manager.smart_search_reservation(keyword)
        
        if not results:
            ModernPopup("Not Found", f"No active reservation found for: '{keyword}'", "fa5s.search", self).exec_()
            return

        # Trường hợp 1: Chỉ có 1 kết quả duy nhất -> Tự động nhảy luôn đến bàn đó
        if len(results) == 1:
            tid = results[0]['TableID']
            self.txt_search.clear()
            self.on_table_clicked(tid)
            self.show_reservation_pane()
            
        # Trường hợp 2: BỊ TRÙNG TÊN -> Mở Dropdown thả xuống dưới thanh Search siêu hiện đại
        else:
            menu = QMenu(self)
            # Style QMenu bo tròn, đổ bóng sang trọng giống hệt UI hiện tại
            menu.setStyleSheet("""
                QMenu {
                    background-color: #FFFFFF;
                    border: 1px solid #E5E7EB;
                    border-radius: 8px;
                    padding: 5px;
                }
                QMenu::item {
                    font-family: 'Nunito'; font-size: 14px; color: #111827;
                    padding: 10px 20px;
                    border-radius: 5px;
                }
                QMenu::item:selected { background-color: #F3F4F6; color: #EF4444; font-weight: bold; }
            """)
            
            # Tạo các lựa chọn trong menu
            for row in results:
                tid = row['TableID']
                name = row['CustomerName']
                phone = row['Phone']
                
                # Che số điện thoại theo chuẩn View trong SQL của bạn (Ví dụ: 091****678)
                masked_phone = f"{phone[:3]}****{phone[-3:]}" if phone and len(phone) >= 10 else phone
                
                action_text = f" {name}   |    {masked_phone}   |    Table {tid:02d}"
                action = menu.addAction(action_text)
                
                # Gắn sự kiện: Bấm vào dòng nào thì nhảy đến bàn đó
                action.triggered.connect(lambda checked, t=tid: self.select_searched_table(t))
            
            # Định vị menu xổ xuống ngay sát mép dưới của thanh Search
            menu.exec_(self.search_container.mapToGlobal(self.search_container.rect().bottomLeft()))

    # Hàm phụ trợ để gọi khi click vào menu thả xuống
    def select_searched_table(self, tid):
        self.txt_search.clear()
        self.on_table_clicked(tid)
        self.show_reservation_pane()

    def refresh_tables(self):
        # FIX LỖI TRƯỢT BÀN: Xóa sạch cả Layout chứa bàn lẫn các khoảng trống (Spacer)
        while self.floor_layout.count():
            item = self.floor_layout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    sub_item = item.layout().takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()
            elif item.widget():
                item.widget().deleteLater()

        self.tables.clear()
        
        db_status = db_manager.get_tables_status()
        row1_data = [{'id': 1, 'cap': 4}, {'id': 2, 'cap': 4}, {'id': 4, 'cap': 6}, {'id': 3, 'cap': 4}, {'id': 5, 'cap': 4}]
        row2_data = [{'id': 6, 'cap': 4}, {'id': 7, 'cap': 4}, {'id': 9, 'cap': 6}, {'id': 8, 'cap': 4}, {'id': 10, 'cap': 4}]

        def build_row(data_list):
            row = QHBoxLayout(); row.setSpacing(100); row.setAlignment(Qt.AlignCenter)
            for data in data_list:
                tid = data['id']; status = db_status.get(tid, 'Available') 
                table = DiningTable(tid, data['cap'], status); table.clicked.connect(self.on_table_clicked); self.tables[tid] = table; row.addWidget(table)
            return row
            
        self.floor_layout.addStretch()
        self.floor_layout.addLayout(build_row(row1_data))
        self.floor_layout.addLayout(build_row(row2_data))
        self.floor_layout.addStretch()

    def create_icon_action(self, icon_name, text):
        container = QWidget(); layout = QVBoxLayout(); layout.setAlignment(Qt.AlignCenter); layout.setSpacing(10)
        btn = QPushButton(); btn.setIcon(qta.icon(icon_name, color='#EF4444', color_disabled='#D1D5DB')); btn.setIconSize(QSize(24,24)); btn.setFixedSize(70, 70); btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setStyleSheet("QPushButton { background-color: #FFFFFF; border: none; border-radius: 35px; } QPushButton:hover { background-color: #FEE2E2; } QPushButton:disabled { background-color: #F3F4F6; }")
        shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(15); shadow.setColor(QColor(0, 0, 0, 20)); shadow.setOffset(0, 5); btn.setGraphicsEffect(shadow)
        lbl = QLabel(text); lbl.setFont(QFont('Nunito', 10, QFont.Bold)); lbl.setStyleSheet(f"QLabel {{ color: #374151; font-family: {MODERN_FONT}; }} QLabel:disabled {{ color: #D1D5DB; }}"); lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(btn); layout.addWidget(lbl); container.setLayout(layout)
        container.btn_reference = btn 
        container.lbl_reference = lbl # ĐỂ ĐỔI TÊN NÚT BÊN DƯỚI
        return container

    def on_table_clicked(self, table_id):
        self.reserve_pane.hide()
        if self.selected_table_id and self.selected_table_id in self.tables:
            old_table = self.tables[self.selected_table_id]; old_table.is_selected = False; old_table.update_style()
        self.selected_table_id = table_id; new_table = self.tables[table_id]; new_table.is_selected = True; new_table.update_style()
        
        status = new_table.status
        self.btn_book.btn_reference.setEnabled(status in ['Available', 'Reserved'])
        self.btn_order.btn_reference.setEnabled(status == 'Occupied')
        
        # LOGIC ĐỔI TÊN NÚT RESERVATION DỰA VÀO STATUS
        if status == 'Reserved':
            self.btn_reserve.btn_reference.setEnabled(True)
            self.btn_reserve.lbl_reference.setText("Res. Info")
        else:
            self.btn_reserve.btn_reference.setEnabled(status == 'Available')
            self.btn_reserve.lbl_reference.setText("Reservation")
            
        self.btn_cancel.btn_reference.setEnabled(True) 
        self.action_container.setVisible(True)

    def deselect_table(self):
        self.reserve_pane.hide()
        if self.selected_table_id and self.selected_table_id in self.tables:
            old_table = self.tables[self.selected_table_id]; old_table.is_selected = False; old_table.update_style()
        self.selected_table_id = None; self.action_container.setVisible(False)

    def occupy_table(self):
        if self.selected_table_id:
            if db_manager.update_table_status(self.selected_table_id, 'Occupied'):
                self.refresh_tables(); self.on_table_clicked(self.selected_table_id)

    def show_occupy_pane(self):
        if self.selected_table_id:
            # KIỂM TRA TRẠNG THÁI BÀN
            status = self.tables[self.selected_table_id].status
            if status == 'Reserved':
                # Nếu đã đặt trước (Reserved) -> Đổi thành Occupy luôn, không mở form
                self.occupy_table()
                ModernPopup("Success", f"Table {self.selected_table_id} is now occupied!", "fa5s.check-circle", self).exec_()
            else:
                # Nếu bàn đang trống (Available) -> Mở form điền thông tin khách
                self.reserve_pane.show_pane(self.selected_table_id, is_occupy=True)

    def on_occupy_created(self, data):
        dt_string = f"{data['date']} {data['time']}"
        # Gọi save_reservation để tạo khách hàng (nếu chưa có) và ghi nhận vào Reservations
        if db_manager.save_reservation(data['name'], data['phone'], data['address'], dt_string, data['guests'], data['table_id']):
            # Ghi đè ngay Table Status thành Occupied (Vì hàm save_reservation kích hoạt Trigger chuyển thành Reserved)
            db_manager.update_table_status(data['table_id'], 'Occupied')
            ModernPopup("Success", "Table occupied with customer info successfully!", "fa5s.check-circle", self).exec_()
            self.refresh_tables(); self.deselect_table()
        else: ModernPopup("Error", "Cannot occupy table. Check DB.", "fa5s.times-circle", self).exec_()

    def show_reservation_pane(self):
        if self.selected_table_id:
            status = self.tables[self.selected_table_id].status
            if status == 'Reserved':
                res_data = db_manager.get_reservation_details(self.selected_table_id)
                self.reserve_pane.show_pane(self.selected_table_id, res_data)
            else:
                self.reserve_pane.show_pane(self.selected_table_id, None)

    def on_reservation_created(self, data):
        dt_string = f"{data['date']} {data['time'].split(' ')[0]}:00"
        if db_manager.save_reservation(data['name'], data['phone'], data['address'], dt_string, data['guests'], data['table_id']):
            ModernPopup("Success", "Reservation saved to database successfully!", "fa5s.check-circle", self).exec_()
            self.refresh_tables(); self.deselect_table()
        else: ModernPopup("Error", "Cannot save reservation. Check MySQL connection.", "fa5s.times-circle", self).exec_()

    def on_reservation_deleted(self, table_id):
        ModernPopup("Canceled", "Reservation has been canceled.", "fa5s.check-circle", self).exec_()
        self.refresh_tables(); self.deselect_table()

    def on_reservation_updated(self):
        ModernPopup("Updated", "Reservation details updated successfully.", "fa5s.check-circle", self).exec_()
        self.refresh_tables(); self.deselect_table()

    def handle_logout(self):
        from login import LoginWindow
        self.login_window = LoginWindow()
        self.login_window.show()
        self.close()

    def open_menu(self):
        self.menu_window = MenuWindow(self.selected_table_id, self); self.menu_window.showFullScreen(); self.hide()

# ==========================================
# BOOTSTRAP 
# ==========================================
if __name__ == '__main__':
    import traceback
    app = QApplication(sys.argv)
    try:
        window = DashboardWindow()
        window.showFullScreen() 
        sys.exit(app.exec_())
    except Exception as e:
        error_msg = traceback.format_exc(); print(error_msg)
        from PyQt5.QtWidgets import QMessageBox
        msg = QMessageBox(); msg.setIcon(QMessageBox.Critical); msg.setWindowTitle("App Crashed - Bắt Lỗi")
        msg.setText("Ứng dụng văng ra vì có lỗi ngầm! Bấm 'Show Details' để xem."); msg.setDetailedText(error_msg); msg.exec_()