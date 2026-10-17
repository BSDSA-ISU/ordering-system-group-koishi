/*
Restaurant Ordering System
Transaction & ETL Developer Project
Target: MySQL Workbench / MySQL 8.x
Based on the uploaded schema:
restaurant_db, users, categories, menu_items, orders, order_items

IMPORTANT:
1. Run this script in MySQL Workbench after your original schema script.
2. It assumes the original tables already exist.
3. It does not create or alter the original five tables.
4. Use test records while demonstrating transactions.
*/

USE restaurant_db;

-- =========================================================
-- SECTION 1: PRE-FLIGHT CHECKS
-- =========================================================
-- Run these queries to confirm that the required records exist.
-- sp_create_order requires a valid customer and available menu item.

SELECT user_id, first_name, last_name, email
FROM users
ORDER BY user_id;

SELECT item_id, item_name, price, is_available
FROM menu_items
ORDER BY item_id;

SELECT order_id, customer_id, order_status, total_amount, created_at
FROM orders
ORDER BY order_id DESC;

-- =========================================================
-- SECTION 2: CREATE THE ETL REPORTING TABLE
-- =========================================================
-- One row per calendar date with at least one completed order.

CREATE TABLE IF NOT EXISTS daily_sales_report (
    report_date DATE PRIMARY KEY,
    total_completed_orders INT NOT NULL DEFAULT 0,
    total_sales DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- SECTION 3: TRANSACTION PROCEDURE
-- =========================================================
-- This procedure creates one order and one order item as a unit.
-- It calculates the unit price from menu_items instead of trusting
-- a price supplied by the caller.
-- If any SQL error occurs after the transaction begins, changes roll back.

DROP PROCEDURE IF EXISTS sp_create_order;

DELIMITER $$

CREATE PROCEDURE sp_create_order(
    IN p_customer_id INT,
    IN p_item_id INT,
    IN p_quantity INT,
    IN p_order_type VARCHAR(20),
    IN p_special_instructions TEXT
)
BEGIN
    DECLARE v_unit_price DECIMAL(10,2);
    DECLARE v_total DECIMAL(10,2);
    DECLARE v_order_id INT;
    DECLARE v_customer_count INT DEFAULT 0;
    DECLARE v_item_count INT DEFAULT 0;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    -- Validate inputs before changing data.
    IF p_quantity IS NULL OR p_quantity <= 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Quantity must be greater than zero.';
    END IF;

    IF p_order_type NOT IN ('Dine-In', 'Takeout', 'Delivery') THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Order type must be Dine-In, Takeout, or Delivery.';
    END IF;

    SELECT COUNT(*) INTO v_customer_count
    FROM users
    WHERE user_id = p_customer_id;

    IF v_customer_count = 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Customer does not exist in users.';
    END IF;

    SELECT COUNT(*) INTO v_item_count
    FROM menu_items
    WHERE item_id = p_item_id
      AND is_available = TRUE;

    IF v_item_count = 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Menu item does not exist or is unavailable.';
    END IF;

    SELECT price INTO v_unit_price
    FROM menu_items
    WHERE item_id = p_item_id;

    SET v_total = v_unit_price * p_quantity;

    START TRANSACTION;

    INSERT INTO orders (
        customer_id,
        order_type,
        order_status,
        total_amount
    )
    VALUES (
        p_customer_id,
        p_order_type,
        'Pending',
        v_total
    );

    SET v_order_id = LAST_INSERT_ID();

    INSERT INTO order_items (
        order_id,
        item_id,
        quantity,
        unit_price,
        subtotal,
        special_instructions
    )
    VALUES (
        v_order_id,
        p_item_id,
        p_quantity,
        v_unit_price,
        v_total,
        p_special_instructions
    );

    COMMIT;

    SELECT
        v_order_id AS created_order_id,
        v_unit_price AS unit_price,
        p_quantity AS quantity,
        v_total AS order_total,
        'Order saved successfully' AS result_message;
END$$

DELIMITER ;

-- =========================================================
-- SECTION 4: TEST A SUCCESSFUL TRANSACTION
-- =========================================================
-- First use Section 1 to find a real user_id and an available item_id.
-- Replace 1 and 1 below with valid IDs from your database.
-- This CALL permanently creates a test order, so only run it when ready.

-- CALL sp_create_order(1, 1, 2, 'Takeout', 'Transaction success test');

-- Verify the created order and its items:
-- SELECT * FROM orders ORDER BY order_id DESC LIMIT 5;
-- SELECT * FROM order_items ORDER BY order_item_id DESC LIMIT 5;

-- =========================================================
-- SECTION 5: TEST ROLLBACK MANUALLY
-- =========================================================
-- Replace the IDs with valid records. Run this whole section as a test.
-- It creates temporary uncommitted changes and then undoes them.
-- Do not put COMMIT in this test.

-- START TRANSACTION;
--
-- INSERT INTO orders (customer_id, order_type, order_status, total_amount)
-- VALUES (1, 'Dine-In', 'Pending', 123.45);
--
-- SET @rollback_test_order_id = LAST_INSERT_ID();
--
-- INSERT INTO order_items
--     (order_id, item_id, quantity, unit_price, subtotal, special_instructions)
-- VALUES
--     (@rollback_test_order_id, 1, 1, 123.45, 123.45, 'Rollback test only');
--
-- SELECT * FROM orders WHERE order_id = @rollback_test_order_id;
-- SELECT * FROM order_items WHERE order_id = @rollback_test_order_id;
--
-- ROLLBACK;
--
-- -- These queries should return no rows for the rolled-back order:
-- SELECT * FROM orders WHERE order_id = @rollback_test_order_id;
-- SELECT * FROM order_items WHERE order_id = @rollback_test_order_id;

-- =========================================================
-- SECTION 6: ETL PROCEDURE — EXTRACT, TRANSFORM, LOAD
-- =========================================================
-- EXTRACT: read orders from the operational orders table.
-- TRANSFORM: keep only Completed orders, group by date, count orders,
--            and sum total_amount.
-- LOAD: replace the reporting table contents in one transaction.

DROP PROCEDURE IF EXISTS sp_refresh_daily_sales_report;

DELIMITER $$

CREATE PROCEDURE sp_refresh_daily_sales_report()
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    DELETE FROM daily_sales_report;

    INSERT INTO daily_sales_report (
        report_date,
        total_completed_orders,
        total_sales,
        generated_at
    )
    SELECT
        DATE(created_at) AS report_date,
        COUNT(*) AS total_completed_orders,
        SUM(total_amount) AS total_sales,
        CURRENT_TIMESTAMP AS generated_at
    FROM orders
    WHERE order_status = 'Completed'
    GROUP BY DATE(created_at);

    COMMIT;
END$$

DELIMITER ;

-- =========================================================
-- SECTION 7: RUN ETL AND CHECK THE REPORT
-- =========================================================

CALL sp_refresh_daily_sales_report();

SELECT
    report_date,
    total_completed_orders,
    total_sales,
    generated_at
FROM daily_sales_report
ORDER BY report_date DESC;

-- =========================================================
-- SECTION 8: VALIDATION / TEST QUERIES
-- =========================================================

-- Test A: Compare completed orders and the reporting totals.
SELECT
    DATE(created_at) AS report_date,
    COUNT(*) AS expected_completed_orders,
    SUM(total_amount) AS expected_total_sales
FROM orders
WHERE order_status = 'Completed'
GROUP BY DATE(created_at)
ORDER BY report_date DESC;

-- Test B: Find order items whose subtotal does not match unit_price * quantity.
-- Ideally this returns no rows.
SELECT
    order_item_id,
    order_id,
    item_id,
    quantity,
    unit_price,
    subtotal
FROM order_items
WHERE subtotal <> unit_price * quantity;

-- Test C: Find orders whose stored total differs from the sum of their items.
-- This can return existing mismatches if the original sample data is incomplete
-- or if order totals were entered manually.
SELECT
    o.order_id,
    o.total_amount AS order_total,
    COALESCE(SUM(oi.subtotal), 0.00) AS item_total
FROM orders AS o
LEFT JOIN order_items AS oi
    ON oi.order_id = o.order_id
GROUP BY o.order_id, o.total_amount
HAVING o.total_amount <> COALESCE(SUM(oi.subtotal), 0.00)
ORDER BY o.order_id;

-- Test D: Count rows in each operational and reporting table.
SELECT 'users' AS table_name, COUNT(*) AS row_count FROM users
UNION ALL
SELECT 'categories', COUNT(*) FROM categories
UNION ALL
SELECT 'menu_items', COUNT(*) FROM menu_items
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL
SELECT 'daily_sales_report', COUNT(*) FROM daily_sales_report;

-- =========================================================
-- END OF PROJECT SCRIPT
-- =========================================================
