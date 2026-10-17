import argparse
import random
from datetime import datetime, timedelta
from faker import Faker
import mariadb
import sys
from pprint import pprint

fake = Faker()

# Database Connection Configuration
db_config = {
    "host": "localhost",
    "user": "ali",
    "password": "koishikomeiji",
    "database": "restaurant",
    "port": 3306
}

def generate_restaurant_data(num_users, num_categories, num_items_per_category, num_orders):
    try:
        conn = mariadb.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        print("Successfully connected to MariaDB database!\n")

        # ---------------------------------------------------------
        # 1. Insert Users
        # ---------------------------------------------------------
        print(f"Generating {num_users} users...")
        user_ids = []
        for _ in range(num_users):
            first_name = fake.first_name()
            last_name = fake.last_name()
            email = fake.unique.email()
            phone = fake.phone_number()[:20]  # Truncate to fit VARCHAR(20)
            password_hash = fake.sha256()[:60]
            
            cursor.execute(
                """
                INSERT INTO users (first_name, last_name, email, phone_number, password_hash) 
                VALUES (?, ?, ?, ?, ?)
                """,
                (first_name, last_name, email, phone, password_hash)
            )
            user_ids.append(cursor.lastrowid)

        # ---------------------------------------------------------
        # 2. Insert Categories
        # ---------------------------------------------------------
        print(f"Generating up to {num_categories} categories...")
        category_data = [
            ("Appetizers", "Light starters to kick off your meal"),
            ("Main Courses", "Hearty and delicious primary dishes"),
            ("Desserts", "Sweet treats to finish your dining experience"),
            ("Beverages", "Refreshing drinks, sodas, and juices"),
            ("Sides", "Complementary side dishes")
        ]
        
        # Ensure we don't request more than available in category_data
        selected_categories = category_data[:num_categories]
        category_ids = []
        for cat_name, desc in selected_categories:
            cursor.execute(
                "INSERT INTO categories (category_name, description) VALUES (?, ?)",
                (cat_name, desc)
            )
            category_ids.append(cursor.lastrowid)

        # ---------------------------------------------------------
        # 3. Insert Menu Items
        # ---------------------------------------------------------
        print(f"Generating menu items ({num_items_per_category} per category)...")
        item_pool = {
            "Appetizers": [("Garlic Bread", 6.50), ("Mozzarella Sticks", 8.00), ("Caesar Salad", 9.25), ("Bruschetta", 7.50)],
            "Main Courses": [("Cheeseburger & Fries", 15.00), ("Grilled Salmon", 22.50), ("Margherita Pizza", 14.00), ("Ribeye Steak", 28.00)],
            "Desserts": [("Chocolate Lava Cake", 8.50), ("Cheesecake", 7.50), ("Tiramisu", 9.00), ("Ice Cream Scoop", 4.50)],
            "Beverages": [("Craft Soda", 3.50), ("Iced Tea", 3.00), ("Lemonade", 3.25), ("Espresso", 4.00)],
            "Sides": [("French Fries", 4.50), ("Onion Rings", 5.00), ("Mashed Potatoes", 4.75), ("Steamed Veggies", 5.25)]
        }

        item_prices = {}
        for idx, cat_id in enumerate(category_ids):
            cat_name = selected_categories[idx][0]
            items = item_pool.get(cat_name, [("Generic Item", 10.00)])
            
            # Slice based on user input
            for item_name, price in items[:num_items_per_category]:
                description = fake.sentence()
                cursor.execute(
                    """
                    INSERT INTO menu_items (category_id, item_name, description, price, is_available) 
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (cat_id, item_name, description, price, True)
                )
                item_prices[cursor.lastrowid] = price

        item_ids = list(item_prices.keys())

        # ---------------------------------------------------------
        # 4 & 5. Insert Orders and Order Items
        # ---------------------------------------------------------
        print(f"Generating {num_orders} orders and corresponding items...")
        order_types = ['Dine-In', 'Takeout', 'Delivery']
        order_statuses = ['Pending', 'Confirmed', 'Preparing', 'Ready', 'Completed', 'Cancelled']
        
        for _ in range(num_orders):
            customer_id = random.choice(user_ids)
            order_type = random.choice(order_types)
            order_status = random.choice(order_statuses)
            
            table_id = random.randint(1, 15) if order_type == 'Dine-In' else None
            staff_id = random.randint(1, 5)
            created_at = datetime.now() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))

            cursor.execute(
                """
                INSERT INTO orders (customer_id, table_id, staff_id, order_type, order_status, total_amount, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (customer_id, table_id, staff_id, order_type, order_status, 0.00, created_at)
            )
            order_id = cursor.lastrowid

            num_order_items = random.randint(1, min(3, len(item_ids)))
            chosen_items = random.sample(item_ids, num_order_items)
            
            order_total = 0.00
            for item_id in chosen_items:
                quantity = random.randint(1, 3)
                unit_price = item_prices[item_id]
                subtotal = quantity * unit_price
                order_total += subtotal
                
                special_instructions = random.choice([None, None, "Extra sauce", "No onions", "Well done"])

                cursor.execute(
                    """
                    INSERT INTO order_items (order_id, item_id, quantity, unit_price, subtotal, special_instructions) 
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (order_id, item_id, quantity, unit_price, subtotal, special_instructions)
                )

            cursor.execute(
                "UPDATE orders SET total_amount = ? WHERE order_id = ?",
                (order_total, order_id)
            )

        conn.commit()
        print("\nSynthetic data generation completed successfully!")

        # ---------------------------------------------------------
        # Preview Sample Data with pprint
        # ---------------------------------------------------------
        print("\n" + "=" * 50)
        print("PREVIEWING GENERATED DATA")
        print("=" * 50)

        cursor.execute("SELECT user_id, first_name, last_name, email FROM users LIMIT 2;")
        pprint(cursor.fetchall())

        cursor.execute("SELECT item_id, item_name, price FROM menu_items LIMIT 2;")
        pprint(cursor.fetchall())

        cursor.execute("SELECT order_id, order_type, total_amount FROM orders LIMIT 2;")
        pprint(cursor.fetchall())

    except mariadb.Error as e:
        print(f"Error connecting to MariaDB: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals() and conn.open:
            cursor.close()
            conn.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic restaurant data.")
    parser.add_argument("-u", "--users", type=int, default=20, help="Number of users to generate")
    parser.add_argument("-c", "--categories", type=int, default=5, help="Number of categories to generate (max 5)")
    parser.add_argument("-i", "--items", type=int, default=4, help="Number of items per category")
    parser.add_argument("-o", "--orders", type=int, default=50)