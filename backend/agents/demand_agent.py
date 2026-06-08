import json
import numpy as np
from groq import Groq
from dotenv import load_dotenv
from agents.base_agent import AgentOutput, AgentStatus
from config.settings import GROQ_API_KEY, GROQ_MODEL, GROQ_MAX_TOKENS

load_dotenv()


class DemandAgent:
    name = "DemandAgent"

    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)

    def _clean_json(self, raw: str) -> str:
        raw = raw.strip()
        if "```" in raw:
            parts = raw.split("```")
            for part in parts:
                if "{" in part:
                    raw = part
                    break
        if raw.startswith("json"):
            raw = raw[4:]
        if "{" in raw and "}" in raw:
            raw = raw[raw.index("{"):raw.rindex("}")+1]
        return raw.strip()

    def analyze(self, product: dict) -> AgentOutput:
        price          = float(product.get("price", 0))
        sales_velocity = float(product.get("sales_velocity", 0))
        elasticity     = float(np.clip(product.get("elasticity", -1.2), -3.0, -0.3))
        markdown_pct   = float(product.get("recommended_markdown_pct", 15.0))
        forecast_days  = int(product.get("forecast_days", 30))
        quantity       = float(product.get("quantity", 0))
        new_price      = price * (1 - markdown_pct / 100)
        base_units     = sales_velocity * forecast_days
        base_revenue   = base_units * price

        try:
            prompt = f"""You are a retail demand forecasting expert for an Indian fashion brand.
Analyze this product and forecast demand impact of the proposed markdown.

Product: {product.get('product_name', 'Unknown')}
Category: {product.get('main_category', 'Unknown')}
Brand: {product.get('brand', 'Unknown')}
Season: {product.get('season', 'All Season')}
Gender: {product.get('gender', 'Unisex')}
Current Price: Rs {price:.2f}
Proposed Price: Rs {new_price:.2f}
Markdown: {markdown_pct}%
Price Elasticity: {elasticity:.2f}
Sales Velocity: {sales_velocity:.3f} units per day
Base Units in {forecast_days} days: {base_units:.1f}
Base Revenue: Rs {base_revenue:.2f}
Current Stock: {quantity:.0f} units
Sell Through: {product.get('sell_through_rate', 0):.1f}%
Clearance Risk: {product.get('clearance_risk', 'MEDIUM')}
ABC Class: {product.get('abc_class', 'B')}

Return a JSON object with these exact keys:
demand_uplift_pct, new_units, incremental_units, new_revenue, revenue_change_pct, clearance_probability, demand_multiplier, reasoning, confidence

Example format:
{{"demand_uplift_pct": 30.0, "new_units": 31.2, "incremental_units": 7.2, "new_revenue": 24935.0, "revenue_change_pct": 4.0, "clearance_probability": 16.0, "demand_multiplier": 1.3, "reasoning": "explanation here", "confidence": 0.8}}"""

            response = self.client.chat.completions.create(
                model    = GROQ_MODEL,
                max_tokens = GROQ_MAX_TOKENS,
                messages = [
                    {
                        "role": "system",
                        "content": "You are a retail demand expert. Respond with a single valid JSON object only. No extra text. No markdown. Start with { end with }."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature = 0.1,
            )

            raw    = response.choices[0].message.content
            raw    = self._clean_json(raw)
            result = json.loads(raw)

            demand_uplift  = float(result.get("demand_uplift_pct", 0))
            new_units      = float(result.get("new_units", base_units))
            incremental    = float(result.get("incremental_units", 0))
            new_revenue    = float(result.get("new_revenue", base_revenue))
            rev_change_pct = float(result.get("revenue_change_pct", 0))
            clearance_prob = float(result.get("clearance_probability", 0))
            multiplier     = float(result.get("demand_multiplier", 1.0))
            reasoning      = result.get("reasoning", "")
            confidence     = float(result.get("confidence", 0.7))

            return AgentOutput(
                agent_name     = self.name,
                recommendation = (
                    f"+{demand_uplift:.1f}% demand uplift | "
                    f"{new_units:.0f} units in {forecast_days}d | "
                    f"Revenue {rev_change_pct:+.1f}%"
                ),
                confidence = confidence,
                reasoning  = reasoning,
                status     = AgentStatus.PASS,
                data       = {
                    "demand_uplift_pct":  demand_uplift,
                    "demand_multiplier":  multiplier,
                    "base_units":         round(base_units, 1),
                    "new_units":          round(new_units, 1),
                    "incremental_units":  round(incremental, 1),
                    "base_revenue":       round(base_revenue, 2),
                    "new_revenue":        round(new_revenue, 2),
                    "revenue_change_pct": round(rev_change_pct, 1),
                    "clearance_prob":     round(clearance_prob, 1),
                },
            )

        except Exception as e:
            demand_change = abs(elasticity) * (markdown_pct / 100)
            new_units_fb  = base_units * (1 + demand_change)
            new_rev_fb    = new_units_fb * new_price
            rev_chg_fb    = (new_rev_fb - base_revenue) / (base_revenue + 1e-9) * 100
            return AgentOutput(
                agent_name     = self.name,
                recommendation = f"+{demand_change*100:.1f}% uplift (fallback)",
                confidence     = 0.50,
                reasoning      = f"LLM error — formula fallback. Error: {e}",
                status         = AgentStatus.PASS,
                data           = {
                    "new_units":          round(new_units_fb, 1),
                    "revenue_change_pct": round(rev_chg_fb, 1),
                    "clearance_prob":     round(min(new_units_fb / (quantity + 1e-9) * 100, 98), 1),
                },
            )
