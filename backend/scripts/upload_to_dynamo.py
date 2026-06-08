"""
Run once to migrate Excel data to DynamoDB.
From your project root: python3 scripts/upload_to_dynamo.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATA_MODE"] = "local"

import pandas as pd
from decimal import Decimal, InvalidOperation
from config.settings import DATA_PATH
import boto3

db = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))

PRODUCTS_TABLE = os.getenv("DYNAMODB_TABLE_PRODUCTS", "retailai_products")

def _clean(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if v is None or (isinstance(v, float) and str(v) in ("nan", "inf", "-inf")):
            continue
        elif isinstance(v, float):
            try:
                out[k] = Decimal(str(round(v, 6)))
            except InvalidOperation:
                out[k] = Decimal("0")
        elif hasattr(v, "item"):
            out[k] = v.item()
        elif not isinstance(v, (int, str, bool, Decimal)):
            out[k] = str(v)
        else:
            out[k] = v
    return out

def batch_upload(table_name: str, df: pd.DataFrame, label: str):
    table = db.Table(table_name)
    total = len(df)
    done  = 0
    with table.batch_writer() as batch:
        for _, row in df.iterrows():
            batch.put_item(Item=_clean(row.to_dict()))
            done += 1
            if done % 500 == 0:
                print(f"  {done}/{total} {label} uploaded")
    print(f"  Done — {total} {label} uploaded")

# Products only — orders stay in Excel (80k rows, too large for free tier)
print("Uploading products...")
products = pd.read_excel(DATA_PATH, sheet_name="product_catalogue")
batch_upload(PRODUCTS_TABLE, products, "products")

print("\nAll done. Set DATA_MODE=dynamodb in .env and restart the server.")