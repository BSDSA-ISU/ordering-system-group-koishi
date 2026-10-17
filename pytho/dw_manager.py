import mariadb
from tabulate import tabulate  # Import tabulate

db_config = {
    "host": "localhost",
    "user": "ali",
    "password": "toshinoukyouko",
    "database": "restaurant_dw",
    "port": 3306
}

try:
    conn = mariadb.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    print("Successfully connected to restaurant_dw!\n")

    # 1. Check the SCD Type 2 history for Ribeye Steak
    cursor.execute("""
        SELECT item_name, price, effective_start_date, effective_end_date, is_current 
        FROM dim_menu_item 
        WHERE item_name = 'Ribeye Steak';
    """)
    steak_history = cursor.fetchall()
    
    print("--- Ribeye Steak SCD Version History ---")
    # tabulate takes the data and headers. 
    # headers="keys" automatically extracts column names from your dictionary keys!
    print(tabulate(steak_history, headers="keys", tablefmt="fancy_grid"))

    # 2. Query Total Sales by Category (Star Schema analytical query)
    print("\n--- Total Revenue by Category ---")
    cursor.execute("""
        SELECT 
            dmi.category_name,
            COUNT(fs.sale_id) AS total_items_sold,
            SUM(fs.subtotal) AS total_revenue
        FROM fact_sales fs
        JOIN dim_menu_item dmi ON fs.item_key = dmi.item_key
        GROUP BY dmi.category_name
        ORDER BY total_revenue DESC;
    """)
    category_sales = cursor.fetchall()
    
    print(tabulate(category_sales, headers="keys", tablefmt="github"))

except mariadb.Error as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals() and conn.open:
        cursor.close()
        conn.close()