# import os
# import boto3
# from decimal import Decimal, InvalidOperation
# from dotenv import load_dotenv

# load_dotenv()

# _db = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))

# def _table(env_key: str):
#     return _db.Table(os.getenv(env_key))

# def _clean(row: dict) -> dict:
#     cleaned = {}
#     for k, v in row.items():
#         if v is None:
#             continue
#         elif isinstance(v, float):
#             try:
#                 cleaned[k] = Decimal(str(round(v, 6)))
#             except InvalidOperation:
#                 cleaned[k] = Decimal("0")
#         elif isinstance(v, bool):
#             cleaned[k] = v
#         elif hasattr(v, 'item'):
#             cleaned[k] = v.item()
#         else:
#             cleaned[k] = str(v) if not isinstance(v, (int, str, bool, Decimal)) else v
#     return cleaned

# def put_product(row: dict):
#     _table("DYNAMODB_TABLE_PRODUCTS").put_item(Item=_clean(row))

# def scan_products() -> list:
#     t = _table("DYNAMODB_TABLE_PRODUCTS")
#     resp = t.scan()
#     items = resp.get("Items", [])
#     while "LastEvaluatedKey" in resp:
#         resp = t.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
#         items.extend(resp.get("Items", []))
#     return items

# def put_order(row: dict):
#     _table("DYNAMODB_TABLE_ORDERS").put_item(Item=_clean(row))

# def scan_orders() -> list:
#     t = _table("DYNAMODB_TABLE_ORDERS")
#     resp = t.scan()
#     items = resp.get("Items", [])
#     while "LastEvaluatedKey" in resp:
#         resp = t.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
#         items.extend(resp.get("Items", []))
#     return items

# def put_decision(row: dict):
#     _table("DYNAMODB_TABLE_DECISIONS").put_item(Item=_clean(row))

# def scan_decisions() -> list:
#     t = _table("DYNAMODB_TABLE_DECISIONS")
#     resp = t.scan()
#     items = resp.get("Items", [])
#     while "LastEvaluatedKey" in resp:
#         resp = t.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
#         items.extend(resp.get("Items", []))
#     return items



# import os
# import time
# import boto3
# from decimal import Decimal, InvalidOperation
# from dotenv import load_dotenv

# load_dotenv()

# _db = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))

# # ── Simple in-memory cache ─────────────────────────────────────────────────
# _cache = {}
# CACHE_TTL = 600  # 10 minutes

# def _get_cache(key):
#     if key in _cache:
#         data, ts = _cache[key]
#         if time.time() - ts < CACHE_TTL:
#             print(f"[cache hit] {key}")
#             return data
#     return None

# def _set_cache(key, data):
#     _cache[key] = (data, time.time())

# # ── Helpers ────────────────────────────────────────────────────────────────
# def _table(env_key: str):
#     return _db.Table(os.getenv(env_key))

# def _clean(row: dict) -> dict:
#     out = {}
#     for k, v in row.items():
#         if v is None:
#             continue
#         if isinstance(v, float):
#             if str(v) in ("nan", "inf", "-inf"):
#                 continue
#             try:
#                 out[k] = Decimal(str(round(v, 6)))
#             except InvalidOperation:
#                 out[k] = Decimal("0")
#         elif hasattr(v, "item"):
#             out[k] = v.item()
#         elif isinstance(v, (int, str, bool, Decimal)):
#             out[k] = v
#         else:
#             out[k] = str(v)
#     return out

# def _scan_all(env_key: str) -> list:
#     t     = _table(env_key)
#     resp  = t.scan()
#     items = resp.get("Items", [])
#     while "LastEvaluatedKey" in resp:
#         resp = t.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
#         items.extend(resp.get("Items", []))
#     return items

# # ── Public API ─────────────────────────────────────────────────────────────
# def scan_products() -> list:
#     cached = _get_cache("products")
#     if cached is not None:
#         return cached
#     print("[dynamo] scanning products...")
#     items = _scan_all("DYNAMODB_TABLE_PRODUCTS")
#     _set_cache("products", items)
#     print(f"[dynamo] {len(items)} products loaded")
#     return items

# def scan_orders() -> list:
#     cached = _get_cache("orders")
#     if cached is not None:
#         return cached
#     print("[dynamo] scanning orders...")
#     items = _scan_all("DYNAMODB_TABLE_ORDERS")
#     _set_cache("orders", items)
#     print(f"[dynamo] {len(items)} orders loaded")
#     return items

# def scan_decisions() -> list:
#     cached = _get_cache("decisions")
#     if cached is not None:
#         return cached
#     items = _scan_all("DYNAMODB_TABLE_DECISIONS")
#     _set_cache("decisions", items)
#     return items

# def put_product(row: dict):
#     _table("DYNAMODB_TABLE_PRODUCTS").put_item(Item=_clean(row))
#     _cache.pop("products", None)  # invalidate cache

# def put_order(row: dict):
#     _table("DYNAMODB_TABLE_ORDERS").put_item(Item=_clean(row))
#     _cache.pop("orders", None)

# def put_decision(row: dict):
#     _table("DYNAMODB_TABLE_DECISIONS").put_item(Item=_clean(row))
#     _cache.pop("decisions", None)











import os
import time
import boto3
from decimal import Decimal, InvalidOperation
from dotenv import load_dotenv

load_dotenv()

_db = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))

# ── Simple in-memory cache ─────────────────────────────────────────────────
_cache = {}
CACHE_TTL = 600  # 10 minutes

def _get_cache(key):
    if key in _cache:
        data, ts = _cache[key]
        if time.time() - ts < CACHE_TTL:
            print(f"[cache hit] {key}")
            return data
    return None

def _set_cache(key, data):
    _cache[key] = (data, time.time())

# ── Helpers ────────────────────────────────────────────────────────────────
def _table(env_key: str):
    return _db.Table(os.getenv(env_key))

def _clean(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if v is None:
            continue
        if isinstance(v, float):
            if str(v) in ("nan", "inf", "-inf"):
                continue
            try:
                out[k] = Decimal(str(round(v, 6)))
            except InvalidOperation:
                out[k] = Decimal("0")
        elif hasattr(v, "item"):
            out[k] = v.item()
        elif isinstance(v, (int, str, bool, Decimal)):
            out[k] = v
        else:
            out[k] = str(v)
    return out

def _scan_all(env_key: str) -> list:
    t     = _table(env_key)
    resp  = t.scan()
    items = resp.get("Items", [])
    while "LastEvaluatedKey" in resp:
        resp = t.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
        items.extend(resp.get("Items", []))
    return items

# ── Public API ─────────────────────────────────────────────────────────────
def scan_products() -> list:
    cached = _get_cache("products")
    if cached is not None:
        return cached
    print("[dynamo] scanning products...")
    items = _scan_all("DYNAMODB_TABLE_PRODUCTS")
    _set_cache("products", items)
    print(f"[dynamo] {len(items)} products loaded")
    return items

def scan_orders() -> list:
    cached = _get_cache("orders")
    if cached is not None:
        return cached
    print("[dynamo] scanning orders...")
    items = _scan_all("DYNAMODB_TABLE_ORDERS")
    _set_cache("orders", items)
    print(f"[dynamo] {len(items)} orders loaded")
    return items

def scan_decisions() -> list:
    cached = _get_cache("decisions")
    if cached is not None:
        return cached
    items = _scan_all("DYNAMODB_TABLE_DECISIONS")
    _set_cache("decisions", items)
    return items

def put_product(row: dict):
    _table("DYNAMODB_TABLE_PRODUCTS").put_item(Item=_clean(row))
    _cache.pop("products", None)  # invalidate cache

def put_order(row: dict):
    _table("DYNAMODB_TABLE_ORDERS").put_item(Item=_clean(row))
    _cache.pop("orders", None)

def put_decision(row: dict):
    _table("DYNAMODB_TABLE_DECISIONS").put_item(Item=_clean(row))
    _cache.pop("decisions", None)

def scan_monthly_revenue() -> list:
    cached = _get_cache("monthly_revenue")
    if cached is not None:
        return cached
    t     = _db.Table("retailai_monthly_revenue")
    resp  = t.scan()
    items = resp.get("Items", [])
    while "LastEvaluatedKey" in resp:
        resp = t.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
        items.extend(resp.get("Items", []))
    _set_cache("monthly_revenue", items)
    return items