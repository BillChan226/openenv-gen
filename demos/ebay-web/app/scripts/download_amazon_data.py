#!/usr/bin/env python3
"""
Download Amazon Products dataset from HuggingFace and convert to eBay app format.
Dataset: https://huggingface.co/datasets/milistu/AMAZON-Products-2023
"""

import json
import os
import re
from collections import defaultdict
from datasets import load_dataset

# Output paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(SCRIPT_DIR)
BACKEND_DATA_DIR = os.path.join(APP_DIR, "backend", "src", "data")
OUTPUT_FILE = os.path.join(BACKEND_DATA_DIR, "amazonData.js")

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

def download_and_process(max_products=500, products_per_category=50):
    """Download dataset and process into app format."""
    print("Loading dataset from HuggingFace...")
    print("This may take a while on first run as it downloads ~1.7GB...")

    # Load the dataset
    dataset = load_dataset("milistu/AMAZON-Products-2023", split="train")

    print(f"Dataset loaded with {len(dataset)} total products")

    # Group products by category
    products_by_category = defaultdict(list)
    categories_data = {}

    print("Processing products...")

    for idx, item in enumerate(dataset):
        if idx % 10000 == 0:
            print(f"  Processed {idx}/{len(dataset)} items...")

        # Get category info - filename contains meta_Category_Name format
        filename = item.get("filename", "")
        main_category = item.get("main_category", "")

        # Map to our category structure using filename
        cat_info = CATEGORY_MAP.get(filename)
        if not cat_info:
            continue

        cat_slug = cat_info["slug"]
        cat_name = cat_info["name"]

        # Use categories list for sub-category if available
        categories_list = item.get("categories", []) or []
        sub_category = categories_list[0] if categories_list else ""

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
        if len(description) > 500:
            description = description[:497] + "..."

        # Get features
        features = item.get("features", []) or []
        if features:
            features = features[:5]  # Limit to 5 features

        # Get details - it's a string representation of a dict
        details_raw = item.get("details", "") or ""
        details = {}
        if details_raw and isinstance(details_raw, str):
            try:
                import ast
                details = ast.literal_eval(details_raw)
            except:
                pass
        elif isinstance(details_raw, dict):
            details = details_raw

        # Create product object
        product = {
            "id": f"amz-{item.get('parent_asin', idx)}",
            "sku": item.get("parent_asin", f"SKU-{idx}"),
            "name": title[:100] if len(title) > 100 else title,
            "price": price,
            "rating": round(float(rating), 1),
            "reviewCount": int(item.get("rating_number", 0) or 0),
            "image": image,
            "categoryPath": [cat_slug],
            "shortDescription": description[:150] + "..." if len(description) > 150 else description,
            "description": description,
            "features": features,
            "details": details if isinstance(details, dict) else {},
            "subCategory": sub_category
        }

        # Add sub-category to path if exists
        if sub_category:
            sub_slug = slugify(sub_category)
            if sub_slug:
                product["categoryPath"].append(sub_slug)

        products_by_category[cat_slug].append(product)

        # Track category info
        if cat_slug not in categories_data:
            categories_data[cat_slug] = {
                "id": cat_slug,
                "name": cat_name,
                "slug": cat_slug,
                "children": {}
            }

        # Track sub-categories
        if sub_category:
            sub_slug = slugify(sub_category)
            if sub_slug and sub_slug not in categories_data[cat_slug]["children"]:
                categories_data[cat_slug]["children"][sub_slug] = {
                    "id": f"{cat_slug}-{sub_slug}",
                    "name": sub_category,
                    "slug": sub_slug,
                    "children": []
                }

    print(f"\nProducts found per category:")
    for cat, prods in products_by_category.items():
        print(f"  {cat}: {len(prods)} products")

    # Select products (limit per category)
    final_products = []
    for cat_slug, prods in products_by_category.items():
        # Sort by review count (popularity) and take top N
        sorted_prods = sorted(prods, key=lambda x: x["reviewCount"], reverse=True)
        selected = sorted_prods[:products_per_category]
        final_products.extend(selected)

    # Build final categories structure
    final_categories = []
    for cat_slug, cat_data in categories_data.items():
        category = {
            "id": cat_data["id"],
            "name": cat_data["name"],
            "slug": cat_data["slug"],
            "children": list(cat_data["children"].values())
        }
        final_categories.append(category)

    print(f"\nTotal products selected: {len(final_products)}")
    print(f"Total categories: {len(final_categories)}")

    return final_products, final_categories

def save_to_js(products, categories):
    """Save data as JavaScript module."""

    js_content = '''// Amazon Products data imported from HuggingFace dataset
// Dataset: https://huggingface.co/datasets/milistu/AMAZON-Products-2023
// Auto-generated - do not edit manually

export const amazonCategories = %s;

export const amazonProducts = %s;
''' % (
        json.dumps(categories, indent=2),
        json.dumps(products, indent=2)
    )

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        f.write(js_content)

    print(f"\nData saved to: {OUTPUT_FILE}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Download Amazon products dataset")
    parser.add_argument("--max-products", type=int, default=500, help="Max total products")
    parser.add_argument("--per-category", type=int, default=50, help="Max products per category")
    args = parser.parse_args()

    products, categories = download_and_process(
        max_products=args.max_products,
        products_per_category=args.per_category
    )
    save_to_js(products, categories)
    print("\nDone!")

if __name__ == "__main__":
    main()
