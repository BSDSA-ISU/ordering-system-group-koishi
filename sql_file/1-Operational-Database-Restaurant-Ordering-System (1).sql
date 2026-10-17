CREATE DATABASE IF NOT EXISTS restaurant_db;
USE restaurant_db;

-- Drop tables in reverse order of dependencies to allow clean re-runs
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS order_details;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS menu_items;
DROP TABLE IF EXISTS staff;
DROP TABLE IF EXISTS customers;

-- 1. Customers Table
CREATE TABLE customers (
    customer_id INT PRIMARY KEY AUTO_INCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone_number VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Staff Table (Operational role tracking)
CREATE TABLE staff (
    staff_id INT PRIMARY KEY AUTO_INCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    role ENUM('Cashier', 'Waiter', 'Chef', 'Manager') NOT NULL,
    hire_date DATE NOT NULL
);

-- 3. MenuItems Table
CREATE TABLE menu_items (
    item_id INT PRIMARY KEY AUTO_INCREMENT,
    item_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock_level INT DEFAULT 50,
    is_available BOOLEAN DEFAULT TRUE
);

-- 4. Orders Table (Linked to Customer and Staff)
CREATE TABLE orders (
    order_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT,
    staff_id INT,
    order_status ENUM('Pending', 'Preparing', 'Ready', 'Completed', 'Cancelled') DEFAULT 'Pending',
    total_amount DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE SET NULL,
    FOREIGN KEY (staff_id) REFERENCES staff(staff_id) ON DELETE SET NULL
);

-- 5. OrderDetails Table (Bridge table for Many-to-Many relationship)
CREATE TABLE order_details (
    order_detail_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    item_id INT NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    subtotal DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES menu_items(item_id)
);

-- 6. Payments Table
CREATE TABLE payments (
    payment_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT UNIQUE NOT NULL,
    amount_paid DECIMAL(10, 2) NOT NULL,
    payment_method ENUM('Cash', 'Credit Card', 'Mobile Wallet') NOT NULL,
    payment_status ENUM('Pending', 'Paid', 'Failed', 'Refunded') DEFAULT 'Pending',
    paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
);

---------------------------------------------------------
-- SAMPLE DATA INSERTION (Exceeds 30 Total Records)
---------------------------------------------------------

-- Customers (8 records)
INSERT INTO customers (first_name, last_name, email, phone_number) VALUES
('Alice', 'Smith', 'alice.smith@example.com', '555-0101'),
('Bob', 'Jones', 'bob.jones@example.com', '555-0102'),
('Charlie', 'Brown', 'charlie.brown@example.com', '555-0103'),
('Diana', 'Prince', 'diana.prince@example.com', '555-0104'),
('Evan', 'Wright', 'evan.wright@example.com', '555-0105'),
('Fiona', 'Gallagher', 'fiona.g@example.com', '555-0106'),
('George', 'Costanza', 'george.c@example.com', '555-0107'),
('Hannah', 'Abbott', 'hannah.a@example.com', '555-0108');

-- Staff (5 records)
INSERT INTO staff (first_name, last_name, role, hire_date) VALUES
('John', 'Doe', 'Manager', '2022-01-15'),
('Jane', 'Smith', 'Cashier', '2023-03-10'),
('Gordon', 'Ramsay', 'Chef', '2021-06-01'),
('Emily', 'Blunt', 'Waiter', '2023-08-20'),
('Michael', 'Scott', 'Waiter', '2024-01-10');

-- Menu Items (8 records)
INSERT INTO menu_items (item_name, category, price, stock_level) VALUES
('Cheeseburger', 'Main Course', 12.99, 40),
('Pepperoni Pizza', 'Main Course', 15.50, 25),
('Caesar Salad', 'Appetizer', 8.50, 30),
('Garlic Bread', 'Appetizer', 5.00, 50),
('Chocolate Lava Cake', 'Dessert', 7.00, 20),
('Iced Tea', 'Beverage', 3.00, 100),
('Craft Soda', 'Beverage', 4.00, 80),
('Ribeye Steak', 'Main Course', 28.99, 15);

-- Orders (5 records)
INSERT INTO orders (customer_id, staff_id, order_status, total_amount) VALUES
(1, 4, 'Completed', 24.49),
(2, 5, 'Completed', 19.50),
(3, 4, 'Preparing', 35.99),
(4, 5, 'Pending', 12.99),
(5, 4, 'Completed', 33.00);

-- Order Details (8 records)
INSERT INTO order_details (order_id, item_id, quantity, subtotal) VALUES
(1, 1, 1, 12.99),
(1, 3, 1, 8.50),
(1, 6, 1, 3.00),
(2, 2, 1, 15.50),
(2, 4, 1, 4.00),
(3, 8, 1, 28.99),
(3, 5, 1, 7.00),
(4, 1, 1, 12.99);

-- Payments (4 records)
INSERT INTO payments (order_id, amount_paid, payment_method, payment_status) VALUES
(1, 24.49, 'Credit Card', 'Paid'),
(2, 19.50, 'Cash', 'Paid'),
(3, 35.99, 'Mobile Wallet', 'Paid'),
(5, 33.00, 'Credit Card', 'Paid');

START TRANSACTION;

-- 1. Insert a new order for Customer ID #6 (Fiona Gallagher)
INSERT INTO orders (customer_id, staff_id, order_status, total_amount) 
VALUES (6, 5, 'Pending', 20.49);

-- Get the generated order ID (suppose it returns order_id = 6)
SET @new_order_id = LAST_INSERT_ID();

-- 2. Add line items to order details (e.g., Pepperoni Pizza + Craft Soda)
INSERT INTO order_details (order_id, item_id, quantity, subtotal) 
VALUES 
(@new_order_id, 2, 1, 15.50),
(@new_order_id, 7, 1, 4.99);

-- 3. Automatically adjust stock levels in menu items
UPDATE menu_items SET stock_level = stock_level - 1 WHERE item_id = 2;
UPDATE menu_items SET stock_level = stock_level - 1 WHERE item_id = 7;

-- 4. Process payment for the order
INSERT INTO payments (order_id, amount_paid, payment_method, payment_status) 
VALUES (@new_order_id, 20.49, 'Mobile Wallet', 'Paid');

-- 5. Update order status to completed
UPDATE orders SET order_status = 'Completed' WHERE order_id = @new_order_id;

ALTER TABLE staff MODIFY COLUMN role ENUM('Cashier', 'Waiter', 'Chef', 'Manager', 'Owner');

COMMIT;