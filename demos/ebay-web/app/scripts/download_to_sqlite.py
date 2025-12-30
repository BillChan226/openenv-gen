#!/usr/bin/env python3
"""
Download Amazon Products dataset from HuggingFace and store in SQLite database.
Dataset: https://huggingface.co/datasets/milistu/AMAZON-Products-2023
"""

import json
import os
import re
import sqlite3
import ast
from collections import defaultdict
from datasets import load_dataset

# Output paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(SCRIPT_DIR)
DB_DIR = os.path.join(APP_DIR, "database")
DB_FILE = os.path.join(DB_DIR, "products.db")

# Category mapping from Amazon meta categories to our slugs
CATEGORY_MAP = {
    "meta_Beauty_and_Personal_Care": {
        "slug": "beauty-personal-care",
        "name": "Beauty & Personal Care"
    },
    "meta_Sports_and_Outdoors": {
        "slug": "sports-outdoors",
        "name": "Sports & Outdoors"
    },
    "meta_Clothing_Shoes_and_Jewelry": {
        "slug": "clothing-shoes-jewelry",
        "name": "Clothing, Shoes & Jewelry"
    },
    "meta_Home_and_Kitchen": {
        "slug": "home-kitchen",
        "name": "Home & Kitchen"
    },
    "meta_Office_Products": {
        "slug": "office-products",
        "name": "Office Products"
    },
    "meta_Tools_and_Home_Improvement": {
        "slug": "tools-home-improvement",
        "name": "Tools & Home Improvement"
    },
    "meta_Health_and_Household": {
        "slug": "health-household",
        "name": "Health & Household"
    },
    "meta_Health_and_Personal_Care": {
        "slug": "health-household",
        "name": "Health & Household"
    },
    "meta_Patio_Lawn_and_Garden": {
        "slug": "patio-lawn-garden",
        "name": "Patio, Lawn & Garden"
    },
    "meta_Electronics": {
        "slug": "electronics",
        "name": "Electronics"
    },
    "meta_Cell_Phones_and_Accessories": {
        "slug": "cell-phones-accessories",
        "name": "Cell Phones & Accessories"
    },
    "meta_Video_Games": {
        "slug": "video-games",
        "name": "Video Games"
    },
    "meta_Grocery_and_Gourmet_Food": {
        "slug": "grocery-gourmet-food",
        "name": "Grocery & Gourmet Food"
    },
    "meta_Digital_Music": {
        "slug": "electronics",
        "name": "Electronics"
    },
    "meta_CDs_and_Vinyl": {
        "slug": "electronics",
        "name": "Electronics"
    },
    "meta_Automotive": {
        "slug": "tools-home-improvement",
        "name": "Tools & Home Improvement"
    },
    "meta_Arts_Crafts_and_Sewing": {
        "slug": "office-products",
        "name": "Office Products"
    },
    "meta_Pet_Supplies": {
        "slug": "health-household",
        "name": "Health & Household"
    },
    "meta_Toys_and_Games": {
        "slug": "video-games",
        "name": "Video Games"
    },
    "meta_Industrial_and_Scientific": {
        "slug": "tools-home-improvement",
        "name": "Tools & Home Improvement"
    },
    "meta_Musical_Instruments": {
        "slug": "electronics",
        "name": "Electronics"
    },
    "meta_Appliances": {
        "slug": "home-kitchen",
        "name": "Home & Kitchen"
    },
    "meta_Baby_Products": {
        "slug": "health-household",
        "name": "Health & Household"
    },
    "meta_Amazon_Fashion": {
        "slug": "clothing-shoes-jewelry",
        "name": "Clothing, Shoes & Jewelry"
    },
}

def slugify(text):
    """Convert text to URL-friendly slug."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

def parse_price(price_val):
    """Parse price value, handling various formats."""
    if price_val is None:
        return None
    if isinstance(price_val, (int, float)):
        if price_val > 0 and price_val < 50000:
            return round(float(price_val), 2)
    return None

def create_database(conn):
    """Create database schema."""
    cursor = conn.cursor()

    # Drop existing tables
    cursor.execute("DROP TABLE IF EXISTS product_categories")
    cursor.execute("DROP TABLE IF EXISTS products")
    cursor.execute("DROP TABLE IF EXISTS categories")

    # Create categories table
    cursor.execute("""
        CREATE TABLE categories (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            parent_id TEXT,
            FOREIGN KEY (parent_id) REFERENCES categories(id)
        )
    """)

    # Create products table
    cursor.execute("""
        CREATE TABLE products (
            id TEXT PRIMARY KEY,
            sku TEXT NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            rating REAL,
            review_count INTEGER DEFAULT 0,
            image TEXT,
            short_description TEXT,
            description TEXT,
            features TEXT,
            details TEXT,
            category_slug TEXT,
            sub_category TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create product_categories junction table for many-to-many
    cursor.execute("""
        CREATE TABLE product_categories (
            product_id TEXT,
            category_slug TEXT,
            PRIMARY KEY (product_id, category_slug),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # Create indexes for efficient querying
    cursor.execute("CREATE INDEX idx_products_category ON products(category_slug)")
    cursor.execute("CREATE INDEX idx_products_price ON products(price)")
    cursor.execute("CREATE INDEX idx_products_rating ON products(rating)")
    cursor.execute("CREATE INDEX idx_products_review_count ON products(review_count)")
    cursor.execute("CREATE INDEX idx_products_name ON products(name)")
    cursor.execute("CREATE INDEX idx_product_categories_slug ON product_categories(category_slug)")

    # Create FTS (Full-Text Search) virtual table for efficient text search
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS products_fts USING fts5(
            id,
            name,
            sku,
            short_description,
            description,
            content='products',
            content_rowid='rowid'
        )
    """)

    conn.commit()

def download_and_process(conn, max_per_category=100):
    """Download dataset and insert into database."""
    print("Loading dataset from HuggingFace...")
    print("This may take a while on first run as it downloads ~1.7GB...")

    # Load the dataset
    dataset = load_dataset("milistu/AMAZON-Products-2023", split="train")

    print(f"Dataset loaded with {len(dataset)} total products")

    cursor = conn.cursor()

    # Track categories
    categories_inserted = set()
    products_by_category = defaultdict(list)

    print("Processing products...")

    for idx, item in enumerate(dataset):
        if idx % 10000 == 0:
            print(f"  Processed {idx}/{len(dataset)} items...")

        # Get category info
        filename = item.get("filename", "")
        cat_info = CATEGORY_MAP.get(filename)
        if not cat_info:
            continue

        cat_slug = cat_info["slug"]
        cat_name = cat_info["name"]

        # Parse price
        price = parse_price(item.get("price"))
        if price is None or price <= 0:
            continue

        # Get rating
        rating = item.get("average_rating")
        if rating is None or rating <= 0:
            continue

        # Get image URL
        image = item.get("image", "")
        if not image or not image.startswith("http"):
            continue

        # Get title/name
        title = item.get("title", "")
        if not title or len(title) < 5:
            continue

        # Get description
        description = item.get("description", "") or ""
        if len(description) > 2000:
            description = description[:1997] + "..."

        # Get features
        features = item.get("features", []) or []
        features_json = json.dumps(features[:10]) if features else "[]"

        # Get details
        details_raw = item.get("details", "") or ""
        details = {}
        if details_raw and isinstance(details_raw, str):
            try:
                details = ast.literal_eval(details_raw)
            except:
                pass
        elif isinstance(details_raw, dict):
            details = details_raw
        details_json = json.dumps(details) if details else "{}"

        # Get sub-category
        categories_list = item.get("categories", []) or []
        sub_category = categories_list[0] if categories_list else ""

        # Insert category if not exists
        if cat_slug not in categories_inserted:
            try:
                cursor.execute(
                    "INSERT OR IGNORE INTO categories (id, name, slug) VALUES (?, ?, ?)",
                    (cat_slug, cat_name, cat_slug)
                )
                categories_inserted.add(cat_slug)
            except:
                pass

        # Store product info for later insertion (we'll select top N per category)
        product = {
            "id": f"amz-{item.get('parent_asin', idx)}",
            "sku": item.get("parent_asin", f"SKU-{idx}"),
            "name": title[:200] if len(title) > 200 else title,
            "price": price,
            "rating": round(float(rating), 1),
            "review_count": int(item.get("rating_number", 0) or 0),
            "image": image,
            "short_description": description[:300] + "..." if len(description) > 300 else description,
            "description": description,
            "features": features_json,
            "details": details_json,
            "category_slug": cat_slug,
            "sub_category": sub_category
        }

        products_by_category[cat_slug].append(product)

    print(f"\nProducts found per category:")
    for cat, prods in products_by_category.items():
        print(f"  {cat}: {len(prods)} products")

    # Insert top N products per category (sorted by review count)
    total_inserted = 0
    for cat_slug, prods in products_by_category.items():
        sorted_prods = sorted(prods, key=lambda x: x["review_count"], reverse=True)
        selected = sorted_prods[:max_per_category]

        for p in selected:
            try:
                cursor.execute("""
                    INSERT INTO products
                    (id, sku, name, price, rating, review_count, image,
                     short_description, description, features, details,
                     category_slug, sub_category)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p["id"], p["sku"], p["name"], p["price"], p["rating"],
                    p["review_count"], p["image"], p["short_description"],
                    p["description"], p["features"], p["details"],
                    p["category_slug"], p["sub_category"]
                ))

                # Insert into junction table
                cursor.execute("""
                    INSERT INTO product_categories (product_id, category_slug)
                    VALUES (?, ?)
                """, (p["id"], p["category_slug"]))

                total_inserted += 1
            except Exception as e:
                print(f"Error inserting product {p['id']}: {e}")

    conn.commit()

    # Rebuild FTS index
    print("\nBuilding full-text search index...")
    cursor.execute("""
        INSERT INTO products_fts (id, name, sku, short_description, description)
        SELECT id, name, sku, short_description, description FROM products
    """)
    conn.commit()

    print(f"\nTotal products inserted: {total_inserted}")
    print(f"Total categories: {len(categories_inserted)}")

    return total_inserted, len(categories_inserted)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Download Amazon products to SQLite")
    parser.add_argument("--per-category", type=int, default=100, help="Max products per category")
    args = parser.parse_args()

    # Create database directory
    os.makedirs(DB_DIR, exist_ok=True)

    # Remove existing database
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"Removed existing database: {DB_FILE}")

    # Connect to database
    conn = sqlite3.connect(DB_FILE)

    try:
        print(f"Creating database at: {DB_FILE}")
        create_database(conn)

        products, categories = download_and_process(conn, max_per_category=args.per_category)

        print(f"\nDatabase created successfully!")
        print(f"  Location: {DB_FILE}")
        print(f"  Products: {products}")
        print(f"  Categories: {categories}")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
