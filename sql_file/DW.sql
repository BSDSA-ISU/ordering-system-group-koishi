CREATE DATABASE restaurant_dw;
USE restaurant_dw;

-- ==========================================
-- DIMENSION TABLES
-- ==========================================

-- 1. Date Dimension (Supports time-series reporting)
CREATE TABLE dim_date (
    date_key INT PRIMARY KEY, -- Format: YYYYMMDD
    full_date DATE NOT NULL,
    day_of_week VARCHAR(15) NOT NULL,
    day_number INT NOT NULL,
    month_number INT NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    quarter INT NOT NULL,
    year INT NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

-- 2. Customer Dimension with SCD Type 2
CREATE TABLE dim_customer (
    customer_key INT PRIMARY KEY AUTO_INCREMENT, -- Surrogate Key
    customer_id INT NOT NULL, -- Natural Key from OLTP
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    effective_start_date DATE NOT NULL,
    effective_end_date DATE NULL,
    is_current BOOLEAN DEFAULT TRUE
);

-- 3. Menu Item Dimension with SCD Type 2 (Tracks historical price changes)
CREATE TABLE dim_menu_item (
    item_key INT PRIMARY KEY AUTO_INCREMENT, -- Surrogate Key
    item_id INT NOT NULL, -- Natural Key from OLTP
    item_name VARCHAR(100) NOT NULL,
    category_name VARCHAR(100) NOT NULL,
    category_description TEXT,
    current_price DECIMAL(10, 2) NOT NULL,
    effective_start_date DATE NOT NULL,
    effective_end_date DATE NULL,
    is_current BOOLEAN DEFAULT TRUE
);

-- 4. Order Type Dimension
CREATE TABLE dim_order_type (
    order_type_key INT PRIMARY KEY AUTO_INCREMENT,
    order_type ENUM('Dine-In', 'Takeout', 'Delivery') NOT NULL,
    order_status VARCHAR(50) NOT NULL
);

-- ==========================================
-- FACT TABLE
-- ==========================================

-- 5. Order Items Fact Table (Grain: One row per item within an order)
CREATE TABLE fact_order_items (
    order_item_fact_id INT PRIMARY KEY AUTO_INCREMENT,
    date_key INT NOT NULL,
    customer_key INT NOT NULL,
    item_key INT NOT NULL,
    order_type_key INT NOT NULL,
    
    -- Degenerate Dimensions (IDs from source system for reference)
    order_id INT NOT NULL,
    order_item_id INT NOT NULL,
    
    -- Measures (Quantitative metrics)
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,
    
    -- Foreign Key Constraints linking to Dimensions
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key),
    FOREIGN KEY (customer_key) REFERENCES dim_customer(customer_key),
    FOREIGN KEY (item_key) REFERENCES dim_menu_item(item_key),
    FOREIGN KEY (order_type_key) REFERENCES dim_order_type(order_type_key)
);
