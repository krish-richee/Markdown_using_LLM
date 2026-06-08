from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from enum import Enum


class AgentStatus(Enum):
    PASS   = "PASS"
    REJECT = "REJECT"
    SKIP   = "SKIP"    # agent had no data to work with


@dataclass
class AgentOutput:
    agent_name:     str
    recommendation: str
    confidence:     float          # 0.0 – 1.0
    reasoning:      str
    data:           Dict[str, Any] = field(default_factory=dict)
    status:         AgentStatus    = AgentStatus.PASS


@dataclass
class CriticVerdict:
    status:    AgentStatus         # PASS or REJECT
    reason:    str
    retry_count: int = 0


@dataclass
class FinalDecision:
    product_id:         str
    product_name:       str
    recommended_markdown_pct: float
    final_price:        float
    health_badge:       str        # 🟢 🟡 🔴
    coordinator_reasoning: str
    critic_verdict:     CriticVerdict
    agent_outputs:      Dict[str, AgentOutput] = field(default_factory=dict)
    promotion_type:     Optional[str] = None   # flash / bundle / seasonal
    notification_sent:  bool = False
    run_timestamp:      str  = ""