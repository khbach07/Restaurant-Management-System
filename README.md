# 🍽️ Maison des Rêves - Luxury Restaurant Management System

A comprehensive, modern desktop application designed to streamline operations for a fine-dining restaurant. Built with **Python (PyQt5)** and powered by a robust **MySQL** database, this system features role-based access control, interactive POS dashboards, advanced financial analytics, and robust data security.

## ✨ Key Features

### 🔐 Role-Based Access Control (RBAC) & Security
* **Multi-Tiered Logins**: Secure access mapped directly to MySQL database users (`Admin`, `Cashier`, `Waiter`).
* **AES-256 Encryption**: Customer phone numbers are heavily encrypted at the database level to protect PII (Personally Identifiable Information).
* **Secure Data Masking**: General UI components display masked customer data (e.g., `090****567`) via the `View_MaskedCustomerInfo` SQL view to prevent shoulder-surfing while preserving usability.

### 🖥️ Staff POS Dashboard (Cashiers & Waiters)
* **Real-Time Floor Plan**: Visual representation of dining tables with color-coded statuses (Available, Occupied, Reserved).
* **Smart Reservation System**: Auto-fill customer details by phone number, calendar integration, and immediate table status updates via SQL triggers.
* **Intuitive Ordering Interface**: Visual menu cards with quantity toggles, categorized filtering, and automatic cart calculations (including a 10% service charge and dynamic 5% discounts for large orders).
* **Smart Search**: Find active reservations quickly using a floating, responsive dropdown search bar.

### 📊 Manager Analytics Dashboard (Admins)
* **Real-Time KPIs**: Track total orders, customer count, revenue, and profit.
* **Interactive Matplotlib Charts**: 
  * Smooth Line Charts (Revenue vs. Expenses).
  * Heatmaps (Peak reservation times).
  * Bar Charts (Orders overview).
* **CRUD Management Operations**: Full control over Menu Items, Operating Expenses, Customer Data, and Invoices.
* **CSV Export**: Export customer and invoice reports directly to your local drive.

### 💾 Data Management
* **Automated Database Backup**: Dedicated Python script to securely generate timestamped MySQL dumps utilizing environment variables.

---

## 🛠️ Technology Stack

* **Frontend GUI**: Python 3.x, PyQt5, QtAwesome (for scalable icons)
* **Data Visualization**: Matplotlib, SciPy (for smooth spline interpolation)
* **Database**: MySQL 8.0+
* **Database Driver**: PyMySQL
* **Environment Management**: `python-dotenv`

---

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone [https://github.com/khbach07/Restaurant-Management-System.git](https://github.com/khbach07/Restaurant-Management-System.git)
cd Restaurant-Management-System
```

### 2. Install Dependencies
Make sure you have Python installed. Install the required libraries using the provided `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 3. Database Configuration
1. Open your MySQL client (e.g., MySQL Workbench, DBeaver).
2. Execute the provided `schema.sql` file. This script will automatically:
   * Create the `restaurant_db` schema.
   * Build all necessary tables, views, stored procedures, and triggers.
   * Insert mock data for testing.
   * Create the database users and assign privileges.
   * Apply AES-256 encryption to the mock customer data.

### 4. Environment Variables
Create a `.env` file in the root directory of the project to securely manage database credentials without hardcoding them:
```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_root_password
DB_NAME=restaurant_db
```

---

## 🔑 Test Accounts

The `schema.sql` script creates three default accounts for testing. Use these on the login screen:

| Role | Username | Password |
| :--- | :--- | :--- |
| **Manager / Admin** | `john_admin` | `StrongPass123!` |
| **Cashier** | `mary_cashier` | `CashierPass!22` |
| **Waiter** | `peter_waiter` | `WaiterPass!33` |

---

## 📂 Project Structure

* `gui_login.py`: The entry point. Handles authentication, floating UI, and routes users to their respective dashboards based on MySQL roles.
* `gui_dashboard.py`: The main POS application for Waiters and Cashiers (Table maps, Orders, Reservations).
* `gui_manager.py`: The administrative panel featuring KPI metrics, charts, and CRUD capabilities.
* `backup.py`: Automated script for generating timestamped SQL database dumps.
* `schema.sql`: Complete database architecture including tables, constraints, triggers, and stored procedures.
* `requirements.txt`: Python package dependencies.
* `menu_images/`: Directory storing local images for the menu items.

---

## ⚙️ Advanced Database Architecture Highlight

This project heavily leverages backend SQL capabilities rather than relying solely on Python logic:
* **`ComputeFinalAmount()`**: A deterministic SQL function that handles dynamic pricing logic (Tax and Discounts).
* **`GenerateBill()`**: A Stored Procedure that calculates subtotals from `OrderDetails` and calls the pricing function to finalize an `Invoice`.
* **Triggers**: Automate table statuses (`After_Reservation_Insert` changes a table to *Reserved*; `After_Invoice_Payment` frees the table).

---

## 🖥️ Usage

To start the application, run the login portal from your terminal:

```bash
python gui_login.py
```

### Navigating the System
Once the login screen appears, you can explore different facets of the application depending on the role you use:

1. **Manager/Admin View**: Log in with `john_admin` to access the Analytics Dashboard, view financial charts, and manage CRUD operations for Menu, Customers, and Expenses.
2. **Staff POS View**: Log in with `peter_waiter` or `mary_cashier` to access the interactive Floor Plan, process customer orders, and manage table reservations.

*💡 Tip: Press `ESC` at any time while on the login or dashboard screens to safely exit the POS system.*

---

## 🔄 Backup & Recovery

### Automated Backup
Generate a secure, timestamped backup of your MySQL database. The script reads credentials directly from your `.env` file.
```bash
python backup.py
```
*Backups are saved by default to `C:/Restaurant_Backups/`.*

### Recovery Procedure
To restore the database from a backup file in case of system failure, open your Command Prompt (CMD) and run:
```cmd
mysql -u root -p restaurant_db < C:\Restaurant_Backups\restaurant_db_YYYYMMDD.sql
```
*(Note: Ensure the `restaurant_db` database exists before running the restore command. If the database was entirely dropped, log into MySQL and run `CREATE DATABASE restaurant_db;` first).*