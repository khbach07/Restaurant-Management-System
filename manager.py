import sys
import os
import csv
import shutil
import numpy as np
import pymysql                 # BẠN THÊM DÒNG NÀY VÀO
import pymysql.cursors
import qtawesome as qta
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect,
                             QScrollArea, QGridLayout, QComboBox, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QSizePolicy, QStackedWidget,
                             QDialog, QLineEdit, QFileDialog, QMessageBox, QMenu, QAction)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QRect
from PyQt5.QtGui import QFont, QCursor, QColor, QPixmap, QPainter, QPainterPath
from dotenv import load_dotenv
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as patches
import matplotlib.patheffects as pe

try:
    from scipy.interpolate import make_interp_spline
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

MODERN_FONT = "'Nunito', 'Segoe UI', sans-serif"
BRIGHT_RED = "#C81E1E" 
RUBY_SOLID = "#9B1D42" 
EXPENSE_GREY = "#374151"   
BG_COLOR = "#F4F6F8"       

MODERN_SCROLL = """
QScrollArea { border: none; background-color: transparent; }
QScrollBar:vertical { border: none; background: transparent; width: 0px; margin: 0px; }
QScrollBar::handle:vertical { background: #D1D5DB; min-height: 30px; border-radius: 4px; }
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
        import pymysql; import pymysql.cursors
        return pymysql.connect(**self.config)

    # --- XÓA VÀ KIỂM TRA RÀNG BUỘC KHÁCH HÀNG ---
    def delete_customer(self, cus_id_str):
        try:
            cid = int(cus_id_str.replace('#CUS', ''))
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM Invoices WHERE CustomerID=%s", (cid,))
            if cursor.fetchone()[0] > 0:
                return False, "Cannot delete: Customer has existing invoices."
            cursor.execute("SELECT COUNT(*) FROM Reservations WHERE CustomerID=%s", (cid,))
            if cursor.fetchone()[0] > 0:
                return False, "Cannot delete: Customer has existing reservations."
            cursor.execute("DELETE FROM Customers WHERE CustomerID=%s", (cid,))
            conn.commit()
            conn.close()
            return True, "Customer deleted successfully."
        except Exception as e:
            return False, str(e)

    # --- CẬP NHẬT KHÁCH HÀNG ---
    def update_customer(self, cus_id_str, name, phone, address):
        try:
            cid = int(cus_id_str.replace('#CUS', ''))
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE Customers SET CustomerName=%s, PhoneNumber=HEX(AES_ENCRYPT(%s, %s)), Address=%s WHERE CustomerID=%s",
                (name, phone, self.aes_key, address, cid)
            )
            conn.commit()
            conn.close()
            return True, "Customer updated successfully."
        except Exception as e:
            return False, str(e)

    # --- CẬP NHẬT MÓN ĂN ---
    def update_menu_item(self, dish_id_str, name, category, price):
        try:
            did = int(dish_id_str)
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE MenuItems SET DishName=%s, Category=%s, Price=%s WHERE DishID=%s",
                (name, category, price, did)
            )
            conn.commit()
            conn.close()
            return True, "Menu item updated successfully."
        except Exception as e:
            return False, str(e)

    def delete_menu_item(self, dish_id_str):
        try:
            did = int(dish_id_str)
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM OrderDetails WHERE DishID=%s", (did,))
            if cursor.fetchone()[0] > 0:
                return False, "Cannot delete: Dish is included in existing orders."
            cursor.execute("DELETE FROM MenuItems WHERE DishID=%s", (did,))
            conn.commit()
            conn.close()
            return True, "Menu item deleted successfully."
        except Exception as e:
            return False, str(e)

    # --- CẬP NHẬT CHI PHÍ ---
    def update_expense(self, exp_id_str, desc, category, amount, date):
        try:
            eid = int(exp_id_str.replace('EX', ''))
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE Expenses SET Description=%s, ExpenseCategory=%s, Amount=%s, ExpenseDate=%s WHERE ExpenseID=%s",
                (desc, category, amount, date, eid)
            )
            conn.commit()
            conn.close()
            return True, "Expense updated successfully."
        except Exception as e:
            return False, str(e)

    def delete_expense(self, exp_id_str):
        try:
            eid = int(exp_id_str.replace('EX', ''))
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Expenses WHERE ExpenseID=%s", (eid,))
            conn.commit()
            conn.close()
            return True, "Expense deleted successfully."
        except Exception as e:
            return False, str(e)

    def get_dashboard_kpis(self):
        try:
            conn = self.connect()
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            cursor.execute("SELECT COUNT(*) as count FROM Invoices")
            total_orders = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM Customers")
            total_cust = cursor.fetchone()['count']

            cursor.execute("SELECT SUM(TotalAmount) as sum FROM Invoices WHERE PaymentDate IS NOT NULL")
            revenue = cursor.fetchone()['sum'] or 0

            cursor.execute("SELECT SUM(Amount) as sum FROM Expenses")
            expenses = cursor.fetchone()['sum'] or 0

            profit = float(revenue) - float(expenses)
            conn.close()

            rev_k = float(revenue) / 1000
            prof_k = profit / 1000
            return {
                "orders": f"{total_orders:,}",
                "customers": f"{total_cust:,}",
                "revenue": f"{rev_k:,.0f}",
                "profit": f"{prof_k:,.0f}"
            }
        except: return {"orders": "0", "customers": "0", "revenue": "0", "profit": "0"}

    def get_recent_orders_dash(self):
        try:
            conn = self.connect()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            query = """
                SELECT i.InvoiceID, c.CustomerName, t.TableNumber, i.PaymentDate, i.TotalAmount,
                       COALESCE((SELECT SUM(Quantity * UnitPrice) FROM OrderDetails WHERE InvoiceID = i.InvoiceID), 0) as Subtotal,
                       CASE WHEN i.PaymentDate IS NULL THEN 'Pending' ELSE 'Paid' END as Status
                FROM Invoices i
                JOIN Customers c ON i.CustomerID = c.CustomerID
                JOIN DiningTables t ON i.TableID = t.TableID
                ORDER BY i.InvoiceID DESC
                LIMIT 5
            """
            cursor.execute(query)
            res = cursor.fetchall()
            conn.close()
            return res
        except:
            return []

    # --- LẤY CHI TIẾT MÓN ĂN CỦA HÓA ĐƠN ---
    def get_invoice_items(self, inv_id_str):
        try:
            iid = int(inv_id_str.replace("INV", ""))
            conn = self.connect()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                "SELECT m.DishName, od.UnitPrice, od.Quantity FROM OrderDetails od JOIN MenuItems m ON od.DishID = m.DishID WHERE od.InvoiceID = %s",
                (iid,)
            )
            res = cursor.fetchall()
            conn.close()
            return res
        except:
            return []

    def get_best_dishes_dash(self):
        try:
            conn = self.connect()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            query = """
                SELECT m.DishName, m.Price, m.ImageName, SUM(od.Quantity) as TotalOrders
                FROM MenuItems m JOIN OrderDetails od ON m.DishID = od.DishID
                GROUP BY m.DishID
                ORDER BY TotalOrders DESC
                LIMIT 4
            """
            cursor.execute(query)
            res = cursor.fetchall()
            conn.close()
            return res
        except:
            return []

    def get_chart_raw_data(self):
        try:
            conn = self.connect()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT TotalAmount, PaymentDate FROM Invoices WHERE PaymentDate IS NOT NULL")
            invs = cursor.fetchall()
            cursor.execute("SELECT Amount, ExpenseDate FROM Expenses WHERE ExpenseDate IS NOT NULL")
            exps = cursor.fetchall()
            cursor.execute("SELECT DateTime FROM Reservations WHERE DateTime IS NOT NULL")
            resv = cursor.fetchall()
            conn.close()
            return invs, exps, resv
        except:
            return [], [], []

    def get_menu_items(self, search_keyword="", category_filter="All Categories"):
        try:
            conn = self.connect()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            query = "SELECT DishID, DishName, Category, Price, ImageName FROM MenuItems WHERE DishName LIKE %s"
            params = [f"%{search_keyword}%"]
            if category_filter != "All Categories":
                query += " AND Category = %s"
                params.append(category_filter)
            query += " ORDER BY DishID ASC"
            cursor.execute(query, params)
            res = cursor.fetchall()
            conn.close()
            return res
        except:
            return []

    def get_expenses(self, category_filter="All Categories"):
        try:
            conn = self.connect(); cursor = conn.cursor(pymysql.cursors.DictCursor)
            query = "SELECT ExpenseID, Description, ExpenseCategory, ExpenseDate, Amount FROM Expenses"
            params = []
            if category_filter != "All Categories":
                query += " WHERE ExpenseCategory = %s"; params.append(category_filter)
            query += " ORDER BY ExpenseDate DESC"
            cursor.execute(query, params); res = cursor.fetchall(); conn.close(); return res
        except: return []

    def get_invoices(self, search_keyword="", status_filter="All Status"):
        try:
            conn = self.connect(); cursor = conn.cursor(pymysql.cursors.DictCursor)
            query = """
                SELECT i.InvoiceID, c.CustomerName, CAST(AES_DECRYPT(UNHEX(c.PhoneNumber), %s) AS CHAR) as Phone, 
                       t.TableNumber, i.PaymentDate, i.TotalAmount,
                       COALESCE((SELECT SUM(Quantity * UnitPrice) FROM OrderDetails WHERE InvoiceID = i.InvoiceID), 0) as Subtotal,
                       CASE WHEN i.PaymentDate IS NULL THEN 'Pending' ELSE 'Paid' END as Status
                FROM Invoices i JOIN Customers c ON i.CustomerID = c.CustomerID JOIN DiningTables t ON i.TableID = t.TableID
                WHERE (c.CustomerName LIKE %s OR i.PaymentDate LIKE %s)
            """
            params = [self.aes_key, f"%{search_keyword}%", f"%{search_keyword}%"]
            if status_filter != "All Status":
                query += " HAVING Status = %s"; params.append(status_filter)
            query += " ORDER BY i.InvoiceID DESC"
            cursor.execute(query, params); res = cursor.fetchall(); conn.close(); return res
        except: return []

    def get_reservations(self, search_keyword=""):
        try:
            conn = self.connect(); cursor = conn.cursor(pymysql.cursors.DictCursor)
            query = """
                SELECT r.ReservationID, c.CustomerName, CAST(AES_DECRYPT(UNHEX(c.PhoneNumber), %s) AS CHAR) as Phone, 
                       r.DateTime, t.TableNumber, r.GuestCount 
                FROM Reservations r JOIN Customers c ON r.CustomerID = c.CustomerID JOIN DiningTables t ON r.TableID = t.TableID
                WHERE c.CustomerName LIKE %s OR CAST(AES_DECRYPT(UNHEX(c.PhoneNumber), %s) AS CHAR) LIKE %s OR r.DateTime LIKE %s
                ORDER BY r.DateTime DESC
            """
            st = f"%{search_keyword}%"
            params = [self.aes_key, st, self.aes_key, st, st]
            cursor.execute(query, params); res = cursor.fetchall(); conn.close(); return res
        except: return []

    def get_all_customers_stats(self, search_keyword=""):
        try:
            conn = self.connect(); cursor = conn.cursor(pymysql.cursors.DictCursor); search_term = f"%{search_keyword}%"
            query = (
                "SELECT c.CustomerID, c.CustomerName, "
                "CAST(AES_DECRYPT(UNHEX(c.PhoneNumber), %s) AS CHAR) as Phone, "
                "c.Address, COUNT(i.InvoiceID) as OrdersPlaced, "
                "COALESCE(SUM(i.TotalAmount), 0) as TotalSpend "
                "FROM Customers c LEFT JOIN Invoices i ON c.CustomerID = i.CustomerID "
                "WHERE c.CustomerName LIKE %s "
                "OR CAST(AES_DECRYPT(UNHEX(c.PhoneNumber), %s) AS CHAR) LIKE %s "
                "GROUP BY c.CustomerID ORDER BY c.CustomerID DESC"
            )
            cursor.execute(query, (self.aes_key, search_term, self.aes_key, search_term)); res = cursor.fetchall(); conn.close(); return res
        except: return []

    def add_menu_item(self, dish_name, category, price, image_name=""):
        try:
            conn = self.connect(); cursor = conn.cursor()
            cursor.execute("INSERT INTO MenuItems (DishName, Category, Price, ImageName) VALUES (%s, %s, %s, %s)", (dish_name, category, price, image_name))
            conn.commit(); conn.close(); return True
        except: return False

db_manager = DatabaseManager()

# ==========================================
# WIDGET POPUP THÔNG BÁO 
# ==========================================
class ModernPopup(QDialog):
    def __init__(self, title, message, icon_name="fa5s.check-circle", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog); self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(440, 240) # ĐÃ SỬA: Tăng kích thước tổng để chứa bóng đổ
        layout = QVBoxLayout(self); layout.setContentsMargins(20, 20, 20, 20) # ĐÃ SỬA: Lùi lề 20px để bóng không bị cắt
        frame = QFrame(); frame.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 15px; border: 1px solid #D1D5DB; }") # ĐÃ SỬA: Thêm viền mảnh
        shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(20); shadow.setColor(QColor(0, 0, 0, 40)); shadow.setOffset(0, 5); frame.setGraphicsEffect(shadow)
        f_layout = QVBoxLayout(frame); f_layout.setContentsMargins(25, 25, 25, 25); f_layout.setSpacing(15)
        h_head = QHBoxLayout(); icon_lbl = QLabel(); icon_lbl.setPixmap(qta.icon(icon_name, color="#EF4444").pixmap(24, 24)); icon_lbl.setStyleSheet("border: none; background: transparent;"); title_lbl = QLabel(title); title_lbl.setFont(QFont('Nunito', 16, QFont.Bold)); title_lbl.setStyleSheet("color: #111827; border: none;"); h_head.addWidget(icon_lbl); h_head.addWidget(title_lbl); h_head.addStretch()
        msg_lbl = QLabel(message); msg_lbl.setWordWrap(True); msg_lbl.setFont(QFont('Nunito', 11)); msg_lbl.setStyleSheet("color: #4B5563; border: none;")
        btn_ok = QPushButton("Got it"); btn_ok.setCursor(QCursor(Qt.PointingHandCursor)); btn_ok.setFixedSize(100, 40); btn_ok.setStyleSheet(f"QPushButton {{ background-color: {RUBY_SOLID}; color: #FFFFFF; border: none; border-radius: 8px; font-weight: bold; font-family: 'Nunito'; font-size: 14px; }} QPushButton:hover {{ background-color: #801836; }}"); btn_ok.clicked.connect(self.accept)
        f_layout.addLayout(h_head); f_layout.addWidget(msg_lbl); f_layout.addWidget(btn_ok, alignment=Qt.AlignRight); layout.addWidget(frame)

class ModernConfirmPopup(QDialog):
    def __init__(self, title, message, icon_name="fa5s.exclamation-triangle", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(460, 240) # ĐÃ SỬA: Tăng không gian
        layout = QVBoxLayout(self); layout.setContentsMargins(20, 20, 20, 20) # ĐÃ SỬA: Lùi lề cho bóng đổ
        frame = QFrame(); frame.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 15px; border: 1px solid #D1D5DB; }")
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

class CustomerFormDialog(QDialog):
    def __init__(self, parent=None, cust_data=None):
        super().__init__(parent)
        self.cust_data = cust_data
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog); self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(490, 440) # ĐÃ SỬA: Tăng kích thước
        layout = QVBoxLayout(self); layout.setContentsMargins(20, 20, 20, 20) # ĐÃ SỬA: Lùi lề
        frame = QFrame(); frame.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 15px; border: 1px solid #D1D5DB; }")
        shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(20); shadow.setColor(QColor(0, 0, 0, 40)); shadow.setOffset(0, 5); frame.setGraphicsEffect(shadow)
        f_layout = QVBoxLayout(frame); f_layout.setContentsMargins(30, 30, 30, 30); f_layout.setSpacing(15)
        title = "Edit Customer" if cust_data else "Add New Customer"
        lbl_title = QLabel(title); lbl_title.setFont(QFont('Nunito', 18, QFont.Bold)); lbl_title.setStyleSheet("color: #111827; border: none;")
        f_layout.addWidget(lbl_title); f_layout.addSpacing(10)
        input_style = f"QLineEdit {{ background-color: #F9FAFB; border: 1px solid #D1D5DB; border-radius: 8px; padding: 12px 15px; font-family: {MODERN_FONT}; font-size: 14px; color: #111827; }} QLineEdit:focus {{ border: 1px solid #3B82F6; }}"
        self.txt_name = QLineEdit(); self.txt_name.setPlaceholderText("Customer Name"); self.txt_name.setStyleSheet(input_style)
        self.txt_phone = QLineEdit(); self.txt_phone.setPlaceholderText("Phone Number"); self.txt_phone.setStyleSheet(input_style)
        self.txt_address = QLineEdit(); self.txt_address.setPlaceholderText("Address (Optional)"); self.txt_address.setStyleSheet(input_style)
        if cust_data:
            self.txt_name.setText(cust_data['CustomerName']); self.txt_phone.setText(cust_data['Phone'] if cust_data['Phone'] else ""); self.txt_address.setText(cust_data['Address'] if cust_data['Address'] else "")
        f_layout.addWidget(QLabel("Full Name", styleSheet="color: #6B7280; font-weight: bold; font-family: 'Nunito'; border: none;")); f_layout.addWidget(self.txt_name)
        f_layout.addWidget(QLabel("Phone Number", styleSheet="color: #6B7280; font-weight: bold; font-family: 'Nunito'; border: none;")); f_layout.addWidget(self.txt_phone)
        f_layout.addWidget(QLabel("Address", styleSheet="color: #6B7280; font-weight: bold; font-family: 'Nunito'; border: none;")); f_layout.addWidget(self.txt_address)
        f_layout.addStretch()
        btn_layout = QHBoxLayout(); btn_cancel = QPushButton("Cancel"); btn_cancel.setCursor(QCursor(Qt.PointingHandCursor)); btn_cancel.setFixedSize(120, 40)
        btn_cancel.setStyleSheet("QPushButton { background-color: transparent; color: #4B5563; border: 1px solid #D1D5DB; border-radius: 8px; font-weight: bold; font-family: 'Nunito'; font-size: 14px; } QPushButton:hover { background-color: #F3F4F6; }")
        btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton("Save"); self.btn_save.setCursor(QCursor(Qt.PointingHandCursor)); self.btn_save.setFixedSize(120, 40)
        self.btn_save.setStyleSheet("QPushButton { background-color: #EF4444; color: #FFFFFF; border: none; border-radius: 8px; font-weight: bold; font-family: 'Nunito'; font-size: 14px; } QPushButton:hover { background-color: #DC2626; }")
        self.btn_save.clicked.connect(self.accept)
        btn_layout.addStretch(); btn_layout.addWidget(btn_cancel); btn_layout.addWidget(self.btn_save)
        f_layout.addLayout(btn_layout); layout.addWidget(frame)

# ==========================================
# COMPONENT: SIDEBAR BUTTON
# ==========================================
class SidebarButton(QPushButton):
    def __init__(self, icon_name, text, is_active=False):
        super().__init__()
        self.icon_name = icon_name; self.setText(f"   {text}"); self.setIconSize(QSize(20, 20)); self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFont(QFont('Nunito', 11, QFont.Bold)); self.is_active = is_active; self.update_style()
    def update_style(self):
        if self.is_active: self.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 0.2); color: #FFFFFF; border: none; border-radius: 12px; padding: 15px 20px; text-align: left; }")
        else: self.setStyleSheet("QPushButton { background-color: transparent; color: #FFFFFF; border: none; border-radius: 12px; padding: 15px 20px; text-align: left; } QPushButton:hover { background-color: rgba(255, 255, 255, 0.1); }")
        self.setIcon(qta.icon(self.icon_name, color='#FFFFFF'))

# ==========================================
# COMPONENT KPI CARD
# ==========================================
class KPICard(QFrame):
    def __init__(self, title, value, icon_name, is_primary=False):
        super().__init__()
        self.setFixedHeight(150); self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(20); shadow.setColor(QColor(0,0,0,8)); shadow.setOffset(0,4); self.setGraphicsEffect(shadow)
        if is_primary:
            self.setStyleSheet(f"QFrame {{ background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {BRIGHT_RED}, stop: 1 #4A0012); border-radius: 15px; border: none; }}")
            title_color = "#FFFFFF"; val_color = "#FFFFFF"; icon_bg = "rgba(255, 255, 255, 0.2)"; icon_color = "#FFFFFF"
        else:
            self.setStyleSheet("QFrame { background-color: white; border-radius: 15px; border: 1px solid #E5E7EB; }")
            title_color = "#6B7280"; val_color = "#111827"; icon_bg = "#FEE2E2"; icon_color = BRIGHT_RED
        layout = QHBoxLayout(self); layout.setContentsMargins(25, 20, 20, 20); layout.setSpacing(20)
        icon_frame = QFrame(); icon_frame.setFixedSize(65, 65); icon_frame.setStyleSheet(f"background-color: {icon_bg}; border-radius: 32px; border: none;") 
        icon_lay = QVBoxLayout(icon_frame); icon_lay.setAlignment(Qt.AlignCenter); lbl_icon = QLabel(); lbl_icon.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(30, 30)); icon_lay.addWidget(lbl_icon)
        text_lay = QVBoxLayout(); text_lay.setAlignment(Qt.AlignLeft | Qt.AlignVCenter); lbl_title = QLabel(title); lbl_title.setFont(QFont('Nunito', 13, QFont.Bold)); lbl_title.setStyleSheet(f"color: {title_color}; border: none; background: transparent;")
        
        # CHỈNH SỬA: Biến lbl_value thành self.lbl_value để có thể cập nhật
        self.lbl_value = QLabel(value)
        self.lbl_value.setFont(QFont("'Inter Black', 'Segoe UI Variable Display', 'Segoe UI Black', sans-serif", 26, QFont.Bold))
        self.lbl_value.setStyleSheet(f"color: {val_color}; border: none; background: transparent; margin-top: 5px;")
        
        text_lay.addWidget(lbl_title); text_lay.addWidget(self.lbl_value); layout.addWidget(icon_frame); layout.addLayout(text_lay); layout.addStretch()

    def update_value(self, new_val):
        self.lbl_value.setText(new_val)

# ==========================================
# KHUNG BIỂU ĐỒ (HOÀN THIỆN TOOLTIP KHÔNG CHẠM, CHUẨN ẢNH 7)
# ==========================================
class ChartCard(QFrame):
    def __init__(self, title, has_legend=False):
        super().__init__()
        self.setStyleSheet("QFrame { background-color: white; border-radius: 15px; border: 1px solid #E5E7EB; }"); self.setMinimumHeight(400) 
        shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(20); shadow.setColor(QColor(0,0,0,8)); shadow.setOffset(0,4); self.setGraphicsEffect(shadow)
        self.layout = QVBoxLayout(self); self.layout.setContentsMargins(25, 25, 25, 20)
        header = QHBoxLayout(); lbl_title = QLabel(title); lbl_title.setFont(QFont('Nunito', 15, QFont.Bold)); lbl_title.setStyleSheet("color: #111827; border: none;")
        self.dropdown = QComboBox(); self.dropdown.addItems(["This Week", "Last Week", "This Month"]); self.dropdown.setCursor(QCursor(Qt.PointingHandCursor))
        self.dropdown.setStyleSheet("QComboBox { background-color: #FFFFFF; color: #4B5563; font-family: 'Nunito'; font-weight: bold; font-size: 13px; border: 1px solid #D1D5DB; border-radius: 6px; padding: 6px 12px; } QComboBox:hover { border: 1px solid #9CA3AF; } QComboBox::drop-down { border: none; width: 24px; }")
        header.addWidget(lbl_title); header.addStretch(); header.addWidget(self.dropdown); self.layout.addLayout(header)
        
        self.dropdown.currentTextChanged.connect(self.update_chart)
        
        self.fig = Figure(dpi=100); self.fig.tight_layout(); self.canvas = FigureCanvas(self.fig); self.canvas.setStyleSheet("border: none;"); self.ax = self.fig.add_subplot(111)
        self.canvas_container = QWidget(); self.canvas_container.setStyleSheet("background: transparent;"); cc_lay = QVBoxLayout(self.canvas_container); cc_lay.setContentsMargins(0, 0, 0, 0); cc_lay.addWidget(self.canvas); self.layout.addWidget(self.canvas_container)
        
        self.tooltip_lbl = QLabel(self.canvas_container); self.tooltip_lbl.setStyleSheet("QLabel { background-color: #FFFFFF; border-radius: 8px; padding: 10px 15px; border: none; }"); shadow_tt = QGraphicsDropShadowEffect(); shadow_tt.setBlurRadius(15); shadow_tt.setColor(QColor(0, 0, 0, 40)); shadow_tt.setOffset(0, 4); self.tooltip_lbl.setGraphicsEffect(shadow_tt); self.tooltip_lbl.hide(); self.tooltip_lbl.setAttribute(Qt.WA_TransparentForMouseEvents) 
        self.hover_dot, = self.ax.plot([], [], 'o', color=BRIGHT_RED, markersize=9, zorder=300, markerfacecolor='white', markeredgewidth=2.5, markeredgecolor=BRIGHT_RED)
        self.canvas.mpl_connect("motion_notify_event", self.on_hover); self.canvas.mpl_connect("axes_leave_event", self._hide_tooltip)
        
        self.chart_type = None; self.x_data = None; self.y_data = None; self.y_data2 = None; self.x_labels = None; self.y_labels = None; self.hm_data = None

    def update_chart(self, text):
        if self.chart_type == 'line': self.draw_line_chart()
        elif self.chart_type == 'bar': self.draw_bar_chart()
        elif self.chart_type == 'heatmap': self.draw_heatmap()

    def _hide_tooltip(self, event=None):
        self.tooltip_lbl.hide()
        if self.hover_dot.get_visible(): self.hover_dot.set_visible(False); self.canvas.draw_idle()

    def _show_tooltip(self, data_x, data_y, text, dot_color=None, vertical_offset=45):
        self.tooltip_lbl.setText(text); self.tooltip_lbl.adjustSize()
        disp_xy = self.ax.transData.transform((data_x, data_y))
        canvas_w, canvas_h = self.canvas.width(), self.canvas.height()
        fig_w, fig_h = self.fig.get_size_inches() * self.fig.dpi
        px = disp_xy[0] * (canvas_w / fig_w); py = canvas_h - disp_xy[1] * (canvas_h / fig_h)
        tip_x = px - self.tooltip_lbl.width() // 2; tip_y = py - self.tooltip_lbl.height() - vertical_offset
        self.tooltip_lbl.move(max(5, min(int(tip_x), self.canvas_container.width()-self.tooltip_lbl.width()-5)), max(5, int(tip_y)))
        self.tooltip_lbl.show(); self.tooltip_lbl.raise_()
        if dot_color: self.hover_dot.set_data([data_x], [data_y]); self.hover_dot.set_markeredgecolor(dot_color); self.hover_dot.set_visible(True); self.canvas.draw_idle()

    def on_hover(self, event):
        if event.inaxes != self.ax: self._hide_tooltip(); return
        x, y = event.xdata, event.ydata
        if x is None or y is None: return
        
        if self.chart_type == 'line' and self.x_data is not None:
            idx = int(round(x))
            if 0 <= idx < len(self.x_data):
                y1, y2 = self.y_data[idx], self.y_data2[idx]
                if abs(y-y1) <= abs(y-y2): dy, c = y1, BRIGHT_RED
                else: dy, c = y2, EXPENSE_GREY
                
                # ĐÃ SỬA: Đổi dấu $ ở đầu thành chữ VND ở đuôi
                text = f"<div style='text-align: center;'><span style='font-size: 12px; color: #6B7280; font-family: \"Nunito\"; font-weight: bold;'>{self.x_labels[idx]}</span><br/><span style='font-size: 15px; color: #111827; font-family: \"Nunito\"; font-weight: 900;'>{dy:,.0f} VND</span></div>"
                self._show_tooltip(idx, dy, text, dot_color=c, vertical_offset=35)
                return
                
        elif self.chart_type == 'bar' and self.x_data is not None:
            idx = int(round(x))
            if 0 <= idx < len(self.x_data) and abs(x-idx) < 0.4:
                val = self.y_data[idx]
                if 0 <= y <= val * 1.2:
                    text = f"<div style='text-align: center;'><span style='font-size: 12px; color: #6B7280; font-family: \"Nunito\"; font-weight: bold;'>{self.x_labels[idx]}</span><br/><span style='font-size: 15px; color: #111827; font-family: \"Nunito\"; font-weight: 900;'>{int(val)} orders</span></div>"
                    self._show_tooltip(idx, val, text, vertical_offset=45)
                    return

        elif self.chart_type == 'heatmap' and self.hm_data is not None:
            j = int(round(x)); i = int(round(y))
            if 0 <= i < self.hm_data.shape[0] and 0 <= j < self.hm_data.shape[1]:
                if abs(x - j) < 0.45 and abs(y - i) < 0.45:
                    val = self.hm_data[i, j]
                    text = f"<div style='text-align: center;'><span style='font-size: 13px; color: #6B7280; font-family: \"Nunito\"; font-weight: bold;'>{self.x_labels[j]} - {self.y_labels[i]}</span><br/><span style='font-size: 16px; color: #111827; font-family: \"Nunito\"; font-weight: 900;'>{int(val)} Reservations</span></div>"
                    self._show_tooltip(j, i, text, vertical_offset=35)
                    return
        self._hide_tooltip()

    def _get_agg_data(self):
        period = self.dropdown.currentText()
        invs, exps, resvs = db_manager.get_chart_raw_data()
        import datetime
        income = np.zeros(7); expense = np.zeros(7); orders = np.zeros(7)
        if period == "This Month":
            income = np.zeros(4); expense = np.zeros(4); orders = np.zeros(4)
            for r in invs:
                w = min(3, (r['PaymentDate'].day - 1) // 7)
                income[w] += float(r['TotalAmount']); orders[w] += 1
            for r in exps:
                w = min(3, (r['ExpenseDate'].day - 1) // 7)
                expense[w] += float(r['Amount'])
            return ['Week 1', 'Week 2', 'Week 3', 'Week 4'], income, expense, orders
        else:
            # Phân tách 2 tuần trong April 2026 (Tuần 15-21 và Tuần 8-14)
            for r in invs:
                day = r['PaymentDate'].day; wd = r['PaymentDate'].weekday()
                if period == "This Week" and day >= 15:
                    income[wd] += float(r['TotalAmount']); orders[wd] += 1
                elif period == "Last Week" and day < 15:
                    income[wd] += float(r['TotalAmount']); orders[wd] += 1
            for r in exps:
                day = r['ExpenseDate'].day; wd = r['ExpenseDate'].weekday()
                if period == "This Week" and day >= 15:
                    expense[wd] += float(r['Amount'])
                elif period == "Last Week" and day < 15:
                    expense[wd] += float(r['Amount'])
            return ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], income, expense, orders

    def draw_line_chart(self):
        self.ax.clear()
        days, income, expense, _ = self._get_agg_data()
        self.chart_type = 'line'; self.x_data = np.arange(len(days)); self.y_data, self.y_data2, self.x_labels = income, expense, days
        if HAS_SCIPY and len(days) > 3 and sum(income)>0:
            x_idx = np.arange(len(days)); x_sm = np.linspace(x_idx.min(), x_idx.max(), 300); spl1 = make_interp_spline(x_idx, income, k=3); spl2 = make_interp_spline(x_idx, expense, k=3)
            self.ax.plot(x_sm, spl1(x_sm), color=BRIGHT_RED, linewidth=3); self.ax.plot(x_sm, spl2(x_sm), color=EXPENSE_GREY, linewidth=3); self.ax.fill_between(x_sm, spl1(x_sm), alpha=0.08, color=BRIGHT_RED); self.ax.fill_between(x_sm, spl2(x_sm), alpha=0.05, color=EXPENSE_GREY)
        else: self.ax.plot(days, income, color=BRIGHT_RED, linewidth=3); self.ax.plot(days, expense, color=EXPENSE_GREY, linewidth=3)
        self.ax.plot(self.x_data, income, 'o', markersize=6, color=BRIGHT_RED); self.ax.plot(self.x_data, expense, 'o', markersize=6, color=EXPENSE_GREY); self.format_ax(days); self.canvas.draw()

    def draw_bar_chart(self):
        self.ax.clear()
        days, _, _, orders = self._get_agg_data()
        x_pos = np.arange(len(days)); self.chart_type = 'bar'; self.x_data, self.y_data, self.x_labels = x_pos, orders, days
        if sum(orders) == 0: self.format_ax(days); self.canvas.draw(); return
        self.ax.vlines(x=x_pos, ymin=0, ymax=orders, color='#FEE2E2', linewidth=40, capstyle='round')
        max_idx = np.argmax(orders)
        self.ax.vlines(x=x_pos[max_idx], ymin=0, ymax=orders[max_idx], color=BRIGHT_RED, linewidth=40, capstyle='round')
        self.format_ax(days); self.ax.set_ylim(0, max(orders) * 1.15); self.canvas.draw()

    def draw_heatmap(self):
        self.ax.clear(); times = ['18:00', '18:30', '19:00', '19:30', '20:00', '20:30', '21:00', '21:30', '22:00']
        period = self.dropdown.currentText()
        invs, exps, resvs = db_manager.get_chart_raw_data()
        
        if period == "This Month":
            days = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
            data = np.zeros((len(times), len(days)))
            for r in resvs:
                d = r['DateTime']
                w = min(3, (d.day - 1) // 7)
                t_str = d.strftime('%H:%M')
                if t_str in times: data[times.index(t_str), w] += 1
        else:
            days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            data = np.zeros((len(times), len(days)))
            for r in resvs:
                d = r['DateTime']
                wd = d.weekday()
                if (period == "This Week" and d.day >= 15) or (period == "Last Week" and d.day < 15):
                    t_str = d.strftime('%H:%M')
                    if t_str in times: data[times.index(t_str), wd] += 1
            
        self.chart_type = 'heatmap'; self.hm_data, self.x_labels, self.y_labels = data, days, times
        import matplotlib.colors as mcolors; cmap = mcolors.LinearSegmentedColormap.from_list("", ["#FEE2E2", BRIGHT_RED]); norm = mcolors.Normalize(vmin=0, vmax=max(1, np.max(data)))
        for i in range(len(times)):
            for j in range(len(days)): self.ax.add_patch(patches.FancyBboxPatch((j-0.35, i-0.35), 0.7, 0.7, boxstyle="round,pad=0.01,rounding_size=0.15", facecolor=cmap(norm(data[i, j])), edgecolor='none'))
        self.ax.set_xlim(-0.6, len(days)-0.4); self.ax.set_ylim(len(times)-0.4, -0.6); self.ax.set_xticks(np.arange(len(days))); self.ax.set_yticks(np.arange(len(times))); self.ax.set_xticklabels(days); self.ax.set_yticklabels(times); self.ax.spines['top'].set_visible(False); self.ax.spines['right'].set_visible(False); self.ax.spines['bottom'].set_visible(False); self.ax.spines['left'].set_visible(False); self.ax.tick_params(axis='both', length=0, colors='#6B7280', pad=10); self.canvas.draw()

    def format_ax(self, x_labels=None):
        self.ax.spines['top'].set_visible(False); self.ax.spines['right'].set_visible(False); self.ax.spines['left'].set_visible(False); self.ax.spines['bottom'].set_color('#E5E7EB')
        if x_labels: self.ax.set_xticks(np.arange(len(x_labels))); self.ax.set_xticklabels(x_labels)
        self.ax.tick_params(axis='both', colors='#9CA3AF', length=0, pad=10, labelsize=10); self.ax.yaxis.grid(True, color='#F3F4F6', linestyle='-', linewidth=1.5); self.ax.set_axisbelow(True)

class BestDishesCard(QFrame):
    def __init__(self):
        super().__init__(); self.setStyleSheet("QFrame { background-color: white; border-radius: 15px; border: 1px solid #E5E7EB; }"); self.setMinimumHeight(450); shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(20); shadow.setColor(QColor(0,0,0,8)); shadow.setOffset(0,4); self.setGraphicsEffect(shadow)
        layout = QVBoxLayout(self); layout.setContentsMargins(25, 25, 25, 25); header = QHBoxLayout(); lbl_title = QLabel("Best Dishes"); lbl_title.setFont(QFont('Nunito', 16, QFont.Bold)); lbl_title.setStyleSheet("color: #111827; border: none;"); header.addWidget(lbl_title); header.addStretch(); layout.addLayout(header); layout.addSpacing(10)
        col_header = QHBoxLayout(); h1 = QLabel("Dishes"); h1.setFont(QFont('Nunito', 13, QFont.Bold)); h1.setStyleSheet("color: #9CA3AF; border: none;"); col_header.addWidget(h1); col_header.addStretch(); h2 = QLabel("Orders"); h2.setFont(QFont('Nunito', 13, QFont.Bold)); h2.setStyleSheet("color: #9CA3AF; border: none;"); col_header.addWidget(h2); layout.addLayout(col_header); layout.addSpacing(15)
        
        db_dishes = db_manager.get_best_dishes_dash()
        for item in db_dishes:
            name = item['DishName']
            price = f"{float(item['Price']):,.0f}"
            orders = int(item['TotalOrders'])
            
            # ĐÃ SỬA: Lấy tên ảnh trực tiếp từ Database
            img = item['ImageName'] if item.get('ImageName') else "default.jpg"
            
            row = QHBoxLayout(); img_lbl = QLabel(); img_lbl.setFixedSize(50, 50); current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # ĐÃ SỬA LỖI QPIXMAP Ở ĐÂY: Load ảnh trước, check tồn tại rồi mới scaled
            pixmap = QPixmap(os.path.join(current_dir, 'menu_images', img))
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(50, 50, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                rounded = QPixmap(scaled_pixmap.size()); rounded.fill(Qt.transparent); painter = QPainter(rounded); painter.setRenderHint(QPainter.Antialiasing); path = QPainterPath(); path.addRoundedRect(0, 0, scaled_pixmap.width(), scaled_pixmap.height(), 10, 10); painter.setClipPath(path); painter.drawPixmap(0, 0, scaled_pixmap); painter.end(); img_lbl.setPixmap(rounded)
            
            img_lbl.setStyleSheet("background-color: #F3F4F6; border: none; border-radius: 10px;"); info_widget = QWidget(); info_lay = QVBoxLayout(info_widget); info_lay.setContentsMargins(0, 0, 0, 0); info_lay.setSpacing(4); n_lbl = QLabel(name); n_lbl.setFont(QFont('Nunito', 13, QFont.Bold)); n_lbl.setStyleSheet("color: #111827; border: none; padding: 0px;"); n_lbl.setMinimumHeight(22); p_lbl = QLabel(f"{price} VND"); p_lbl.setFont(QFont('Nunito', 11, QFont.Bold)); p_lbl.setStyleSheet(f"color: {BRIGHT_RED}; border: none; padding: 0px;"); p_lbl.setMinimumHeight(20); info_lay.addWidget(n_lbl); info_lay.addWidget(p_lbl); info_lay.setAlignment(Qt.AlignVCenter); o_lbl = QLabel(str(orders)); o_lbl.setFont(QFont('Nunito', 15, QFont.Bold)); o_lbl.setStyleSheet("color: #111827; border: none;"); row.addWidget(img_lbl); row.addSpacing(15); row.addWidget(info_widget); row.addStretch(); row.addWidget(o_lbl); layout.addLayout(row); layout.addSpacing(25) 
        layout.addStretch()

# ==========================================
# TRANG THÊM MÓN ĂN
# ==========================================
class AddMenuItemPage(QWidget):
    dish_saved = pyqtSignal(); cancelled = pyqtSignal()
    CATEGORIES = ["Main Course", "Appetizer", "Dessert", "Beverage"]; BORDEAUX = "#5C1A2E"; TEXT_DARK = "#1A0A0F"; TEXT_GRAY = "#7B5B65"; ROSE_MID = "#E8C5D0"; ROSE_LIGHT = "#FCE8EE"
    def __init__(self, parent=None):
        super().__init__(parent); self.selected_image_path = ""; self.saved_image_name = ""; self.setStyleSheet(f"background-color: {BG_COLOR};"); self._build_ui()
    def reset(self):
        self.txt_name.clear(); self.txt_price.clear(); self.combo_cat.setCurrentIndex(0); self.selected_image_path = ""; self.saved_image_name = ""; self.lbl_filename.setText("No file chosen"); self.img_preview.setPixmap(qta.icon('fa5s.image', color='rgba(255,255,255,0.45)').pixmap(48, 48)); self.img_preview.setStyleSheet(f"QLabel {{ background-color: rgba(255,255,255,0.12); border: 3px dashed #FFFFFF; border-radius: 16px; }}")
    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(60, 40, 60, 40); root.setSpacing(0); nav_row = QHBoxLayout(); self.btn_back = QPushButton(qta.icon('fa5s.arrow-left', color='#7B5B65'), "  Back to Menu"); self.btn_back.setCursor(QCursor(Qt.PointingHandCursor)); self.btn_back.setFixedHeight(38); self.btn_back.setStyleSheet(f"QPushButton {{ background: transparent; border: none; color: {self.TEXT_GRAY}; font-family: 'Nunito'; font-weight: bold; font-size: 13px; }} QPushButton:hover {{ color: {RUBY_SOLID}; }}"); self.btn_back.clicked.connect(self.cancelled.emit); nav_row.addWidget(self.btn_back); nav_row.addStretch(); root.addLayout(nav_row); root.addSpacing(16); lbl_title = QLabel("New Dish"); lbl_title.setFont(QFont('Nunito', 28, QFont.Bold)); lbl_title.setStyleSheet(f"color: {self.TEXT_DARK}; background: transparent;"); root.addWidget(lbl_title); lbl_sub = QLabel("Fill in the details below to add a new item to your menu."); lbl_sub.setFont(QFont('Nunito', 13)); lbl_sub.setStyleSheet(f"color: {self.TEXT_GRAY}; background: transparent;"); root.addWidget(lbl_sub); root.addSpacing(30); card = QFrame(); card.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 20px; border: none; }"); shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(30); shadow.setColor(QColor(92, 26, 46, 28)); shadow.setOffset(0, 6); card.setGraphicsEffect(shadow); root.addWidget(card); card_lay = QHBoxLayout(card); card_lay.setContentsMargins(0, 0, 0, 0); card_lay.setSpacing(0); left_panel = QFrame(); left_panel.setFixedWidth(280); left_panel.setStyleSheet(f"QFrame {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {self.BORDEAUX}, stop:1 {RUBY_SOLID}); border-top-left-radius: 20px; border-bottom-left-radius: 20px; border: none; }}"); lp_lay = QVBoxLayout(left_panel); lp_lay.setContentsMargins(30, 40, 30, 40); lp_lay.setSpacing(20); deco_lbl = QLabel(); deco_lbl.setPixmap(qta.icon('fa5s.utensils', color='#FFFFFF').pixmap(64, 64)); deco_lbl.setStyleSheet("border: none; background: transparent;"); deco_lbl.setAlignment(Qt.AlignCenter); lp_title = QLabel("Dish\nPhoto"); lp_title.setFont(QFont('Nunito', 22, QFont.Bold)); lp_title.setStyleSheet("color: #FFFFFF; background: transparent; border: none;"); lp_title.setAlignment(Qt.AlignCenter); self.img_preview = QLabel(); self.img_preview.setFixedSize(140, 140); self.img_preview.setAlignment(Qt.AlignCenter); self.img_preview.setStyleSheet(f"QLabel {{ background-color: rgba(255,255,255,0.12); border: 3px dashed #FFFFFF; border-radius: 16px; }}"); self.img_preview.setPixmap(qta.icon('fa5s.image', color='rgba(255,255,255,0.45)').pixmap(48, 48)); btn_upload_img = QPushButton("  Choose Photo"); btn_upload_img.setIcon(qta.icon('fa5s.camera', color='#FFFFFF')); btn_upload_img.setCursor(QCursor(Qt.PointingHandCursor)); btn_upload_img.setFixedHeight(42); btn_upload_img.setStyleSheet("QPushButton { background: rgba(255,255,255,0.18); color: #FFFFFF; border: 1px solid rgba(255,255,255,0.35); border-radius: 10px; font-family: 'Nunito'; font-weight: bold; font-size: 13px; } QPushButton:hover { background: rgba(255,255,255,0.28); }"); btn_upload_img.clicked.connect(self._choose_image); self.lbl_filename = QLabel("No file chosen"); self.lbl_filename.setFont(QFont('Nunito', 10)); self.lbl_filename.setWordWrap(True); self.lbl_filename.setStyleSheet("color: rgba(255,255,255,0.50); border: none; background: transparent;"); self.lbl_filename.setAlignment(Qt.AlignCenter); lp_lay.addStretch(); lp_lay.addWidget(deco_lbl); lp_lay.addWidget(lp_title); lp_lay.addSpacing(10); lp_lay.addWidget(self.img_preview, alignment=Qt.AlignCenter); lp_lay.addSpacing(10); lp_lay.addWidget(btn_upload_img); lp_lay.addWidget(self.lbl_filename); lp_lay.addStretch(); card_lay.addWidget(left_panel); right_panel = QWidget(); right_panel.setStyleSheet("background: transparent;"); rp_lay = QVBoxLayout(right_panel); rp_lay.setContentsMargins(45, 45, 45, 45); rp_lay.setSpacing(0); label_ss = f"color: {self.TEXT_GRAY}; font-weight: bold; font-family: 'Nunito'; font-size: 11px; letter-spacing: 1px; border: none; background: transparent;"; input_ss = f"QLineEdit {{ background-color: #FAFAFA; border: 1.5px solid {self.ROSE_MID}; border-radius: 10px; padding: 13px 16px; font-family: 'Nunito'; font-size: 14px; color: {self.TEXT_DARK}; }} QLineEdit:focus {{ border: 1.5px solid {RUBY_SOLID}; background-color: {self.ROSE_LIGHT}; }}"; combo_ss = f"QComboBox {{ background-color: #FAFAFA; border: 1.5px solid {self.ROSE_MID}; border-radius: 10px; padding: 13px 16px; font-family: 'Nunito'; font-size: 14px; color: {self.TEXT_DARK}; }} QComboBox:focus {{ border: 1.5px solid {RUBY_SOLID}; }} QComboBox::drop-down {{ border: none; width: 32px; }} QComboBox QAbstractItemView {{ border: 1px solid {self.ROSE_MID}; border-radius: 8px; background: #FFFFFF; outline: none; padding: 4px; selection-background-color: {self.ROSE_LIGHT}; selection-color: {RUBY_SOLID}; }} QComboBox QAbstractItemView::item {{ min-height: 36px; padding-left: 12px; font-family: 'Nunito'; font-size: 13px; color: {self.TEXT_DARK}; border-radius: 6px; }}"
        def field(l, w): lbl = QLabel(l, styleSheet=label_ss); rp_lay.addWidget(lbl); rp_lay.addSpacing(6); rp_lay.addWidget(w); rp_lay.addSpacing(22)
        self.txt_name = QLineEdit(); self.txt_name.setPlaceholderText("e.g.  Wagyu Ribeye Steak"); self.txt_name.setFixedHeight(50); self.txt_name.setStyleSheet(input_ss); field("DISH NAME", self.txt_name); self.combo_cat = QComboBox(); self.combo_cat.addItems(self.CATEGORIES); self.combo_cat.setFixedHeight(50); self.combo_cat.setStyleSheet(combo_ss); field("CATEGORY", self.combo_cat); self.txt_price = QLineEdit(); self.txt_price.setPlaceholderText("e.g.  1,500,000"); self.txt_price.setFixedHeight(50); self.txt_price.setStyleSheet(input_ss); price_row = QHBoxLayout(); price_row.setSpacing(10); price_row.addWidget(self.txt_price); lbl_vnd = QLabel("VND"); lbl_vnd.setFixedHeight(50); lbl_vnd.setAlignment(Qt.AlignCenter); lbl_vnd.setStyleSheet(f"QLabel {{ background-color: {self.ROSE_LIGHT}; color: {RUBY_SOLID}; border-radius: 10px; padding: 0 16px; font-family: 'Nunito'; font-weight: bold; font-size: 13px; border: none; }}"); price_row.addWidget(lbl_vnd); rp_lay.addWidget(QLabel("PRICE", styleSheet=label_ss)); rp_lay.addSpacing(6); rp_lay.addLayout(price_row); rp_lay.addSpacing(22); rp_lay.addStretch(); div = QFrame(); div.setFixedHeight(1); div.setStyleSheet(f"background-color: {self.ROSE_MID}; border: none;"); rp_lay.addWidget(div); rp_lay.addSpacing(22); footer = QHBoxLayout(); footer.setSpacing(12); btn_cancel = QPushButton("Cancel"); btn_cancel.setFixedHeight(48); btn_cancel.setMinimumWidth(120); btn_cancel.setCursor(QCursor(Qt.PointingHandCursor)); btn_cancel.setStyleSheet(f"QPushButton {{ background: transparent; color: {self.TEXT_GRAY}; border: 1.5px solid #D1D5DB; border-radius: 10px; font-family: 'Nunito'; font-weight: bold; font-size: 14px; }} QPushButton:hover {{ background: {self.ROSE_LIGHT}; border-color: {self.ROSE_MID}; color: {RUBY_SOLID}; }}"); btn_cancel.clicked.connect(self.cancelled.emit); self.btn_save = QPushButton("  Save Change"); self.btn_save.setIcon(qta.icon('fa5s.check', color='#FFFFFF')); self.btn_save.setFixedHeight(48); self.btn_save.setMinimumWidth(160); self.btn_save.setCursor(QCursor(Qt.PointingHandCursor)); self.btn_save.setStyleSheet(f"QPushButton {{ background-color: {RUBY_SOLID}; color: #FFFFFF; border: none; border-radius: 10px; font-family: 'Nunito'; font-weight: bold; font-size: 14px; }} QPushButton:hover {{ background-color: #801836; }}"); self.btn_save.clicked.connect(self._on_save); footer.addStretch(); footer.addWidget(btn_cancel); footer.addWidget(self.btn_save); rp_lay.addLayout(footer); card_lay.addWidget(right_panel, stretch=1); root.addStretch()

    def _choose_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Dish Image", "", "Image Files (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not path: return
        self.selected_image_path = path; self.lbl_filename.setText(os.path.basename(path)); px = QPixmap(path)
        if not px.isNull():
            scaled = px.scaled(140, 140, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            crop = scaled.copy(QRect((scaled.width()-140)//2, (scaled.height()-140)//2, 140, 140)); rounded = QPixmap(140, 140); rounded.fill(Qt.transparent); painter = QPainter(rounded); painter.setRenderHint(QPainter.Antialiasing); ppath = QPainterPath(); ppath.addRoundedRect(0, 0, 140, 140, 16, 16); painter.setClipPath(ppath); painter.drawPixmap(0, 0, crop); painter.end(); self.img_preview.setPixmap(rounded)
            self.img_preview.setStyleSheet("QLabel { background-color: transparent; border: 3px dashed #FFFFFF; border-radius: 16px; }")

    def _on_save(self):
        name = self.txt_name.text().strip(); cat = self.combo_cat.currentText(); price = self.txt_price.text().strip()
        if not name: ModernPopup("Error", "Name required.", "fa5s.exclamation-circle", self).exec_(); return
        image_name = ""
        if self.selected_image_path:
            current_dir = os.path.dirname(os.path.abspath(__file__)); images_dir = os.path.join(current_dir, 'menu_images'); os.makedirs(images_dir, exist_ok=True); image_name = os.path.basename(self.selected_image_path); shutil.copy2(self.selected_image_path, os.path.join(images_dir, image_name))
        ok = db_manager.add_menu_item(name, cat, float(price.replace(",", "").replace(".", "")), image_name)
        if ok: self.dish_saved.emit()

# ==========================================
# TRANG THÊM CHI PHÍ 
# ==========================================
class AddExpensePage(QWidget):
    expense_saved = pyqtSignal(); cancelled = pyqtSignal()
    CATEGORIES = ["Ingredients", "Marketing", "Maintenance", "Payroll", "Utilities", "Supplies"]; BORDEAUX = "#5C1A2E"; TEXT_DARK = "#1A0A0F"; TEXT_GRAY = "#7B5B65"; ROSE_MID = "#E8C5D0"; ROSE_LIGHT = "#FCE8EE"
    def __init__(self, parent=None):
        super().__init__(parent); self.setStyleSheet(f"background-color: {BG_COLOR};"); self._build_ui()
    def reset(self):
        self.txt_desc.clear(); self.txt_amount.clear(); self.txt_date.clear(); self.combo_cat.setCurrentIndex(0)
    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(60, 40, 60, 40); root.setSpacing(0); nav_row = QHBoxLayout(); self.btn_back = QPushButton(qta.icon('fa5s.arrow-left', color='#7B5B65'), "  Back to Expenses"); self.btn_back.setFixedHeight(38); self.btn_back.setStyleSheet(f"QPushButton {{ background: transparent; border: none; color: {self.TEXT_GRAY}; font-family: 'Nunito'; font-weight: bold; font-size: 13px; }} QPushButton:hover {{ color: {RUBY_SOLID}; }}"); self.btn_back.clicked.connect(self.cancelled.emit); nav_row.addWidget(self.btn_back); nav_row.addStretch(); root.addLayout(nav_row); root.addSpacing(16); lbl_page_title = QLabel("New Expense"); lbl_page_title.setFont(QFont('Nunito', 28, QFont.Bold)); lbl_page_title.setStyleSheet(f"color: {self.TEXT_DARK}; background: transparent;"); root.addWidget(lbl_page_title); lbl_sub = QLabel("Record a new operating expense."); lbl_sub.setFont(QFont('Nunito', 13)); lbl_sub.setStyleSheet(f"color: {self.TEXT_GRAY}; background: transparent;"); root.addWidget(lbl_sub); root.addSpacing(30); card = QFrame(); card.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 20px; border: none; }"); shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(30); shadow.setColor(QColor(92, 26, 46, 28)); shadow.setOffset(0, 6); card.setGraphicsEffect(shadow); root.addWidget(card); card_lay = QHBoxLayout(card); card_lay.setContentsMargins(0, 0, 0, 0); card_lay.setSpacing(0); left_panel = QFrame(); left_panel.setFixedWidth(280); left_panel.setStyleSheet(f"QFrame {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {self.BORDEAUX}, stop:1 {RUBY_SOLID}); border-top-left-radius: 20px; border-bottom-left-radius: 20px; border: none; }}"); lp_lay = QVBoxLayout(left_panel); lp_lay.setContentsMargins(30, 40, 30, 40); lp_lay.setSpacing(20); deco_lbl = QLabel(); deco_lbl.setPixmap(qta.icon('fa5s.file-invoice-dollar', color='#FFFFFF').pixmap(80, 80)); deco_lbl.setStyleSheet("border: none; background: transparent;"); deco_lbl.setAlignment(Qt.AlignCenter); lp_title = QLabel("Add\nExpense"); lp_title.setFont(QFont('Nunito', 22, QFont.Bold)); lp_title.setStyleSheet("color: #FFFFFF; background: transparent; border: none;"); lp_title.setAlignment(Qt.AlignCenter); lp_lay.addStretch(); lp_lay.addWidget(deco_lbl); lp_lay.addWidget(lp_title); lp_lay.addStretch(); card_lay.addWidget(left_panel); right_panel = QWidget(); right_panel.setStyleSheet("background: transparent;"); rp_lay = QVBoxLayout(right_panel); rp_lay.setContentsMargins(45, 45, 45, 45); rp_lay.setSpacing(0); label_ss = f"color: {self.TEXT_GRAY}; font-weight: bold; font-family: 'Nunito'; font-size: 11px; letter-spacing: 1px; border: none; background: transparent;"; input_ss = f"QLineEdit {{ background-color: #FAFAFA; border: 1.5px solid {self.ROSE_MID}; border-radius: 10px; padding: 13px 16px; font-family: 'Nunito'; font-size: 14px; color: {self.TEXT_DARK}; }} QLineEdit:focus {{ border: 1.5px solid {RUBY_SOLID}; background-color: {self.ROSE_LIGHT}; }}"; combo_ss = f"QComboBox {{ background-color: #FAFAFA; border: 1.5px solid {self.ROSE_MID}; border-radius: 10px; padding: 13px 16px; font-family: 'Nunito'; font-size: 14px; color: {self.TEXT_DARK}; }} QComboBox:focus {{ border: 1.5px solid {RUBY_SOLID}; }} QComboBox::drop-down {{ border: none; width: 32px; }} QComboBox QAbstractItemView {{ border: 1px solid {self.ROSE_MID}; border-radius: 8px; background: #FFFFFF; outline: none; padding: 4px; selection-background-color: {self.ROSE_LIGHT}; selection-color: {RUBY_SOLID}; }} QComboBox QAbstractItemView::item {{ min-height: 36px; padding-left: 12px; font-family: 'Nunito'; font-size: 13px; color: {self.TEXT_DARK}; border-radius: 6px; }}"
        def field(l, w): lbl = QLabel(l, styleSheet=label_ss); rp_lay.addWidget(lbl); rp_lay.addSpacing(6); rp_lay.addWidget(w); rp_lay.addSpacing(22)
        self.txt_desc = QLineEdit(); self.txt_desc.setPlaceholderText("e.g. Electricity Bill"); self.txt_desc.setFixedHeight(50); self.txt_desc.setStyleSheet(input_ss); field("DESCRIPTION", self.txt_desc); self.combo_cat = QComboBox(); self.combo_cat.addItems(self.CATEGORIES); self.combo_cat.setFixedHeight(50); self.combo_cat.setStyleSheet(combo_ss); field("CATEGORY", self.combo_cat); self.txt_amount = QLineEdit(); self.txt_amount.setPlaceholderText("e.g. 5,000,000"); self.txt_amount.setFixedHeight(50); self.txt_amount.setStyleSheet(input_ss); field("AMOUNT (VND)", self.txt_amount); self.txt_date = QLineEdit(); self.txt_date.setPlaceholderText("YYYY-MM-DD"); self.txt_date.setFixedHeight(50); self.txt_date.setStyleSheet(input_ss); field("EXPENSE DATE", self.txt_date); rp_lay.addStretch(); div = QFrame(); div.setFixedHeight(1); div.setStyleSheet(f"background-color: {self.ROSE_MID}; border: none;"); rp_lay.addWidget(div); rp_lay.addSpacing(22); footer = QHBoxLayout(); footer.setSpacing(12); btn_cancel = QPushButton("Cancel"); btn_cancel.setFixedHeight(48); btn_cancel.setMinimumWidth(120); btn_cancel.setStyleSheet(f"QPushButton {{ background: transparent; color: {self.TEXT_GRAY}; border: 1.5px solid #D1D5DB; border-radius: 10px; font-family: 'Nunito'; font-weight: bold; font-size: 14px; }} QPushButton:hover {{ background: {self.ROSE_LIGHT}; border-color: {RUBY_SOLID}; color: {RUBY_SOLID}; }}"); btn_cancel.clicked.connect(self.cancelled.emit); btn_save = QPushButton("  Save Change"); btn_save.setFixedHeight(48); btn_save.setMinimumWidth(160)
        btn_save.setStyleSheet(f"QPushButton {{ background-color: {RUBY_SOLID}; color: #FFFFFF; border: none; border-radius: 10px; font-family: 'Nunito'; font-weight: bold; font-size: 14px; }} QPushButton:hover {{ background-color: #801836; }}"); btn_save.clicked.connect(lambda: self.expense_saved.emit()); footer.addStretch(); footer.addWidget(btn_cancel); footer.addWidget(btn_save); rp_lay.addLayout(footer); card_lay.addWidget(right_panel, stretch=1); root.addStretch()

# ==========================================
# TRANG SỬA THÔNG TIN KHÁCH HÀNG (FULL PAGE GIỐNG ẢNH 2)
# ==========================================
class EditCustomerPage(QWidget):
    customer_saved = pyqtSignal(); cancelled = pyqtSignal()
    BORDEAUX = "#5C1A2E"; TEXT_DARK = "#1A0A0F"; TEXT_GRAY = "#7B5B65"; ROSE_MID = "#E8C5D0"; ROSE_LIGHT = "#FCE8EE"
    def __init__(self, parent=None):
        super().__init__(parent); self.cid = ""; self.setStyleSheet(f"background-color: {BG_COLOR};"); self._build_ui()
    def load_data(self, cid, name, phone, address):
        self.cid = cid; self.txt_name.setText(name); self.txt_phone.setText(phone); self.txt_address.setText(address)
    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(60, 40, 60, 40); root.setSpacing(0); nav_row = QHBoxLayout(); self.btn_back = QPushButton(qta.icon('fa5s.arrow-left', color='#7B5B65'), "  Back to Customers"); self.btn_back.setFixedHeight(38); self.btn_back.setStyleSheet(f"QPushButton {{ background: transparent; border: none; color: {self.TEXT_GRAY}; font-family: 'Nunito'; font-weight: bold; font-size: 13px; }} QPushButton:hover {{ color: {RUBY_SOLID}; }}"); self.btn_back.clicked.connect(self.cancelled.emit); nav_row.addWidget(self.btn_back); nav_row.addStretch(); root.addLayout(nav_row); root.addSpacing(16); lbl_page_title = QLabel("Edit Customer"); lbl_page_title.setFont(QFont('Nunito', 28, QFont.Bold)); lbl_page_title.setStyleSheet(f"color: {self.TEXT_DARK}; background: transparent;"); root.addWidget(lbl_page_title); lbl_sub = QLabel("Update customer details below."); lbl_sub.setFont(QFont('Nunito', 13)); lbl_sub.setStyleSheet(f"color: {self.TEXT_GRAY}; background: transparent;"); root.addWidget(lbl_sub); root.addSpacing(30); card = QFrame(); card.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 20px; border: none; }"); shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(30); shadow.setColor(QColor(92, 26, 46, 28)); shadow.setOffset(0, 6); card.setGraphicsEffect(shadow); root.addWidget(card); card_lay = QHBoxLayout(card); card_lay.setContentsMargins(0, 0, 0, 0); card_lay.setSpacing(0); left_panel = QFrame(); left_panel.setFixedWidth(280); left_panel.setStyleSheet(f"QFrame {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {self.BORDEAUX}, stop:1 {RUBY_SOLID}); border-top-left-radius: 20px; border-bottom-left-radius: 20px; border: none; }}"); lp_lay = QVBoxLayout(left_panel); lp_lay.setContentsMargins(30, 40, 30, 40); lp_lay.setSpacing(20); deco_lbl = QLabel(); deco_lbl.setPixmap(qta.icon('fa5s.user-edit', color='#FFFFFF').pixmap(80, 80)); deco_lbl.setStyleSheet("border: none; background: transparent;"); deco_lbl.setAlignment(Qt.AlignCenter); lp_title = QLabel("Edit\nCustomer"); lp_title.setFont(QFont('Nunito', 22, QFont.Bold)); lp_title.setStyleSheet("color: #FFFFFF; background: transparent; border: none;"); lp_title.setAlignment(Qt.AlignCenter); lp_lay.addStretch(); lp_lay.addWidget(deco_lbl); lp_lay.addWidget(lp_title); lp_lay.addStretch(); card_lay.addWidget(left_panel); right_panel = QWidget(); right_panel.setStyleSheet("background: transparent;"); rp_lay = QVBoxLayout(right_panel); rp_lay.setContentsMargins(45, 45, 45, 45); rp_lay.setSpacing(0); label_ss = f"color: {self.TEXT_GRAY}; font-weight: bold; font-family: 'Nunito'; font-size: 11px; letter-spacing: 1px; border: none; background: transparent;"; input_ss = f"QLineEdit {{ background-color: #FAFAFA; border: 1.5px solid {self.ROSE_MID}; border-radius: 10px; padding: 13px 16px; font-family: 'Nunito'; font-size: 14px; color: {self.TEXT_DARK}; }} QLineEdit:focus {{ border: 1.5px solid {RUBY_SOLID}; background-color: {self.ROSE_LIGHT}; }}"; 
        def field(l, w): lbl = QLabel(l, styleSheet=label_ss); rp_lay.addWidget(lbl); rp_lay.addSpacing(6); rp_lay.addWidget(w); rp_lay.addSpacing(22)
        self.txt_name = QLineEdit(); self.txt_name.setPlaceholderText("Customer Name"); self.txt_name.setFixedHeight(50); self.txt_name.setStyleSheet(input_ss); field("CUSTOMER NAME", self.txt_name); self.txt_phone = QLineEdit(); self.txt_phone.setPlaceholderText("Phone Number"); self.txt_phone.setFixedHeight(50); self.txt_phone.setStyleSheet(input_ss); field("PHONE NUMBER", self.txt_phone); self.txt_address = QLineEdit(); self.txt_address.setPlaceholderText("Address"); self.txt_address.setFixedHeight(50); self.txt_address.setStyleSheet(input_ss); field("ADDRESS", self.txt_address); rp_lay.addStretch(); div = QFrame(); div.setFixedHeight(1); div.setStyleSheet(f"background-color: {self.ROSE_MID}; border: none;"); rp_lay.addWidget(div); rp_lay.addSpacing(22); footer = QHBoxLayout(); footer.setSpacing(12); btn_cancel = QPushButton("Cancel"); btn_cancel.setFixedHeight(48); btn_cancel.setMinimumWidth(120); btn_cancel.setCursor(QCursor(Qt.PointingHandCursor)); btn_cancel.setStyleSheet(f"QPushButton {{ background: transparent; color: {self.TEXT_GRAY}; border: 1.5px solid #D1D5DB; border-radius: 10px; font-family: 'Nunito'; font-weight: bold; font-size: 14px; }} QPushButton:hover {{ background: {self.ROSE_LIGHT}; border-color: {RUBY_SOLID}; color: {RUBY_SOLID}; }}"); btn_cancel.clicked.connect(self.cancelled.emit); btn_save = QPushButton("  Save Change"); btn_save.setFixedHeight(48); btn_save.setMinimumWidth(160); btn_save.setCursor(QCursor(Qt.PointingHandCursor)); btn_save.setStyleSheet(f"QPushButton {{ background-color: {RUBY_SOLID}; color: #FFFFFF; border: none; border-radius: 10px; font-family: 'Nunito'; font-weight: bold; font-size: 14px; }} QPushButton:hover {{ background-color: #801836; }}"); btn_save.clicked.connect(self._on_save); footer.addStretch(); footer.addWidget(btn_cancel); footer.addWidget(btn_save); rp_lay.addLayout(footer); card_lay.addWidget(right_panel, stretch=1); root.addStretch()
    def _on_save(self):
        name = self.txt_name.text().strip(); phone = self.txt_phone.text().strip(); address = self.txt_address.text().strip()
        if not name or not phone: ModernPopup("Error", "Name and Phone are required.", "fa5s.exclamation-circle", self).exec_(); return
        success, msg = db_manager.update_customer(self.cid, name, phone, address)
        if success: self.customer_saved.emit()
        else: ModernPopup("Error", msg, "fa5s.times-circle", self).exec_()

# ==========================================
# TRANG SỬA MÓN ĂN (FULL PAGE LUXURY)
# ==========================================
class EditMenuItemPage(QWidget):
    menu_saved = pyqtSignal(); cancelled = pyqtSignal()
    CATEGORIES = ["Main Course", "Appetizer", "Dessert", "Beverage"]; BORDEAUX = "#5C1A2E"; TEXT_DARK = "#1A0A0F"; TEXT_GRAY = "#7B5B65"; ROSE_MID = "#E8C5D0"; ROSE_LIGHT = "#FCE8EE"
    def __init__(self, parent=None):
        super().__init__(parent); self.did = ""; self.setStyleSheet(f"background-color: {BG_COLOR};"); self._build_ui()
    def load_data(self, did, name, cat, price):
        self.did = did; self.txt_name.setText(name); self.combo_cat.setCurrentText(cat); self.txt_price.setText(str(int(float(price))))
    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(60, 40, 60, 40); root.setSpacing(0); nav_row = QHBoxLayout(); self.btn_back = QPushButton(qta.icon('fa5s.arrow-left', color='#7B5B65'), "  Back to Menu"); self.btn_back.setCursor(QCursor(Qt.PointingHandCursor)); self.btn_back.setFixedHeight(38); self.btn_back.setStyleSheet(f"QPushButton {{ background: transparent; border: none; color: {self.TEXT_GRAY}; font-family: 'Nunito'; font-weight: bold; font-size: 13px; }} QPushButton:hover {{ color: {RUBY_SOLID}; }}"); self.btn_back.clicked.connect(self.cancelled.emit); nav_row.addWidget(self.btn_back); nav_row.addStretch(); root.addLayout(nav_row); root.addSpacing(16); lbl_title = QLabel("Edit Dish"); lbl_title.setFont(QFont('Nunito', 28, QFont.Bold)); lbl_title.setStyleSheet(f"color: {self.TEXT_DARK}; background: transparent;"); root.addWidget(lbl_title); lbl_sub = QLabel("Update dish details in your menu."); lbl_sub.setFont(QFont('Nunito', 13)); lbl_sub.setStyleSheet(f"color: {self.TEXT_GRAY}; background: transparent;"); root.addWidget(lbl_sub); root.addSpacing(30); card = QFrame(); card.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 20px; border: none; }"); shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(30); shadow.setColor(QColor(92, 26, 46, 28)); shadow.setOffset(0, 6); card.setGraphicsEffect(shadow); root.addWidget(card); card_lay = QHBoxLayout(card); card_lay.setContentsMargins(0, 0, 0, 0); card_lay.setSpacing(0); left_panel = QFrame(); left_panel.setFixedWidth(280); left_panel.setStyleSheet(f"QFrame {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {self.BORDEAUX}, stop:1 {RUBY_SOLID}); border-top-left-radius: 20px; border-bottom-left-radius: 20px; border: none; }}"); lp_lay = QVBoxLayout(left_panel); lp_lay.setContentsMargins(30, 40, 30, 40); lp_lay.setSpacing(20); deco_lbl = QLabel(); deco_lbl.setPixmap(qta.icon('fa5s.utensils', color='#FFFFFF').pixmap(80, 80)); deco_lbl.setStyleSheet("border: none; background: transparent;"); deco_lbl.setAlignment(Qt.AlignCenter); lp_title = QLabel("Edit\nMenu Item"); lp_title.setFont(QFont('Nunito', 22, QFont.Bold)); lp_title.setStyleSheet("color: #FFFFFF; background: transparent; border: none;"); lp_title.setAlignment(Qt.AlignCenter); lp_lay.addStretch(); lp_lay.addWidget(deco_lbl); lp_lay.addWidget(lp_title); lp_lay.addStretch(); card_lay.addWidget(left_panel); right_panel = QWidget(); right_panel.setStyleSheet("background: transparent;"); rp_lay = QVBoxLayout(right_panel); rp_lay.setContentsMargins(45, 45, 45, 45); rp_lay.setSpacing(0); label_ss = f"color: {self.TEXT_GRAY}; font-weight: bold; font-family: 'Nunito'; font-size: 11px; letter-spacing: 1px; border: none; background: transparent;"; input_ss = f"QLineEdit {{ background-color: #FAFAFA; border: 1.5px solid {self.ROSE_MID}; border-radius: 10px; padding: 13px 16px; font-family: 'Nunito'; font-size: 14px; color: {self.TEXT_DARK}; }} QLineEdit:focus {{ border: 1.5px solid {RUBY_SOLID}; background-color: {self.ROSE_LIGHT}; }}"; combo_ss = f"QComboBox {{ background-color: #FAFAFA; border: 1.5px solid {self.ROSE_MID}; border-radius: 10px; padding: 13px 16px; font-family: 'Nunito'; font-size: 14px; color: {self.TEXT_DARK}; }} QComboBox:focus {{ border: 1.5px solid {RUBY_SOLID}; }} QComboBox::drop-down {{ border: none; width: 32px; }} QComboBox QAbstractItemView {{ border: 1px solid {self.ROSE_MID}; border-radius: 8px; background: #FFFFFF; outline: none; padding: 4px; selection-background-color: {self.ROSE_LIGHT}; selection-color: {RUBY_SOLID}; }} QComboBox QAbstractItemView::item {{ min-height: 36px; padding-left: 12px; font-family: 'Nunito'; font-size: 13px; color: {self.TEXT_DARK}; border-radius: 6px; }}"
        def field(l, w): lbl = QLabel(l, styleSheet=label_ss); rp_lay.addWidget(lbl); rp_lay.addSpacing(6); rp_lay.addWidget(w); rp_lay.addSpacing(22)
        self.txt_name = QLineEdit(); self.txt_name.setPlaceholderText("e.g. Wagyu Ribeye Steak"); self.txt_name.setFixedHeight(50); self.txt_name.setStyleSheet(input_ss); field("DISH NAME", self.txt_name); self.combo_cat = QComboBox(); self.combo_cat.addItems(self.CATEGORIES); self.combo_cat.setFixedHeight(50); self.combo_cat.setStyleSheet(combo_ss); field("CATEGORY", self.combo_cat); self.txt_price = QLineEdit(); self.txt_price.setPlaceholderText("e.g. 1500000"); self.txt_price.setFixedHeight(50); self.txt_price.setStyleSheet(input_ss); price_row = QHBoxLayout(); price_row.setSpacing(10); price_row.addWidget(self.txt_price); lbl_vnd = QLabel("VND"); lbl_vnd.setFixedHeight(50); lbl_vnd.setAlignment(Qt.AlignCenter); lbl_vnd.setStyleSheet(f"QLabel {{ background-color: {self.ROSE_LIGHT}; color: {RUBY_SOLID}; border-radius: 10px; padding: 0 16px; font-family: 'Nunito'; font-weight: bold; font-size: 13px; border: none; }}"); price_row.addWidget(lbl_vnd); rp_lay.addWidget(QLabel("PRICE", styleSheet=label_ss)); rp_lay.addSpacing(6); rp_lay.addLayout(price_row); rp_lay.addSpacing(22); rp_lay.addStretch(); div = QFrame(); div.setFixedHeight(1); div.setStyleSheet(f"background-color: {self.ROSE_MID}; border: none;"); rp_lay.addWidget(div); rp_lay.addSpacing(22); footer = QHBoxLayout(); footer.setSpacing(12); btn_cancel = QPushButton("Cancel"); btn_cancel.setFixedHeight(48); btn_cancel.setMinimumWidth(120); btn_cancel.setCursor(QCursor(Qt.PointingHandCursor)); btn_cancel.setStyleSheet(f"QPushButton {{ background: transparent; color: {self.TEXT_GRAY}; border: 1.5px solid #D1D5DB; border-radius: 10px; font-family: 'Nunito'; font-weight: bold; font-size: 14px; }} QPushButton:hover {{ background: {self.ROSE_LIGHT}; border-color: {self.ROSE_MID}; color: {RUBY_SOLID}; }}"); btn_cancel.clicked.connect(self.cancelled.emit); btn_save = QPushButton("  Save Change"); btn_save.setFixedHeight(48); btn_save.setMinimumWidth(160); btn_save.setCursor(QCursor(Qt.PointingHandCursor)); btn_save.setStyleSheet(f"QPushButton {{ background-color: {RUBY_SOLID}; color: #FFFFFF; border: none; border-radius: 10px; font-family: 'Nunito'; font-weight: bold; font-size: 14px; }} QPushButton:hover {{ background-color: #801836; }}"); btn_save.clicked.connect(self._on_save); footer.addStretch(); footer.addWidget(btn_cancel); footer.addWidget(btn_save); rp_lay.addLayout(footer); card_lay.addWidget(right_panel, stretch=1); root.addStretch()
    def _on_save(self):
        name = self.txt_name.text().strip(); cat = self.combo_cat.currentText(); price = self.txt_price.text().strip().replace(",", "").replace(".", "")
        if not name or not price: ModernPopup("Error", "Name and Price required.", "fa5s.exclamation-circle", self).exec_(); return
        success, msg = db_manager.update_menu_item(self.did, name, cat, float(price))
        if success: self.menu_saved.emit()
        else: ModernPopup("Error", msg, "fa5s.times-circle", self).exec_()

# ==========================================
# TRANG SỬA CHI PHÍ (FULL PAGE LUXURY)
# ==========================================
class EditExpensePage(QWidget):
    expense_saved = pyqtSignal(); cancelled = pyqtSignal()
    CATEGORIES = ["Ingredients", "Marketing", "Maintenance", "Payroll", "Utilities", "Supplies"]; BORDEAUX = "#5C1A2E"; TEXT_DARK = "#1A0A0F"; TEXT_GRAY = "#7B5B65"; ROSE_MID = "#E8C5D0"; ROSE_LIGHT = "#FCE8EE"
    def __init__(self, parent=None):
        super().__init__(parent); self.eid = ""; self.setStyleSheet(f"background-color: {BG_COLOR};"); self._build_ui()
    def load_data(self, eid, desc, cat, date, amount):
        self.eid = eid; self.txt_desc.setText(desc); self.combo_cat.setCurrentText(cat); self.txt_date.setText(date); self.txt_amount.setText(str(int(float(amount))))
    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(60, 40, 60, 40); root.setSpacing(0); nav_row = QHBoxLayout(); self.btn_back = QPushButton(qta.icon('fa5s.arrow-left', color='#7B5B65'), "  Back to Expenses"); self.btn_back.setFixedHeight(38); self.btn_back.setStyleSheet(f"QPushButton {{ background: transparent; border: none; color: {self.TEXT_GRAY}; font-family: 'Nunito'; font-weight: bold; font-size: 13px; }} QPushButton:hover {{ color: {RUBY_SOLID}; }}"); self.btn_back.clicked.connect(self.cancelled.emit); nav_row.addWidget(self.btn_back); nav_row.addStretch(); root.addLayout(nav_row); root.addSpacing(16); lbl_page_title = QLabel("Edit Expense"); lbl_page_title.setFont(QFont('Nunito', 28, QFont.Bold)); lbl_page_title.setStyleSheet(f"color: {self.TEXT_DARK}; background: transparent;"); root.addWidget(lbl_page_title); lbl_sub = QLabel("Update operating expense details."); lbl_sub.setFont(QFont('Nunito', 13)); lbl_sub.setStyleSheet(f"color: {self.TEXT_GRAY}; background: transparent;"); root.addWidget(lbl_sub); root.addSpacing(30); card = QFrame(); card.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 20px; border: none; }"); shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(30); shadow.setColor(QColor(92, 26, 46, 28)); shadow.setOffset(0, 6); card.setGraphicsEffect(shadow); root.addWidget(card); card_lay = QHBoxLayout(card); card_lay.setContentsMargins(0, 0, 0, 0); card_lay.setSpacing(0); left_panel = QFrame(); left_panel.setFixedWidth(280); left_panel.setStyleSheet(f"QFrame {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {self.BORDEAUX}, stop:1 {RUBY_SOLID}); border-top-left-radius: 20px; border-bottom-left-radius: 20px; border: none; }}"); lp_lay = QVBoxLayout(left_panel); lp_lay.setContentsMargins(30, 40, 30, 40); lp_lay.setSpacing(20); deco_lbl = QLabel(); deco_lbl.setPixmap(qta.icon('fa5s.file-invoice-dollar', color='#FFFFFF').pixmap(80, 80)); deco_lbl.setStyleSheet("border: none; background: transparent;"); deco_lbl.setAlignment(Qt.AlignCenter); lp_title = QLabel("Edit\nExpense"); lp_title.setFont(QFont('Nunito', 22, QFont.Bold)); lp_title.setStyleSheet("color: #FFFFFF; background: transparent; border: none;"); lp_title.setAlignment(Qt.AlignCenter); lp_lay.addStretch(); lp_lay.addWidget(deco_lbl); lp_lay.addWidget(lp_title); lp_lay.addStretch(); card_lay.addWidget(left_panel); right_panel = QWidget(); right_panel.setStyleSheet("background: transparent;"); rp_lay = QVBoxLayout(right_panel); rp_lay.setContentsMargins(45, 45, 45, 45); rp_lay.setSpacing(0); label_ss = f"color: {self.TEXT_GRAY}; font-weight: bold; font-family: 'Nunito'; font-size: 11px; letter-spacing: 1px; border: none; background: transparent;"; input_ss = f"QLineEdit {{ background-color: #FAFAFA; border: 1.5px solid {self.ROSE_MID}; border-radius: 10px; padding: 13px 16px; font-family: 'Nunito'; font-size: 14px; color: {self.TEXT_DARK}; }} QLineEdit:focus {{ border: 1.5px solid {RUBY_SOLID}; background-color: {self.ROSE_LIGHT}; }}"; combo_ss = f"QComboBox {{ background-color: #FAFAFA; border: 1.5px solid {self.ROSE_MID}; border-radius: 10px; padding: 13px 16px; font-family: 'Nunito'; font-size: 14px; color: {self.TEXT_DARK}; }} QComboBox:focus {{ border: 1.5px solid {RUBY_SOLID}; }} QComboBox::drop-down {{ border: none; width: 32px; }} QComboBox QAbstractItemView {{ border: 1px solid {self.ROSE_MID}; border-radius: 8px; background: #FFFFFF; outline: none; padding: 4px; selection-background-color: {self.ROSE_LIGHT}; selection-color: {RUBY_SOLID}; }} QComboBox QAbstractItemView::item {{ min-height: 36px; padding-left: 12px; font-family: 'Nunito'; font-size: 13px; color: {self.TEXT_DARK}; border-radius: 6px; }}"
        def field(l, w): lbl = QLabel(l, styleSheet=label_ss); rp_lay.addWidget(lbl); rp_lay.addSpacing(6); rp_lay.addWidget(w); rp_lay.addSpacing(22)
        self.txt_desc = QLineEdit(); self.txt_desc.setPlaceholderText("e.g. Electricity Bill"); self.txt_desc.setFixedHeight(50); self.txt_desc.setStyleSheet(input_ss); field("DESCRIPTION", self.txt_desc); self.combo_cat = QComboBox(); self.combo_cat.addItems(self.CATEGORIES); self.combo_cat.setFixedHeight(50); self.combo_cat.setStyleSheet(combo_ss); field("CATEGORY", self.combo_cat); self.txt_amount = QLineEdit(); self.txt_amount.setPlaceholderText("e.g. 5,000,000"); self.txt_amount.setFixedHeight(50); self.txt_amount.setStyleSheet(input_ss); field("AMOUNT (VND)", self.txt_amount); self.txt_date = QLineEdit(); self.txt_date.setPlaceholderText("YYYY-MM-DD"); self.txt_date.setFixedHeight(50); self.txt_date.setStyleSheet(input_ss); field("EXPENSE DATE", self.txt_date); rp_lay.addStretch(); div = QFrame(); div.setFixedHeight(1); div.setStyleSheet(f"background-color: {self.ROSE_MID}; border: none;"); rp_lay.addWidget(div); rp_lay.addSpacing(22); footer = QHBoxLayout(); footer.setSpacing(12); btn_cancel = QPushButton("Cancel"); btn_cancel.setFixedHeight(48); btn_cancel.setMinimumWidth(120); btn_cancel.setCursor(QCursor(Qt.PointingHandCursor)); btn_cancel.setStyleSheet(f"QPushButton {{ background: transparent; color: {self.TEXT_GRAY}; border: 1.5px solid #D1D5DB; border-radius: 10px; font-family: 'Nunito'; font-weight: bold; font-size: 14px; }} QPushButton:hover {{ background: {self.ROSE_LIGHT}; border-color: {RUBY_SOLID}; color: {RUBY_SOLID}; }}"); btn_cancel.clicked.connect(self.cancelled.emit); btn_save = QPushButton("  Save Change"); btn_save.setFixedHeight(48); btn_save.setMinimumWidth(160); btn_save.setCursor(QCursor(Qt.PointingHandCursor)); btn_save.setStyleSheet(f"QPushButton {{ background-color: {RUBY_SOLID}; color: #FFFFFF; border: none; border-radius: 10px; font-family: 'Nunito'; font-weight: bold; font-size: 14px; }} QPushButton:hover {{ background-color: #801836; }}"); btn_save.clicked.connect(self._on_save); footer.addStretch(); footer.addWidget(btn_cancel); footer.addWidget(btn_save); rp_lay.addLayout(footer); card_lay.addWidget(right_panel, stretch=1); root.addStretch()
    def _on_save(self):
        desc = self.txt_desc.text().strip(); cat = self.combo_cat.currentText(); date = self.txt_date.text().strip(); amount = self.txt_amount.text().strip().replace(",", "").replace(".", "")
        if not desc or not amount or not date: ModernPopup("Error", "Description, Date and Amount are required.", "fa5s.exclamation-circle", self).exec_(); return
        success, msg = db_manager.update_expense(self.eid, desc, cat, float(amount), date)
        if success: self.expense_saved.emit()
        else: ModernPopup("Error", msg, "fa5s.times-circle", self).exec_()

# ==========================================
# GIAO DIỆN QUẢN LÝ HÓA ĐƠN (INVOICES - FILTER BẰNG NÚT)
# ==========================================
class InvoicesWidget(QWidget):
    view_receipt_requested = pyqtSignal(str, str, str, str, str, str, str, str, str)

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: transparent;")
        self.layout = QVBoxLayout(self); self.layout.setContentsMargins(40, 40, 40, 40)
        self.current_page = 1; self.items_per_page = 8; self.total_pages = 1; self.total_items = 0
        self.current_filter = "All Status"
        self.initUI()

    def _create_status_pill(self, status):
        w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0,0,0,0); l.setAlignment(Qt.AlignCenter); lbl = QLabel(status)
        if status == "Paid": lbl.setStyleSheet("background-color: #D1FAE5; color: #059669; padding: 6px 14px; border-radius: 12px; font-weight: bold; font-family: 'Nunito'; font-size: 12px;")
        elif status == "Pending": lbl.setStyleSheet("background-color: #FEF3C7; color: #D97706; padding: 6px 14px; border-radius: 12px; font-weight: bold; font-family: 'Nunito'; font-size: 12px;")
        l.addWidget(lbl); return w

    def initUI(self):
        main_card = QFrame(); main_card.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 15px; border: 1px solid #E5E7EB; }"); shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(20); shadow.setColor(QColor(0,0,0,8)); shadow.setOffset(0,4); main_card.setGraphicsEffect(shadow); self.card_layout = QVBoxLayout(main_card); self.card_layout.setContentsMargins(30, 30, 30, 30); self.card_layout.setSpacing(20)
        
        top_header = QHBoxLayout(); search_frame = QFrame(); search_frame.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #D1D5DB; border-radius: 25px; }"); search_frame.setFixedSize(400, 50); search_lay = QHBoxLayout(search_frame); search_lay.setContentsMargins(20, 0, 20, 0); search_lay.setSpacing(10); lbl_search_icon = QLabel(); lbl_search_icon.setPixmap(qta.icon('fa5s.search', color='#9CA3AF').pixmap(18, 18)); lbl_search_icon.setStyleSheet("border: none;"); self.txt_search = QLineEdit(); self.txt_search.setPlaceholderText("Search Invoices by Name or Date..."); self.txt_search.setStyleSheet("border: none; background: transparent; font-family: 'Nunito'; font-size: 15px; color: #111827;"); search_lay.addWidget(lbl_search_icon); search_lay.addWidget(self.txt_search); top_header.addWidget(search_frame); top_header.addStretch()
        
        self.txt_search.textChanged.connect(self._on_search)
        
        self.btn_filter = QPushButton(qta.icon('fa5s.filter', color='#6B7280'), " Filter")
        self.btn_filter.setFixedHeight(50)
        self.btn_filter.setStyleSheet("QPushButton { background-color: #FFFFFF; color: #6B7280; border: 1px solid #D1D5DB; border-radius: 25px; padding: 0 25px; font-weight: bold; font-family: 'Nunito'; font-size: 14px; } QPushButton:hover { background-color: #F3F4F6; } QPushButton::menu-indicator { image: none; }")
        
        self.filter_menu = QMenu(self)
        self.filter_menu.setStyleSheet("QMenu { background-color: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 8px; } QMenu::item { padding: 8px 25px; font-family: 'Nunito'; font-size: 14px; color: #4B5563; } QMenu::item:selected { background-color: #F3F4F6; color: #111827; }")
        a1 = QAction("All Status", self); a1.triggered.connect(lambda: self._on_filter_changed("All Status"))
        a2 = QAction("Paid", self); a2.triggered.connect(lambda: self._on_filter_changed("Paid"))
        a3 = QAction("Pending", self); a3.triggered.connect(lambda: self._on_filter_changed("Pending"))
        self.filter_menu.addActions([a1, a2, a3])
        self.btn_filter.setMenu(self.filter_menu)
        top_header.addWidget(self.btn_filter)
        top_header.addSpacing(15)

        self.btn_export = QPushButton(qta.icon('fa5s.download', color='#6B7280'), " Export"); self.btn_export.setFixedHeight(50); self.btn_export.setStyleSheet("QPushButton { background-color: #FFFFFF; color: #6B7280; border: 1px solid #D1D5DB; border-radius: 25px; padding: 0 25px; font-weight: bold; font-family: 'Nunito'; font-size: 15px; } QPushButton:hover { background-color: #F3F4F6; }"); self.btn_export.setCursor(QCursor(Qt.PointingHandCursor)); self.btn_export.clicked.connect(self._on_export); top_header.addWidget(self.btn_export); self.card_layout.addLayout(top_header)
        
        self.table = QTableWidget(); self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Invoice ID", "Customer Name", "Table", "Date", "Total Amount", "Status", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter); self.table.verticalHeader().setVisible(False); self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed); self.table.verticalHeader().setDefaultSectionSize(70); self.table.setFocusPolicy(Qt.NoFocus); self.table.setSelectionMode(QTableWidget.NoSelection); self.table.setShowGrid(False); self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff); 
        self.table.setStyleSheet("QTableWidget { border: none; background: transparent; font-family: 'Nunito'; outline: none; } QHeaderView::section { background-color: #E8EAED; color: #4B5563; font-weight: bold; font-size: 15px; border: none; padding: 15px 10px; } QHeaderView::section:first { border-top-left-radius: 12px; border-bottom-left-radius: 12px; } QHeaderView::section:last { border-top-right-radius: 12px; border-bottom-right-radius: 12px; } QTableWidget::item { border-bottom: 1px solid #F3F4F6; color: #111827; font-size: 15px; font-weight: 500; padding: 10px 10px; } QScrollBar:vertical { width: 0px; background: transparent; }")
        self.card_layout.addWidget(self.table, stretch=1); self.pagination_container = QWidget(); self.pagination_layout = QHBoxLayout(self.pagination_container); self.pagination_layout.setContentsMargins(0, 10, 0, 0); self.card_layout.addWidget(self.pagination_container); self.layout.addWidget(main_card); self.load_mock_data()

    def _on_search(self):
        self.current_page = 1; self.load_mock_data()

    def _on_filter_changed(self, status):
        self.current_filter = status
        self.current_page = 1
        self.load_mock_data()

    def load_mock_data(self):
        st = self.txt_search.text().strip().lower()
        raw_data = db_manager.get_invoices(search_keyword=st, status_filter=self.current_filter)
        
        all_data = []
        for item in raw_data:
            inv_id = f"INV{item['InvoiceID']:03d}"
            cust_name = item['CustomerName']
            phone = str(item['Phone'])
            masked_phone = phone[:3] + "****" + phone[-3:] if len(phone) >= 6 else phone
            table_no = str(item['TableNumber'])
            
            date_val = item['PaymentDate']
            date_str = date_val.strftime('%Y-%m-%d %H:%M') if date_val else "-"
            
            subtotal_val = float(item['Subtotal'])
            svc_val = subtotal_val * 0.10
            disc_val = subtotal_val * 0.05 if subtotal_val > 3000000 else 0
            total_val = subtotal_val + svc_val - disc_val
            
            subtotal = f"{subtotal_val:,.0f}"
            svc = f"{svc_val:,.0f}"
            discount = f"{disc_val:,.0f}"
            total = f"{total_val:,.0f} VND"
            status = item['Status']
            
            all_data.append((inv_id, cust_name, masked_phone, table_no, date_str, subtotal, svc, discount, total, status))
        
        if not all_data:
            self.table.setRowCount(0); self.total_items = 0; self.total_pages = 1; self.update_pagination_ui(); return

        self.total_items = len(all_data); self.total_pages = (self.total_items + self.items_per_page - 1) // self.items_per_page; self.current_page = max(1, min(self.current_page, self.total_pages)); start_idx = (self.current_page - 1) * self.items_per_page; end_idx = start_idx + self.items_per_page; page_data = all_data[start_idx:end_idx]; self.table.setRowCount(len(page_data))
        
        for row, data in enumerate(page_data):
            item_id = QTableWidgetItem(data[0]); item_id.setTextAlignment(Qt.AlignCenter); item_id.setForeground(QColor("#4B5563")); self.table.setItem(row, 0, item_id)
            item_name = QTableWidgetItem(data[1]); item_name.setTextAlignment(Qt.AlignCenter); self.table.setItem(row, 1, item_name)
            item_tb = QTableWidgetItem(data[3]); item_tb.setTextAlignment(Qt.AlignCenter); self.table.setItem(row, 2, item_tb)
            item_dt = QTableWidgetItem(data[4]); item_dt.setTextAlignment(Qt.AlignCenter); self.table.setItem(row, 3, item_dt)
            
            item_amt = QTableWidgetItem(data[8]); item_amt.setTextAlignment(Qt.AlignCenter); 
            self.table.setItem(row, 4, item_amt)
            
            self.table.setCellWidget(row, 5, self._create_status_pill(data[9]))
            
            act_w = QWidget(); act_l = QHBoxLayout(act_w); act_l.setContentsMargins(0,0,0,0); act_l.setAlignment(Qt.AlignCenter)
            btn_view = QPushButton(qta.icon('fa5s.file-invoice', color='#6B7280'), ""); btn_view.setFixedSize(35, 35); btn_view.setCursor(QCursor(Qt.PointingHandCursor)); btn_view.setStyleSheet("QPushButton { background: transparent; border: none; } QPushButton:hover { color: #111827; }")
            
            inv_id = data[0]; cust = data[1]; ph = data[2]; tab = data[3]; dt = data[4]; subt = data[5]; svc = data[6]; disc = data[7]; tot = data[8]
            btn_view.clicked.connect(lambda checked, i=inv_id, c=cust, p=ph, t=tab, d=dt, s=subt, sv=svc, ds=disc, a=tot: self.view_receipt_requested.emit(i, c, p, t, d, s, sv, ds, a))
            act_l.addWidget(btn_view); self.table.setCellWidget(row, 6, act_w)

        self.update_pagination_ui()

    def update_pagination_ui(self):
        while self.pagination_layout.count():
            item = self.pagination_layout.takeAt(0); [item.widget().deleteLater() if item.widget() else None]
        if self.total_items == 0: return
        lbl_show = QLabel("Showing page"); lbl_show.setStyleSheet("color: #9CA3AF; font-family: 'Nunito'; font-size: 16px; font-weight: bold; border: none;"); self.txt_show = QLineEdit(str(self.current_page)); self.txt_show.setFixedSize(50, 40); self.txt_show.setAlignment(Qt.AlignCenter); self.txt_show.setStyleSheet(f"QLineEdit {{ background-color: #FCE8E8; color: {BRIGHT_RED}; border-radius: 10px; font-weight: bold; font-family: 'Nunito'; font-size: 16px; border: none; }}"); self.txt_show.editingFinished.connect(self.go_to_page_from_input); lbl_out = QLabel(f"out of {self.total_pages}"); lbl_out.setStyleSheet("color: #9CA3AF; font-family: 'Nunito'; font-size: 16px; font-weight: bold; border: none;"); self.pagination_layout.addWidget(lbl_show); self.pagination_layout.addSpacing(5); self.pagination_layout.addWidget(self.txt_show); self.pagination_layout.addSpacing(5); self.pagination_layout.addWidget(lbl_out); self.pagination_layout.addStretch()
        total = self.total_pages; current = self.current_page
        if total <= 5: seq = list(range(1, total + 1))
        elif current <= 3: seq = [1, 2, 3, 4, "...", total]
        elif current >= total - 2: seq = [1, "...", total - 3, total - 2, total - 1, total]
        else: seq = [1, "...", current - 1, current, current + 1, "...", total]
        for p in seq:
            if p == "...": lbl = QLabel("..."); lbl.setStyleSheet("color: #9CA3AF; font-family: 'Nunito'; font-weight: bold; font-size: 18px; border: none;"); self.pagination_layout.addWidget(lbl); self.pagination_layout.addSpacing(5)
            else:
                btn = QPushButton(str(p)); btn.setFixedSize(40, 40); btn.setCursor(QCursor(Qt.PointingHandCursor)); btn.setStyleSheet(f"QPushButton {{ background-color: {BRIGHT_RED if p == self.current_page else '#E8EAED'}; color: {'white' if p == self.current_page else '#4B5563'}; border: none; border-radius: 8px; font-weight: bold; font-family: 'Nunito'; font-size: 15px; }}"); btn.clicked.connect(lambda ch, page=p: self.change_page(page)); self.pagination_layout.addWidget(btn); self.pagination_layout.addSpacing(5)

    def change_page(self, page):
        if self.current_page != page: self.current_page = page; self.load_mock_data()

    def go_to_page_from_input(self):
        text = self.txt_show.text().strip()
        if text.isdigit():
            page = max(1, min(int(text), self.total_pages))
            if page != self.current_page: self.change_page(page)
            else: self.txt_show.setText(str(self.current_page))
        else: self.txt_show.setText(str(self.current_page))

    def _on_export(self):
        out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output'); os.makedirs(out_dir, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(self, "Export Invoices", os.path.join(out_dir, "Invoices.csv"), "CSV Files (*.csv)")
        if not path: return
        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount() - 1)]
                writer.writerow(headers)
                for row in range(self.table.rowCount()):
                    row_data = []
                    for col in range(self.table.columnCount() - 1):
                        it = self.table.item(row, col)
                        if it: row_data.append(it.text())
                        else:
                            w = self.table.cellWidget(row, col)
                            lbl = w.findChild(QLabel) if w else None
                            row_data.append(lbl.text() if lbl else "")
                    writer.writerow(row_data)
            ModernPopup("Success", "Invoices exported to CSV successfully!", "fa5s.check-circle", self.window()).exec_()
        except Exception as e: ModernPopup("Error", f"Export failed: {str(e)}", "fa5s.times-circle", self.window()).exec_()

# ==========================================
# GIAO DIỆN CUSTOMERS
# ==========================================
class CustomersWidget(QWidget):
    edit_requested = pyqtSignal(str, str, str, str) # THÊM SIGNAL CHO NÚT BÚT CHÌ

    def __init__(self):
        super().__init__(); self.setStyleSheet("background: transparent;"); self.layout = QVBoxLayout(self); self.layout.setContentsMargins(40, 40, 40, 40); self.current_page = 1; self.items_per_page = 8; self.total_pages = 1; self.total_items = 0; self.initUI()
    def initUI(self):
        main_card = QFrame(); main_card.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 15px; border: 1px solid #E5E7EB; }"); shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(20); shadow.setColor(QColor(0,0,0,8)); shadow.setOffset(0,4); main_card.setGraphicsEffect(shadow); self.card_layout = QVBoxLayout(main_card); self.card_layout.setContentsMargins(30, 30, 30, 30); self.card_layout.setSpacing(20)
        top_header = QHBoxLayout(); search_frame = QFrame(); search_frame.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #D1D5DB; border-radius: 25px; }"); search_frame.setFixedSize(400, 50); search_lay = QHBoxLayout(search_frame); search_lay.setContentsMargins(20, 0, 20, 0); search_lay.setSpacing(10); lbl_search_icon = QLabel(); lbl_search_icon.setPixmap(qta.icon('fa5s.search', color='#9CA3AF').pixmap(18, 18)); lbl_search_icon.setStyleSheet("border: none;"); self.txt_search = QLineEdit(); self.txt_search.setPlaceholderText("Search Name or Phone..."); self.txt_search.setStyleSheet("border: none; background: transparent; font-family: 'Nunito'; font-size: 15px; color: #111827;"); search_lay.addWidget(lbl_search_icon); search_lay.addWidget(self.txt_search); top_header.addWidget(search_frame); top_header.addStretch()
        
        self.txt_search.textChanged.connect(self._on_search) 
        
        self.btn_export = QPushButton(qta.icon('fa5s.download', color='#6B7280'), " Export"); self.btn_export.setFixedHeight(50); self.btn_export.setStyleSheet("QPushButton { background-color: #FFFFFF; color: #6B7280; border: 1px solid #D1D5DB; border-radius: 25px; padding: 0 25px; font-weight: bold; font-family: 'Nunito'; font-size: 15px; } QPushButton:hover { background-color: #F3F4F6; }"); self.btn_export.setCursor(QCursor(Qt.PointingHandCursor)); self.btn_export.clicked.connect(self._on_export); top_header.addWidget(self.btn_export); self.card_layout.addLayout(top_header)
        
        self.table = QTableWidget(); self.table.setColumnCount(7); self.table.setHorizontalHeaderLabels(["ID", "Name", "Phone", "Address", "Orders", "Spend", "Action"]); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter); self.table.verticalHeader().setVisible(False); self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed); self.table.verticalHeader().setDefaultSectionSize(70); self.table.setFocusPolicy(Qt.NoFocus); self.table.setSelectionMode(QTableWidget.NoSelection); self.table.setShowGrid(False); self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff); 
        self.table.setStyleSheet("QTableWidget { border: none; background: transparent; font-family: 'Nunito'; outline: none; } QHeaderView::section { background-color: #E8EAED; color: #4B5563; font-weight: bold; font-size: 15px; border: none; padding: 15px 10px; } QHeaderView::section:first { border-top-left-radius: 12px; border-bottom-left-radius: 12px; } QHeaderView::section:last { border-top-right-radius: 12px; border-bottom-right-radius: 12px; } QTableWidget::item { border-bottom: 1px solid #F3F4F6; color: #111827; font-size: 15px; font-weight: 500; padding: 10px 10px; } QScrollBar:vertical { width: 0px; background: transparent; }")
        self.card_layout.addWidget(self.table, stretch=1); self.pagination_container = QWidget(); self.pagination_layout = QHBoxLayout(self.pagination_container); self.pagination_layout.setContentsMargins(0, 10, 0, 0); self.card_layout.addWidget(self.pagination_container); self.layout.addWidget(main_card); self.load_mock_data()
        
    def _on_search(self):
        self.current_page = 1; self.load_mock_data()
        
    def _on_delete(self, cid_str):
        confirm = ModernConfirmPopup("Delete Customer", f"Are you sure you want to delete {cid_str}?\nThis action cannot be undone.", "fa5s.exclamation-triangle", self.window())
        if confirm.exec_() == QDialog.Accepted:
            success, msg = db_manager.delete_customer(cid_str)
            if success:
                ModernPopup("Success", msg, "fa5s.check-circle", self.window()).exec_()
                self.load_mock_data()
            else:
                ModernPopup("Delete Failed", msg, "fa5s.times-circle", self.window()).exec_()
    def _on_view_phone(self, name, raw_phone):
        ModernPopup("Phone Number", f"{name}: {raw_phone}", "fa5s.phone", self.window()).exec_()

    def load_mock_data(self):
        st = self.txt_search.text().strip().lower()
        raw_data = db_manager.get_all_customers_stats(search_keyword=st)
        
        all_d = []
        for item in raw_data:
            cus_id = f"#CUS{item['CustomerID']:03d}"
            name = item['CustomerName']
            raw_phone = str(item['Phone']) if item['Phone'] else ""
            if len(raw_phone) >= 7: phone = raw_phone[:3] + "****" + raw_phone[-3:]
            else: phone = raw_phone
            address = item['Address'] if item['Address'] else "N/A"
            raw_address = item['Address'] if item['Address'] else "" # Address thật không có N/A
            orders = str(item['OrdersPlaced'])
            spend = f"{float(item['TotalSpend']):,.0f} VND"
            all_d.append((cus_id, name, phone, address, orders, spend, raw_phone, raw_address)) # Lưu raw vào array ẩn
            
        self.total_items = len(all_d); self.total_pages = max(1, (self.total_items+7)//8)
        self.current_page = max(1, min(self.current_page, self.total_pages))
        if self.total_items == 0: self.table.setRowCount(0); self.update_pagination_ui(); return
        
        p_data = all_d[(self.current_page-1)*8:self.current_page*8]; self.table.setRowCount(len(p_data))
        for r, d in enumerate(p_data):
            for c in range(6):
                item = QTableWidgetItem(d[c]); item.setTextAlignment(Qt.AlignCenter); 
                # ĐÃ SỬA: Giấu số điện thoại thật (cột raw_phone d[6]) vào thuộc tính ẩn của ô hiển thị
                if c == 2: item.setData(Qt.UserRole, d[6])
                if c == 5: item.setForeground(QColor(BRIGHT_RED))
                self.table.setItem(r, c, item)
            
            act_w = QWidget(); act_l = QHBoxLayout(act_w); act_l.setContentsMargins(0,0,0,0); act_l.setAlignment(Qt.AlignCenter)
            btn_view = QPushButton(qta.icon('fa5s.eye', color='#6B7280'), ""); btn_view.setFixedSize(35, 35); btn_view.setCursor(QCursor(Qt.PointingHandCursor))
            btn_view.setStyleSheet("QPushButton { background: transparent; border: 1px solid #D1D5DB; border-radius: 6px; } QPushButton:hover { border-color: #6B7280; }")
            btn_edit = QPushButton(qta.icon('fa5s.pen', color='#6B7280'), ""); btn_edit.setFixedSize(35, 35); btn_edit.setCursor(QCursor(Qt.PointingHandCursor))
            btn_edit.setStyleSheet("QPushButton { background: transparent; border: 1px solid #D1D5DB; border-radius: 6px; } QPushButton:hover { border-color: #6B7280; }")
            btn_cancel = QPushButton(qta.icon('fa5s.times', color='#6B7280'), ""); btn_cancel.setFixedSize(35, 35); btn_cancel.setCursor(QCursor(Qt.PointingHandCursor))
            btn_cancel.setStyleSheet("QPushButton { background: transparent; border: 1px solid #D1D5DB; border-radius: 6px; } QPushButton:hover { border-color: #EF4444; }")

            cid_str = d[0]; c_name = d[1]; c_raw_phone = d[6]; c_raw_addr = d[7]
            btn_view.clicked.connect(lambda checked, rn=c_name, rp=c_raw_phone: self._on_view_phone(rn, rp))
            btn_edit.clicked.connect(lambda checked, rid=cid_str, rn=c_name, rp=c_raw_phone, ra=c_raw_addr: self.edit_requested.emit(rid, rn, rp, ra)) # KÍCH HOẠT SỰ KIỆN EDIT
            btn_cancel.clicked.connect(lambda checked, rid=cid_str: self._on_delete(rid))

            act_l.addWidget(btn_view); act_l.addSpacing(5); act_l.addWidget(btn_edit); act_l.addSpacing(5); act_l.addWidget(btn_cancel)
            self.table.setCellWidget(r, 6, act_w)
        self.update_pagination_ui()
        
    def update_pagination_ui(self):
        while self.pagination_layout.count():
            item = self.pagination_layout.takeAt(0); [item.widget().deleteLater() if item.widget() else None]
        if self.total_items == 0: return
        self.txt_show = QLineEdit(str(self.current_page)); self.txt_show.setFixedSize(50, 40); self.txt_show.setAlignment(Qt.AlignCenter); self.txt_show.setStyleSheet(f"QLineEdit {{ background-color: #FCE8E8; color: {BRIGHT_RED}; border-radius: 10px; font-weight: bold; font-family: 'Nunito'; font-size: 16px; border: none; }}"); self.txt_show.editingFinished.connect(self.go_to_page_from_input); self.pagination_layout.addWidget(QLabel("Showing page", styleSheet="color: #9CA3AF; font-family: 'Nunito'; font-size: 16px; font-weight: bold; border: none;")); self.pagination_layout.addSpacing(5); self.pagination_layout.addWidget(self.txt_show); self.pagination_layout.addSpacing(5); self.pagination_layout.addWidget(QLabel(f"out of {self.total_pages}", styleSheet="color: #9CA3AF; font-family: 'Nunito'; font-size: 16px; font-weight: bold; border: none;")); self.pagination_layout.addStretch()
        seq = [1, 2, 3, 4, "...", self.total_pages] if self.total_pages > 5 else list(range(1, self.total_pages+1))
        for p in seq:
            if p == "...": self.pagination_layout.addWidget(QLabel("...", styleSheet="color: #9CA3AF; font-family: 'Nunito'; font-weight: bold; font-size: 18px; border: none;"))
            else:
                btn = QPushButton(str(p)); btn.setFixedSize(40, 40); btn.setCursor(QCursor(Qt.PointingHandCursor)); btn.setStyleSheet(f"QPushButton {{ background-color: {BRIGHT_RED if p == self.current_page else '#E8EAED'}; color: {'white' if p == self.current_page else '#4B5563'}; border: none; border-radius: 8px; font-weight: bold; font-family: 'Nunito'; font-size: 15px; }}"); btn.clicked.connect(lambda ch, page=p: self.change_page(page)); self.pagination_layout.addWidget(btn)
    def change_page(self, page):
        if self.current_page != page: self.current_page = page; self.load_mock_data()
    def go_to_page_from_input(self):
        text = self.txt_show.text().strip()
        if text.isdigit():
            page = max(1, min(int(text), self.total_pages))
            if page != self.current_page: self.change_page(page)
            else: self.txt_show.setText(str(self.current_page))
        else: self.txt_show.setText(str(self.current_page))

    def _on_export(self):
        out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output'); os.makedirs(out_dir, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(self, "Export Customers", os.path.join(out_dir, "Customers.csv"), "CSV Files (*.csv)")
        if not path: return
        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount() - 1)]
                writer.writerow(headers)
                for row in range(self.table.rowCount()):
                    row_data = []
                    for col in range(self.table.columnCount() - 1):
                        it = self.table.item(row, col)
                        if not it: 
                            row_data.append("")
                        # ĐÃ SỬA LẠI: Dùng format ="Giá_trị" để Excel tự động ẩn format, giữ nguyên số 0
                        elif col == 2: 
                            val = str(it.data(Qt.UserRole)) if it.data(Qt.UserRole) else it.text()
                            row_data.append(f'="{val}"' if val else "")
                        else: 
                            row_data.append(it.text())
                    writer.writerow(row_data)
            ModernPopup("Success", "Customer list exported successfully!", "fa5s.check-circle", self.window()).exec_()
        except Exception as e: ModernPopup("Error", f"Export failed: {str(e)}", "fa5s.times-circle", self.window()).exec_()

# ==========================================
# GIAO DIỆN QUẢN LÝ THỰC ĐƠN
# ==========================================
class MenuWidget(QWidget):
    edit_requested = pyqtSignal(str, str, str, str) # SIGNAL CHUYỂN SANG TRANG EDIT

    def __init__(self):
        super().__init__(); self.setStyleSheet("background: transparent;"); self.layout = QVBoxLayout(self); self.layout.setContentsMargins(40, 40, 40, 40); self.current_page = 1; self.items_per_page = 6; self.total_pages = 1; self.total_items = 0
        self.current_filter = "All Categories" 
        self.initUI()
        
    def initUI(self):
        main_card = QFrame(); main_card.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 15px; border: 1px solid #E5E7EB; }"); shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(20); shadow.setColor(QColor(0,0,0,8)); shadow.setOffset(0,4); main_card.setGraphicsEffect(shadow); self.card_layout = QVBoxLayout(main_card); self.card_layout.setContentsMargins(30, 30, 30, 30); self.card_layout.setSpacing(20)
        top_header = QHBoxLayout(); search_frame = QFrame(); search_frame.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #D1D5DB; border-radius: 25px; }"); search_frame.setFixedSize(400, 50); search_lay = QHBoxLayout(search_frame); search_lay.setContentsMargins(20, 0, 20, 0); search_lay.setSpacing(10); lbl_search_icon = QLabel(); lbl_search_icon.setPixmap(qta.icon('fa5s.search', color='#9CA3AF').pixmap(18, 18)); lbl_search_icon.setStyleSheet("border: none;"); self.txt_search = QLineEdit(); self.txt_search.setPlaceholderText("Search Menu..."); self.txt_search.setStyleSheet("border: none; background: transparent; font-family: 'Nunito'; font-size: 15px; color: #111827;"); search_lay.addWidget(lbl_search_icon); search_lay.addWidget(self.txt_search); top_header.addWidget(search_frame); top_header.addStretch()
        
        self.txt_search.textChanged.connect(self._on_search)
        
        self.btn_filter = QPushButton(qta.icon('fa5s.filter', color='#6B7280'), " Filter"); self.btn_filter.setFixedHeight(50); self.btn_filter.setStyleSheet("QPushButton { background-color: #FFFFFF; color: #6B7280; border: 1px solid #D1D5DB; border-radius: 25px; padding: 0 25px; font-weight: bold; font-family: 'Nunito'; font-size: 14px; } QPushButton:hover { background-color: #F3F4F6; } QPushButton::menu-indicator { image: none; }")
        self.filter_menu = QMenu(self)
        self.filter_menu.setStyleSheet("QMenu { background-color: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 8px; } QMenu::item { padding: 8px 25px; font-family: 'Nunito'; font-size: 14px; color: #4B5563; } QMenu::item:selected { background-color: #F3F4F6; color: #111827; }")
        cats = ["All Categories", "Main Course", "Appetizer", "Dessert", "Beverage"]
        for cat in cats:
            action = QAction(cat, self); action.triggered.connect(lambda checked, c=cat: self._on_filter_changed(c)); self.filter_menu.addAction(action)
        self.btn_filter.setMenu(self.filter_menu)
        top_header.addWidget(self.btn_filter); top_header.addSpacing(15)

        self.btn_add = QPushButton(qta.icon('fa5s.plus', color=BRIGHT_RED), " Add New Item"); self.btn_add.setCursor(QCursor(Qt.PointingHandCursor)); self.btn_add.setFixedHeight(50); self.btn_add.setStyleSheet(f"QPushButton {{ background-color: #FCE8E8; color: {BRIGHT_RED}; border: none; border-radius: 25px; padding: 0 25px; font-weight: bold; font-family: 'Nunito'; font-size: 15px; }} QPushButton:hover {{ background-color: #F8D7D7; }}"); self.btn_add.clicked.connect(self._open_add_dialog); top_header.addWidget(self.btn_add); top_header.addSpacing(15); self.card_layout.addLayout(top_header)
        self.table = QTableWidget(); self.table.setColumnCount(6); self.table.setHorizontalHeaderLabels(["ID", "Image", "Dish Name", "Category", "Price", "Action"]); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter); self.table.verticalHeader().setVisible(False); self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed); self.table.verticalHeader().setDefaultSectionSize(100); self.table.setFocusPolicy(Qt.NoFocus); self.table.setSelectionMode(QTableWidget.NoSelection); self.table.setShowGrid(False); self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff); self.table.setStyleSheet("QTableWidget { border: none; background: transparent; font-family: 'Nunito'; outline: none; } QHeaderView::section { background-color: #E8EAED; color: #4B5563; font-weight: bold; font-size: 15px; border: none; padding: 15px 10px; } QHeaderView::section:first { border-top-left-radius: 12px; border-bottom-left-radius: 12px; } QHeaderView::section:last { border-top-right-radius: 12px; border-bottom-right-radius: 12px; } QTableWidget::item { border-bottom: 1px solid #F3F4F6; color: #111827; font-size: 15px; font-weight: 500; padding: 10px 10px; } QScrollBar:vertical { width: 0px; background: transparent; }")
        self.card_layout.addWidget(self.table, stretch=1); self.pagination_container = QWidget(); self.pagination_layout = QHBoxLayout(self.pagination_container); self.pagination_layout.setContentsMargins(0, 10, 0, 0); self.card_layout.addWidget(self.pagination_container); self.layout.addWidget(main_card); self.load_mock_data()

    def _on_search(self):
        self.current_page = 1; self.load_mock_data()

    def _on_filter_changed(self, category):
        self.current_filter = category; self.current_page = 1; self.load_mock_data()

    def _on_delete(self, did_str):
        confirm = ModernConfirmPopup("Delete Menu Item", f"Are you sure you want to delete Dish ID {did_str}?", "fa5s.exclamation-triangle", self.window())
        if confirm.exec_() == QDialog.Accepted:
            success, msg = db_manager.delete_menu_item(did_str)
            if success:
                ModernPopup("Success", msg, "fa5s.check-circle", self.window()).exec_()
                self.load_mock_data()
            else:
                ModernPopup("Delete Failed", msg, "fa5s.times-circle", self.window()).exec_()

    def load_mock_data(self):
        st = self.txt_search.text().strip().lower()
        raw_data = db_manager.get_menu_items(search_keyword=st, category_filter=self.current_filter)
        
        all_d = []
        for item in raw_data:
            dish_id = f"{item['DishID']:02d}"
            dish_name = item['DishName']
            category = item['Category']
            price = float(item['Price'])
            
            # ĐÃ SỬA: Lấy tên ảnh trực tiếp từ Database
            image = item['ImageName'] if item.get('ImageName') else "default.jpg"
            
            all_d.append((dish_id, dish_name, category, price, image))
        
        self.total_items = len(all_d); self.total_pages = max(1, (self.total_items+5)//6)
        if self.total_items == 0: self.table.setRowCount(0); self.update_pagination_ui(); return
        
        self.current_page = max(1, min(self.current_page, self.total_pages)); start_idx = (self.current_page - 1) * 6; p_data = all_d[start_idx:start_idx+6]; self.table.setRowCount(len(p_data))
        for r, d in enumerate(p_data):
            id_item = QTableWidgetItem(d[0]); id_item.setTextAlignment(Qt.AlignCenter); self.table.setItem(r, 0, id_item)
            img_lbl = QLabel(); img_lbl.setFixedSize(70, 70); current_dir = os.path.dirname(os.path.abspath(__file__)); pixmap = QPixmap(os.path.join(current_dir, 'menu_images', d[4]))
            if not pixmap.isNull():
                scaled = pixmap.scaled(70, 70, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation); crop = scaled.copy(QRect((scaled.width()-70)//2, (scaled.height()-70)//2, 70, 70)); rounded = QPixmap(70, 70); rounded.fill(Qt.transparent); painter = QPainter(rounded); painter.setRenderHint(QPainter.Antialiasing); path = QPainterPath(); path.addRoundedRect(0, 0, 70, 70, 12, 12); painter.setClipPath(path); painter.drawPixmap(0, 0, crop); painter.end(); img_lbl.setPixmap(rounded)
            img_lbl.setStyleSheet("background-color: #F3F4F6; border: none; border-radius: 12px;"); img_w = QWidget(); img_l = QVBoxLayout(img_w); img_l.setContentsMargins(0,0,0,0); img_l.setAlignment(Qt.AlignCenter); img_l.addWidget(img_lbl); self.table.setCellWidget(r, 1, img_w)
            self.table.setItem(r, 2, QTableWidgetItem(d[1]))
            cat_item = QTableWidgetItem(d[2]); cat_item.setTextAlignment(Qt.AlignCenter); self.table.setItem(r, 3, cat_item)
            p_item = QTableWidgetItem(f"{d[3]:,.0f} VND"); p_item.setTextAlignment(Qt.AlignCenter); 
            # ĐÃ SỬA: Chỉ giữ màu đỏ, xóa bỏ setFont để đồng nhất kích thước (15px của bảng)
            p_item.setForeground(QColor(BRIGHT_RED)); 
            self.table.setItem(r, 4, p_item)
            
            # ĐÃ SỬA: Nút Action (Sửa + Xóa) y hệt tab Reservations
            act_w = QWidget(); act_l = QHBoxLayout(act_w); act_l.setContentsMargins(0,0,0,0); act_l.setAlignment(Qt.AlignCenter)
            btn_edit = QPushButton(qta.icon('fa5s.pen', color='#6B7280'), ""); btn_edit.setFixedSize(35, 35); btn_edit.setCursor(QCursor(Qt.PointingHandCursor))
            btn_edit.setStyleSheet("QPushButton { background: transparent; border: 1px solid #D1D5DB; border-radius: 6px; } QPushButton:hover { border-color: #6B7280; }")
            btn_cancel = QPushButton(qta.icon('fa5s.times', color='#6B7280'), ""); btn_cancel.setFixedSize(35, 35); btn_cancel.setCursor(QCursor(Qt.PointingHandCursor))
            btn_cancel.setStyleSheet("QPushButton { background: transparent; border: 1px solid #D1D5DB; border-radius: 6px; } QPushButton:hover { border-color: #EF4444; }")
            
            did_str = str(d[0]); d_name = str(d[1]); d_cat = str(d[2]); d_price = str(d[3])
            btn_edit.clicked.connect(lambda checked, i=did_str, n=d_name, c=d_cat, p=d_price: self.edit_requested.emit(i, n, c, p))
            btn_cancel.clicked.connect(lambda checked, rid=did_str: self._on_delete(rid))
            
            act_l.addWidget(btn_edit); act_l.addSpacing(5); act_l.addWidget(btn_cancel)
            self.table.setCellWidget(r, 5, act_w)
        self.update_pagination_ui()

    def update_pagination_ui(self):
        while self.pagination_layout.count():
            item = self.pagination_layout.takeAt(0); [item.widget().deleteLater() if item.widget() else None]
        if self.total_items == 0: return
        self.txt_show = QLineEdit(str(self.current_page)); self.txt_show.setFixedSize(50, 40); self.txt_show.setAlignment(Qt.AlignCenter); self.txt_show.setStyleSheet(f"QLineEdit {{ background-color: #FCE8E8; color: {BRIGHT_RED}; border-radius: 10px; font-weight: bold; font-family: 'Nunito'; font-size: 16px; border: none; }}"); self.txt_show.editingFinished.connect(self.go_to_page_from_input); self.pagination_layout.addWidget(QLabel("Showing page", styleSheet="color: #9CA3AF; font-family: 'Nunito'; font-size: 16px; font-weight: bold; border: none;")); self.pagination_layout.addSpacing(5); self.pagination_layout.addWidget(self.txt_show); self.pagination_layout.addSpacing(5); self.pagination_layout.addWidget(QLabel(f"out of {self.total_pages}", styleSheet="color: #9CA3AF; font-family: 'Nunito'; font-size: 16px; font-weight: bold; border: none;")); self.pagination_layout.addStretch()
        seq = [1, 2, 3, 4, "...", self.total_pages] if self.total_pages > 5 else list(range(1, self.total_pages+1))
        for p in seq:
            if p == "...": self.pagination_layout.addWidget(QLabel("...", styleSheet="color: #9CA3AF; font-family: 'Nunito'; font-weight: bold; font-size: 18px; border: none;"))
            else:
                btn = QPushButton(str(p)); btn.setFixedSize(40, 40); btn.setCursor(QCursor(Qt.PointingHandCursor)); btn.setStyleSheet(f"QPushButton {{ background-color: {BRIGHT_RED if p == self.current_page else '#E8EAED'}; color: {'white' if p == self.current_page else '#4B5563'}; border: none; border-radius: 8px; font-weight: bold; font-family: 'Nunito'; font-size: 15px; }}"); btn.clicked.connect(lambda ch, page=p: self.change_page(page)); self.pagination_layout.addWidget(btn)
    def change_page(self, page):
        if self.current_page != page: self.current_page = page; self.load_mock_data()
    def go_to_page_from_input(self):
        text = self.txt_show.text().strip()
        if text.isdigit():
            page = max(1, min(int(text), self.total_pages))
            if page != self.current_page: self.change_page(page)
            else: self.txt_show.setText(str(self.current_page))
        else: self.txt_show.setText(str(self.current_page))
    def _open_add_dialog(self):
        if hasattr(self, '_on_add_requested'): self._on_add_requested()

# ==========================================
# GIAO DIỆN QUẢN LÝ CHI PHÍ (EXPENSES)
# ==========================================
class ExpensesWidget(QWidget):
    edit_requested = pyqtSignal(str, str, str, str, str) # SIGNAL CHUYỂN SANG TRANG EDIT

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: transparent;")
        self.layout = QVBoxLayout(self); self.layout.setContentsMargins(40, 40, 40, 40)
        self.current_page = 1; self.items_per_page = 8; self.total_pages = 1; self.total_items = 0
        self.current_filter = "All Categories"
        self.initUI()

    def initUI(self):
        main_card = QFrame(); main_card.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 15px; border: 1px solid #E5E7EB; }"); shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(20); shadow.setColor(QColor(0,0,0,8)); shadow.setOffset(0,4); main_card.setGraphicsEffect(shadow); self.card_layout = QVBoxLayout(main_card); self.card_layout.setContentsMargins(30, 30, 30, 30); self.card_layout.setSpacing(20)
        
        top_header = QHBoxLayout(); top_header.addStretch() 
        
        self.btn_filter = QPushButton(qta.icon('fa5s.filter', color='#6B7280'), " Filter"); self.btn_filter.setFixedHeight(50); self.btn_filter.setStyleSheet("QPushButton { background-color: #FFFFFF; color: #6B7280; border: 1px solid #D1D5DB; border-radius: 25px; padding: 0 25px; font-weight: bold; font-family: 'Nunito'; font-size: 15px; } QPushButton:hover { background-color: #F3F4F6; } QPushButton::menu-indicator { image: none; }")
        self.filter_menu = QMenu(self)
        self.filter_menu.setStyleSheet("QMenu { background-color: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 8px; } QMenu::item { padding: 8px 25px; font-family: 'Nunito'; font-size: 14px; color: #4B5563; } QMenu::item:selected { background-color: #F3F4F6; color: #111827; }")
        cats = ["All Categories", "Ingredients", "Marketing", "Maintenance", "Payroll", "Utilities", "Supplies"]
        for cat in cats:
            action = QAction(cat, self); action.triggered.connect(lambda checked, c=cat: self._on_filter_changed(c)); self.filter_menu.addAction(action)
        self.btn_filter.setMenu(self.filter_menu)
        top_header.addWidget(self.btn_filter); top_header.addSpacing(15)

        self.btn_add = QPushButton(qta.icon('fa5s.plus', color=BRIGHT_RED), " Add New Expense"); self.btn_add.setCursor(QCursor(Qt.PointingHandCursor)); self.btn_add.setFixedHeight(50); self.btn_add.setStyleSheet(f"QPushButton {{ background-color: #FCE8E8; color: {BRIGHT_RED}; border: none; border-radius: 25px; padding: 0 25px; font-weight: bold; font-family: 'Nunito'; font-size: 15px; }} QPushButton:hover {{ background-color: #F8D7D7; }}"); self.btn_add.clicked.connect(self._open_add_dialog); top_header.addWidget(self.btn_add); top_header.addSpacing(15); self.card_layout.addLayout(top_header)
        self.table = QTableWidget(); self.table.setColumnCount(6); self.table.setHorizontalHeaderLabels(["ID", "Description", "Category", "Date", "Amount", "Action"]); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter); self.table.verticalHeader().setVisible(False); self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed); self.table.verticalHeader().setDefaultSectionSize(70); self.table.setFocusPolicy(Qt.NoFocus); self.table.setSelectionMode(QTableWidget.NoSelection); self.table.setShowGrid(False); self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff); 
        self.table.setStyleSheet("QTableWidget { border: none; background: transparent; font-family: 'Nunito'; outline: none; } QHeaderView::section { background-color: #E8EAED; color: #4B5563; font-weight: bold; font-size: 15px; border: none; padding: 15px 10px; } QHeaderView::section:first { border-top-left-radius: 12px; border-bottom-left-radius: 12px; } QHeaderView::section:last { border-top-right-radius: 12px; border-bottom-right-radius: 12px; } QTableWidget::item { border-bottom: 1px solid #F3F4F6; color: #111827; font-size: 15px; font-weight: 500; padding: 10px 10px; } QScrollBar:vertical { width: 0px; background: transparent; }")
        self.card_layout.addWidget(self.table, stretch=1); self.pagination_container = QWidget(); self.pagination_layout = QHBoxLayout(self.pagination_container); self.pagination_layout.setContentsMargins(0, 10, 0, 0); self.card_layout.addWidget(self.pagination_container); self.layout.addWidget(main_card); self.load_mock_data()

    def _on_filter_changed(self, category):
        self.current_filter = category; self.current_page = 1; self.load_mock_data()

    def _on_delete(self, exp_id_str):
        confirm = ModernConfirmPopup("Delete Expense", f"Are you sure you want to delete Expense ID {exp_id_str}?", "fa5s.exclamation-triangle", self.window())
        if confirm.exec_() == QDialog.Accepted:
            success, msg = db_manager.delete_expense(exp_id_str)
            if success:
                ModernPopup("Success", msg, "fa5s.check-circle", self.window()).exec_()
                self.load_mock_data()
            else:
                ModernPopup("Delete Failed", msg, "fa5s.times-circle", self.window()).exec_()

    def load_mock_data(self):
        raw_data = db_manager.get_expenses(category_filter=self.current_filter)
        all_data = []
        for item in raw_data:
            expense_id = f"EX{item['ExpenseID']:03d}"
            desc = item['Description']
            cat = item['ExpenseCategory']
            
            date_val = item['ExpenseDate']
            date_str = date_val.strftime('%Y-%m-%d') if hasattr(date_val, 'strftime') else str(date_val)
            raw_amt = str(item['Amount']) # LƯU RAW AMOUNT CHO NÚT EDIT
            amount = f"{float(item['Amount']):,.0f} VND"
            
            all_data.append((expense_id, desc, cat, date_str, amount, raw_amt))
            
        self.total_items = len(all_data); self.total_pages = max(1, (self.total_items + self.items_per_page - 1) // self.items_per_page)
        if self.total_items == 0: self.table.setRowCount(0); self.update_pagination_ui(); return
        
        self.current_page = max(1, min(self.current_page, self.total_pages)); start_idx = (self.current_page - 1) * self.items_per_page; end_idx = start_idx + self.items_per_page; page_data = all_data[start_idx:end_idx]; self.table.setRowCount(len(page_data))
        for row, data in enumerate(page_data):
            for col in range(5):
                item = QTableWidgetItem(data[col]); item.setTextAlignment(Qt.AlignCenter)
                # ĐÃ SỬA: Bỏ font size to, chỉ giữ màu đỏ
                if col == 4: item.setForeground(QColor(BRIGHT_RED))
                self.table.setItem(row, col, item)
                
            # ĐÃ SỬA: Nút Action (Sửa + Xóa) y hệt tab Reservations
            act_w = QWidget(); act_l = QHBoxLayout(act_w); act_l.setContentsMargins(0,0,0,0); act_l.setAlignment(Qt.AlignCenter)
            btn_edit = QPushButton(qta.icon('fa5s.pen', color='#6B7280'), ""); btn_edit.setFixedSize(35, 35); btn_edit.setCursor(QCursor(Qt.PointingHandCursor))
            btn_edit.setStyleSheet("QPushButton { background: transparent; border: 1px solid #D1D5DB; border-radius: 6px; } QPushButton:hover { border-color: #6B7280; }")
            btn_cancel = QPushButton(qta.icon('fa5s.times', color='#6B7280'), ""); btn_cancel.setFixedSize(35, 35); btn_cancel.setCursor(QCursor(Qt.PointingHandCursor))
            btn_cancel.setStyleSheet("QPushButton { background: transparent; border: 1px solid #D1D5DB; border-radius: 6px; } QPushButton:hover { border-color: #EF4444; }")
            
            exp_id_str = str(data[0]); e_desc = str(data[1]); e_cat = str(data[2]); e_date = str(data[3]); e_raw_amt = str(data[5])
            btn_edit.clicked.connect(lambda checked, i=exp_id_str, d=e_desc, c=e_cat, dt=e_date, a=e_raw_amt: self.edit_requested.emit(i, d, c, dt, a))
            btn_cancel.clicked.connect(lambda checked, rid=exp_id_str: self._on_delete(rid))
            
            act_l.addWidget(btn_edit); act_l.addSpacing(5); act_l.addWidget(btn_cancel)
            self.table.setCellWidget(row, 5, act_w)
        self.update_pagination_ui()

    def update_pagination_ui(self):
        while self.pagination_layout.count():
            item = self.pagination_layout.takeAt(0); [item.widget().deleteLater() if item.widget() else None]
        if self.total_items == 0: return
        lbl_show = QLabel("Showing page"); lbl_show.setStyleSheet("color: #9CA3AF; font-family: 'Nunito'; font-size: 16px; font-weight: bold; border: none;"); self.txt_show = QLineEdit(str(self.current_page)); self.txt_show.setFixedSize(50, 40); self.txt_show.setAlignment(Qt.AlignCenter); self.txt_show.setStyleSheet(f"QLineEdit {{ background-color: #FCE8E8; color: {BRIGHT_RED}; border-radius: 10px; font-weight: bold; font-family: 'Nunito'; font-size: 16px; border: none; }}"); self.txt_show.editingFinished.connect(self.go_to_page_from_input); lbl_out = QLabel(f"out of {self.total_pages}"); lbl_out.setStyleSheet("color: #9CA3AF; font-family: 'Nunito'; font-size: 16px; font-weight: bold; border: none;"); self.pagination_layout.addWidget(lbl_show); self.pagination_layout.addSpacing(5); self.pagination_layout.addWidget(self.txt_show); self.pagination_layout.addSpacing(5); self.pagination_layout.addWidget(lbl_out); self.pagination_layout.addStretch()
        total = self.total_pages; current = self.current_page
        if total <= 5: seq = list(range(1, total + 1))
        elif current <= 3: seq = [1, 2, 3, 4, "...", total]
        elif current >= total - 2: seq = [1, "...", total - 3, total - 2, total - 1, total]
        else: seq = [1, "...", current - 1, current, current + 1, "...", total]
        for p in seq:
            if p == "...": lbl = QLabel("..."); lbl.setStyleSheet("color: #9CA3AF; font-family: 'Nunito'; font-weight: bold; font-size: 18px; border: none;"); self.pagination_layout.addWidget(lbl); self.pagination_layout.addSpacing(5)
            else:
                btn = QPushButton(str(p)); btn.setFixedSize(40, 40); btn.setCursor(QCursor(Qt.PointingHandCursor)); btn.setStyleSheet(f"QPushButton {{ background-color: {BRIGHT_RED if p == self.current_page else '#E8EAED'}; color: {'white' if p == self.current_page else '#4B5563'}; border: none; border-radius: 8px; font-weight: bold; font-family: 'Nunito'; font-size: 15px; }}"); btn.clicked.connect(lambda ch, page=p: self.change_page(page)); self.pagination_layout.addWidget(btn); self.pagination_layout.addSpacing(5)

    def change_page(self, page):
        if self.current_page != page: self.current_page = page; self.load_mock_data()
    def go_to_page_from_input(self):
        text = self.txt_show.text().strip()
        if text.isdigit():
            page = max(1, min(int(text), self.total_pages))
            if page != self.current_page: self.change_page(page)
            else: self.txt_show.setText(str(self.current_page))
        else: self.txt_show.setText(str(self.current_page))
    def _open_add_dialog(self):
        if hasattr(self, '_on_add_requested'): self._on_add_requested()

# ==========================================
# GIAO DIỆN QUẢN LÝ ĐẶT BÀN (RESERVATIONS)
# ==========================================
class ReservationsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: transparent;")
        self.layout = QVBoxLayout(self); self.layout.setContentsMargins(40, 40, 40, 40)
        self.current_page = 1; self.items_per_page = 8; self.total_pages = 1; self.total_items = 0; self.initUI()

    def initUI(self):
        main_card = QFrame(); main_card.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 15px; border: 1px solid #E5E7EB; }"); shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(20); shadow.setColor(QColor(0,0,0,8)); shadow.setOffset(0,4); main_card.setGraphicsEffect(shadow); self.card_layout = QVBoxLayout(main_card); self.card_layout.setContentsMargins(30, 30, 30, 30); self.card_layout.setSpacing(20)
        
        top_header = QHBoxLayout(); search_frame = QFrame(); search_frame.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #D1D5DB; border-radius: 25px; }"); search_frame.setFixedSize(400, 50); search_lay = QHBoxLayout(search_frame); search_lay.setContentsMargins(20, 0, 20, 0); search_lay.setSpacing(10); lbl_search_icon = QLabel(); lbl_search_icon.setPixmap(qta.icon('fa5s.search', color='#9CA3AF').pixmap(18, 18)); lbl_search_icon.setStyleSheet("border: none;"); self.txt_search = QLineEdit(); self.txt_search.setPlaceholderText("Search Reservations by Name, Phone or Date..."); self.txt_search.setStyleSheet("border: none; background: transparent; font-family: 'Nunito'; font-size: 15px; color: #111827;"); search_lay.addWidget(lbl_search_icon); search_lay.addWidget(self.txt_search); top_header.addWidget(search_frame); top_header.addStretch()
        
        self.txt_search.textChanged.connect(self._on_search) # THÊM SEARCH REAL-TIME
        
        self.btn_export = QPushButton(qta.icon('fa5s.download', color='#6B7280'), " Export"); self.btn_export.setFixedHeight(50); self.btn_export.setStyleSheet("QPushButton { background-color: #FFFFFF; color: #6B7280; border: 1px solid #D1D5DB; border-radius: 25px; padding: 0 25px; font-weight: bold; font-family: 'Nunito'; font-size: 15px; } QPushButton:hover { background-color: #F3F4F6; }"); top_header.addWidget(self.btn_export); self.card_layout.addLayout(top_header)
        
        self.table = QTableWidget(); self.table.setColumnCount(7); self.table.setHorizontalHeaderLabels(["Reservation ID", "Customer Name", "Phone", "Date & Time", "Table", "Guest Count", "Action"]); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter); self.table.verticalHeader().setVisible(False); self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed); self.table.verticalHeader().setDefaultSectionSize(70); self.table.setFocusPolicy(Qt.NoFocus); self.table.setSelectionMode(QTableWidget.NoSelection); self.table.setShowGrid(False); self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff); 
        self.table.setStyleSheet("QTableWidget { border: none; background: transparent; font-family: 'Nunito'; outline: none; } QHeaderView::section { background-color: #E8EAED; color: #4B5563; font-weight: bold; font-size: 15px; border: none; padding: 15px 10px; } QHeaderView::section:first { border-top-left-radius: 12px; border-bottom-left-radius: 12px; } QHeaderView::section:last { border-top-right-radius: 12px; border-bottom-right-radius: 12px; } QTableWidget::item { border-bottom: 1px solid #F3F4F6; color: #111827; font-size: 15px; font-weight: 500; padding: 10px 10px; } QScrollBar:vertical { width: 0px; background: transparent; }")
        self.card_layout.addWidget(self.table, stretch=1); self.pagination_container = QWidget(); self.pagination_layout = QHBoxLayout(self.pagination_container); self.pagination_layout.setContentsMargins(0, 10, 0, 0); self.card_layout.addWidget(self.pagination_container); self.layout.addWidget(main_card); self.load_mock_data()

    def _on_search(self):
        self.current_page = 1; self.load_mock_data()

    def _on_delete(self, res_id_str):
        confirm = ModernConfirmPopup(
            "Cancel Reservation",
            f"Are you sure you want to cancel {res_id_str}?\nThis action cannot be undone.",
            "fa5s.exclamation-triangle",
            self.window()
        )
        if confirm.exec_() == QDialog.Accepted:
            try:
                rid = int(res_id_str.replace('RES', ''))
                conn = db_manager.connect()
                cursor = conn.cursor()
                cursor.execute("SELECT TableID FROM Reservations WHERE ReservationID = %s", (rid,))
                res = cursor.fetchone()
                if res:
                    table_id = res[0]
                    cursor.execute("DELETE FROM Reservations WHERE ReservationID = %s", (rid,))
                    cursor.execute("UPDATE DiningTables SET Status = 'Available' WHERE TableID = %s", (table_id,))
                    conn.commit()
                conn.close()
                ModernPopup("Success", f"{res_id_str} has been cancelled.", "fa5s.check-circle", self.window()).exec_()
                self.load_mock_data()
            except Exception as e:
                ModernPopup("Error", str(e), "fa5s.times-circle", self.window()).exec_()

    def load_mock_data(self):
        st = self.txt_search.text().strip().lower()
        raw_data = db_manager.get_reservations(search_keyword=st)
        all_data = []
        
        for item in raw_data:
            res_id = f"RES{item['ReservationID']:03d}"
            cust_name = item['CustomerName']
            phone = str(item['Phone'])
            masked_phone = phone[:3] + "****" + phone[-3:] if len(phone) >= 6 else phone
            
            date_val = item['DateTime']
            date_str = date_val.strftime('%Y-%m-%d %H:%M') if hasattr(date_val, 'strftime') else str(date_val)
            
            table_no = str(item['TableNumber'])
            guests = str(item['GuestCount'])
            
            all_data.append((res_id, cust_name, masked_phone, date_str, table_no, guests))
            
        self.total_items = len(all_data); 
        if self.total_items == 0: 
            self.table.setRowCount(0); self.total_pages = 1; self.update_pagination_ui(); return
            
        self.total_pages = (self.total_items + self.items_per_page - 1) // self.items_per_page; self.current_page = max(1, min(self.current_page, self.total_pages)); start_idx = (self.current_page - 1) * self.items_per_page; end_idx = start_idx + self.items_per_page; page_data = all_data[start_idx:end_idx]; self.table.setRowCount(len(page_data))
        
        for row, data in enumerate(page_data):
            for col in range(6):
                item = QTableWidgetItem(data[col]); item.setTextAlignment(Qt.AlignCenter)
                if col == 0: item.setForeground(QColor("#4B5563"))
                self.table.setItem(row, col, item)
                
            act_w = QWidget(); act_l = QHBoxLayout(act_w); act_l.setContentsMargins(0,0,0,0); act_l.setAlignment(Qt.AlignCenter)
            btn_cancel = QPushButton(qta.icon('fa5s.times', color='#6B7280'), ""); btn_cancel.setFixedSize(35, 35); btn_cancel.setCursor(QCursor(Qt.PointingHandCursor))
            btn_cancel.setStyleSheet("QPushButton { background: transparent; border: 1px solid #D1D5DB; border-radius: 6px; } QPushButton:hover { border-color: #EF4444; }")
            res_id_str = data[0]
            btn_cancel.clicked.connect(lambda checked, rid=res_id_str: self._on_delete(rid))
            act_l.addWidget(btn_cancel)
            self.table.setCellWidget(row, 6, act_w)
            
        self.update_pagination_ui()

    def update_pagination_ui(self):
        while self.pagination_layout.count():
            item = self.pagination_layout.takeAt(0); [item.widget().deleteLater() if item.widget() else None]
        if self.total_items == 0: return
        lbl_show = QLabel("Showing page"); lbl_show.setStyleSheet("color: #9CA3AF; font-family: 'Nunito'; font-size: 16px; font-weight: bold; border: none;"); self.txt_show = QLineEdit(str(self.current_page)); self.txt_show.setFixedSize(50, 40); self.txt_show.setAlignment(Qt.AlignCenter); self.txt_show.setStyleSheet(f"QLineEdit {{ background-color: #FCE8E8; color: {BRIGHT_RED}; border-radius: 10px; font-weight: bold; font-family: 'Nunito'; font-size: 16px; border: none; }}"); self.txt_show.editingFinished.connect(self.go_to_page_from_input); lbl_out = QLabel(f"out of {self.total_pages}"); lbl_out.setStyleSheet("color: #9CA3AF; font-family: 'Nunito'; font-size: 16px; font-weight: bold; border: none;"); self.pagination_layout.addWidget(lbl_show); self.pagination_layout.addSpacing(5); self.pagination_layout.addWidget(self.txt_show); self.pagination_layout.addSpacing(5); self.pagination_layout.addWidget(lbl_out); self.pagination_layout.addStretch()
        total = self.total_pages; current = self.current_page
        if total <= 5: seq = list(range(1, total + 1))
        elif current <= 3: seq = [1, 2, 3, 4, "...", total]
        elif current >= total - 2: seq = [1, "...", total - 3, total - 2, total - 1, total]
        else: seq = [1, "...", current - 1, current, current + 1, "...", total]
        for p in seq:
            if p == "...": lbl = QLabel("..."); lbl.setStyleSheet("color: #9CA3AF; font-family: 'Nunito'; font-weight: bold; font-size: 18px; border: none;"); self.pagination_layout.addWidget(lbl); self.pagination_layout.addSpacing(5)
            else:
                btn = QPushButton(str(p)); btn.setFixedSize(40, 40); btn.setCursor(QCursor(Qt.PointingHandCursor)); btn.setStyleSheet(f"QPushButton {{ background-color: {BRIGHT_RED if p == self.current_page else '#E8EAED'}; color: {'white' if p == self.current_page else '#4B5563'}; border: none; border-radius: 8px; font-weight: bold; font-family: 'Nunito'; font-size: 15px; }}"); btn.clicked.connect(lambda ch, page=p: self.change_page(page)); self.pagination_layout.addWidget(btn); self.pagination_layout.addSpacing(5)

    def change_page(self, page):
        if self.current_page != page: self.current_page = page; self.load_mock_data()

    def go_to_page_from_input(self):
        text = self.txt_show.text().strip()
        if text.isdigit():
            page = max(1, min(int(text), self.total_pages))
            if page != self.current_page: self.change_page(page)
            else: self.txt_show.setText(str(self.current_page))
        else: self.txt_show.setText(str(self.current_page))


class ReceiptPage(QWidget):
    close_receipt = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {BG_COLOR};")
        self.inv_id = ""; self.customer = ""; self.phone = ""; self.table_no = ""; self.date = ""; self.subtotal = ""; self.svc = ""; self.discount = ""; self.total = ""
        self._build_ui()
        
    def load_receipt(self, inv_id, customer, phone, table_no, date, subtotal, svc, discount, total):
        self.inv_id = inv_id; self.customer = customer; self.phone = phone; self.table_no = table_no; self.date = date; self.subtotal = subtotal; self.svc = svc; self.discount = discount; self.total = total
        self.lbl_title.setText(f"<span style='color: {RUBY_SOLID};'>#</span><span style='color: {RUBY_SOLID};'>{self.inv_id}</span>")
        self.val_cust.setText(self.customer); self.val_phone.setText(self.phone); self.val_tab.setText(self.table_no); self.val_date.setText(self.date)
        
        self.val_sub.setText(self.subtotal.replace(" VND", ""))
        self.val_svc.setText(self.svc.replace(" VND", ""))
        self.val_disc.setText(f"-{self.discount.replace(' VND', '')}" if float(self.discount.replace(',', '')) > 0 else "0")
        self.val_tot.setText(self.total)
        
        # --- UPDATE TABLE ITEMS DYNAMICALLY ---
        items = db_manager.get_invoice_items(self.inv_id)
        self.table.setRowCount(len(items))
        for r, data in enumerate(items):
            name = data['DishName']
            price = f"{float(data['UnitPrice']):,.0f}"
            qty = str(data['Quantity'])
            tot = f"{(float(data['UnitPrice']) * data['Quantity']):,.0f}"
            
            it0 = QTableWidgetItem(name); it0.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            it1 = QTableWidgetItem(price); it1.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            it2 = QTableWidgetItem(qty); it2.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            it3 = QTableWidgetItem(tot); it3.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            self.table.setItem(r, 0, it0)
            self.table.setItem(r, 1, it1)
            self.table.setItem(r, 2, it2)
            self.table.setItem(r, 3, it3)
        self.table.resizeRowsToContents()
        
        # ĐÃ SỬA: Tính toán độ cao chuẩn của bảng để hiển thị hết tất cả các món không bị ẩn
        table_height = self.table.horizontalHeader().height()
        for r in range(self.table.rowCount()): table_height += self.table.rowHeight(r)
        self.table.setFixedHeight(table_height + 10)
        
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0) # Xóa margin ngoài cùng để cuộn full trang
        
        # ĐÃ SỬA: Bao QScrollArea ngoài để hóa đơn dài xuống dưới không giới hạn
        scroll = QScrollArea()
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { border: none; background: transparent; width: 8px; margin: 0px; } QScrollBar::handle:vertical { background: #D1D5DB; border-radius: 4px; }")
        scroll.setWidgetResizable(True)
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        content_lay = QVBoxLayout(scroll_content)
        content_lay.setContentsMargins(60, 40, 60, 40)
        
        center_lay = QHBoxLayout()
        center_lay.addStretch()
        
        main_frame = QFrame()
        main_frame.setFixedWidth(700) # ĐÃ SỬA: Chỉ set chiều rộng tĩnh, chiều dài mở khóa
        main_frame.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E5E7EB; }")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20); shadow.setColor(QColor(0, 0, 0, 15)); shadow.setOffset(0, 4)
        main_frame.setGraphicsEffect(shadow)
        
        f_lay = QVBoxLayout(main_frame)
        f_lay.setContentsMargins(50, 50, 50, 50)
        f_lay.setSpacing(25)

        head_lay = QHBoxLayout()
        
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(0)
        self.lbl_title = QLabel("")
        bordeaux_num_font = QFont("'Inter Black', 'Segoe UI Variable Display', 'Segoe UI Black', sans-serif", 32, QFont.Bold)
        self.lbl_title.setFont(bordeaux_num_font)
        self.lbl_title.setStyleSheet("border: none; background: transparent; margin: 0; padding: 0;")
        
        lbl_sub = QLabel("MAISON DES RÊVES")
        lbl_sub.setStyleSheet("color: #9CA3AF; font-family: 'Nunito'; font-weight: 800; font-size: 14px; border: none; background: transparent; letter-spacing: 1px; margin: 0; padding: 0;")
        
        title_vbox.addWidget(self.lbl_title)
        title_vbox.addWidget(lbl_sub)
        
        head_lay.addLayout(title_vbox)
        head_lay.addStretch()
        
        btn_close_top = QPushButton(qta.icon('fa5s.times', color='#9CA3AF'), "")
        btn_close_top.setIconSize(QSize(24, 24))
        btn_close_top.setFixedSize(40, 40)
        btn_close_top.setCursor(QCursor(Qt.PointingHandCursor))
        btn_close_top.setStyleSheet("QPushButton { background: transparent; border: none; } QPushButton:hover { background-color: #F3F4F6; border-radius: 20px; }")
        btn_close_top.clicked.connect(self.close_receipt.emit)
        head_lay.addWidget(btn_close_top, alignment=Qt.AlignTop)
        
        f_lay.addLayout(head_lay)
        
        div1 = QFrame(); div1.setFixedHeight(1); div1.setStyleSheet("background-color: #F3F4F6; border: none;")
        f_lay.addWidget(div1)
        
        info_lay = QGridLayout(); info_lay.setSpacing(15)
        def mk_lbl(text, is_val=False):
            l = QLabel(text)
            if is_val: 
                l.setStyleSheet("color: #111827; font-family: 'Nunito'; font-size: 14px; font-weight: 800; border: none;")
            else: 
                l.setStyleSheet("color: #9CA3AF; font-family: 'Nunito'; font-size: 14px; font-weight: 800; border: none;")
            return l

        info_lay.addWidget(mk_lbl("CUSTOMER:"), 0, 0); self.val_cust = mk_lbl("", True); info_lay.addWidget(self.val_cust, 1, 0)
        info_lay.addWidget(mk_lbl("PHONE:"), 0, 1); self.val_phone = mk_lbl("", True); info_lay.addWidget(self.val_phone, 1, 1)
        info_lay.addWidget(mk_lbl("TABLE:"), 2, 0); self.val_tab = mk_lbl("", True); info_lay.addWidget(self.val_tab, 3, 0)
        info_lay.addWidget(mk_lbl("PAYMENT DATE:"), 2, 1); self.val_date = mk_lbl("", True); info_lay.addWidget(self.val_date, 3, 1)
        f_lay.addLayout(info_lay)

        f_lay.addSpacing(10)
        
        lbl_det = QLabel("ORDER DETAIL")
        lbl_det.setStyleSheet("color: #6B7280; font-family: 'Nunito'; font-weight: 800; font-size: 14px; border: none;")
        f_lay.addWidget(lbl_det)
        
        self.table = QTableWidget(0, 4) 
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 4): self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setFocusPolicy(Qt.NoFocus); self.table.setSelectionMode(QTableWidget.NoSelection); self.table.setShowGrid(False)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.table.setFrameShape(QFrame.NoFrame)
        self.table.setStyleSheet("""
            QTableWidget { border: none; background: transparent; font-family: 'Nunito'; outline: none; }
            QHeaderView { border: none; background: transparent; }
            QHeaderView::section { 
                background-color: transparent; 
                color: #9CA3AF; 
                font-weight: 800; 
                font-size: 13px; 
                border-top: 1px solid #E5E7EB; 
                border-bottom: 1px solid #E5E7EB; 
                border-left: 0px solid transparent; 
                border-right: 0px solid transparent; 
                border-radius: 0px;
                padding: 12px 5px; 
            }
            QTableWidget::item { border: none; color: #111827; padding: 15px 5px; font-size: 14px; font-weight: 700; }
        """)
        
        headers = ["ITEM NAME", "PRICE", "QTY", "TOTAL"]
        self.table.setColumnCount(4)
        for i, h in enumerate(headers):
            h_item = QTableWidgetItem(h)
            if i == 0: h_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            elif i == 1: h_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            elif i == 2: h_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            else: h_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setHorizontalHeaderItem(i, h_item)
        
        f_lay.addWidget(self.table)
        f_lay.setSpacing(0)  # ép 2 widget liền nhau

        div_mid = QFrame(); div_mid.setFixedHeight(1); div_mid.setStyleSheet("background-color: #E5E7EB; border: none;")
        f_lay.addWidget(div_mid)

        f_lay.addSpacing(25)  # trả lại spacing cho phần bên dưới div_mid

        tot_container = QWidget()
        tot_container.setStyleSheet("background: transparent;") 
        tot_lay = QVBoxLayout(tot_container)
        tot_lay.setContentsMargins(0, 10, 0, 10)
        tot_lay.setSpacing(15)
        
        def add_tot_row(label_text, val_widget, is_grand_total=False):
            r = QHBoxLayout()
            r.setContentsMargins(0, 0, 0, 0)
            l = QLabel(label_text)
            if is_grand_total:
                l.setStyleSheet("color: #111827; font-family: 'Nunito'; font-weight: 900; font-size: 18px; border: none;")
                val_widget.setStyleSheet("color: #111827; font-family: 'Nunito'; font-weight: 900; font-size: 16px; border: none;")
            else:
                l.setStyleSheet("color: #6B7280; font-family: 'Nunito'; font-weight: 700; font-size: 16px; border: none;")
                val_widget.setStyleSheet("color: #111827; font-family: 'Nunito'; font-weight: 800; font-size: 16px; border: none;")
            
            val_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            r.addWidget(l); r.addStretch(); r.addWidget(val_widget); tot_lay.addLayout(r)

        self.val_sub = QLabel("0")
        self.val_svc = QLabel("0")
        self.val_disc = QLabel("0")
        self.val_tot = QLabel("0 VND")
        
        add_tot_row("Subtotal:", self.val_sub)
        add_tot_row("Service Charge (10%):", self.val_svc)
        add_tot_row("Discount (5%):", self.val_disc)
        
        div_tot = QFrame(); div_tot.setFixedHeight(1); div_tot.setStyleSheet("background-color: #E5E7EB; border: none;")
        tot_lay.addWidget(div_tot)
        
        tot_lay.addSpacing(5)
        add_tot_row("Grand Total:", self.val_tot, True)
        f_lay.addWidget(tot_container)

        f_lay.addSpacing(20)
        
        btn_lay = QHBoxLayout()
        btn_close = QPushButton("Close")
        btn_close.setFixedSize(160, 50)
        btn_close.setCursor(QCursor(Qt.PointingHandCursor))
        btn_close.setStyleSheet("QPushButton { background-color: #FFFFFF; color: #4B5563; border: 2px solid #E5E7EB; border-radius: 8px; font-weight: bold; font-family: 'Nunito'; font-size: 15px; } QPushButton:hover { background-color: #F9FAFB; }")
        btn_close.clicked.connect(self.close_receipt.emit)
        
        btn_print = QPushButton("Print Receipt")
        btn_print.setFixedSize(160, 50)
        btn_print.setCursor(QCursor(Qt.PointingHandCursor))
        btn_print.setStyleSheet(f"QPushButton {{ background-color: {RUBY_SOLID}; color: #FFFFFF; border: none; border-radius: 8px; font-weight: bold; font-family: 'Nunito'; font-size: 15px; }} QPushButton:hover {{ background-color: #801836; }}")
        
        btn_lay.addWidget(btn_close)
        btn_lay.addStretch()
        btn_lay.addWidget(btn_print)
        f_lay.addLayout(btn_lay)

        center_lay.addWidget(main_frame)
        center_lay.addStretch()
        content_lay.addLayout(center_lay) # Add vào content của scroll
        
        scroll.setWidget(scroll_content)
        root.addWidget(scroll) # Add thanh cuộn vào root


# ==========================================
# MAIN DASHBOARD WINDOW 
# ==========================================
class ManagerDashboard(QWidget):
    def __init__(self):
        super().__init__(); self.setWindowTitle("Manager Dashboard"); self.setStyleSheet(f"background-color: {BG_COLOR};"); self.initUI()

    def handle_logout(self):
        from login import LoginWindow
        self.login_window = LoginWindow()
        self.login_window.show()
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def create_status_pill(self, status):
        w = QWidget(); w.setStyleSheet("background-color: #FFFFFF;"); l = QHBoxLayout(w); l.setContentsMargins(0,0,0,0); l.setAlignment(Qt.AlignCenter); lbl = QLabel(status)
        if status == "Paid": lbl.setStyleSheet("background-color: #D1FAE5; color: #059669; padding: 6px 14px; border-radius: 12px; font-weight: bold; font-family: 'Nunito'; font-size: 11px;")
        elif status == "Pending": lbl.setStyleSheet("background-color: #FEF3C7; color: #D97706; padding: 6px 14px; border-radius: 12px; font-weight: bold; font-family: 'Nunito'; font-size: 11px;")
        l.addWidget(lbl); return w

    def switch_tab(self, index):
        self.stack.setCurrentIndex(index)
        self.btn_dash.is_active = (index == 0); self.btn_dash.update_style()
        self.btn_cust.is_active = (index == 1); self.btn_cust.update_style()
        self.btn_resv.is_active = (index == 2); self.btn_resv.update_style()
        self.btn_menu.is_active = (index == 3); self.btn_menu.update_style()
        self.btn_invoices.is_active = (index == 4); self.btn_invoices.update_style()
        self.btn_expense.is_active = (index == 5); self.btn_expense.update_style()
        
        # MỚI: Nếu quay lại Dashboard thì tự động làm mới dữ liệu
        if index == 0:
            self.refresh_dashboard_data()

    def initUI(self):
        main_layout = QHBoxLayout(self); main_layout.setContentsMargins(20, 20, 20, 20); main_layout.setSpacing(20)
        sidebar = QFrame(); sidebar.setFixedWidth(260); sidebar.setStyleSheet(f"QFrame {{ background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {BRIGHT_RED}, stop: 1 #4A0012); border-radius: 25px; }}"); side_layout = QVBoxLayout(sidebar); side_layout.setContentsMargins(20, 40, 20, 40)
        lbl_logo = QLabel("MAISON\n DES RÊVES"); lbl_logo.setFont(QFont('Nunito', 14, QFont.Bold)); lbl_logo.setStyleSheet("color: #FFFFFF; border: none; letter-spacing: 2px; background: transparent;"); lbl_logo.setAlignment(Qt.AlignCenter); side_layout.addWidget(lbl_logo); side_layout.addSpacing(50)
        
        self.btn_dash = SidebarButton("fa5s.chart-bar", "Dashboard", is_active=True)
        self.btn_cust = SidebarButton("fa5s.user", "Customers")
        self.btn_resv = SidebarButton("fa5s.calendar-check", "Reservations")
        self.btn_menu = SidebarButton("fa5s.list-alt", "Menu")
        self.btn_invoices = SidebarButton("fa5s.receipt", "Invoices")
        self.btn_expense = SidebarButton("fa5s.file-invoice-dollar", "Expenses")
        self.btn_exit = SidebarButton("fa5s.sign-out-alt", "Logout")
        
        self.btn_dash.clicked.connect(lambda: self.switch_tab(0))
        self.btn_cust.clicked.connect(lambda: self.switch_tab(1))
        self.btn_resv.clicked.connect(lambda: self.switch_tab(2))
        self.btn_menu.clicked.connect(lambda: self.switch_tab(3))
        self.btn_invoices.clicked.connect(lambda: self.switch_tab(4))
        self.btn_expense.clicked.connect(lambda: self.switch_tab(5))
        self.btn_exit.clicked.connect(self.handle_logout)
        
        [side_layout.addWidget(btn) for btn in [self.btn_dash, self.btn_cust, self.btn_resv, self.btn_menu, self.btn_invoices, self.btn_expense]]
        side_layout.addSpacing(5); side_layout.addStretch(); side_layout.addWidget(self.btn_exit); main_layout.addWidget(sidebar)
        self.stack = QStackedWidget(); main_layout.addWidget(self.stack, stretch=1)

        # TAB 0: DASHBOARD
        dash_scroll = QScrollArea(); dash_scroll.setStyleSheet(MODERN_SCROLL); dash_scroll.setWidgetResizable(True); dash_content = QWidget(); dash_layout = QVBoxLayout(dash_content); dash_layout.setContentsMargins(20, 20, 20, 20); dash_layout.setSpacing(30)
        # Header row: Dashboard title + Exit POS button
        dash_header_lay = QHBoxLayout(); dash_header_lay.setContentsMargins(0,0,0,0)
        lbl_d = QLabel("Dashboard"); lbl_d.setFont(QFont('Nunito', 26, QFont.Bold)); lbl_d.setStyleSheet("color: #111827;")
        btn_exit_pos = QPushButton(qta.icon('fa5s.power-off', color='#FFFFFF', scale_factor=0.7), " Exit POS")
        btn_exit_pos.setFixedSize(110, 36)
        btn_exit_pos.setCursor(QCursor(Qt.PointingHandCursor))
        btn_exit_pos.setFont(QFont('Nunito', 8, QFont.Bold))
        btn_exit_pos.setStyleSheet(f"QPushButton {{ background-color: {EXPENSE_GREY}; color: #FFFFFF; border: none; border-radius: 8px; padding: 0 10px; }} QPushButton:hover {{ background-color: #1F2937; }}")
        btn_exit_pos.clicked.connect(self.close)
        dash_header_lay.addWidget(lbl_d); dash_header_lay.addStretch(); dash_header_lay.addWidget(btn_exit_pos)
        dash_layout.addLayout(dash_header_lay)
        
        stats = db_manager.get_dashboard_kpis()
        kpi_lay = QHBoxLayout()
        self.kpi_orders = KPICard("Total Orders", stats['orders'], "fa5s.receipt")
        self.kpi_cust = KPICard("Total Customers", stats['customers'], "fa5s.users")
        self.kpi_profit = KPICard("Total Profit (Thousand VND)", stats['profit'], "fa5s.chart-line")
        self.kpi_revenue = KPICard("Total Revenue (Thousand VND)", stats['revenue'], "fa5s.wallet", is_primary=True)
        
        kpi_lay.addWidget(self.kpi_orders); kpi_lay.addWidget(self.kpi_cust); kpi_lay.addWidget(self.kpi_profit); kpi_lay.addWidget(self.kpi_revenue)
        dash_layout.addLayout(kpi_lay)
        
        row2 = QHBoxLayout(); self.c1 = ChartCard("Total Revenue", has_legend=True); self.c1.draw_line_chart(); self.c2 = ChartCard("Peak Times"); self.c2.draw_heatmap(); row2.addWidget(self.c1, 2); row2.addWidget(self.c2, 1); dash_layout.addLayout(row2)
        row3 = QHBoxLayout(); self.c3 = ChartCard("Orders Overview"); self.c3.draw_bar_chart(); 
        
        # Chứa Best Dishes vào 1 layout để dễ xóa và vẽ lại khi refresh
        self.best_dishes_container = QWidget(); self.best_dishes_lay = QVBoxLayout(self.best_dishes_container); self.best_dishes_lay.setContentsMargins(0,0,0,0)
        self.bd = BestDishesCard(); self.best_dishes_lay.addWidget(self.bd)
        
        row3.addWidget(self.c3, 2); row3.addWidget(self.best_dishes_container, 1); dash_layout.addLayout(row3)
        
        table_card = QFrame(); table_card.setStyleSheet("QFrame { background-color: white; border-radius: 15px; border: 1px solid #E5E7EB; }"); table_card.setMinimumHeight(350); shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(20); shadow.setColor(QColor(0,0,0,8)); shadow.setOffset(0,4); table_card.setGraphicsEffect(shadow); t_layout = QVBoxLayout(table_card); t_layout.setContentsMargins(25, 25, 25, 25); t_layout.setSpacing(20); t_header = QHBoxLayout(); lbl_t = QLabel("Recent Orders"); lbl_t.setFont(QFont('Nunito', 16, QFont.Bold)); lbl_t.setStyleSheet("border: none; color: #111827;"); t_header.addWidget(lbl_t); t_header.addStretch(); t_layout.addLayout(t_header)
        
        self.table_dash = QTableWidget(5, 7)
        self.table_dash.setHorizontalHeaderLabels(["Invoice ID", "Customer Name", "Table", "Date", "Total Amount", "Status", "Action"])
        self.table_dash.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.table_dash.horizontalHeader().setDefaultAlignment(Qt.AlignCenter); self.table_dash.verticalHeader().setVisible(False); self.table_dash.verticalHeader().setDefaultSectionSize(70); self.table_dash.setFocusPolicy(Qt.NoFocus); self.table_dash.setSelectionMode(QTableWidget.NoSelection); self.table_dash.setShowGrid(False); 
        self.table_dash.setStyleSheet("QTableWidget, QTableView { border: none; background-color: #FFFFFF; font-family: 'Nunito'; outline: none; } QHeaderView::section { background-color: #F3F4F6; color: #6B7280; font-weight: bold; font-size: 13px; border: none; padding: 15px 10px; } QHeaderView::section:first { border-top-left-radius: 8px; border-bottom-left-radius: 8px; } QHeaderView::section:last { border-top-right-radius: 8px; border-bottom-right-radius: 8px; } QTableWidget::item { border-bottom: 1px solid #F3F4F6; background-color: #FFFFFF; color: #111827; padding: 10px 10px; font-size: 13px; font-weight: 600; } QTableWidget::item:selected { background-color: transparent; }")
        
        t_layout.addWidget(self.table_dash); dash_layout.addWidget(table_card); dash_scroll.setWidget(dash_content); self.stack.addWidget(dash_scroll)

        # CÁC TAB KHÁC
        self.customers_view = CustomersWidget(); self.stack.addWidget(self.customers_view)
        self.reservations_view = ReservationsWidget(); self.stack.addWidget(self.reservations_view)
        self.menu_view = MenuWidget(); self.stack.addWidget(self.menu_view)
        self.invoices_view = InvoicesWidget(); self.stack.addWidget(self.invoices_view)
        self.expense_view = ExpensesWidget(); self.stack.addWidget(self.expense_view)
        self.add_menu_page = AddMenuItemPage(); self.stack.addWidget(self.add_menu_page)
        self.menu_view._on_add_requested = lambda: self.stack.setCurrentWidget(self.add_menu_page)
        self.add_menu_page.cancelled.connect(lambda: self.stack.setCurrentWidget(self.menu_view)); self.add_menu_page.dish_saved.connect(self.on_dish_saved)
        self.add_expense_page = AddExpensePage(); self.stack.addWidget(self.add_expense_page)
        self.expense_view._on_add_requested = lambda: self.stack.setCurrentWidget(self.add_expense_page)
        self.add_expense_page.cancelled.connect(lambda: self.stack.setCurrentWidget(self.expense_view)); self.add_expense_page.expense_saved.connect(self.on_expense_saved)
        self.receipt_page = ReceiptPage(); self.stack.addWidget(self.receipt_page)
        self.invoices_view.view_receipt_requested.connect(self._show_receipt_page)
        self.receipt_page.close_receipt.connect(self._hide_receipt_page)
        
        # KẾT NỐI TRANG EDIT CUSTOMER
        self.edit_customer_page = EditCustomerPage(); self.stack.addWidget(self.edit_customer_page)
        self.customers_view.edit_requested.connect(self._open_edit_customer)
        self.edit_customer_page.cancelled.connect(lambda: self.stack.setCurrentWidget(self.customers_view))
        self.edit_customer_page.customer_saved.connect(self.on_customer_updated)

        # KẾT NỐI TRANG EDIT MENU
        self.edit_menu_page = EditMenuItemPage(); self.stack.addWidget(self.edit_menu_page)
        self.menu_view.edit_requested.connect(self._open_edit_menu)
        self.edit_menu_page.cancelled.connect(lambda: self.stack.setCurrentWidget(self.menu_view))
        self.edit_menu_page.menu_saved.connect(self.on_menu_updated)

        # KẾT NỐI TRANG EDIT EXPENSE
        self.edit_expense_page = EditExpensePage(); self.stack.addWidget(self.edit_expense_page)
        self.expense_view.edit_requested.connect(self._open_edit_expense)
        self.edit_expense_page.cancelled.connect(lambda: self.stack.setCurrentWidget(self.expense_view))
        self.edit_expense_page.expense_saved.connect(self.on_expense_updated)
        
        # Load dữ liệu Dashboard lần đầu
        self.refresh_dashboard_data()

    # THÊM HÀM MỚI CHO DASHBOARD XỬ LÝ EDIT EXPENSE
    def _open_edit_expense(self, eid, desc, cat, date, amount):
        self.edit_expense_page.load_data(eid, desc, cat, date, amount)
        self.stack.setCurrentWidget(self.edit_expense_page)

    def on_expense_updated(self):
        self.stack.setCurrentWidget(self.expense_view)
        self.expense_view.load_mock_data()
        ModernPopup("Success", "Expense Details Updated!", "fa5s.check-circle", self).exec_()
        self.refresh_dashboard_data() # Làm mới KPI trên Dashboard

    # THÊM HÀM MỚI CHO DASHBOARD XỬ LÝ EDIT MENU
    def _open_edit_menu(self, did, name, cat, price):
        self.edit_menu_page.load_data(did, name, cat, price)
        self.stack.setCurrentWidget(self.edit_menu_page)

    def on_menu_updated(self):
        self.stack.setCurrentWidget(self.menu_view)
        self.menu_view.load_mock_data()
        ModernPopup("Success", "Menu Item Updated!", "fa5s.check-circle", self).exec_()

    # THÊM HÀM MỚI CHO DASHBOARD XỬ LÝ EDIT CUSTOMER
    def _open_edit_customer(self, cid, name, phone, address):
        self.edit_customer_page.load_data(cid, name, phone, address)
        self.stack.setCurrentWidget(self.edit_customer_page)

    def on_customer_updated(self):
        self.stack.setCurrentWidget(self.customers_view)
        self.customers_view.load_mock_data()
        ModernPopup("Success", "Customer Details Updated!", "fa5s.check-circle", self).exec_()

    def refresh_dashboard_data(self):
        # 1. Cập nhật thẻ KPI
        stats = db_manager.get_dashboard_kpis()
        self.kpi_orders.update_value(stats['orders'])
        self.kpi_cust.update_value(stats['customers'])
        self.kpi_profit.update_value(stats['profit'])
        self.kpi_revenue.update_value(stats['revenue'])
        
        # 2. Cập nhật Biểu đồ
        self.c1.update_chart(self.c1.dropdown.currentText())
        self.c2.update_chart(self.c2.dropdown.currentText())
        self.c3.update_chart(self.c3.dropdown.currentText())
        
        # 3. Làm mới Best Dishes
        self.bd.setParent(None); self.bd = BestDishesCard(); self.best_dishes_lay.addWidget(self.bd)
        
        # 4. Cập nhật Bảng Recent Orders
        db_orders = db_manager.get_recent_orders_dash()
        self.table_dash.setRowCount(len(db_orders))
        bordeaux_num_font = QFont("'Inter Black', 'Segoe UI Variable Display', 'Segoe UI Black', sans-serif", 12, QFont.Bold)
        for row, data in enumerate(db_orders):
            inv_id_str = f"INV{data['InvoiceID']:03d}"
            item_id = QTableWidgetItem(inv_id_str); item_id.setTextAlignment(Qt.AlignCenter); item_id.setForeground(QColor("#4B5563")); self.table_dash.setItem(row, 0, item_id)
            item_name = QTableWidgetItem(data['CustomerName']); item_name.setTextAlignment(Qt.AlignCenter); self.table_dash.setItem(row, 1, item_name)
            item_tb = QTableWidgetItem(str(data['TableNumber'])); item_tb.setTextAlignment(Qt.AlignCenter); self.table_dash.setItem(row, 2, item_tb)
            d_val = data['PaymentDate']
            dt_str = d_val.strftime('%Y-%m-%d %H:%M') if hasattr(d_val, 'strftime') else str(d_val)
            item_dt = QTableWidgetItem(dt_str); item_dt.setTextAlignment(Qt.AlignCenter); self.table_dash.setItem(row, 3, item_dt)
            amt_str = f"{float(data['TotalAmount']):,.0f} VND"
            item_amt = QTableWidgetItem(amt_str); item_amt.setTextAlignment(Qt.AlignCenter); self.table_dash.setItem(row, 4, item_amt)
            self.table_dash.setCellWidget(row, 5, self.create_status_pill(data['Status']))
            
            subt = float(data['Subtotal'])
            svc = subt * 0.10
            disc = subt * 0.05 if subt > 3000000 else 0
            
            s_str = f"{subt:,.0f}"
            sv_str = f"{svc:,.0f}"
            ds_str = f"{disc:,.0f}"

            act_w = QWidget(); act_w.setStyleSheet("background-color: #FFFFFF;"); act_l = QHBoxLayout(act_w); act_l.setContentsMargins(0,0,0,0); act_l.setAlignment(Qt.AlignCenter)
            btn_view = QPushButton(qta.icon('fa5s.file-invoice', color='#9CA3AF'), ""); btn_view.setFixedSize(35, 35); btn_view.setCursor(QCursor(Qt.PointingHandCursor)); btn_view.setStyleSheet("QPushButton { background: transparent; border: none; } QPushButton:hover { color: #111827; }")
            btn_view.clicked.connect(lambda checked, i=inv_id_str, c=data['CustomerName'], p="N/A", t=str(data['TableNumber']), d=dt_str, s=s_str, sv=sv_str, ds=ds_str, a=amt_str: self._show_receipt_page(i, c, p, t, d, s, sv, ds, a))
            act_l.addWidget(btn_view); self.table_dash.setCellWidget(row, 6, act_w)

    def _show_receipt_page(self, inv_id, cust, ph, tab, dt, subt, svc, disc, tot):
        self.return_page = self.stack.currentWidget() 
        self.receipt_page.load_receipt(inv_id, cust, ph, tab, dt, subt, svc, disc, tot)
        self.stack.setCurrentWidget(self.receipt_page)

    def _hide_receipt_page(self):
        if hasattr(self, 'return_page') and self.return_page: self.stack.setCurrentWidget(self.return_page)
        else: self.stack.setCurrentWidget(self.invoices_view)

    def on_dish_saved(self):
        self.stack.setCurrentWidget(self.menu_view); self.menu_view.load_mock_data(); ModernPopup("Success", "Dish Added!", "fa5s.check-circle", self).exec_(); self.add_menu_page.reset()

    def on_expense_saved(self):
        self.stack.setCurrentWidget(self.expense_view); self.expense_view.load_mock_data(); ModernPopup("Success", "Expense Recorded!", "fa5s.check-circle", self).exec_(); self.add_expense_page.reset()

if __name__ == '__main__':
    app = QApplication(sys.argv); window = ManagerDashboard(); window.showFullScreen(); sys.exit(app.exec_())