"""
RetailAI — Fashion & Lifestyle Synthetic Data Generator
scripts/generate_data.py

Fully aligned with utils/data_loader.py column expectations.

Sheets generated:
  1. product_catalogue       — 10 000 SKUs with cost_price, margin, stock profile
  2. orders                  — 80 000 orders with net_revenue
  3. order_items             — line items for completed orders
  4. customers               — 30 000 customer profiles
  5. bq_events               — 250 000 GA4-style behavioural events
  6. invoices                — invoice rows for completed orders
  7. store_performance       — 15 stores: HOT / AVG / COLD summary card data
  8. store_monthly_trends    — 12 months × 15 stores (sparkline / trend charts)
  9. store_category_breakdown— 15 stores × 10 categories (heatmap drill-down)

Run:
    python scripts/generate_data.py

Output:
    data/synthetic_retail_data.xlsx
"""

import os
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

np.random.seed(99)
random.seed(99)

# ── Output path ────────────────────────────────────────────────────────────
# Resolve relative to this file so it works from any working directory
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR  = os.path.join(BASE_DIR, "data")
OUT_FILE  = os.path.join(DATA_DIR, "synthetic_retail_data.xlsx")

# ══════════════════════════════════════════════════════════════════════════
#  MASTER LOOKUPS
# ══════════════════════════════════════════════════════════════════════════

CATEGORIES = [
    "Ethnic Wear", "Western Wear", "Footwear", "Accessories",
    "Skincare & Beauty", "Bags & Wallets", "Sportswear",
    "Innerwear & Sleepwear", "Kids Fashion", "Jewellery",
]

PRODUCT_NAMES = {
    "Ethnic Wear":           ["Kurta Set", "Saree", "Lehenga", "Salwar Suit", "Sherwani", "Dupatta", "Anarkali Dress", "Palazzo Set"],
    "Western Wear":          ["Denim Jeans", "Casual Shirt", "Blazer", "Mini Skirt", "Crop Top", "Hoodie", "Trench Coat", "Cargo Pants"],
    "Footwear":              ["Sneakers", "Heels", "Sandals", "Loafers", "Boots", "Flip Flops", "Oxford Shoes", "Wedges"],
    "Accessories":           ["Sunglasses", "Belt", "Scarf", "Cap", "Watch", "Hair Band", "Tie", "Gloves"],
    "Skincare & Beauty":     ["Face Serum", "Moisturizer", "Lipstick", "Foundation", "Sunscreen", "Eye Cream", "Face Wash", "Toner"],
    "Bags & Wallets":        ["Tote Bag", "Clutch", "Backpack", "Sling Bag", "Wallet", "Travel Bag", "Laptop Bag", "Crossbody Bag"],
    "Sportswear":            ["Yoga Pants", "Sports Bra", "Running Shorts", "Track Jacket", "Compression Tee", "Gym Vest", "Cycling Shorts", "Sports Shoes"],
    "Innerwear & Sleepwear": ["Bra Set", "Boxers", "Pyjama Set", "Nightgown", "Camisole", "Thermal Set", "Loungewear", "Sleep Shorts"],
    "Kids Fashion":          ["Kids Frock", "Boys Kurta", "Kids Jeans", "School Shoes", "Kids T-Shirt", "Baby Onesie", "Kids Jacket", "Girls Skirt"],
    "Jewellery":             ["Earrings", "Necklace", "Bracelet", "Ring", "Anklet", "Nose Pin", "Bangles", "Pendant Set"],
}

BRANDS = {
    "Ethnic Wear":           ["Biba", "W", "FabIndia", "Aurelia", "Global Desi"],
    "Western Wear":          ["Zara", "H&M", "Mango", "Only", "Vero Moda"],
    "Footwear":              ["Metro", "Bata", "Steve Madden", "Inc.5", "Clarks"],
    "Accessories":           ["Fossil", "Fastrack", "Hidesign", "Baggit", "Titan"],
    "Skincare & Beauty":     ["Lakme", "Mamaearth", "Dot & Key", "Minimalist", "Plum"],
    "Bags & Wallets":        ["Lavie", "Baggit", "Caprese", "Hidesign", "Eske"],
    "Sportswear":            ["Nike", "Adidas", "Puma", "Decathlon", "Reebok"],
    "Innerwear & Sleepwear": ["Jockey", "Enamor", "Amante", "Clovia", "PrettySecrets"],
    "Kids Fashion":          ["FirstCry", "H&M Kids", "Hopscotch", "Mothercare", "Carter's"],
    "Jewellery":             ["Tanishq", "Malabar", "Voylla", "Pipa Bella", "Sia Fashion"],
}

# Realistic Indian fashion price ranges (min, max) in INR
PRICE_RANGE = {
    "Ethnic Wear":           (499,  8999),
    "Western Wear":          (399,  5999),
    "Footwear":              (299,  6999),
    "Accessories":           (199,  4999),
    "Skincare & Beauty":     (149,  2499),
    "Bags & Wallets":        (499,  7999),
    "Sportswear":            (399,  4999),
    "Innerwear & Sleepwear": (149,  1499),
    "Kids Fashion":          (199,  2999),
    "Jewellery":             (299,  9999),
}

PAYMENT_METHODS = ["credit_card", "debit_card", "upi", "net_banking", "wallet", "emi", "cod"]

CITIES      = ["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai",
               "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Surat"]
STATES_LIST = ["Maharashtra", "Delhi", "Karnataka", "Telangana", "Tamil Nadu",
               "Maharashtra", "West Bengal", "Gujarat", "Rajasthan", "Gujarat"]

EVENT_TYPES = ["session_start", "view_item", "add_to_cart", "begin_checkout",
               "purchase", "remove_from_cart", "view_item_list", "select_item", "wishlist_add"]
PLATFORMS   = ["WEB", "IOS", "ANDROID"]
SEASONS     = ["Summer", "Winter", "Festive", "Monsoon", "All Season"]
GENDERS     = ["Women", "Men", "Unisex", "Kids"]
COLORS      = ["Black", "White", "Blue", "Red", "Green", "Pink",
               "Yellow", "Beige", "Navy", "Olive", "Maroon", "Teal"]

# ── Store master ───────────────────────────────────────────────────────────
# tier T1 = premium / high-footfall malls  |  T2 = mid-tier
STORES = [
    {"store_id": "STR_001", "store_name": "Phoenix Palladium Mumbai",  "city": "Mumbai",    "state_name": "Maharashtra", "tier": "T1"},
    {"store_id": "STR_002", "store_name": "Select Citywalk Delhi",     "city": "Delhi",     "state_name": "Delhi",       "tier": "T1"},
    {"store_id": "STR_003", "store_name": "UB City Bengaluru",         "city": "Bengaluru", "state_name": "Karnataka",   "tier": "T1"},
    {"store_id": "STR_004", "store_name": "Inorbit Mall Hyderabad",    "city": "Hyderabad", "state_name": "Telangana",   "tier": "T1"},
    {"store_id": "STR_005", "store_name": "Express Avenue Chennai",    "city": "Chennai",   "state_name": "Tamil Nadu",  "tier": "T1"},
    {"store_id": "STR_006", "store_name": "Seawoods Grand Pune",       "city": "Pune",      "state_name": "Maharashtra", "tier": "T2"},
    {"store_id": "STR_007", "store_name": "South City Mall Kolkata",   "city": "Kolkata",   "state_name": "West Bengal", "tier": "T2"},
    {"store_id": "STR_008", "store_name": "Ahmedabad One Mall",        "city": "Ahmedabad", "state_name": "Gujarat",     "tier": "T2"},
    {"store_id": "STR_009", "store_name": "World Trade Park Jaipur",   "city": "Jaipur",    "state_name": "Rajasthan",   "tier": "T2"},
    {"store_id": "STR_010", "store_name": "Surat Diamond Bourse Mall", "city": "Surat",     "state_name": "Gujarat",     "tier": "T2"},
    {"store_id": "STR_011", "store_name": "Viviana Mall Mumbai",       "city": "Mumbai",    "state_name": "Maharashtra", "tier": "T2"},
    {"store_id": "STR_012", "store_name": "Ambience Mall Delhi",       "city": "Delhi",     "state_name": "Delhi",       "tier": "T1"},
    {"store_id": "STR_013", "store_name": "Orion Mall Bengaluru",      "city": "Bengaluru", "state_name": "Karnataka",   "tier": "T2"},
    {"store_id": "STR_014", "store_name": "Inorbit Mall Mumbai",       "city": "Mumbai",    "state_name": "Maharashtra", "tier": "T2"},
    {"store_id": "STR_015", "store_name": "GVK One Hyderabad",         "city": "Hyderabad", "state_name": "Telangana",   "tier": "T1"},
]


# ══════════════════════════════════════════════════════════════════════════
#  GENERATORS
# ══════════════════════════════════════════════════════════════════════════

# ── 1. Products ────────────────────────────────────────────────────────────
def generate_products(n: int = 10_000) -> pd.DataFrame:
    print(f"  Generating {n:,} products...")
    rows = []
    for i in range(n):
        cat        = random.choice(CATEGORIES)
        base_name  = random.choice(PRODUCT_NAMES[cat])
        brand      = random.choice(BRANDS[cat])
        season     = random.choice(SEASONS)
        gender     = random.choice(GENDERS)
        color      = random.choice(COLORS)
        size_range = random.choice(["XS-XXL", "S-XL", "One Size", "6-10 UK", "28-36 Waist"])

        lo, hi       = PRICE_RANGE[cat]
        price        = round(random.uniform(lo, hi), 2)
        discount_pct = round(random.uniform(5, 55), 1)
        special      = round(price * (1 - discount_pct / 100), 2)
        cost_price   = round(special * random.uniform(0.45, 0.65), 2)
        margin_pct   = round((special - cost_price) / special * 100, 1) if special > 0 else 0

        # Stock profile → clearance risk distribution
        profile  = random.choices(["fast", "medium", "slow"], weights=[30, 40, 30])[0]
        quantity = {"fast": random.randint(5, 60),
                    "medium": random.randint(40, 250),
                    "slow": random.randint(180, 700)}[profile]

        rows.append({
            # ── data_loader columns ──
            "product_id":    f"SKU_{i+1:05d}",
            "product_name":  f"{brand} {color} {base_name}",
            "main_category": cat,
            "price":         price,
            "special_price": special,
            "cost_price":    cost_price,
            "quantity":      quantity,
            "discount_pct":  discount_pct,
            # ── descriptive ──
            "brand":         brand,
            "gender":        gender,
            "season":        season,
            "color":         color,
            "size_range":    size_range,
            "margin_pct":    margin_pct,
            # internal — dropped before save
            "_profile":      profile,
        })
    return pd.DataFrame(rows)


# ── 2. Orders ──────────────────────────────────────────────────────────────
def generate_orders(n: int = 80_000) -> pd.DataFrame:
    print(f"  Generating {n:,} orders...")
    start = datetime(2023, 1, 1)
    end   = datetime(2026, 3, 31)
    span  = (end - start).days
    rows  = []
    for i in range(n):
        city_idx     = random.randint(0, len(CITIES) - 1)
        order_date   = start + timedelta(days=random.randint(0, span))
        grand_total  = round(random.uniform(299, 12_000), 2)
        discount_amt = round(grand_total * random.uniform(0, 0.45), 2)
        net_revenue  = round(grand_total - discount_amt, 2)
        state        = random.choices(
            ["complete", "pending", "canceled", "processing"],
            weights=[72, 12, 10, 6],
        )[0]
        rows.append({
            "order_id":          f"ORD_{i+1:06d}",
            "order_date":         order_date,
            "state":              state,
            "grand_total":        grand_total,
            "net_revenue":        net_revenue,          # required by data_loader
            "discount_amount":    discount_amt,
            "total_qty_ordered":  random.randint(1, 8),
            "payment_method":     random.choice(PAYMENT_METHODS),
            "customer_is_guest":  random.choice([0, 1]),
            "city":               CITIES[city_idx],
            "state_name":         STATES_LIST[city_idx],
        })
    return pd.DataFrame(rows)


# ── 3. Order Items ─────────────────────────────────────────────────────────
def generate_order_items(orders_df: pd.DataFrame, products_df: pd.DataFrame) -> pd.DataFrame:
    print("  Generating order items...")
    completed = orders_df[orders_df["state"] == "complete"]

    weights = products_df["_profile"].map({"fast": 5.0, "medium": 1.8, "slow": 0.3}).values
    weights = weights / weights.sum()

    rows = []
    for _, order in completed.iterrows():
        n_items = random.randint(1, 4)
        prods   = products_df.sample(n_items, weights=weights, replace=True)
        for _, prod in prods.iterrows():
            qty       = random.randint(1, 4)
            price     = prod["price"]
            discount  = round(price * random.uniform(0, 0.40), 2)
            row_total = round((price - discount) * qty, 2)
            rows.append({
                "order_id":                  order["order_id"],
                "product_id":                prod["product_id"],
                "item_name":                 prod["product_name"],
                "product_main_category":     prod["main_category"],
                "qty_ordered":               qty,
                "price":                     price,
                "discount_amount":           discount,
                "row_total":                 row_total,
                "line_total_after_discount": row_total,
                "order_state":               order["state"],   # filter key in data_loader
                "order_date":                order["order_date"],
                "brand":                     prod["brand"],
            })
    return pd.DataFrame(rows)


# ── 4. Customers ───────────────────────────────────────────────────────────
def generate_customers(n: int = 30_000) -> pd.DataFrame:
    print(f"  Generating {n:,} customers...")
    start = datetime(2022, 1, 1)
    rows  = []
    for i in range(n):
        city_idx = random.randint(0, len(CITIES) - 1)
        created  = start + timedelta(days=random.randint(0, 1500))
        rows.append({
            "customer_id":           f"CUST_{i+1:06d}",
            "customer_created_date":  created,
            "customer_is_guest":      random.choice([0, 1]),
            "city":                   CITIES[city_idx],
            "state_name":             STATES_LIST[city_idx],
            "gender":                 random.choice(["Female", "Male", "Other"]),
        })
    return pd.DataFrame(rows)


# ── 5. BQ Events ───────────────────────────────────────────────────────────
def generate_bq_events(products_df: pd.DataFrame, n: int = 250_000) -> pd.DataFrame:
    print(f"  Generating {n:,} BQ events...")
    start   = datetime(2024, 1, 1)
    end     = datetime(2026, 3, 31)
    span    = (end - start).days
    weights = [15, 28, 14, 7, 5, 4, 10, 7, 10]   # funnel drop-off
    rows    = []
    for _ in range(n):
        event_date = start + timedelta(days=random.randint(0, span))
        event_name = random.choices(EVENT_TYPES, weights=weights)[0]
        prod       = products_df.sample(1).iloc[0]
        rows.append({
            "event_date":         event_date,
            "event_name":         event_name,
            "ga_session_id":      f"SESSION_{random.randint(1, 50_000)}",
            "user_pseudo_id":     f"USER_{random.randint(1, 30_000)}",
            "item_name":          prod["product_name"] if event_name != "session_start" else None,
            "platform":           random.choice(PLATFORMS),
            "event_value_in_usd": round(random.uniform(299, 9_999), 2) if event_name == "purchase" else 0,
        })
    return pd.DataFrame(rows)


# ── 6. Invoices ────────────────────────────────────────────────────────────
def generate_invoices(orders_df: pd.DataFrame) -> pd.DataFrame:
    print("  Generating invoices...")
    completed = orders_df[orders_df["state"] == "complete"].copy()
    rows      = []
    for i, (_, order) in enumerate(completed.iterrows()):
        rows.append({
            "invoice_id":   f"INV_{i+1:06d}",
            "order_id":     order["order_id"],
            "invoice_date": order["order_date"] + timedelta(days=random.randint(0, 3)),
            "grand_total":  order["grand_total"],
        })
    return pd.DataFrame(rows)


# ── 7. Store Performance ───────────────────────────────────────────────────
def generate_store_performance() -> pd.DataFrame:
    """
    One summary row per store.
    Columns used by dashboard.py store cards:
        store_id, store_name, city, state_name, tier,
        performance_label   → HOT / AVG / COLD
        sell_through_rate   → % (main KPI on card)
        avg_discount_depth  → % avg markdown depth
        active_skus         → SKUs actively selling
        monthly_revenue     → INR
        total_stock_units
        units_sold
        units_remaining
        top_category
    """
    print(f"  Generating store performance for {len(STORES)} stores...")
    rows = []
    for store in STORES:
        # T1 malls skew HOT, T2 malls skew COLD
        if store["tier"] == "T1":
            perf = random.choices(["HOT", "AVG", "COLD"], weights=[55, 35, 10])[0]
        else:
            perf = random.choices(["HOT", "AVG", "COLD"], weights=[20, 45, 35])[0]

        if perf == "HOT":
            sell_through_rate  = round(random.uniform(78, 92), 1)
            avg_discount_depth = round(random.uniform(15, 24), 1)
            active_skus        = random.randint(8, 14)
        elif perf == "AVG":
            sell_through_rate  = round(random.uniform(68, 78), 1)
            avg_discount_depth = round(random.uniform(22, 28), 1)
            active_skus        = random.randint(12, 18)
        else:  # COLD
            sell_through_rate  = round(random.uniform(50, 68), 1)
            avg_discount_depth = round(random.uniform(27, 38), 1)
            active_skus        = random.randint(16, 25)

        monthly_revenue   = round(sell_through_rate * random.uniform(18_000, 45_000), 2)
        total_stock_units = random.randint(300, 1_200)
        units_sold        = int(total_stock_units * sell_through_rate / 100)
        units_remaining   = total_stock_units - units_sold

        rows.append({
            "store_id":           store["store_id"],
            "store_name":         store["store_name"],
            "city":               store["city"],
            "state_name":         store["state_name"],
            "tier":               store["tier"],
            "performance_label":  perf,
            "sell_through_rate":  sell_through_rate,
            "avg_discount_depth": avg_discount_depth,
            "active_skus":        active_skus,
            "monthly_revenue":    monthly_revenue,
            "total_stock_units":  total_stock_units,
            "units_sold":         units_sold,
            "units_remaining":    units_remaining,
            "top_category":       random.choice(CATEGORIES),
        })
    return pd.DataFrame(rows)


# ── 8. Store Monthly Trends ────────────────────────────────────────────────
def generate_store_monthly_trends() -> pd.DataFrame:
    """
    12 months × 15 stores — used for sparklines & trend charts.
    Seasonal bumps:
        Oct–Dec  → festive  +15–40 %
        Jun–Jul  → summer sale +8–20 %
        Jan–Feb  → post-festive dip  -5–15 %
    Columns:
        store_id, store_name, year_month,
        revenue, sell_through_rate, avg_discount_depth,
        units_sold, footfall
    """
    print("  Generating store monthly trends...")
    months = pd.date_range(start="2025-04-01", periods=12, freq="MS")
    rows   = []
    for store in STORES:
        base_revenue = (
            random.uniform(500_000, 2_000_000) if store["tier"] == "T1"
            else random.uniform(200_000, 800_000)
        )
        base_st      = random.uniform(65, 85)
        trend_factor = random.uniform(-0.02, 0.04)   # monthly growth / decay

        for i, month in enumerate(months):
            m = month.month
            if m in [10, 11, 12]:
                seasonal = random.uniform(1.15, 1.40)   # festive
            elif m in [6, 7]:
                seasonal = random.uniform(1.08, 1.20)   # summer sale
            elif m in [1, 2]:
                seasonal = random.uniform(0.85, 0.95)   # post-festive dip
            else:
                seasonal = random.uniform(0.97, 1.05)

            revenue           = round(base_revenue * seasonal * (1 + trend_factor * i) * random.uniform(0.92, 1.08), 2)
            sell_through_rate = round(min(98.0, base_st * seasonal * random.uniform(0.95, 1.05)), 1)
            avg_discount      = round(random.uniform(15, 35), 1)
            units_sold        = int(revenue / random.uniform(500, 2_000))
            footfall          = int(units_sold * random.uniform(8, 20))

            rows.append({
                "store_id":           store["store_id"],
                "store_name":         store["store_name"],
                "year_month":         month.strftime("%Y-%m"),
                "revenue":            revenue,
                "sell_through_rate":  sell_through_rate,
                "avg_discount_depth": avg_discount,
                "units_sold":         units_sold,
                "footfall":           footfall,
            })
    return pd.DataFrame(rows)


# ── 9. Store × Category Breakdown ─────────────────────────────────────────
def generate_store_category_breakdown() -> pd.DataFrame:
    """
    15 stores × 10 categories — used for heatmaps & category drill-down.
    Columns:
        store_id, store_name, main_category,
        category_revenue, category_units_sold,
        category_sell_through_rate, category_avg_discount
    """
    print("  Generating store × category breakdown...")
    rows = []
    for store in STORES:
        for cat in CATEGORIES:
            cat_revenue  = round(random.uniform(20_000, 300_000), 2)
            units_sold   = int(cat_revenue / random.uniform(400, 3_000))
            sell_through = round(random.uniform(50, 92), 1)
            avg_discount = round(random.uniform(12, 40), 1)
            rows.append({
                "store_id":                   store["store_id"],
                "store_name":                 store["store_name"],
                "main_category":              cat,
                "category_revenue":           cat_revenue,
                "category_units_sold":        units_sold,
                "category_sell_through_rate": sell_through,
                "category_avg_discount":      avg_discount,
            })
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🚀 RetailAI — Generating Fashion & Lifestyle synthetic data\n")

    # ── Generate ──
    products             = generate_products(10_000)
    orders               = generate_orders(80_000)
    order_items          = generate_order_items(orders, products)
    customers            = generate_customers(30_000)
    bq_events            = generate_bq_events(products, 250_000)
    invoices             = generate_invoices(orders)
    store_performance    = generate_store_performance()
    store_monthly        = generate_store_monthly_trends()
    store_cat_breakdown  = generate_store_category_breakdown()

    products_save = products.drop(columns=["_profile"])

    # ── Summary ──
    print("\n📊 Dataset Summary:")
    print(f"  product_catalogue        {len(products_save):>8,} rows")
    print(f"  orders                   {len(orders):>8,} rows")
    print(f"  order_items              {len(order_items):>8,} rows")
    print(f"  customers                {len(customers):>8,} rows")
    print(f"  bq_events                {len(bq_events):>8,} rows")
    print(f"  invoices                 {len(invoices):>8,} rows")
    print(f"  store_performance        {len(store_performance):>8,} stores")
    print(f"  store_monthly_trends     {len(store_monthly):>8,} rows  (12 months × {len(STORES)} stores)")
    print(f"  store_category_breakdown {len(store_cat_breakdown):>8,} rows  ({len(STORES)} stores × {len(CATEGORIES)} categories)")

    # ── Store label distribution ──
    dist = store_performance["performance_label"].value_counts()
    print("\n🏬 Store performance distribution:")
    for label, count in dist.items():
        emoji = {"HOT": "🔴", "AVG": "🟡", "COLD": "🔵"}.get(label, "")
        avg_st = store_performance[store_performance["performance_label"] == label]["sell_through_rate"].mean()
        print(f"  {emoji} {label:4s}  {count} stores   avg sell-through {avg_st:.1f}%")

    # ── Clearance risk preview ──
    completed_items = order_items[order_items["order_state"] == "complete"]
    sold = (
        completed_items
        .groupby("product_id")["qty_ordered"].sum()
        .reset_index()
        .rename(columns={"qty_ordered": "total_qty_sold"})
    )
    preview = products[["product_id", "quantity", "_profile"]].merge(sold, on="product_id", how="left")
    preview["total_qty_sold"] = preview["total_qty_sold"].fillna(0)
    days = max((orders["order_date"].max() - orders["order_date"].min()).days, 1)
    preview["velocity"] = preview["total_qty_sold"] / days
    preview["clearance_risk"] = np.where(
        (preview["quantity"] > 50) & (preview["velocity"] < 0.1), "HIGH",
        np.where((preview["quantity"] > 20) & (preview["velocity"] < 0.3), "MEDIUM", "LOW"),
    )
    risk_dist = preview["clearance_risk"].value_counts(normalize=True).mul(100).round(1)
    print("\n📦 Clearance risk distribution:")
    for k, v in risk_dist.items():
        print(f"  {k}: {v}%")

    # ── Save ──
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"\n💾 Saving → {OUT_FILE}")

    with pd.ExcelWriter(OUT_FILE, engine="openpyxl") as writer:
        products_save.to_excel(      writer, sheet_name="product_catalogue",        index=False)
        orders.to_excel(             writer, sheet_name="orders",                   index=False)
        order_items.to_excel(        writer, sheet_name="order_items",              index=False)
        customers.to_excel(          writer, sheet_name="customers",                index=False)
        bq_events.to_excel(          writer, sheet_name="bq_events",               index=False)
        invoices.to_excel(           writer, sheet_name="invoices",                 index=False)
        store_performance.to_excel(  writer, sheet_name="store_performance",        index=False)
        store_monthly.to_excel(      writer, sheet_name="store_monthly_trends",     index=False)
        store_cat_breakdown.to_excel(writer, sheet_name="store_category_breakdown", index=False)

    print("✅ Done!\n")
    print("Next step — update DATA_PATH in utils/data_loader.py:")
    print('  DATA_PATH = "data/synthetic_retail_data.xlsx"')
    print("\nNew sheets available for dashboard.py store cards:")
    print("  → store_performance         sell_through_rate, avg_discount_depth, active_skus, performance_label")
    print("  → store_monthly_trends      revenue, sell_through_rate per month (sparklines)")
    print("  → store_category_breakdown  category_revenue, sell_through per store (heatmap)")