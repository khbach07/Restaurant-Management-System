-- =============================================================================
-- SECTION 1: DATABASE INITIALIZATION
-- =============================================================================

-- Temporarily disable checks to allow clean schema creation
SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- -----------------------------------------------------------------------------
-- Schema: restaurant_db
-- -----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS `restaurant_db` DEFAULT CHARACTER SET utf8;
USE `restaurant_db`;


-- =============================================================================
-- SECTION 2: TABLE DEFINITIONS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Table: MenuItems
-- Stores all dishes available on the restaurant menu.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `restaurant_db`.`MenuItems` (
  `DishID`    INT           NOT NULL AUTO_INCREMENT,
  `DishName`  VARCHAR(100)  NOT NULL,
  `Category`  VARCHAR(50)   NULL,
  `Price`     DECIMAL(10,2) NOT NULL,
  `ImageName` VARCHAR(255)  NULL DEFAULT 'default.jpg',
  PRIMARY KEY (`DishID`)
) ENGINE = InnoDB;


-- -----------------------------------------------------------------------------
-- Table: Customers
-- Stores customer profiles including contact information.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `restaurant_db`.`Customers` (
  `CustomerID`   INT          NOT NULL AUTO_INCREMENT,
  `CustomerName` VARCHAR(45)  NOT NULL,
  `PhoneNumber`  VARCHAR(255) NOT NULL,
  `Address`      VARCHAR(255) NULL,
  PRIMARY KEY (`CustomerID`)
) ENGINE = InnoDB;


-- -----------------------------------------------------------------------------
-- Table: DiningTables
-- Tracks physical tables and their current availability status.
-- Possible values for Status: 'Available', 'Occupied', 'Reserved'
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `restaurant_db`.`DiningTables` (
  `TableID`     INT         NOT NULL AUTO_INCREMENT,
  `TableNumber` VARCHAR(10) NOT NULL,
  `Status`      VARCHAR(45) NOT NULL DEFAULT 'Available',
  PRIMARY KEY (`TableID`)
) ENGINE = InnoDB;


-- -----------------------------------------------------------------------------
-- Table: Expenses
-- Records all operational expenses for financial reporting.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `restaurant_db`.`Expenses` (
  `ExpenseID`       INT           NOT NULL AUTO_INCREMENT,
  `ExpenseCategory` VARCHAR(50)   NOT NULL,
  `Description`     VARCHAR(255)  NULL,
  `Amount`          DECIMAL(10,2) NOT NULL,
  `ExpenseDate`     DATETIME      NOT NULL,
  PRIMARY KEY (`ExpenseID`)
) ENGINE = InnoDB;


-- -----------------------------------------------------------------------------
-- Table: Reservations
-- Links customers and tables for future bookings.
-- Inserting a row here automatically triggers a table status update (see Trigger 1).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `restaurant_db`.`Reservations` (
  `ReservationID` INT      NOT NULL AUTO_INCREMENT,
  `DateTime`      DATETIME NOT NULL,
  `GuestCount`    INT      NOT NULL,
  `CustomerID`    INT      NOT NULL,
  `TableID`       INT      NOT NULL,
  PRIMARY KEY (`ReservationID`),
  INDEX `fk_Reservations_Customers_idx` (`CustomerID` ASC) VISIBLE,
  INDEX `fk_Reservations_Tables1_idx`   (`TableID`    ASC) VISIBLE,
  CONSTRAINT `fk_Reservations_Customers`
    FOREIGN KEY (`CustomerID`)
    REFERENCES `restaurant_db`.`Customers` (`CustomerID`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_Reservations_Tables1`
    FOREIGN KEY (`TableID`)
    REFERENCES `restaurant_db`.`DiningTables` (`TableID`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION
) ENGINE = InnoDB;


-- -----------------------------------------------------------------------------
-- Table: Invoices
-- Represents a billing record per dining session.
-- TotalAmount is computed by the stored procedure GenerateBill().
-- A NULL PaymentDate indicates an unpaid invoice.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `restaurant_db`.`Invoices` (
  `InvoiceID`   INT           NOT NULL AUTO_INCREMENT,
  `TotalAmount` DECIMAL(10,2) NULL,
  `PaymentDate` DATETIME      NULL,
  `CustomerID`  INT           NOT NULL,
  `TableID`     INT           NOT NULL,
  PRIMARY KEY (`InvoiceID`),
  INDEX `fk_Invoices_Customers1_idx` (`CustomerID` ASC) VISIBLE,
  INDEX `fk_Invoices_Tables1_idx`    (`TableID`    ASC) VISIBLE,
  CONSTRAINT `fk_Invoices_Customers1`
    FOREIGN KEY (`CustomerID`)
    REFERENCES `restaurant_db`.`Customers` (`CustomerID`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_Invoices_Tables1`
    FOREIGN KEY (`TableID`)
    REFERENCES `restaurant_db`.`DiningTables` (`TableID`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION
) ENGINE = InnoDB;


-- -----------------------------------------------------------------------------
-- Table: OrderDetails
-- Line items for each invoice; records what was ordered and at what price.
-- UnitPrice is stored at time of order to preserve historical pricing.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `restaurant_db`.`OrderDetails` (
  `OrderDetailID` INT           NOT NULL AUTO_INCREMENT,
  `Quantity`      INT           NOT NULL,
  `UnitPrice`     DECIMAL(10,2) NOT NULL,
  `InvoiceID`     INT           NOT NULL,
  `DishID`        INT           NOT NULL,
  PRIMARY KEY (`OrderDetailID`),
  INDEX `fk_OrderDetails_Invoices1_idx`   (`InvoiceID` ASC) VISIBLE,
  INDEX `fk_OrderDetails_MenuItems1_idx`  (`DishID`    ASC) VISIBLE,
  CONSTRAINT `fk_OrderDetails_Invoices1`
    FOREIGN KEY (`InvoiceID`)
    REFERENCES `restaurant_db`.`Invoices` (`InvoiceID`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_OrderDetails_MenuItems1`
    FOREIGN KEY (`DishID`)
    REFERENCES `restaurant_db`.`MenuItems` (`DishID`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION
) ENGINE = InnoDB;


-- Restore original SQL mode settings
SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;


-- =============================================================================
-- SECTION 3: SAMPLE DATA
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Customers (10 rows)
-- -----------------------------------------------------------------------------
INSERT INTO Customers (CustomerName, PhoneNumber, Address) VALUES
('Alice Pham',      '0901234567', 'Hoan Kiem, Hanoi'),
('Bob Nguyen',      '0912345678', 'Ba Dinh, Hanoi'),
('Charlie Tran',    '0923456789', 'Cau Giay, Hanoi'),
('David Le',        '0934567890', 'Hai Ba Trung, Hanoi'),
('Son Tung',        '0945678901', 'Tay Ho, Hanoi'),
('Fiona Hoang',     '0956789012', 'Ba Dinh, Hanoi'),
('Mark Lee',        '0967890123', 'Thanh Xuan, Hanoi'),
('Gia Bao',         '0978901234', 'Nam Tu Liem, Hanoi'),
('Ian Dinh',        '0989012345', 'Long Bien, Hanoi'),
('Fujinaga Sakuya', '0990123456', 'Hoang Mai, Hanoi');

-- -----------------------------------------------------------------------------
-- 2. DiningTables (10 rows)
-- -----------------------------------------------------------------------------
INSERT INTO DiningTables (TableNumber, Status) VALUES
('T01',  'Available'),
('T02',  'Occupied'),
('T03',  'Reserved'),
('T04',  'Available'),
('T05',  'Occupied'),
('T06',  'Reserved'),
('T07',  'Available'),
('T08',  'Occupied'),
('T09',  'Reserved'),
('T10', 'Available');

-- -----------------------------------------------------------------------------
-- 3. MenuItems (10 rows)
-- -----------------------------------------------------------------------------
INSERT INTO MenuItems (DishName, Category, Price, ImageName) VALUES
('Wagyu Ribeye Steak',     'Main Course', 1500000.00, 'wagyu.jpg'),
('Lobster Bisque',         'Appetizer',    450000.00, 'lobster.jpg'),
('Truffle Pasta',          'Main Course',  650000.00, 'truffle.jpg'),
('Basque Burnt Cheesecake','Dessert',      250000.00, 'cheesecake.jpg'),
('Bordeaux Red Wine',      'Beverage',    1200000.00, 'wine.jpg'),
('Pan-Seared Foie Gras',   'Appetizer',    850000.00, 'foie_gras.jpg'),
('Beef Wellington',        'Main Course', 1800000.00, 'wellington.jpg'),
('Grilled Salmon',         'Main Course',  180000.00, 'salmon.jpg'),
('Classic Tiramisu',       'Dessert',      150000.00, 'tiramisu.jpg'),
('Sparkling Water',        'Beverage',     100000.00, 'water.jpg');

-- -----------------------------------------------------------------------------
-- 4. Expenses (10 rows)
-- -----------------------------------------------------------------------------
INSERT INTO Expenses (ExpenseCategory, Description, Amount, ExpenseDate) VALUES
('Ingredients', 'Purchase 2kg Wagyu Beef',              1000000.00, '2026-04-01 00:00:00'),
('Utilities',   'Electricity bill March',                  1000000.00, '2026-04-05 00:00:00'),
('Ingredients',     'Restock Sparking Water',                      500000.00, '2026-04-10 00:00:00'),
('Marketing',   'Social media ads',                        300000.00, '2026-04-12 00:00:00'),
('Maintenance', 'Kitchen equipment repair',                3500000.00, '2026-04-15 00:00:00'),
('Ingredients', 'Premium cream cheese & baking supplies',  1500000.00, '2026-04-09 00:00:00'),
('Ingredients', 'Imported Red Wine restock',              1000000.00, '2026-04-10 00:00:00'),
('Payroll',     'Manager Wages',               7000000.00, '2026-04-18 00:00:00'),
('Utilities',   'Water bill March',                        1200000.00, '2026-04-19 00:00:00'),
('Supplies',    'Dining napkins & candles',                 300000.00, '2026-04-20 00:00:00');

-- -----------------------------------------------------------------------------
-- 5. Reservations (10 rows)
-- -----------------------------------------------------------------------------
INSERT INTO Reservations (DateTime, GuestCount, CustomerID, TableID) VALUES
('2026-04-18 19:00:00', 2,  1,  3),
('2026-04-18 22:00:00', 4,  2,  1),
('2026-04-19 18:30:00', 2,  3,  2),
('2026-04-20 19:30:00', 6,  4,  4),
('2026-04-21 20:00:00', 3,  5,  5),
('2026-04-22 18:00:00', 2,  6,  6),
('2026-04-22 19:00:00', 4,  7,  7),
('2026-04-23 20:30:00', 2,  8,  8),
('2026-04-24 19:30:00', 5,  9,  9),
('2026-04-25 18:30:00', 2, 10, 10);

-- -----------------------------------------------------------------------------
-- 6. Invoices (10 rows)
-- NULL PaymentDate = invoice not yet settled
-- -----------------------------------------------------------------------------
INSERT INTO Invoices (TotalAmount, PaymentDate, CustomerID, TableID) VALUES
(4567500.00, '2026-04-12 19:30:00',  1,  3),
(3990000.00, '2026-04-15 18:45:00',  2,  1),
(1650000.00, NULL,                   3,  2),
( 550000.00, '2026-04-16 19:00:00',  4,  4),
(2970000.00, '2026-04-17 21:00:00',  5,  5),
(2145000.00, '2026-04-18 18:30:00',  6,  6),
(2420000.00, '2026-04-18 20:45:00',  7,  7),
( 396000.00, NULL,                   8,  8),
( 660000.00, '2026-04-19 21:30:00',  9,  9),
( 605000.00, '2026-04-20 20:00:00', 10, 10);

-- -----------------------------------------------------------------------------
-- 7. OrderDetails (20 rows)
-- -----------------------------------------------------------------------------
INSERT INTO OrderDetails (Quantity, UnitPrice, InvoiceID, DishID) VALUES
(1, 1500000.00,  1,  1),
(2, 1200000.00,  1,  5),
(1,  450000.00,  1,  2),
(2, 1800000.00,  2,  7),
(2,  100000.00,  2, 10),
(1,  650000.00,  3,  3),
(1,  850000.00,  3,  6),
(2,  250000.00,  4,  4),
(1, 1500000.00,  5,  1),
(1, 1200000.00,  5,  5),
(1,  650000.00,  6,  3),
(1,  450000.00,  6,  2),
(1,  850000.00,  6,  6),
(1, 1800000.00,  7,  7),
(2,  150000.00,  7,  9),
(1,  100000.00,  7, 10),
(2,  180000.00,  8,  8),
(4,  150000.00,  9,  9),
(1,  250000.00, 10,  4),
(3,  100000.00, 10, 10);


-- =============================================================================
-- SECTION 4: INDEXES
-- =============================================================================

-- Speeds up menu searches by dish name
CREATE INDEX idx_dish_name       ON MenuItems(DishName);

-- Speeds up reservation queries filtered by date
CREATE INDEX idx_reservation_date ON Reservations(DateTime);

-- Speeds up customer lookup by phone number (frequent staff operation)
CREATE INDEX idx_customer_phone  ON Customers(PhoneNumber);

-- Speeds up customer profile search by name
CREATE INDEX idx_customer_name   ON Customers(CustomerName);

-- Speeds up invoice queries filtered by payment date
CREATE INDEX idx_payment_date    ON Invoices(PaymentDate);


-- =============================================================================
-- SECTION 5: VIEWS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- View: View_AvailableTables
-- Returns tables that are currently free to seat guests.
-- -----------------------------------------------------------------------------
CREATE VIEW View_AvailableTables AS
SELECT TableID, TableNumber
FROM DiningTables
WHERE Status = 'Available';


-- -----------------------------------------------------------------------------
-- View: View_DailyBookings
-- Aggregates total reservations and guest headcount per day.
-- -----------------------------------------------------------------------------
CREATE VIEW View_DailyBookings AS
SELECT
    DATE(DateTime)        AS BookingDate,
    COUNT(ReservationID)  AS TotalReservations,
    SUM(GuestCount)       AS TotalGuests
FROM Reservations
GROUP BY DATE(DateTime)
ORDER BY BookingDate;


-- -----------------------------------------------------------------------------
-- View: View_TopSellingDishes
-- Ranks dishes by total units sold across all invoices.
-- -----------------------------------------------------------------------------
CREATE VIEW View_TopSellingDishes AS
SELECT
    m.DishName,
    m.Category,
    SUM(od.Quantity) AS TotalSold
FROM MenuItems m
JOIN OrderDetails od ON m.DishID = od.DishID
GROUP BY m.DishID
ORDER BY TotalSold DESC;


-- =============================================================================
-- SECTION 6: STORED PROCEDURES & USER-DEFINED FUNCTION
-- =============================================================================
DELIMITER //

-- -----------------------------------------------------------------------------
-- Function: ComputeFinalAmount
-- Calculates the final amount payable after applying:
--   - 10% service charge on all orders
--   - 5% discount for orders exceeding 3,000,000 VND
-- -----------------------------------------------------------------------------
CREATE FUNCTION ComputeFinalAmount(p_BaseAmount DECIMAL(10,2))
RETURNS DECIMAL(10,2)
DETERMINISTIC
BEGIN
    DECLARE v_ServiceCharge DECIMAL(10,2);
    DECLARE v_Discount      DECIMAL(10,2) DEFAULT 0.00;

    -- Rule 1: Apply a 10% service charge
    SET v_ServiceCharge = p_BaseAmount * 0.10;

    -- Rule 2: Apply a 5% discount if the base amount exceeds 3,000,000 VND
    IF p_BaseAmount > 3000000 THEN
        SET v_Discount = p_BaseAmount * 0.05;
    END IF;

    RETURN (p_BaseAmount + v_ServiceCharge - v_Discount);
END //


-- -----------------------------------------------------------------------------
-- Procedure: ConfirmReservation
-- Inserts a new reservation record for the given customer and table.
-- Note: Table status is updated automatically by Trigger After_Reservation_Insert.
-- -----------------------------------------------------------------------------
CREATE PROCEDURE ConfirmReservation(
    IN p_CustomerID INT,
    IN p_TableID    INT,
    IN p_DateTime   DATETIME,
    IN p_GuestCount INT
)
BEGIN
    INSERT INTO Reservations (DateTime, GuestCount, CustomerID, TableID)
    VALUES (p_DateTime, p_GuestCount, p_CustomerID, p_TableID);
END //


-- -----------------------------------------------------------------------------
-- Procedure: GenerateBill
-- Computes and writes the final invoice total for a given InvoiceID.
-- Steps:
--   1. Sum all line items from OrderDetails.
--   2. Pass the subtotal through ComputeFinalAmount() for charges/discounts.
--   3. Update the TotalAmount field in the Invoices table.
-- -----------------------------------------------------------------------------
CREATE PROCEDURE GenerateBill(IN p_InvoiceID INT)
BEGIN
    DECLARE v_BaseTotal  DECIMAL(10,2);
    DECLARE v_FinalTotal DECIMAL(10,2);

    -- Step 1: Calculate the subtotal from all order line items
    SELECT SUM(Quantity * UnitPrice) INTO v_BaseTotal
    FROM OrderDetails
    WHERE InvoiceID = p_InvoiceID;

    -- Step 2: Apply service charge and discount
    SET v_FinalTotal = ComputeFinalAmount(v_BaseTotal);

    -- Step 3: Persist the final amount to the invoice record
    UPDATE Invoices
    SET TotalAmount = v_FinalTotal
    WHERE InvoiceID = p_InvoiceID;
END //


-- =============================================================================
-- SECTION 7: TRIGGERS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Trigger: After_Reservation_Insert
-- Automatically marks a table as 'Reserved' when a new reservation is created.
-- -----------------------------------------------------------------------------
CREATE TRIGGER After_Reservation_Insert
AFTER INSERT ON Reservations
FOR EACH ROW
BEGIN
    UPDATE DiningTables
    SET Status = 'Reserved'
    WHERE TableID = NEW.TableID;
END //


-- -----------------------------------------------------------------------------
-- Trigger: After_Invoice_Payment
-- Automatically marks a table as 'Available' once an invoice is paid.
-- Condition: PaymentDate transitions from NULL to a valid timestamp.
-- -----------------------------------------------------------------------------
CREATE TRIGGER After_Invoice_Payment
AFTER UPDATE ON Invoices
FOR EACH ROW
BEGIN
    IF OLD.PaymentDate IS NULL AND NEW.PaymentDate IS NOT NULL THEN
        UPDATE DiningTables
        SET Status = 'Available'
        WHERE TableID = NEW.TableID;
    END IF;
END //

DELIMITER ;


-- =============================================================================
-- SECTION 8: ROLES & PRIVILEGES
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Step 1: Clean up existing roles and users to prevent "Already Exists" errors
-- -----------------------------------------------------------------------------
DROP ROLE IF EXISTS 'admin_role', 'cashier_role', 'waiter_role';
DROP USER IF EXISTS 'john_admin'@'localhost';
DROP USER IF EXISTS 'mary_cashier'@'localhost';
DROP USER IF EXISTS 'peter_waiter'@'localhost';

-- Flush privilege cache before recreating
FLUSH PRIVILEGES;

-- -----------------------------------------------------------------------------
-- Step 2: Create roles
-- -----------------------------------------------------------------------------
CREATE ROLE 'admin_role', 'cashier_role', 'waiter_role';

-- -----------------------------------------------------------------------------
-- Step 3: Create users and assign roles
-- -----------------------------------------------------------------------------

-- Admin: full access to the database
CREATE USER 'john_admin'@'localhost' IDENTIFIED BY 'StrongPass123!';
GRANT 'admin_role' TO 'john_admin'@'localhost';
SET DEFAULT ROLE 'admin_role' TO 'john_admin'@'localhost';

-- Cashier: manage billing and order records
CREATE USER 'mary_cashier'@'localhost' IDENTIFIED BY 'CashierPass!22';
GRANT 'cashier_role' TO 'mary_cashier'@'localhost';
SET DEFAULT ROLE 'cashier_role' TO 'mary_cashier'@'localhost';

-- Waiter: manage table orders and customer interactions
CREATE USER 'peter_waiter'@'localhost' IDENTIFIED BY 'WaiterPass!33';
GRANT 'waiter_role' TO 'peter_waiter'@'localhost';
SET DEFAULT ROLE 'waiter_role' TO 'peter_waiter'@'localhost';

-- -----------------------------------------------------------------------------
-- Step 4: Grant REPLICATION CLIENT to allow server status monitoring (avoids error 1227)
-- -----------------------------------------------------------------------------
GRANT REPLICATION CLIENT ON *.* TO 'peter_waiter'@'localhost';
GRANT REPLICATION CLIENT ON *.* TO 'mary_cashier'@'localhost';
GRANT REPLICATION CLIENT ON *.* TO 'john_admin'@'localhost';

-- -----------------------------------------------------------------------------
-- Step 5: Assign permissions per role
-- -----------------------------------------------------------------------------

-- Waiter: read and write access
GRANT SELECT, INSERT, UPDATE, DELETE ON restaurant_db.* TO 'waiter_role';

-- Cashier: full data manipulation access (no DDL)
GRANT SELECT, INSERT, UPDATE, DELETE ON restaurant_db.* TO 'cashier_role';

-- Admin: unrestricted access to the database
GRANT ALL PRIVILEGES ON restaurant_db.* TO 'admin_role';

-- Apply all privilege changes
FLUSH PRIVILEGES;


-- =============================================================================
-- SECTION 9: SECURITY MECHANISMS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- [1] Data Encryption: AES-256 encryption for customer phone numbers
-- Ensures PII remains unreadable even if the database is compromised.
-- Idempotency guard: AES_ENCRYPT on a 10-digit phone number always produces
-- exactly 32 HEX characters. The REGEXP check matches this exact length,
-- so re-running this statement will safely skip already-encrypted values.
-- -----------------------------------------------------------------------------
UPDATE Customers
SET PhoneNumber = HEX(AES_ENCRYPT(PhoneNumber, 'RestaurantSecretKey2026'))
WHERE CustomerID > 0
  AND PhoneNumber NOT REGEXP '^[0-9A-F]{32}$';

-- -----------------------------------------------------------------------------
-- [2] Secure Data Masking: General view for UI display
-- Purpose: Decrypts phone numbers on the fly and masks sensitive digits.
-- This view is used across various UI components (Reservation Info, Customer Tab) 
-- to prevent "shoulder-surfing" and limit PII exposure for non-admin operations.
-- -----------------------------------------------------------------------------
CREATE VIEW View_MaskedCustomerInfo AS
SELECT
    CustomerName,
    CONCAT(
        LEFT (CAST(AES_DECRYPT(UNHEX(PhoneNumber), 'RestaurantSecretKey2026') AS CHAR), 3),
        '****',
        RIGHT(CAST(AES_DECRYPT(UNHEX(PhoneNumber), 'RestaurantSecretKey2026') AS CHAR), 3)
    ) AS MaskedPhone
FROM Customers;