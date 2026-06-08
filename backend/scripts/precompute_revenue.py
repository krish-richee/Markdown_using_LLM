"""
Run once: python3 scripts/precompute_revenue.py
Reads orders from Excel, computes monthly revenue, uploads ~24 rows to DynamoDB.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATA_MODE"] = "local"

import pandas as pd
import boto3
from decimal import Decimal
from config.settings import DATA_PATH

db    = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
table = db.Table("retailai_monthly_revenue")

print("Reading orders from Excel...")
orders = pd.read_excel(DATA_PATH, sheet_name="orders")
orders["order_date"]  = pd.to_datetime(orders["order_date"],  errors="coerce")
orders["net_revenue"] = pd.to_numeric(orders["net_revenue"],  errors="coerce").fillna(0)
orders["grand_total"] = pd.to_numeric(orders["grand_total"],  errors="coerce").fillna(0)
orders["discount_amount"] = pd.to_numeric(orders["discount_amount"], errors="coerce").fillna(0)

orders["month"] = orders["order_date"].dt.strftime("%Y-%m")
orders["month_label"] = orders["order_date"].dt.strftime("%b %y")

monthly = (
    orders.groupby(["month", "month_label"])
    .agg(
        revenue      =("net_revenue",      "sum"),
        grand_total  =("grand_total",      "sum"),
        discount     =("discount_amount",  "sum"),
        order_count  =("order_id",         "count"),
    )
    .reset_index()
    .sort_values("month")
)

print(f"Uploading {len(monthly)} monthly rows...")
with table.batch_writer() as batch:
    for _, row in monthly.iterrows():
        batch.put_item(Item={
            "month":        row["month"],
            "month_label":  row["month_label"],
            "revenue":      Decimal(str(round(float(row["revenue"]), 2))),
            "grand_total":  Decimal(str(round(float(row["grand_total"]), 2))),
            "discount":     Decimal(str(round(float(row["discount"]), 2))),
            "order_count":  int(row["order_count"]),
        })

print(f"Done — {len(monthly)} months uploaded to retailai_monthly_revenue")
print("Months:", list(monthly["month_label"]))