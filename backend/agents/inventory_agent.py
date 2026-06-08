import json
from groq import Groq
from dotenv import load_dotenv
from agents.base_agent import AgentOutput, AgentStatus
from config.settings import GROQ_API_KEY, GROQ_MODEL, GROQ_MAX_TOKENS

load_dotenv()


class InventoryAgent:
    """
    Prompt-based inventory agent.
    Sends stock signals to Groq and asks it to
    assess urgency and recommend action.
    """

    name = "InventoryAgent"

    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)

    def analyze(self, product: dict) -> AgentOutput:
        try:
            prompt = f"""You are a senior retail inventory manager for an Indian fashion brand.

Analyze this product's inventory situation and recommend the urgency level and action.

PRODUCT DATA:
- Name:            {product.get('product_name', 'Unknown')}
- Category:        {product.get('main_category', 'Unknown')}
- Brand:           {product.get('brand', 'Unknown')}
- Season:          {product.get('season', 'All Season')}

INVENTORY SIGNALS:
- Current Stock:   {product.get('quantity', 0):.0f} units
- Days of Stock:   {product.get('days_of_stock', 0):.0f} days
- Sales Velocity:  {product.get('sales_velocity', 0):.3f} units/day
- Sell-Through:    {product.get('sell_through_rate', 0):.1f}%
- Dead Inventory:  {product.get('is_dead_inventory', False)}
- Clearance Risk:  {product.get('clearance_risk', 'MEDIUM')}
- ABC Class:       {product.get('abc_class', 'B')}

CONTEXT:
- Dead inventory = products not sold in 180+ days
- High DOS = stock will last too long at current velocity
- Overstock = quantity > 2× expected 30-day sales

YOUR TASK:
1. Assess the urgency level (CRITICAL / HIGH / MEDIUM / LOW)
2. Recommend a specific action
3. Explain your reasoning in 2-3 sentences
4. Give a confidence score (0.0-1.0)
5. Flag if this is overstock situation

IMPORTANT: Respond ONLY in this exact JSON format, no other text:
{{
    "urgency": "<CRITICAL|HIGH|MEDIUM|LOW>",
    "action": "<specific action to take>",
    "reasoning": "<2-3 sentence explanation>",
    "confidence": <0.0-1.0>,
    "is_overstock": <true|false>,
    "restock_recommended": <true|false>
}}"""

            response = self.client.chat.completions.create(
                model      = GROQ_MODEL,
                max_tokens = GROQ_MAX_TOKENS,
                messages   = [
                    {
                        "role": "system",
                        "content": (
                            "You are a retail inventory expert. "
                            "Always respond with valid JSON only. "
                            "No markdown, no explanation outside JSON."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature = 0.3,
            )

            raw = response.choices[0].message.content.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            result = json.loads(raw)

            urgency    = result.get("urgency", "MEDIUM")
            action     = result.get("action", "Monitor stock levels")
            reasoning  = result.get("reasoning", "")
            confidence = float(result.get("confidence", 0.7))
            is_overstock       = bool(result.get("is_overstock", False))
            restock_recommended= bool(result.get("restock_recommended", False))

            return AgentOutput(
                agent_name     = self.name,
                recommendation = f"{urgency} urgency — {action}",
                confidence     = confidence,
                reasoning      = reasoning,
                status         = AgentStatus.PASS,
                data           = {
                    "urgency":              urgency,
                    "action":               action,
                    "is_overstock":         is_overstock,
                    "restock_recommended":  restock_recommended,
                    "days_of_stock":        product.get("days_of_stock", 0),
                    "quantity":             product.get("quantity", 0),
                },
            )

        except json.JSONDecodeError as e:
            # fallback
            dos    = float(product.get("days_of_stock", 9999))
            urgency= "CRITICAL" if dos > 180 else "HIGH" if dos > 90 else "MEDIUM"
            return AgentOutput(
                agent_name     = self.name,
                recommendation = f"{urgency} urgency — rule fallback",
                confidence     = 0.50,
                reasoning      = f"LLM JSON parse error — used rule fallback. Error: {e}",
                status         = AgentStatus.PASS,
                data           = {"urgency": urgency},
            )

        except Exception as e:
            return AgentOutput(
                agent_name     = self.name,
                recommendation = "Unable to assess inventory",
                confidence     = 0.0,
                reasoning      = f"Error: {e}",
                status         = AgentStatus.SKIP,
                data           = {},
            )