import json
import os
from google import genai
from dotenv import load_dotenv
from agents.base_agent import AgentStatus, CriticVerdict, FinalDecision
from config.settings import GROQ_API_KEY, GROQ_MODEL, GROQ_MAX_TOKENS, MARKDOWN_RULES

load_dotenv()

class CriticAgent:
    name = "CriticAgent"

    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model  = "gemini-2.0-flash"

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

    def review(self, product: dict, decision: FinalDecision) -> CriticVerdict:
        price      = float(product.get("price", 0))
        cost_price = float(product.get("cost_price", 0)) or price * 0.55
        min_price  = round(cost_price * MARKDOWN_RULES["min_margin_floor"], 2)
        max_mkd    = MARKDOWN_RULES["max_markdown_pct"]

        agent_summary = ""
        for name, output in decision.agent_outputs.items():
            if output.status == AgentStatus.PASS:
                agent_summary += f"- {name}: {output.recommendation}\n"

        try:
            prompt = f"""You are a strict retail director. Respond with a single valid JSON object only. No extra text. No markdown. Start with {{ and end with }}.

You are reviewing a markdown decision made by your merchandising team.

PRODUCT:
- Name:           {product.get('product_name', 'Unknown')}
- Category:       {product.get('main_category', 'Unknown')}
- Brand:          {product.get('brand', 'Unknown')}
- Current Price:  Rs {price:.2f}
- Cost Price:     Rs {cost_price:.2f}
- Min Sell Price: Rs {min_price:.2f} (10% margin floor)
- ABC Class:      {product.get('abc_class', 'B')}
- Clearance Risk: {product.get('clearance_risk', 'MEDIUM')}
- Stock:          {product.get('quantity', 0):.0f} units
- Days of Stock:  {product.get('days_of_stock', 0):.0f} days

COORDINATOR DECISION:
- Recommended Markdown: {decision.recommended_markdown_pct}%
- Final Price:          Rs {decision.final_price:.2f}
- Health Badge:         {decision.health_badge}
- Promotion Type:       {decision.promotion_type}
- Reasoning:            {decision.coordinator_reasoning}

AGENT REPORTS:
{agent_summary}

VERDICT RULES:
- PASS if decision is sound and respects all business rules
- REJECT if decision violates cost floor or reasoning is illogical

Return ONLY this JSON:
{{"verdict": "<PASS|REJECT>", "reason": "<2-3 sentences>", "confidence": <0.0-1.0>, "suggested_fix": "<if REJECT what to change, else empty string>"}}"""

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            raw    = self._clean_json(response.text)
            result = json.loads(raw)

            verdict       = result.get("verdict", "PASS").upper()
            reason        = result.get("reason", "")
            confidence    = float(result.get("confidence", 0.7))
            suggested_fix = result.get("suggested_fix", "")
            status        = AgentStatus.PASS if verdict == "PASS" else AgentStatus.REJECT

            decision.critic_verdict = CriticVerdict(
                status      = status,
                reason      = reason,
                retry_count = decision.critic_verdict.retry_count,
            )

            print(f"  🔍 Critic verdict: {verdict} | {reason[:80]}...")

            return CriticVerdict(
                status      = status,
                reason      = reason + (f" Fix: {suggested_fix}" if suggested_fix else ""),
                retry_count = decision.critic_verdict.retry_count,
            )

        except Exception as e:
            verdict = CriticVerdict(
                status      = AgentStatus.PASS,
                reason      = f"Critic error — auto approved. Error: {e}",
                retry_count = decision.critic_verdict.retry_count,
            )
            decision.critic_verdict = verdict
            return verdict
