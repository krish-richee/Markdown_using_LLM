"""
Full pipeline test — one product through all agents
with critic retry loop.
"""
from agents.pricing_agent import PricingAgent
from agents.inventory_agent import InventoryAgent
from agents.demand_agent import DemandAgent
from agents.promotion_agent import PromotionAgent
from agents.behavior_agent import BehaviorAgent
from agents.competitor_agent import CompetitorAgent
from agents.coordinator import CoordinatorAgent
from agents.critic_agent import CriticAgent
from agents.notification_agent import NotificationAgent
from agents.base_agent import AgentStatus
from config.settings import MAX_CRITIC_RETRIES
from utils.data_loader import compute_sales_metrics, compute_elasticity_data, compute_event_metrics

print("🚀 RetailAI — Full Pipeline Test\n")

# ── Load real product from data ────────────────────────────────────────────
print("📦 Loading data...")
metrics       = compute_sales_metrics()
elasticity_df = compute_elasticity_data()
event_metrics = compute_event_metrics()

# Pick a HIGH risk product for interesting results
high_risk = metrics[metrics["clearance_risk"] == "HIGH"]
row       = high_risk.iloc[0]

# Get elasticity for this product
elast_row = elasticity_df[elasticity_df["product_id"] == row["product_id"]]
elasticity = float(elast_row["elasticity"].mean()) if not elast_row.empty else -1.2

product = row.to_dict()
product["elasticity"]              = elasticity
product["recommended_markdown_pct"]= 20
product["forecast_days"]           = 30

print(f"\n🛍️  Product: {product['product_name']}")
print(f"   Category: {product['main_category']}")
print(f"   Price:    ₹{product['price']:,.2f}")
print(f"   Risk:     {product['clearance_risk']}")
print(f"   ABC:      {product['abc_class']}")
print(f"   DOS:      {product['days_of_stock']:.0f} days")
print(f"   Stock:    {product['quantity']:.0f} units")

# ── Run all agents ─────────────────────────────────────────────────────────
print("\n🤖 Running agents...")
agent_outputs = {
    "PricingAgent":    PricingAgent().analyze(product),
    "InventoryAgent":  InventoryAgent().analyze(product),
    "DemandAgent":     DemandAgent().analyze(product),
    "PromotionAgent":  PromotionAgent().analyze(product),
    "BehaviorAgent":   BehaviorAgent().analyze(product, event_metrics),
    "CompetitorAgent": CompetitorAgent().analyze(product),
}

print("\n📋 Agent outputs:")
for name, out in agent_outputs.items():
    print(f"  {name:<20} | conf={out.confidence:.2f} | {out.recommendation[:60]}")

# ── Coordinator + Critic retry loop ───────────────────────────────────────
print("\n🧠 Running coordinator + critic loop...")
coordinator = CoordinatorAgent()
critic      = CriticAgent()
notifier    = NotificationAgent()

decision     = None
retry_count  = 0
critic_feedback = ""

while retry_count <= MAX_CRITIC_RETRIES:
    print(f"\n  🔄 Attempt {retry_count + 1}/{MAX_CRITIC_RETRIES + 1}")

    decision = coordinator.synthesise(
        product,
        agent_outputs,
        retry_count    = retry_count,
        critic_feedback= critic_feedback,
    )

    print(f"  📊 Coordinator: {decision.recommended_markdown_pct}% → ₹{decision.final_price:.2f} | {decision.health_badge}")

    verdict = critic.review(product, decision)

    if verdict.status == AgentStatus.PASS:
        print(f"  ✅ Critic: PASS — {verdict.reason[:80]}")
        break
    else:
        print(f"  ❌ Critic: REJECT — {verdict.reason[:80]}")
        critic_feedback = verdict.reason
        retry_count    += 1

        if retry_count > MAX_CRITIC_RETRIES:
            print(f"  ⚠️  Max retries reached — forcing PASS")
            decision.critic_verdict.status = AgentStatus.PASS
            break

# ── Notifications ──────────────────────────────────────────────────────────
print("\n📣 Sending notifications...")
notifications = notifier.notify(product, decision)

# ── Final summary ──────────────────────────────────────────────────────────
print("\n" + "="*60)
print("✅ FINAL DECISION")
print("="*60)
print(f"  Product:   {decision.product_name}")
print(f"  Markdown:  {decision.recommended_markdown_pct}%")
print(f"  New Price: ₹{decision.final_price:.2f}")
print(f"  Health:    {decision.health_badge}")
print(f"  Promo:     {decision.promotion_type}")
print(f"  Retries:   {retry_count}")
print(f"  Alerts:    {notifications['alerts_sent']}")
print(f"\n  Reasoning: {decision.coordinator_reasoning}")
print("="*60)
