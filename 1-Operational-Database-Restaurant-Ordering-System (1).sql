CREATE DATABASE restaurant;
USE restaurant;

-- 1. Users Table (Must be created first because orders reference it)
CREATE TABLE IF NOT EXISTS users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone_number VARCHAR(20),
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Categories Table
CREATE TABLE IF NOT EXISTS categories (
    category_id INT PRIMARY KEY AUTO_INCREMENT,
    category_name VARCHAR(100) NOT NULL,
    description TEXT
);

-- 3. Menu Items Table
CREATE TABLE IF NOT EXISTS menu_items (
    item_id INT PRIMARY KEY AUTO_INCREMENT,
    category_id INT,
    item_name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

-- 4. Orders Table
CREATE TABLE IF NOT EXISTS orders (
    order_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT,
    table_id INT NULL,
    staff_id INT NULL,
    order_type ENUM('Dine-In', 'Takeout', 'Delivery') NOT NULL,
    order_status ENUM('Pending', 'Confirmed', 'Preparing', 'Ready', 'Completed', 'Cancelled') DEFAULT 'Pending',
    total_amount DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES users(user_id)
);

-- 5. Order Items Table
CREATE TABLE IF NOT EXISTS order_items (
    order_item_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT,
    item_id INT,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,
    special_instructions TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES menu_items(item_id)
);

-- ==========================================
-- INSERT SAMPLE DATA
-- ==========================================

-- 6. Insert a mock user/customer
INSERT INTO users (first_name, last_name, email, password_hash) 
VALUES ('John', 'Doe', 'john.doe@example.com', 'hashed_pass_123');

-- 7. Insert a mock order created today
INSERT INTO orders (customer_id, order_type, order_status, total_amount, created_at) 
VALUES (1, 'Dine-In', 'Completed', 45.50, NOW());