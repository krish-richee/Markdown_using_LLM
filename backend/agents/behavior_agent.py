from agents.base_agent import AgentOutput, AgentStatus


class BehaviorAgent:
    """
    Analyses customer behaviour signals from BQ events:
    cart abandonment, wishlist adds, view-to-purchase ratio.
    Uses pre-computed event metrics from data_loader.
    """

    name = "BehaviorAgent"

    def analyze(self, product: dict, event_metrics: dict = None) -> AgentOutput:
        try:
            event_metrics = event_metrics or {}

            cart_abandonment  = float(event_metrics.get("cart_abandonment_rate", 0))
            purchase_conv     = float(event_metrics.get("purchase_conversion", 0))
            checkout_conv     = float(event_metrics.get("checkout_conversion", 0))
            cart_conv         = float(event_metrics.get("cart_conversion_rate", 0))
            total_wishlist    = int(event_metrics.get("total_wishlist", 0))
            total_views       = int(event_metrics.get("total_views", 1))

            product_name      = product.get("product_name", "")
            price             = float(product.get("price", 0))
            clearance_risk    = product.get("clearance_risk", "MEDIUM")

            # Signal interpretation
            signals = []

            if cart_abandonment > 70:
                signals.append(f"HIGH cart abandonment ({cart_abandonment:.1f}%) — price sensitivity detected")
                price_signal = "price_too_high"
            elif cart_abandonment > 50:
                signals.append(f"MODERATE cart abandonment ({cart_abandonment:.1f}%)")
                price_signal = "price_borderline"
            else:
                signals.append(f"LOW cart abandonment ({cart_abandonment:.1f}%) — price acceptable")
                price_signal = "price_ok"

            if purchase_conv < 5:
                signals.append(f"Low purchase conversion ({purchase_conv:.1f}%) — consider discount")
            elif purchase_conv > 15:
                signals.append(f"Strong purchase conversion ({purchase_conv:.1f}%) — no discount needed")

            if total_wishlist > total_views * 0.05:
                signals.append("High wishlist ratio — customers want it but hesitating on price")

            # Recommendation
            if price_signal == "price_too_high" and clearance_risk in ["HIGH", "MEDIUM"]:
                recommendation = (
                    f"Price reduction strongly indicated — "
                    f"{cart_abandonment:.1f}% abandonment suggests price barrier. "
                    f"Recommend 15-25% markdown to unlock conversions."
                )
                confidence = 0.88
            elif price_signal == "price_borderline":
                recommendation = (
                    f"Moderate price sensitivity — "
                    f"small markdown (10-15%) may improve conversion."
                )
                confidence = 0.72
            else:
                recommendation = (
                    f"Behaviour signals healthy — "
                    f"no price reduction needed from demand side."
                )
                confidence = 0.65

            reasoning = (
                f"Cart abandonment: {cart_abandonment:.1f}% | "
                f"Purchase conv: {purchase_conv:.1f}% | "
                f"Checkout conv: {checkout_conv:.1f}% | "
                f"Cart conv: {cart_conv:.1f}% | "
                f"Wishlist: {total_wishlist:,} | "
                f"Signal: {price_signal} | "
                f"Signals: {' | '.join(signals)}"
            )

            return AgentOutput(
                agent_name     = self.name,
                recommendation = recommendation,
                confidence     = confidence,
                reasoning      = reasoning,
                status         = AgentStatus.PASS,
                data           = {
                    "price_signal":       price_signal,
                    "cart_abandonment":   cart_abandonment,
                    "purchase_conv":      purchase_conv,
                    "checkout_conv":      checkout_conv,
                    "total_wishlist":     total_wishlist,
                    "signals":            signals,
                },
            )

        except Exception as e:
            return AgentOutput(
                agent_name     = self.name,
                recommendation = "Unable to analyse behaviour",
                confidence     = 0.0,
                reasoning      = f"Error: {e}",
                status         = AgentStatus.SKIP,
                data           = {},
            )