# import os
# import streamlit as st
# import pandas as pd
# import numpy as np
# from config.settings import DATA_PATH
# from config.settings import DATA_MODE
# from utils.dynamodb import scan_products, scan_orders
# import pandas as pd


# # ── Raw loaders ────────────────────────────────────────────────────────────

# @st.cache_data
# def load_products() -> pd.DataFrame:
#     df = pd.read_excel(DATA_PATH, sheet_name="product_catalogue")
#     df["price"]         = pd.to_numeric(df["price"],         errors="coerce").fillna(0)
#     df["special_price"] = pd.to_numeric(df["special_price"], errors="coerce").fillna(0)
#     df["cost_price"]    = pd.to_numeric(df["cost_price"],    errors="coerce").fillna(0)
#     df["quantity"]      = pd.to_numeric(df["quantity"],      errors="coerce").fillna(0)
#     return df


# @st.cache_data
# def load_orders() -> pd.DataFrame:
#     df = pd.read_excel(DATA_PATH, sheet_name="orders")
#     df["order_date"]     = pd.to_datetime(df["order_date"], errors="coerce")
#     df["grand_total"]    = pd.to_numeric(df["grand_total"],  errors="coerce").fillna(0)
#     df["net_revenue"]    = pd.to_numeric(df["net_revenue"],  errors="coerce").fillna(0)
#     df["discount_amount"]= pd.to_numeric(df["discount_amount"], errors="coerce").fillna(0)
#     return df


# @st.cache_data
# def load_order_items() -> pd.DataFrame:
#     df = pd.read_excel(DATA_PATH, sheet_name="order_items")
#     df["order_date"]   = pd.to_datetime(df["order_date"], errors="coerce")
#     df["qty_ordered"]  = pd.to_numeric(df["qty_ordered"], errors="coerce").fillna(0)
#     df["price"]        = pd.to_numeric(df["price"],       errors="coerce").fillna(0)
#     df["row_total"]    = pd.to_numeric(df["row_total"],   errors="coerce").fillna(0)
#     return df[df["order_state"] == "complete"]


# @st.cache_data
# def load_customers() -> pd.DataFrame:
#     df = pd.read_excel(DATA_PATH, sheet_name="customers")
#     df["customer_created_date"] = pd.to_datetime(df["customer_created_date"], errors="coerce")
#     return df


# @st.cache_data
# def load_bq_events() -> pd.DataFrame:
#     df = pd.read_excel(DATA_PATH, sheet_name="bq_events")
#     df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
#     df["event_value_in_usd"] = pd.to_numeric(df["event_value_in_usd"], errors="coerce").fillna(0)
#     return df


# @st.cache_data
# def load_store_performance() -> pd.DataFrame:
#     df = pd.read_excel(DATA_PATH, sheet_name="store_performance")
#     df["sell_through_rate"]   = pd.to_numeric(df["sell_through_rate"],   errors="coerce").fillna(0)
#     df["avg_discount_depth"]  = pd.to_numeric(df["avg_discount_depth"],  errors="coerce").fillna(0)
#     df["monthly_revenue"]     = pd.to_numeric(df["monthly_revenue"],     errors="coerce").fillna(0)
#     return df


# @st.cache_data
# def load_store_monthly_trends() -> pd.DataFrame:
#     df = pd.read_excel(DATA_PATH, sheet_name="store_monthly_trends")
#     df["revenue"]            = pd.to_numeric(df["revenue"],            errors="coerce").fillna(0)
#     df["sell_through_rate"]  = pd.to_numeric(df["sell_through_rate"],  errors="coerce").fillna(0)
#     return df


# @st.cache_data
# def load_store_category_breakdown() -> pd.DataFrame:
#     return pd.read_excel(DATA_PATH, sheet_name="store_category_breakdown")


# # ── Computed metrics ───────────────────────────────────────────────────────

# @st.cache_data
# def compute_sales_metrics() -> pd.DataFrame:
#     products   = load_products()
#     order_items = load_order_items()
#     orders     = load_orders()

#     # total qty sold per product
#     sold = (
#         order_items
#         .groupby("product_id")
#         .agg(
#             total_qty_sold  = ("qty_ordered", "sum"),
#             total_revenue   = ("row_total",   "sum"),
#             order_count     = ("order_id",    "nunique"),
#         )
#         .reset_index()
#     )

#     df = products.merge(sold, on="product_id", how="left")
#     df["total_qty_sold"] = df["total_qty_sold"].fillna(0)
#     df["total_revenue"]  = df["total_revenue"].fillna(0)
#     df["order_count"]    = df["order_count"].fillna(0)

#     # date range for velocity
#     days = max((orders["order_date"].max() - orders["order_date"].min()).days, 1)

#     # sales velocity (units/day)
#     df["sales_velocity"] = df["total_qty_sold"] / days

#     # sell-through rate
#     df["sell_through_rate"] = np.where(
#         (df["total_qty_sold"] + df["quantity"]) > 0,
#         df["total_qty_sold"] / (df["total_qty_sold"] + df["quantity"]) * 100,
#         0,
#     ).round(1)

#     # days of stock
#     df["days_of_stock"] = np.where(
#         df["sales_velocity"] > 0,
#         df["quantity"] / df["sales_velocity"],
#         9999,
#     ).round(0)

#     # dead inventory flag
#     df["is_dead_inventory"] = df["days_of_stock"] > 180

#     # ABC classification — by total revenue
#     df = df.sort_values("total_revenue", ascending=False).reset_index(drop=True)
#     df["revenue_cumsum"] = df["total_revenue"].cumsum()
#     total_rev = df["total_revenue"].sum()
#     df["revenue_pct"] = df["revenue_cumsum"] / (total_rev + 1e-9)
#     df["abc_class"] = np.where(
#         df["revenue_pct"] <= 0.10, "A",
#         np.where(df["revenue_pct"] <= 0.50, "B", "C"),
#     )

#     # clearance risk
#     df["clearance_risk"] = np.where(
#         (df["quantity"] > 50) & (df["sales_velocity"] < 0.1), "HIGH",
#         np.where(
#             (df["quantity"] > 20) & (df["sales_velocity"] < 0.3), "MEDIUM", "LOW"
#         ),
#     )

#     return df.drop(columns=["revenue_cumsum", "revenue_pct"])


# @st.cache_data
# def compute_elasticity_data() -> pd.DataFrame:
#     """
#     Simple price elasticity per product:
#     uses price vs qty_ordered from order_items.
#     Returns product_id + elasticity (clipped -3.0 to -0.3).
#     """
#     items = load_order_items()
#     if items.empty:
#         return pd.DataFrame(columns=["product_id", "elasticity"])

#     grp = (
#         items.groupby(["product_id", "price"])["qty_ordered"]
#         .sum()
#         .reset_index()
#     )

#     results = []
#     for pid, group in grp.groupby("product_id"):
#         if len(group) < 2:
#             results.append({"product_id": pid, "elasticity": -1.2})
#             continue
#         pct_price  = group["price"].pct_change().dropna()
#         pct_qty    = group["qty_ordered"].pct_change().dropna()
#         valid      = (pct_price.abs() > 0.001)
#         if valid.sum() == 0:
#             results.append({"product_id": pid, "elasticity": -1.2})
#             continue
#         elasticity = (pct_qty[valid] / pct_price[valid]).mean()
#         elasticity = float(np.clip(elasticity, -3.0, -0.3))
#         results.append({"product_id": pid, "elasticity": elasticity})

#     return pd.DataFrame(results)


# @st.cache_data
# def compute_event_metrics() -> dict:
#     """
#     Cart abandonment funnel and conversion rates from BQ events.
#     Returns a dict of summary metrics.
#     """
#     events = load_bq_events()
#     if events.empty:
#         return {}

#     counts = events["event_name"].value_counts().to_dict()

#     views       = counts.get("view_item", 1)
#     add_to_cart = counts.get("add_to_cart", 0)
#     checkout    = counts.get("begin_checkout", 0)
#     purchase    = counts.get("purchase", 0)
#     wishlist    = counts.get("wishlist_add", 0)

#     return {
#         "total_sessions":         counts.get("session_start", 0),
#         "total_views":            views,
#         "total_add_to_cart":      add_to_cart,
#         "total_checkouts":        checkout,
#         "total_purchases":        purchase,
#         "total_wishlist":         wishlist,
#         "cart_conversion_rate":   round(add_to_cart / views * 100, 1) if views else 0,
#         "checkout_conversion":    round(checkout / add_to_cart * 100, 1) if add_to_cart else 0,
#         "purchase_conversion":    round(purchase / checkout * 100, 1) if checkout else 0,
#         "cart_abandonment_rate":  round((1 - purchase / add_to_cart) * 100, 1) if add_to_cart else 0,
#     }



import os
import pandas as pd
import numpy as np
from config.settings import DATA_PATH, DATA_MODE

# ── Raw loaders ────────────────────────────────────────────────────────────

def load_products() -> pd.DataFrame:
    if DATA_MODE == "dynamodb":
        from utils.dynamodb import scan_products
        df = pd.DataFrame(scan_products())
    else:
        df = pd.read_excel(DATA_PATH, sheet_name="product_catalogue")

    df["price"]         = pd.to_numeric(df["price"],         errors="coerce").fillna(0)
    df["special_price"] = pd.to_numeric(df["special_price"], errors="coerce").fillna(0)
    df["cost_price"]    = pd.to_numeric(df["cost_price"],    errors="coerce").fillna(0)
    df["quantity"]      = pd.to_numeric(df["quantity"],      errors="coerce").fillna(0)
    return df


def load_orders() -> pd.DataFrame:
    if DATA_MODE == "dynamodb":
        from utils.dynamodb import scan_orders
        df = pd.DataFrame(scan_orders())
    else:
        df = pd.read_excel(DATA_PATH, sheet_name="orders")
    df["order_date"]      = pd.to_datetime(df["order_date"],     errors="coerce")
    df["grand_total"]     = pd.to_numeric(df["grand_total"],     errors="coerce").fillna(0)
    df["net_revenue"]     = pd.to_numeric(df["net_revenue"],     errors="coerce").fillna(0)
    df["discount_amount"] = pd.to_numeric(df["discount_amount"], errors="coerce").fillna(0)
    return df


def load_order_items() -> pd.DataFrame:
    if DATA_MODE == "dynamodb":
        from utils.dynamodb import scan_orders
        rows = scan_orders()
        df = pd.DataFrame(rows)
        # Map DynamoDB order fields to order_items format
        if not df.empty:
            if "qty_ordered" not in df.columns:
                df["qty_ordered"] = df.get("grand_total", pd.Series(1, index=df.index))
            if "row_total" not in df.columns:
                df["row_total"] = df.get("net_revenue", pd.Series(0, index=df.index))
            if "price" not in df.columns:
                df["price"] = df.get("grand_total", pd.Series(0, index=df.index))
            if "order_state" not in df.columns:
                df["order_state"] = df.get("state", "complete")
            if "product_id" not in df.columns:
                df["product_id"] = "unknown"
    else:
        df = pd.read_excel(DATA_PATH, sheet_name="order_items")
    df["order_date"]  = pd.to_datetime(df["order_date"],  errors="coerce")
    df["qty_ordered"] = pd.to_numeric(df["qty_ordered"],  errors="coerce").fillna(0)
    df["price"]       = pd.to_numeric(df["price"],        errors="coerce").fillna(0)
    df["row_total"]   = pd.to_numeric(df["row_total"],    errors="coerce").fillna(0)
    return df[df["order_state"] == "complete"]


def load_customers() -> pd.DataFrame:
    if DATA_MODE == "dynamodb":
        return pd.DataFrame()
    df = pd.read_excel(DATA_PATH, sheet_name="customers")
    df["customer_created_date"] = pd.to_datetime(df["customer_created_date"], errors="coerce")
    return df


def load_bq_events() -> pd.DataFrame:
    if DATA_MODE == "dynamodb":
        return pd.DataFrame()
    df = pd.read_excel(DATA_PATH, sheet_name="bq_events")
    df["event_date"]         = pd.to_datetime(df["event_date"], errors="coerce")
    df["event_value_in_usd"] = pd.to_numeric(df["event_value_in_usd"], errors="coerce").fillna(0)
    return df


def load_store_performance() -> pd.DataFrame:
    if DATA_MODE == "dynamodb":
        try:
            from utils.dynamodb import scan_store_performance
            df = pd.DataFrame(scan_store_performance())
        except:
            return pd.DataFrame()
    else:
        df = pd.read_excel(DATA_PATH, sheet_name="store_performance")
    df["sell_through_rate"]  = pd.to_numeric(df["sell_through_rate"],  errors="coerce").fillna(0)
    df["avg_discount_depth"] = pd.to_numeric(df["avg_discount_depth"], errors="coerce").fillna(0)
    df["monthly_revenue"]    = pd.to_numeric(df["monthly_revenue"],    errors="coerce").fillna(0)
    return df


def load_store_monthly_trends() -> pd.DataFrame:
    if DATA_MODE == "dynamodb":
        try:
            from utils.dynamodb import scan_monthly_revenue
            rows = scan_monthly_revenue()
            df = pd.DataFrame(rows) if rows else pd.DataFrame()
        except:
            return pd.DataFrame()
    else:
        df = pd.read_excel(DATA_PATH, sheet_name="store_monthly_trends")
    df["revenue"]           = pd.to_numeric(df["revenue"],           errors="coerce").fillna(0)
    df["sell_through_rate"] = pd.to_numeric(df["sell_through_rate"], errors="coerce").fillna(0)
    return df


def load_store_category_breakdown() -> pd.DataFrame:
    if DATA_MODE == "dynamodb":
        return pd.DataFrame()
    return pd.read_excel(DATA_PATH, sheet_name="store_category_breakdown")


# ── Computed metrics ───────────────────────────────────────────────────────

_metrics_cache = {"data": None, "ts": 0}
METRICS_TTL = 600  # 10 min

def compute_sales_metrics() -> pd.DataFrame:
    import time
    now = time.time()
    if _metrics_cache["data"] is not None and now - _metrics_cache["ts"] < METRICS_TTL:
        return _metrics_cache["data"]
    result = _compute_sales_metrics_inner()
    _metrics_cache["data"] = result
    _metrics_cache["ts"] = now
    return result

def _compute_sales_metrics_inner() -> pd.DataFrame:
    products    = load_products()
    order_items = load_order_items()
    orders      = load_orders()

    sold = (
        order_items
        .groupby("product_id")
        .agg(
            total_qty_sold=("qty_ordered", "sum"),
            total_revenue =("row_total",   "sum"),
            order_count   =("order_id",    "nunique"),
        )
        .reset_index()
    )

    df = products.merge(sold, on="product_id", how="left")
    df["total_qty_sold"] = df["total_qty_sold"].fillna(0)
    df["total_revenue"]  = df["total_revenue"].fillna(0)
    df["order_count"]    = df["order_count"].fillna(0)

    days = max((orders["order_date"].max() - orders["order_date"].min()).days, 1)
    df["sales_velocity"] = df["total_qty_sold"] / days

    df["sell_through_rate"] = np.where(
        (df["total_qty_sold"] + df["quantity"]) > 0,
        df["total_qty_sold"] / (df["total_qty_sold"] + df["quantity"]) * 100,
        0,
    ).round(1)

    df["days_of_stock"] = np.where(
        df["sales_velocity"] > 0,
        df["quantity"] / df["sales_velocity"],
        9999,
    ).round(0)

    df["is_dead_inventory"] = df["days_of_stock"] > 180

    df = df.sort_values("total_revenue", ascending=False).reset_index(drop=True)
    df["revenue_cumsum"] = df["total_revenue"].cumsum()
    total_rev = df["total_revenue"].sum()
    df["revenue_pct"] = df["revenue_cumsum"] / (total_rev + 1e-9)
    df["abc_class"] = np.where(
        df["revenue_pct"] <= 0.10, "A",
        np.where(df["revenue_pct"] <= 0.50, "B", "C"),
    )

    df["clearance_risk"] = np.where(
        (df["quantity"] > 50) & (df["sales_velocity"] < 0.1), "HIGH",
        np.where(
            (df["quantity"] > 20) & (df["sales_velocity"] < 0.3), "MEDIUM", "LOW"
        ),
    )

    return df.drop(columns=["revenue_cumsum", "revenue_pct"])


def compute_elasticity_data() -> pd.DataFrame:
    items = load_order_items()
    if items.empty:
        return pd.DataFrame(columns=["product_id", "elasticity"])

    grp = (
        items.groupby(["product_id", "price"])["qty_ordered"]
        .sum()
        .reset_index()
    )

    results = []
    for pid, group in grp.groupby("product_id"):
        if len(group) < 2:
            results.append({"product_id": pid, "elasticity": -1.2})
            continue
        pct_price = group["price"].pct_change().dropna()
        pct_qty   = group["qty_ordered"].pct_change().dropna()
        valid     = pct_price.abs() > 0.001
        if valid.sum() == 0:
            results.append({"product_id": pid, "elasticity": -1.2})
            continue
        elasticity = float(np.clip((pct_qty[valid] / pct_price[valid]).mean(), -3.0, -0.3))
        results.append({"product_id": pid, "elasticity": elasticity})

    return pd.DataFrame(results)


def compute_event_metrics() -> dict:
    events = load_bq_events()
    if events.empty:
        return {}

    counts      = events["event_name"].value_counts().to_dict()
    views       = counts.get("view_item", 1)
    add_to_cart = counts.get("add_to_cart", 0)
    checkout    = counts.get("begin_checkout", 0)
    purchase    = counts.get("purchase", 0)

    return {
        "total_sessions":        counts.get("session_start", 0),
        "total_views":           views,
        "total_add_to_cart":     add_to_cart,
        "total_checkouts":       checkout,
        "total_purchases":       purchase,
        "total_wishlist":        counts.get("wishlist_add", 0),
        "cart_conversion_rate":  round(add_to_cart / views * 100, 1)          if views       else 0,
        "checkout_conversion":   round(checkout / add_to_cart * 100, 1)       if add_to_cart else 0,
        "purchase_conversion":   round(purchase / checkout * 100, 1)          if checkout    else 0,
        "cart_abandonment_rate": round((1 - purchase / add_to_cart) * 100, 1) if add_to_cart else 0,
    }