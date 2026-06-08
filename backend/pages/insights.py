import streamlit as st
import plotly.graph_objects as go
from utils.data_loader import compute_sales_metrics, compute_elasticity_data, compute_event_metrics
from agents.pricing_agent import PricingAgent
from agents.inventory_agent import InventoryAgent
from agents.demand_agent import DemandAgent
from agents.promotion_agent import PromotionAgent
from agents.behavior_agent import BehaviorAgent
from agents.competitor_agent import CompetitorAgent
from agents.coordinator import CoordinatorAgent
from agents.critic_agent import CriticAgent
from agents.base_agent import AgentStatus
from config.settings import MAX_CRITIC_RETRIES


def render():
    st.markdown("""
    <div class="page-header">
        <div class="page-title">🧠 Agent Insights</div>
        <div class="page-subtitle">
            Price IQ · Full agent pipeline transparency · See how AI decides
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Load data ──────────────────────────────────────────────────────────
    with st.spinner("Loading data..."):
        metrics       = compute_sales_metrics()
        elasticity_df = compute_elasticity_data()
        event_metrics = compute_event_metrics()

    # ── Product selector ───────────────────────────────────────────────────
    col1, col2 = st.columns([1, 2])
    with col1:
        cat_options  = ["All"] + sorted(
            metrics["main_category"].unique().tolist()
        )
        selected_cat = st.selectbox("Category", cat_options, key="ins_cat")

    filtered = metrics
    if selected_cat != "All":
        filtered = metrics[metrics["main_category"] == selected_cat]

    with col2:
        selected_name = st.selectbox(
            f"Product ({len(filtered)} available)",
            filtered["product_name"].tolist(),
            key="ins_prod",
        )

    if not selected_name:
        return

    row = filtered[filtered["product_name"] == selected_name].iloc[0]
    pid = row["product_id"]

    elast_row  = elasticity_df[elasticity_df["product_id"] == pid]
    elasticity = float(elast_row["elasticity"].mean()) \
                 if not elast_row.empty else -1.2

    product = row.to_dict()
    product["elasticity"]               = elasticity
    product["recommended_markdown_pct"] = 20
    product["forecast_days"]            = 30

    # ── Run button ─────────────────────────────────────────────────────────
    if st.button(
        "🔍 Run Full Agent Analysis",
        type="primary",
        use_container_width=False,
    ):
        with st.spinner("Running all agents..."):
            agent_outputs = {
                "PricingAgent":    PricingAgent().analyze(product),
                "InventoryAgent":  InventoryAgent().analyze(product),
                "DemandAgent":     DemandAgent().analyze(product),
                "PromotionAgent":  PromotionAgent().analyze(product),
                "BehaviorAgent":   BehaviorAgent().analyze(
                    product, event_metrics
                ),
                "CompetitorAgent": CompetitorAgent().analyze(product),
            }

            # Coordinator + Critic
            coordinator     = CoordinatorAgent()
            critic          = CriticAgent()
            retry_count     = 0
            critic_feedback = ""
            decision        = None

            while retry_count <= MAX_CRITIC_RETRIES:
                decision = coordinator.synthesise(
                    product, agent_outputs,
                    retry_count=retry_count,
                    critic_feedback=critic_feedback,
                )
                verdict = critic.review(product, decision)
                if verdict.status == AgentStatus.PASS:
                    break
                else:
                    critic_feedback = verdict.reason
                    retry_count    += 1
                    if retry_count > MAX_CRITIC_RETRIES:
                        decision.critic_verdict.status = AgentStatus.PASS
                        break

        st.session_state["ins_decision"]      = decision
        st.session_state["ins_agent_outputs"] = agent_outputs
        st.session_state["ins_retry_count"]   = retry_count
        st.session_state["ins_product"]       = product

    # ── Show insights ──────────────────────────────────────────────────────
    if "ins_decision" not in st.session_state:
        st.info("Select a product and click Run Full Agent Analysis.")
        return

    decision      = st.session_state["ins_decision"]
    agent_outputs = st.session_state["ins_agent_outputs"]
    retry_count   = st.session_state["ins_retry_count"]

    st.divider()

    # ── Final decision banner ──────────────────────────────────────────────
    health = decision.health_badge
    if "🟢" in health:
        badge_css = "health-green"
    elif "🔴" in health:
        badge_css = "health-red"
    else:
        badge_css = "health-yellow"

    st.markdown(f"""
    <div style="background:#ffffff; border:1px solid #e8eaed;
                border-radius:12px; padding:1.25rem 1.5rem;
                margin-bottom:1.5rem;">
        <div style="font-size:0.75rem;font-weight:600;
                    color:#6b7280;text-transform:uppercase;
                    letter-spacing:0.06em;margin-bottom:0.5rem;">
            FINAL DECISION
        </div>
        <div style="display:flex;align-items:center;gap:1.5rem;
                    flex-wrap:wrap;">
            <div>
                <div style="font-size:2rem;font-weight:700;
                            color:#1a1d23;">
                    {decision.recommended_markdown_pct}%
                </div>
                <div style="font-size:0.75rem;color:#6b7280;">
                    Markdown
                </div>
            </div>
            <div>
                <div style="font-size:2rem;font-weight:700;
                            color:#4f46e5;">
                    ₹{decision.final_price:,.2f}
                </div>
                <div style="font-size:0.75rem;color:#6b7280;">
                    New Price
                </div>
            </div>
            <div>
                <div style="font-size:1rem;font-weight:600;
                            color:#1a1d23;">
                    {decision.promotion_type.upper()}
                </div>
                <div style="font-size:0.75rem;color:#6b7280;">
                    Promotion
                </div>
            </div>
            <div>
                <span class="{badge_css}">{health}</span>
            </div>
            <div style="margin-left:auto;text-align:right;">
                <div style="font-size:0.8rem;color:#6b7280;">
                    Critic retries: <b>{retry_count}</b>
                </div>
                <div style="font-size:0.8rem;color:#6b7280;">
                    Verdict:
                    <b style="color:#16a34a;">
                        {decision.critic_verdict.status.value}
                    </b>
                </div>
            </div>
        </div>
        <div style="margin-top:0.75rem;font-size:0.85rem;
                    color:#4b5563;line-height:1.6;
                    border-top:1px solid #f3f4f6;
                    padding-top:0.75rem;">
            <b>Coordinator reasoning:</b>
            {decision.coordinator_reasoning}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Agent confidence chart ─────────────────────────────────────────────
    st.markdown("#### 📊 Agent Confidence Scores")
    agent_names  = list(agent_outputs.keys())
    confidences  = [agent_outputs[n].confidence for n in agent_names]

    fig = go.Figure(go.Bar(
        x            = confidences,
        y            = agent_names,
        orientation  = "h",
        marker_color = [
            "#16a34a" if c >= 0.8 else
            "#f59e0b" if c >= 0.6 else
            "#dc2626"
            for c in confidences
        ],
        text         = [f"{c:.0%}" for c in confidences],
        textposition = "outside",
    ))
    fig.update_layout(
        height       = 280,
        margin       = dict(l=0, r=60, t=10, b=0),
        plot_bgcolor = "rgba(0,0,0,0)",
        paper_bgcolor= "rgba(0,0,0,0)",
        xaxis        = dict(range=[0, 1.1], showticklabels=False,
                            showgrid=False),
        yaxis        = dict(tickfont=dict(size=11)),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Individual agent cards ─────────────────────────────────────────────
    st.markdown("#### 🤖 Agent Reports")

    agent_icons = {
        "PricingAgent":    "💰",
        "InventoryAgent":  "📦",
        "DemandAgent":     "📈",
        "PromotionAgent":  "🎯",
        "BehaviorAgent":   "👥",
        "CompetitorAgent": "🔍",
    }

    agent_types = {
        "PricingAgent":    "Groq LLM",
        "InventoryAgent":  "Groq LLM",
        "DemandAgent":     "Groq LLM",
        "PromotionAgent":  "Rule-based",
        "BehaviorAgent":   "Rule-based",
        "CompetitorAgent": "Tavily Search",
    }

    for name, out in agent_outputs.items():
        icon      = agent_icons.get(name, "🤖")
        atype     = agent_types.get(name, "")
        conf_pct  = int(out.confidence * 100)
        conf_color= (
            "#16a34a" if out.confidence >= 0.8 else
            "#f59e0b" if out.confidence >= 0.6 else
            "#dc2626"
        )
        status_color = (
            "#16a34a" if out.status == AgentStatus.PASS else "#dc2626"
        )

        with st.expander(
            f"{icon} {name} — {out.recommendation[:60]}...",
            expanded=name in ["PricingAgent", "CoordinatorAgent"],
        ):
            st.markdown(f"""
            <div style="display:flex;gap:1rem;
                        margin-bottom:0.75rem;flex-wrap:wrap;">
                <span style="background:#f3f4f6;color:#4b5563;
                             font-size:0.7rem;font-weight:600;
                             padding:2px 8px;border-radius:6px;">
                    {atype}
                </span>
                <span style="background:{status_color}20;
                             color:{status_color};
                             font-size:0.7rem;font-weight:600;
                             padding:2px 8px;border-radius:6px;">
                    {out.status.value}
                </span>
                <span style="background:{conf_color}20;
                             color:{conf_color};
                             font-size:0.7rem;font-weight:600;
                             padding:2px 8px;border-radius:6px;">
                    Confidence: {conf_pct}%
                </span>
            </div>
            <div style="font-size:0.9rem;font-weight:500;
                        color:#1a1d23;margin-bottom:0.5rem;">
                {out.recommendation}
            </div>
            <div style="font-size:0.85rem;color:#4b5563;
                        line-height:1.6;">
                {out.reasoning}
            </div>
            """, unsafe_allow_html=True)

            if out.data:
                st.json(out.data)

    # ── Critic verdict ─────────────────────────────────────────────────────
    st.markdown("#### 🔍 Critic Verdict")
    verdict       = decision.critic_verdict
    verdict_color = (
        "#16a34a" if verdict.status == AgentStatus.PASS else "#dc2626"
    )
    st.markdown(f"""
    <div style="background:#ffffff;border:1px solid #e8eaed;
                border-left:4px solid {verdict_color};
                border-radius:8px;padding:1rem 1.25rem;">
        <div style="font-size:1rem;font-weight:600;
                    color:{verdict_color};">
            {verdict.status.value}
        </div>
        <div style="font-size:0.85rem;color:#4b5563;
                    margin-top:0.4rem;line-height:1.6;">
            {verdict.reason}
        </div>
        <div style="font-size:0.75rem;color:#9ca3af;margin-top:0.4rem;">
            Retries: {verdict.retry_count}
        </div>
    </div>
    """, unsafe_allow_html=True)
