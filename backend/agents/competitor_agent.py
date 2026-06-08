import os
import json
from tavily import TavilyClient
from dotenv import load_dotenv
from agents.base_agent import AgentOutput, AgentStatus

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")


class CompetitorAgent:
    """
    Tavily-based competitor pricing agent.
    Searches web in real time for competitor prices
    and compares against your current price.
    """

    name = "CompetitorAgent"

    def __init__(self):
        self.client = TavilyClient(api_key=TAVILY_API_KEY)

    def analyze(self, product: dict) -> AgentOutput:
        try:
            price        = float(product.get("price", 0))
            brand        = product.get("brand", "")
            category     = product.get("main_category", "")
            product_name = product.get("product_name", "")
            color        = product.get("color", "")

            # Build search query
            base_name = product_name.replace(brand, "").replace(color, "").strip()
            query     = f"{brand} {base_name} price India buy online"

            # Search web
            results = self.client.search(
                query             = query,
                search_depth      = "basic",
                max_results       = 5,
                include_answer    = True,
            )

            # Extract prices from results
            competitor_prices = []
            sources           = []

            for r in results.get("results", []):
                title   = r.get("title", "")
                content = r.get("content", "")
                url     = r.get("url", "")
                text    = f"{title} {content}"

                # Parse price mentions (Rs/₹ followed by numbers)
                import re
                price_matches = re.findall(
                    r'(?:Rs\.?|₹|INR)\s*([0-9,]+)', text
                )
                for pm in price_matches:
                    try:
                        p = float(pm.replace(",", ""))
                        # filter realistic price range
                        if 50 < p < 50000:
                            competitor_prices.append(p)
                            sources.append(url)
                    except:
                        continue

            # No prices found
            if not competitor_prices:
                return AgentOutput(
                    agent_name     = self.name,
                    recommendation = "No competitor prices found — web search returned no price data",
                    confidence     = 0.35,
                    reasoning      = (
                        f"Searched for '{query}' but could not extract "
                        f"competitor prices from results. "
                        f"Estimated market range: "
                        f"₹{price*0.90:,.0f}–₹{price*1.10:,.0f}"
                    ),
                    status = AgentStatus.PASS,
                    data   = {
                        "data_available":  False,
                        "price_position":  "unknown",
                        "your_price":      price,
                        "estimated_low":   round(price * 0.90, 2),
                        "estimated_high":  round(price * 1.10, 2),
                        "query":           query,
                    },
                )

            # Calculate stats
            avg_comp   = round(sum(competitor_prices) / len(competitor_prices), 2)
            min_comp   = round(min(competitor_prices), 2)
            max_comp   = round(max(competitor_prices), 2)
            suggested  = round(avg_comp * 0.95, 2)

            # Position
            if price > avg_comp * 1.10:
                position   = "ABOVE_MARKET"
                signal     = (
                    f"Your price ₹{price:,.0f} is "
                    f"{((price/avg_comp)-1)*100:.1f}% above "
                    f"market avg ₹{avg_comp:,.0f} — markdown recommended"
                )
                confidence = 0.88
            elif price < avg_comp * 0.90:
                position   = "BELOW_MARKET"
                signal     = (
                    f"Your price ₹{price:,.0f} is already "
                    f"{((1-price/avg_comp))*100:.1f}% below "
                    f"market avg ₹{avg_comp:,.0f} — no markdown needed"
                )
                confidence = 0.82
            else:
                position   = "AT_MARKET"
                signal     = (
                    f"Your price ₹{price:,.0f} is in line "
                    f"with market avg ₹{avg_comp:,.0f}"
                )
                confidence = 0.75

            reasoning = (
                f"Searched: '{query}' | "
                f"Found {len(competitor_prices)} price points | "
                f"Your price: ₹{price:,.0f} | "
                f"Market avg: ₹{avg_comp:,.0f} | "
                f"Range: ₹{min_comp:,.0f}–₹{max_comp:,.0f} | "
                f"Position: {position} | {signal}"
            )

            return AgentOutput(
                agent_name     = self.name,
                recommendation = f"{position} — {signal}",
                confidence     = confidence,
                reasoning      = reasoning,
                status         = AgentStatus.PASS,
                data           = {
                    "data_available":   True,
                    "price_position":   position,
                    "your_price":       price,
                    "avg_comp_price":   avg_comp,
                    "min_comp_price":   min_comp,
                    "max_comp_price":   max_comp,
                    "suggested_price":  suggested,
                    "prices_found":     len(competitor_prices),
                    "query":            query,
                    "sources":          sources[:3],
                },
            )

        except Exception as e:
            return AgentOutput(
                agent_name     = self.name,
                recommendation = "Unable to fetch competitor prices",
                confidence     = 0.0,
                reasoning      = f"Error: {e}",
                status         = AgentStatus.SKIP,
                data           = {},
            )
