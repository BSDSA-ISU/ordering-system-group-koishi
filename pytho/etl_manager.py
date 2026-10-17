import mariadb
import sys
from pprint import pprint

# Database Connection Configuration
db_config = {
    "host": "localhost",
    "user": "ali",
    "password": "toshinoukyouko",
    "database": "restaurant",  # Match your database name (restaurant or restaurant_db)
    "port": 3306
}

def run_restaurant_operations():
    try:
        # Connect to MariaDB
        conn = mariadb.connect(**db_config)
        # Use dictionary cursor so rows are returned as key-value pairs for pprint
        cursor = conn.cursor(dictionary=True)
        print("Successfully connected to MariaDB database!\n")

        # ---------------------------------------------------------
        # 1. Test the Transaction Procedure: sp_create_order
        # ---------------------------------------------------------
        print("Calling sp_create_order...")
        
        # Parameters: (p_customer_id, p_item_id, p_quantity, p_order_type, p_special_instructions)
        # Make sure user_id 1 and item_id 1 exist in your database first!
        customer_id = 1
        item_id = 1
        quantity = 2
        order_type = 'Takeout'
        instructions = 'Extra sauce, please!'

        try:
            # Execute the stored procedure
            cursor.execute(
                "CALL sp_create_order(?, ?, ?, ?, ?)",
                (customer_id, item_id, quantity, order_type, instructions)
            )
            
            # Fetch the result from the stored procedure
            order_result = cursor.fetchone()
            print("\n--- Order Created Successfully via Transaction ---")
            pprint(order_result)
            
            # CLEAR PENDING RESULTS (This fixes the "Commands out of sync" error)
            while cursor.nextset():
                pass
            
            # Note: Stored procedures that perform modifications need to be committed if autocommit is off
            conn.commit()

        except mariadb.Error as e:
            print(f"Transaction failed and rolled back automatically: {e}")

        # ---------------------------------------------------------
        # 2. Run the ETL Pipeline: sp_refresh_daily_sales_report
        # ---------------------------------------------------------
        print("\nRunning ETL Pipeline (sp_refresh_daily_sales_report)...")
        cursor.execute("CALL sp_refresh_daily_sales_report();")
        conn.commit()
        print("ETL Refresh completed successfully!")

        # ---------------------------------------------------------
        # 3. View the Resulting Daily Sales Report with pprint
        # ---------------------------------------------------------
        print("\n" + "=" * 50)
        print("DAILY SALES REPORT (From ETL Table)")
        print("=" * 50)
        
        cursor.execute("""
            SELECT report_date, total_completed_orders, total_sales, generated_at 
            FROM daily_sales_report 
            ORDER BY report_date DESC 
            LIMIT 5;
        """)
        
        sales_report = cursor.fetchall()
        pprint(sales_report)

    except mariadb.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals() and conn.open:
            cursor.close()
            conn.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    run_restaurant_operations()