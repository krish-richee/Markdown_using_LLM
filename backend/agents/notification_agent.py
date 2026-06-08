import os
import json
import urllib.request
from datetime import datetime
from dotenv import load_dotenv
from agents.base_agent import AgentStatus, FinalDecision
from config.settings import SLACK_WEBHOOK_URL, SNS_TOPIC_ARN

load_dotenv()


class NotificationAgent:
    """
    Sends notifications based on final decision.

    POC mode  — prints to console + logs to file
    Prod mode — sends to Slack webhook + AWS SNS

    Triggers:
        HIGH risk product approved    → Slack alert
        Cost floor breached           → immediate alert
        Critic rejected 3 times       → manager alert
        Decision health RED           → SNS email
    """

    name = "NotificationAgent"

    LOG_FILE = "data/notification_log.jsonl"

    def notify(
        self,
        product: dict,
        decision: FinalDecision,
    ) -> dict:

        alerts = []
        price      = float(product.get("price", 0))
        risk       = product.get("clearance_risk", "MEDIUM")
        abc        = product.get("abc_class", "B")
        verdict    = decision.critic_verdict.status
        retries    = decision.critic_verdict.retry_count
        health     = decision.health_badge
        markdown   = decision.recommended_markdown_pct

        # ── Trigger 1 — RED health badge ──────────────────────────────
        if "🔴" in health:
            alerts.append({
                "type":     "RED_HEALTH",
                "severity": "HIGH",
                "message":  (
                    f"⚠️ RED decision on {product.get('product_name')} | "
                    f"Markdown {markdown}% not recommended | "
                    f"Revenue likely to decline"
                ),
            })

        # ── Trigger 2 — HIGH risk product approved ────────────────────
        if risk == "HIGH" and verdict == AgentStatus.PASS:
            alerts.append({
                "type":     "HIGH_RISK_APPROVED",
                "severity": "MEDIUM",
                "message":  (
                    f"✅ HIGH risk product approved: "
                    f"{product.get('product_name')} | "
                    f"{markdown}% markdown → ₹{decision.final_price:.2f} | "
                    f"Promo: {decision.promotion_type}"
                ),
            })

        # ── Trigger 3 — Max retries hit ───────────────────────────────
        if retries >= 3:
            alerts.append({
                "type":     "MAX_RETRIES",
                "severity": "HIGH",
                "message":  (
                    f"🔄 Critic rejected {retries}x for "
                    f"{product.get('product_name')} — "
                    f"escalate to senior merchandiser"
                ),
            })

        # ── Trigger 4 — ABC A product deep discount ───────────────────
        if abc == "A" and markdown > 20:
            alerts.append({
                "type":     "ABC_A_DEEP_DISCOUNT",
                "severity": "MEDIUM",
                "message":  (
                    f"⚠️ ABC A product getting {markdown}% markdown: "
                    f"{product.get('product_name')} — "
                    f"verify margin protection"
                ),
            })

        # ── Trigger 5 — Dead inventory clearance ──────────────────────
        if product.get("is_dead_inventory") and verdict == AgentStatus.PASS:
            alerts.append({
                "type":     "DEAD_INVENTORY_CLEARANCE",
                "severity": "LOW",
                "message":  (
                    f"🗑️ Dead inventory clearance approved: "
                    f"{product.get('product_name')} | "
                    f"{markdown}% off | "
                    f"DOS: {product.get('days_of_stock', 0):.0f}d"
                ),
            })

        # ── Send notifications ─────────────────────────────────────────
        for alert in alerts:
            self._send(alert, decision)

        # ── Log to file ────────────────────────────────────────────────
        log_entry = {
            "timestamp":   datetime.now().isoformat(),
            "product_id":  product.get("product_id"),
            "product_name":product.get("product_name"),
            "markdown_pct":markdown,
            "final_price": decision.final_price,
            "health":      health,
            "verdict":     verdict.value,
            "alerts_sent": len(alerts),
            "alerts":      alerts,
        }
        self._log(log_entry)

        decision.notification_sent = len(alerts) > 0

        return {
            "alerts_sent": len(alerts),
            "alerts":      alerts,
        }

    def _send(self, alert: dict, decision: FinalDecision):
        severity_emoji = {
            "HIGH":   "🚨",
            "MEDIUM": "⚠️",
            "LOW":    "ℹ️",
        }.get(alert["severity"], "📢")

        msg = f"{severity_emoji} [{alert['type']}] {alert['message']}"

        # POC — print to console
        print(f"  📣 NOTIFICATION: {msg}")

        # Production — send to Slack
        if SLACK_WEBHOOK_URL:
            self._send_slack(msg)

        # Production — send to SNS for HIGH severity
        if SNS_TOPIC_ARN and alert["severity"] == "HIGH":
            self._send_sns(msg)

    def _send_slack(self, message: str):
        try:
            payload = json.dumps({"text": message}).encode()
            req     = urllib.request.Request(
                SLACK_WEBHOOK_URL,
                data    = payload,
                headers = {"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            print(f"  ⚠️ Slack send failed: {e}")

    def _send_sns(self, message: str):
        try:
            import boto3
            sns = boto3.client("sns")
            sns.publish(
                TopicArn = SNS_TOPIC_ARN,
                Message  = message,
                Subject  = "RetailAI — Markdown Alert",
            )
        except Exception as e:
            print(f"  ⚠️ SNS send failed: {e}")

    def _log(self, entry: dict):
        try:
            os.makedirs("data", exist_ok=True)
            with open(self.LOG_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"  ⚠️ Log write failed: {e}")
