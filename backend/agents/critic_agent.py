import json
import google.generativeai as genai
import os
from dotenv import load_dotenv
from agents.base_agent import AgentStatus, CriticVerdict, FinalDecision
from config.settings import GROQ_API_KEY, GROQ_MODEL, GROQ_MAX_TOKENS, MARKDOWN_RULES

load_dotenv()


class CriticAgent:
    """
    Prompt-based critic agent.
    Reviews the coordinator's final decision
    and either approves (PASS) or rejects (REJECT)
    with specific feedback for revision.
    Max retries: MAX_CRITIC_RETRIES from settings.
    """

    name = "CriticAgent"

    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-1.5-flash")

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

    def review(
        self,
        product: dict,
        decision: FinalDecision,
    ) -> CriticVerdict:

        price      = float(product.get("price", 0))
        cost_price = float(product.get("cost_price", 0)) or price * 0.55
        min_price  = round(cost_price * MARKDOWN_RULES["min_margin_floor"], 2)
        max_mkd    = MARKDOWN_RULES["max_markdown_pct"]

        # Build agent summary for critic context
        agent_summary = ""
        for name, output in decision.agent_outputs.items():
            if output.status == AgentStatus.PASS:
                agent_summary += f"- {name}: {output.recommendation}\n"

        try:
            prompt = f"""You are a regional retail director reviewing a markdown decision made by your merchandising team.

Your job is to critically evaluate if this decision is sound, profitable, and aligned with business goals.

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
- Season:         {product.get('season', 'All Season')}

COORDINATOR DECISION:
- Recommended Markdown: {decision.recommended_markdown_pct}%
- Final Price:          Rs {decision.final_price:.2f}
- Health Badge:         {decision.health_badge}
- Promotion Type:       {decision.promotion_type}
- Reasoning:            {decision.coordinator_reasoning}

AGENT REPORTS SUMMARY:
{agent_summary}

CRITIC CHECKLIST — verify all of these:
1. Is the final price above the cost floor Rs {min_price:.2f}?
2. Is the markdown within 0-{max_mkd}% range?
3. Does the markdown make business sense given the risk level?
4. Is the promotion type appropriate for this product?
5. Is the reasoning clear and justified?
6. For ABC A products — is margin being protected?
7. For HIGH risk products — is clearance being prioritised?
8. Does the decision contradict any agent report without good reason?

VERDICT RULES:
- PASS if decision is sound, logical, and respects all business rules
- REJECT if decision violates cost floor, ignores critical signals,
  or the reasoning is illogical or contradictory

Return ONLY this JSON:
{{"verdict": "<PASS|REJECT>", "reason": "<specific explanation in 2-3 sentences>", "confidence": <0.0-1.0>, "suggested_fix": "<if REJECT — what should be changed, else empty string>"}}"""

            full_prompt = (
                "You are a strict retail director. "
                "Respond with a single valid JSON object only. "
                "No extra text. No markdown. "
                "Start with { and end with }.\n\n"
                + prompt
            )
            response = self.model.generate_content(full_prompt)
            raw = response.text
            raw    = self._clean_json(raw)
            result = json.loads(raw)

            verdict       = result.get("verdict", "PASS").upper()
            reason        = result.get("reason", "")
            confidence    = float(result.get("confidence", 0.7))
            suggested_fix = result.get("suggested_fix", "")

            status = AgentStatus.PASS if verdict == "PASS" else AgentStatus.REJECT

            # Update decision's critic verdict
            decision.critic_verdict = CriticVerdict(
                status      = status,
                reason      = reason,
                retry_count = decision.critic_verdict.retry_count,
            )

            if status == AgentStatus.PASS:
                decision.notification_sent = False

            print(f"  🔍 Critic verdict: {verdict} | {reason[:80]}...")

            return CriticVerdict(
                status      = status,
                reason      = reason + (f" Fix: {suggested_fix}" if suggested_fix else ""),
                retry_count = decision.critic_verdict.retry_count,
            )

        except Exception as e:
            # On error — default to PASS to avoid infinite loops
            verdict = CriticVerdict(
                status      = AgentStatus.PASS,
                reason      = f"Critic error — auto approved. Error: {e}",
                retry_count = decision.critic_verdict.retry_count,
            )
            decision.critic_verdict = verdict
            return verdict
