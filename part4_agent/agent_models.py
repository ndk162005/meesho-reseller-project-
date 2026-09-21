from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Union

@dataclass
class CategoryGrowth:
    category: str
    previous_revenue: float
    current_revenue: float
    mom_pct: Union[float, str]
    classification: str

@dataclass
class AgentResult:
    run_month: str
    validation_status: str
    validation_errors: List[str] = field(default_factory=list)
    flagged_categories: List[Dict[str, Any]] = field(default_factory=list)
    drafted_categories: List[Dict[str, Any]] = field(default_factory=list)
    suppressed_categories: List[Dict[str, Any]] = field(default_factory=list)
    escalated_categories: List[Dict[str, Any]] = field(default_factory=list)
    action_taken: str = "none"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
