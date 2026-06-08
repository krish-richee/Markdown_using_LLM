# import os
# from dotenv import load_dotenv

# load_dotenv()

# # ── Data source ────────────────────────────────────────────────────────────
# BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# DATA_PATH = os.path.join(BASE_DIR, "data", "synthetic_retail_data.xlsx")

# # ── Mode flag ──────────────────────────────────────────────────────────────
# # "local"    → reads from Excel (POC / dev)
# # "dynamodb" → reads from AWS DynamoDB (production)
# DATA_MODE = os.getenv("DATA_MODE", "local")

# # ── AWS ────────────────────────────────────────────────────────────────────
# AWS_REGION     = os.getenv("AWS_REGION", "ap-south-1")
# DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "retailai_recommendations")
# S3_BUCKET      = os.getenv("S3_BUCKET", "retailai-data")

# # ── Anthropic (optional) ───────────────────────────────────────────────────
# ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
# LLM_MODEL         = "claude-haiku-4-5-20251001"
# LLM_MAX_TOKENS    = 1024

# # ── Groq ───────────────────────────────────────────────────────────────────
# GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")
# GROQ_MODEL      = "llama-3.1-8b-instant"
# GROQ_MAX_TOKENS = 1024

# # ── Agent settings ─────────────────────────────────────────────────────────
# MAX_CRITIC_RETRIES = 3       # how many times critic can reject before forcing pass
# MIN_CONFIDENCE     = 0.60    # coordinator rejects agent output below this

# # ── Markdown rules ─────────────────────────────────────────────────────────
# MARKDOWN_RULES = {
#     "base_by_risk":     {"HIGH": 30, "MEDIUM": 15, "LOW": 5},
#     "abc_multiplier":   {"A": 0.50, "B": 1.00, "C": 1.30},
#     "max_markdown_pct": 60,
#     "min_margin_floor": 1.10,    # new_price >= cost_price × 1.10
# }

# # ── Notification ───────────────────────────────────────────────────────────
# SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
# SNS_TOPIC_ARN     = os.getenv("SNS_TOPIC_ARN", "")







import os
from dotenv import load_dotenv

load_dotenv()

# ── Data source ────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "synthetic_retail_data.xlsx")

# ── Mode flag ──────────────────────────────────────────────────────────────
# "local"    → reads from Excel (POC / dev)
# "dynamodb" → reads from AWS DynamoDB (production)
DATA_MODE = os.getenv("DATA_MODE", "local")

# ── AWS ────────────────────────────────────────────────────────────────────
AWS_REGION     = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET      = os.getenv("S3_BUCKET", "retailai-data")

# ── DynamoDB tables ────────────────────────────────────────────────────────
DYNAMODB_TABLE_PRODUCTS  = os.getenv("DYNAMODB_TABLE_PRODUCTS",  "retailai_products")
DYNAMODB_TABLE_ORDERS    = os.getenv("DYNAMODB_TABLE_ORDERS",    "retailai_orders")
DYNAMODB_TABLE_DECISIONS = os.getenv("DYNAMODB_TABLE_DECISIONS", "retailai_decisions")

# ── Anthropic (optional) ───────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL         = "claude-haiku-4-5-20251001"
LLM_MAX_TOKENS    = 1024

# ── Groq ───────────────────────────────────────────────────────────────────
GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL      = "llama-3.1-8b-instant"
GROQ_MAX_TOKENS = 1024

# ── Agent settings ─────────────────────────────────────────────────────────
MAX_CRITIC_RETRIES = 3
MIN_CONFIDENCE     = 0.60

# ── Markdown rules ─────────────────────────────────────────────────────────
MARKDOWN_RULES = {
    "base_by_risk":     {"HIGH": 30, "MEDIUM": 15, "LOW": 5},
    "abc_multiplier":   {"A": 0.50, "B": 1.00, "C": 1.30},
    "max_markdown_pct": 60,
    "min_margin_floor": 1.10,
}

# ── Notification ───────────────────────────────────────────────────────────
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SNS_TOPIC_ARN     = os.getenv("SNS_TOPIC_ARN", "")