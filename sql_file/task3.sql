-- ==========================================================
-- ROLE 3: DATA WAREHOUSE & SCD TYPE 2 IMPLEMENTATION
-- Target: MySQL 8.x / MariaDB
-- ==========================================================

CREATE DATABASE IF NOT EXISTS restaurant_dw;
USE restaurant_dw;

-- Clean up existing DW tables if re-running script
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_menu_item;
DROP TABLE IF EXISTS dim_time;

-- ==========================================================
-- TASKS 5 & 6: STAR SCHEMA DESIGN
-- ==========================================================

-- 1. Dimension Table: dim_time
-- Grain: One row per unique calendar date
CREATE TABLE dim_time (
    time_key INT PRIMARY KEY AUTO_INCREMENT,
    date_val DATE UNIQUE NOT NULL,
    day_of_week VARCHAR(10) NOT NULL,
    month_name VARCHAR(15) NOT NULL,
    quarter INT NOT NULL,
    year INT NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

-- 2. Dimension Table: dim_customer (SCD Type 1 or static profile view)
-- Grain: One row per customer
CREATE TABLE dim_customer (
    customer_key INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL, -- Natural key from operational DB
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL
);

-- 3. Dimension Table: dim_menu_item (SCD Type 2 Implementation)
-- Grain: One row per version of a menu item (tracks historical price/category shifts)
CREATE TABLE dim_menu_item (
    item_key INT PRIMARY KEY AUTO_INCREMENT,
    item_id INT NOT NULL,          -- Natural key from operational DB
    item_name VARCHAR(100) NOT NULL,
    category_name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    -- SCD Type 2 Tracking Columns
    effective_start_date DATETIME NOT NULL,
    effective_end_date DATETIME NULL,
    is_current BOOLEAN NOT NULL DEFAULT TRUE
);

-- 4. Fact Table: fact_sales
-- Business Process: Capturing completed restaurant order line items
-- Grain: One row per order item within an order
CREATE TABLE fact_sales (
    sale_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,         -- Operational order reference
    customer_key INT NOT NULL,     -- Foreign key to dim_customer
    item_key INT NOT NULL,         -- Foreign key to dim_menu_item (captures item version at time of sale)
    time_key INT NOT NULL,         -- Foreign key to dim_time
    quantity INT NOT NULL,         -- Numerical Measure
    unit_price DECIMAL(10,2) NOT NULL, -- Numerical Measure
    subtotal DECIMAL(10,2) NOT NULL,   -- Numerical Measure
    FOREIGN KEY (customer_key) REFERENCES dim_customer(customer_key),
    FOREIGN KEY (item_key) REFERENCES dim_menu_item(item_key),
    FOREIGN KEY (time_key) REFERENCES dim_time(time_key)
);

-- ==========================================================
-- ETL: POPULATING THE DATA WAREHOUSE FROM 'restaurant' DB
-- ==========================================================

-- Populate dim_time from operational orders
INSERT IGNORE INTO dim_time (date_val, day_of_week, month_name, quarter, year, is_weekend)
SELECT DISTINCT
    DATE(created_at) AS date_val,
    DAYNAME(created_at) AS day_of_week,
    MONTHNAME(created_at) AS month_name,
    QUARTER(created_at) AS quarter,
    YEAR(created_at) AS year,
    CASE WHEN DAYOFWEEK(created_at) IN (1, 7) THEN TRUE ELSE FALSE END AS is_weekend
FROM restaurant.orders;

-- Populate dim_customer
INSERT INTO dim_customer (customer_id, first_name, last_name, email)
SELECT user_id, first_name, last_name, email
FROM restaurant.users;

-- Populate dim_menu_item (Initial Load as Current Versions - SCD Type 2 Base)
INSERT INTO dim_menu_item (item_id, item_name, category_name, price, effective_start_date, effective_end_date, is_current)
SELECT 
    m.item_id,
    m.item_name,
    c.category_name,
    m.price,
    NOW() - INTERVAL 1 YEAR AS effective_start_date, -- Baseline historical start
    NULL AS effective_end_date,
    TRUE AS is_current
FROM restaurant.menu_items m
JOIN restaurant.categories c ON m.category_id = c.category_id;

-- Populate fact_sales for completed orders
INSERT INTO fact_sales (order_id, customer_key, item_key, time_key, quantity, unit_price, subtotal)
SELECT 
    o.order_id,
    dc.customer_key,
    dmi.item_key,
    dt.time_key,
    oi.quantity,
    oi.unit_price,
    oi.subtotal
FROM restaurant.orders o
JOIN restaurant.order_items oi ON o.order_id = oi.order_id
JOIN restaurant.users u ON o.customer_id = u.user_id
JOIN dim_customer dc ON dc.customer_id = u.user_id
JOIN dim_menu_item dmi ON dmi.item_id = oi.item_id AND dmi.is_current = TRUE
JOIN dim_time dt ON dt.date_val = DATE(o.created_at)
WHERE o.order_status = 'Completed';


-- ==========================================================
-- TASK 7: SLOWLY CHANGING DIMENSION (SCD) TYPE 2 DEMONSTRATION
-- Tracking historical price updates for a menu item (e.g., Ribeye Steak price hike)
-- ==========================================================

-- Step 7.1: View current active version of a specific item before change
SELECT * FROM dim_menu_item WHERE item_name = 'Ribeye Steak' AND is_current = TRUE;

-- Step 7.2: Simulate SCD Type 2 Update Transaction
-- Scenario: The price of 'Ribeye Steak' increases from 28.00 to 32.50.
-- We must:
-- 1. Close out the old record (Set effective_end_date and is_current = FALSE)
-- 2. Insert a brand new record with the updated price, new start date, and is_current = TRUE

START TRANSACTION;

-- A. Expire the current active record
UPDATE dim_menu_item
SET effective_end_date = CURRENT_TIMESTAMP,
    is_current = FALSE
WHERE item_name = 'Ribeye Steak' 
  AND is_current = TRUE;

-- B. Insert the new version with the updated price
INSERT INTO dim_menu_item (item_id, item_name, category_name, price, effective_start_date, effective_end_date, is_current)
SELECT 
    item_id,
    item_name,
    category_name,
    32.50 AS price, -- New updated price
    CURRENT_TIMESTAMP AS effective_start_date,
    NULL AS effective_end_date,
    TRUE AS is_current
FROM dim_menu_item
WHERE item_name = 'Ribeye Steak' 
  AND effective_end_date = CURRENT_TIMESTAMP; -- Pulls metadata from the record we just closed

COMMIT;

-- ==========================================================
-- STEP 7.3: VERIFY SCD VERSIONING RESULTS
-- ==========================================================
-- This query proves both versions exist: the historical closed version and the new active version.
SELECT 
    item_key,
    item_id,
    item_name,
    price,
    effective_start_date,
    effective_end_date,
    is_current
FROM dim_menu_item
WHERE item_name = 'Ribeye Steak'
ORDER BY effective_start_date DESC;
