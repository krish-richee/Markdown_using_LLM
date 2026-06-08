import json
from datetime import datetime
from typing import Dict
from groq import Groq
from dotenv import load_dotenv
from agents.base_agent import AgentOutput, AgentStatus, CriticVerdict, FinalDecision
from config.settings import GROQ_API_KEY, GROQ_MODEL, GROQ_MAX_TOKENS, MARKDOWN_RULES

load_dotenv()


class CoordinatorAgent:
    """
    Prompt-based coordinator.
    Receives all agent outputs and sends one
    comprehensive prompt to Groq to make the
    final markdown decision.
    """

    name = "CoordinatorAgent"

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

    def synthesise(
        self,
        product: dict,
        agent_outputs: Dict[str, AgentOutput],
        retry_count: int = 0,
        critic_feedback: str = "",
    ) -> FinalDecision:

        price      = float(product.get("price", 0))
        cost_price = float(product.get("cost_price", 0)) or price * 0.55
        min_price  = round(cost_price * MARKDOWN_RULES["min_margin_floor"], 2)
        max_mkd    = MARKDOWN_RULES["max_markdown_pct"]

        # Build agent summary for prompt
        agent_summary = ""
        for agent_name, output in agent_outputs.items():
            if output.status == AgentStatus.PASS:
                agent_summary += f"""
{agent_name}:
  Recommendation: {output.recommendation}
  Confidence: {output.confidence}
  Reasoning: {output.reasoning}
"""

        try:
            prompt = f"""You are the head of merchandising for an Indian fashion retail brand.

You have received reports from 6 specialist agents about this product.
Your job is to synthesise all reports and make ONE final markdown decision.

PRODUCT:
- Name:          {product.get('product_name', 'Unknown')}
- Category:      {product.get('main_category', 'Unknown')}
- Brand:         {product.get('brand', 'Unknown')}
- Current Price: Rs {price:.2f}
- Cost Price:    Rs {cost_price:.2f}
- Min Sell Price (10% margin floor): Rs {min_price:.2f}
- Max Markdown Allowed: {max_mkd}%
- ABC Class:     {product.get('abc_class', 'B')}
- Clearance Risk: {product.get('clearance_risk', 'MEDIUM')}
- Stock:         {product.get('quantity', 0):.0f} units
- Days of Stock: {product.get('days_of_stock', 0):.0f} days
- Season:        {product.get('season', 'All Season')}

AGENT REPORTS:
{agent_summary}

{f"CRITIC FEEDBACK (retry #{retry_count}): {critic_feedback}" if retry_count > 0 else ""}

YOUR TASK:
1. Read all agent reports carefully
2. Decide the final markdown percentage (0-{max_mkd}%)
3. Make sure new price is above Rs {min_price:.2f} (cost floor)
4. Choose promotion type: flash_sale / bundle / seasonal / clearance / loyalty / none
5. Write clear business reasoning in 3-4 sentences
6. Give overall confidence (0.0-1.0)
7. Assign health badge based on business outcome

Health badge rules:
- Green: revenue up AND margin impact less than -5pp
- Yellow: revenue up BUT margin impact more than -10pp OR uncertain
- Red: revenue declines at this discount level

Return ONLY this JSON:
{{"final_markdown_pct": <number>, "final_price": <number>, "health_badge": "<Green Healthy|Yellow Caution|Red Not Recommended>", "promotion_type": "<flash_sale|bundle|seasonal|clearance|loyalty|none>", "reasoning": "<3-4 sentence business explanation>", "confidence": <0.0-1.0>, "key_factor": "<the single most important reason for this decision>"}}"""

            response = self.client.chat.completions.create(
                model      = GROQ_MODEL,
                max_tokens = GROQ_MAX_TOKENS,
                messages   = [
                    {
                        "role": "system",
                        "content": (
                            "You are a head of merchandising. "
                            "Respond with a single valid JSON object only. "
                            "No extra text. No markdown. "
                            "Start with { and end with }."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature = 0.2,
            )

            raw    = response.choices[0].message.content
            raw    = self._clean_json(raw)
            result = json.loads(raw)

            markdown_pct = float(result.get("final_markdown_pct", 15))
            final_price  = float(result.get("final_price",
                           price * (1 - markdown_pct / 100)))
            health_badge = result.get("health_badge", "Yellow Caution")
            promo_type   = result.get("promotion_type", "none")
            reasoning    = result.get("reasoning", "")
            confidence   = float(result.get("confidence", 0.7))
            key_factor   = result.get("key_factor", "")

            # Safety — enforce cost floor
            if final_price < min_price:
                markdown_pct = round(max((price - min_price) / price * 100, 0), 1)
                final_price  = price * (1 - markdown_pct / 100)
                reasoning   += f" Cost floor enforced — markdown capped at {markdown_pct}%."

            # Add emoji to health badge
            if "Green" in health_badge or "Healthy" in health_badge:
                health_badge = "🟢 Healthy — revenue up, margin acceptable"
            elif "Red" in health_badge or "Not" in health_badge:
                health_badge = "🔴 Not recommended — revenue declines"
            else:
                health_badge = "🟡 Caution — monitor margin erosion"

            return FinalDecision(
                product_id               = product.get("product_id", ""),
                product_name             = product.get("product_name", ""),
                recommended_markdown_pct = round(markdown_pct, 1),
                final_price              = round(final_price, 2),
                health_badge             = health_badge,
                coordinator_reasoning    = reasoning,
                critic_verdict           = CriticVerdict(
                    status      = AgentStatus.PASS,
                    reason      = "Pending critic review",
                    retry_count = retry_count,
                ),
                agent_outputs  = agent_outputs,
                promotion_type = promo_type,
                run_timestamp  = datetime.now().isoformat(),
            )

        except Exception as e:
            # Fallback — use pricing agent output
            pricing = agent_outputs.get("PricingAgent")
            mkd     = float(pricing.data.get("markdown_pct", 15)) if pricing else 15
            fp      = price * (1 - mkd / 100)
            return FinalDecision(
                product_id               = product.get("product_id", ""),
                product_name             = product.get("product_name", ""),
                recommended_markdown_pct = mkd,
                final_price              = round(fp, 2),
                health_badge             = "🟡 Caution — LLM fallback",
                coordinator_reasoning    = f"LLM error — used pricing agent fallback. Error: {e}",
                critic_verdict           = CriticVerdict(
                    status      = AgentStatus.PASS,
                    reason      = "Fallback",
                    retry_count = retry_count,
                ),
                agent_outputs  = agent_outputs,
                promotion_type = "none",
                run_timestamp  = datetime.now().isoformat(),
            )
