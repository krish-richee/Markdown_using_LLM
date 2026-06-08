from agents.base_agent import AgentOutput, AgentStatus


class PromotionAgent:
    """
    Suggests the best promotion type based on
    product profile, season, category, and inventory urgency.

    Promotion types:
        flash_sale   — 24-48hr deep discount, high urgency
        bundle       — pair with complementary product
        seasonal     — align with upcoming season/festival
        clearance    — end-of-life, no restocking
        loyalty      — reward repeat buyers, low urgency
        none         — no promotion needed
    """

    name = "PromotionAgent"

    # Category → best bundle partner
    BUNDLE_MAP = {
        "Footwear":              "Accessories",
        "Ethnic Wear":           "Jewellery",
        "Western Wear":          "Bags & Wallets",
        "Sportswear":            "Footwear",
        "Skincare & Beauty":     "Accessories",
        "Bags & Wallets":        "Western Wear",
        "Jewellery":             "Ethnic Wear",
        "Innerwear & Sleepwear": "Skincare & Beauty",
        "Kids Fashion":          "Footwear",
        "Accessories":           "Western Wear",
    }

    # Season → upcoming festival/event
    SEASON_EVENTS = {
        "Festive":  "Diwali / Navratri sale — bundle ethnic + jewellery",
        "Winter":   "End-of-season winter clearance",
        "Summer":   "Summer EOSS — flat discount on light fabrics",
        "Monsoon":  "Monsoon refresh — waterproof + accessories bundle",
        "All Season": "Year-round value pack",
    }

    def analyze(self, product: dict) -> AgentOutput:
        try:
            category       = product.get("main_category", "")
            season         = product.get("season", "All Season")
            clearance_risk = product.get("clearance_risk", "MEDIUM")
            days_of_stock  = float(product.get("days_of_stock", 9999))
            sell_through   = float(product.get("sell_through_rate", 0))
            abc_class      = product.get("abc_class", "B")
            markdown_pct   = float(product.get("recommended_markdown_pct", 15))

            # Decision tree
            if days_of_stock > 180 or clearance_risk == "HIGH" and markdown_pct >= 25:
                promo_type  = "clearance"
                description = (
                    f"End-of-life clearance — {markdown_pct:.0f}% off. "
                    f"No restocking recommended after sell-out."
                )
                confidence  = 0.92

            elif clearance_risk == "HIGH" and days_of_stock > 60:
                promo_type  = "flash_sale"
                description = (
                    f"48-hour flash sale at {markdown_pct:.0f}% off. "
                    f"High urgency — {days_of_stock:.0f} DOS remaining."
                )
                confidence  = 0.88

            elif abc_class == "A" and sell_through > 60:
                promo_type  = "loyalty"
                description = (
                    f"Loyalty reward for repeat buyers — "
                    f"exclusive {min(markdown_pct, 10):.0f}% off for members. "
                    f"Protect margin on top-performing SKU."
                )
                confidence  = 0.80

            elif category in self.BUNDLE_MAP:
                bundle_cat  = self.BUNDLE_MAP[category]
                promo_type  = "bundle"
                description = (
                    f"Bundle {category} with {bundle_cat} — "
                    f"combo discount {markdown_pct:.0f}% on primary item. "
                    f"Increases basket size without deep single-item discount."
                )
                confidence  = 0.75

            elif season in self.SEASON_EVENTS:
                promo_type  = "seasonal"
                description = (
                    f"Seasonal promotion — "
                    f"{self.SEASON_EVENTS[season]}. "
                    f"Recommended depth: {markdown_pct:.0f}%."
                )
                confidence  = 0.70

            else:
                promo_type  = "none"
                description = "No specific promotion needed — standard markdown sufficient."
                confidence  = 0.60

            reasoning = (
                f"Category: {category} | Season: {season} | "
                f"Risk: {clearance_risk} | DOS: {days_of_stock:.0f}d | "
                f"ABC: {abc_class} | ST: {sell_through:.1f}% | "
                f"Promo: {promo_type}"
            )

            return AgentOutput(
                agent_name     = self.name,
                recommendation = f"{promo_type.upper()} — {description}",
                confidence     = confidence,
                reasoning      = reasoning,
                status         = AgentStatus.PASS,
                data           = {
                    "promo_type":   promo_type,
                    "description":  description,
                    "bundle_with":  self.BUNDLE_MAP.get(category, ""),
                    "season_event": self.SEASON_EVENTS.get(season, ""),
                },
            )

        except Exception as e:
            return AgentOutput(
                agent_name     = self.name,
                recommendation = "Unable to suggest promotion",
                confidence     = 0.0,
                reasoning      = f"Error: {e}",
                status         = AgentStatus.SKIP,
                data           = {},
            )