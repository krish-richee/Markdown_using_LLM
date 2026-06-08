import os
import json
from groq import Groq
from dotenv import load_dotenv
from agents.base_agent import AgentOutput, AgentStatus
from config.settings import GROQ_API_KEY, GROQ_MODEL, GROQ_MAX_TOKENS, MARKDOWN_RULES

load_dotenv()


class PricingAgent:
    """
    Prompt-based pricing agent.
    Sends product data to Groq LLM and asks it to
    recommend a markdown percentage with reasoning.
    """

    name = "PricingAgent"

    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)

    def analyze(self, product: dict) -> AgentOutput:
        try:
            # ── Build prompt ───────────────────────────────────────────
            prompt = f"""You are a senior retail pricing expert for an Indian fashion brand.

Analyze this product and recommend the best markdown percentage.

PRODUCT DATA:
- Name:            {product.get('product_name', 'Unknown')}
- Category:        {product.get('main_category', 'Unknown')}
- Brand:           {product.get('brand', 'Unknown')}
- Current Price:   ₹{product.get('price', 0):,.2f}
- Cost Price:      ₹{product.get('cost_price', 0):,.2f}
- Special Price:   ₹{product.get('special_price', 0):,.2f}
- Current Margin:  {product.get('margin_pct', 0):.1f}%

INVENTORY & SALES SIGNALS:
- Stock Units:     {product.get('quantity', 0):.0f} units
- Days of Stock:   {product.get('days_of_stock', 0):.0f} days
- Sales Velocity:  {product.get('sales_velocity', 0):.3f} units/day
- Sell-Through:    {product.get('sell_through_rate', 0):.1f}%
- Dead Inventory:  {product.get('is_dead_inventory', False)}

CLASSIFICATION:
- ABC Class:       {product.get('abc_class', 'B')}
- Clearance Risk:  {product.get('clearance_risk', 'MEDIUM')}
- Season:          {product.get('season', 'All Season')}
- Gender:          {product.get('gender', 'Unisex')}

MARKDOWN RULES:
- Max markdown allowed:  {MARKDOWN_RULES['max_markdown_pct']}%
- Min margin floor:      cost_price × {MARKDOWN_RULES['min_margin_floor']} 
  (minimum sell price = ₹{product.get('cost_price', 0) * MARKDOWN_RULES['min_margin_floor']:,.2f})
- ABC A products:        protect margin, conservative markdown
- ABC C products:        aggressive clearance allowed
- HIGH risk:             prioritise clearing stock over margin

YOUR TASK:
1. Recommend a markdown percentage (0-{MARKDOWN_RULES['max_markdown_pct']}%)
2. Calculate the new price
3. Explain your reasoning in 2-3 sentences
4. Give a confidence score (0.0-1.0)

IMPORTANT: Respond ONLY in this exact JSON format, no other text:
{{
    "markdown_pct": <number>,
    "new_price": <number>,
    "reasoning": "<2-3 sentence explanation>",
    "confidence": <0.0-1.0>,
    "risk_assessment": "<LOW|MEDIUM|HIGH>"
}}"""

            # ── Call Groq ──────────────────────────────────────────────
            response = self.client.chat.completions.create(
                model      = GROQ_MODEL,
                max_tokens = GROQ_MAX_TOKENS,
                messages   = [
                    {
                        "role": "system",
                        "content": (
                            "You are a retail pricing expert. "
                            "Always respond with valid JSON only. "
                            "No markdown, no explanation outside JSON."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature = 0.3,   # low temp = consistent decisions
            )

            raw = response.choices[0].message.content.strip()

            # ── Parse JSON response ────────────────────────────────────
            # strip markdown fences if model adds them
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            result = json.loads(raw)

            markdown_pct = float(result.get("markdown_pct", 15))
            new_price    = float(result.get("new_price",
                           product.get("price", 0) * (1 - markdown_pct / 100)))
            reasoning    = result.get("reasoning", "")
            confidence   = float(result.get("confidence", 0.7))
            risk         = result.get("risk_assessment", "MEDIUM")

            # ── Safety check — cost floor ──────────────────────────────
            cost_price     = float(product.get("cost_price", 0)) or float(product.get("price", 0)) * 0.55
            min_sell_price = cost_price * MARKDOWN_RULES["min_margin_floor"]
            floor_breached = new_price < min_sell_price

            if floor_breached:
                price        = float(product.get("price", 0))
                markdown_pct = round(max((price - min_sell_price) / price * 100, 0), 1)
                new_price    = price * (1 - markdown_pct / 100)
                reasoning   += f" ⚠️ Cost floor applied — markdown capped at {markdown_pct}%."

            return AgentOutput(
                agent_name     = self.name,
                recommendation = f"{markdown_pct}% markdown → ₹{new_price:.2f}",
                confidence     = confidence,
                reasoning      = reasoning,
                status         = AgentStatus.PASS,
                data           = {
                    "markdown_pct":   round(markdown_pct, 1),
                    "new_price":      round(new_price, 2),
                    "floor_breached": floor_breached,
                    "min_sell_price": round(min_sell_price, 2),
                    "risk":           risk,
                },
            )

        except json.JSONDecodeError as e:
            # LLM returned bad JSON — fallback to rule-based
            price          = float(product.get("price", 0))
            clearance_risk = product.get("clearance_risk", "MEDIUM")
            base           = MARKDOWN_RULES["base_by_risk"].get(clearance_risk, 15)
            new_price      = price * (1 - base / 100)
            return AgentOutput(
                agent_name     = self.name,
                recommendation = f"{base}% markdown → ₹{new_price:.2f} (fallback)",
                confidence     = 0.50,
                reasoning      = f"LLM JSON parse error — used rule fallback. Error: {e}",
                status         = AgentStatus.PASS,
                data           = {"markdown_pct": base, "new_price": round(new_price, 2)},
            )

        except Exception as e:
            return AgentOutput(
                agent_name     = self.name,
                recommendation = "0% markdown — error",
                confidence     = 0.0,
                reasoning      = f"Error: {e}",
                status         = AgentStatus.SKIP,
                data           = {},
            )