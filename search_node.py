from dataclasses import dataclass, field
from typing import FrozenSet, Dict

@dataclass(order=True)
class SearchNode:

    neg_f:float #for getting hight f(n) using minheap
    selected: FrozenSet[str] = field(compare=False)
    budget_used: float = field(compare=False)
    roi_acheived: float = field(compare=False)
    h_value: float = field(compare=False)
    spend_per_channel: Dict[str, float] = field(compare=False, default_factory=dict)

    @property
    def f(self) -> float:
        return -self.neg_f   # actual f(n) = g(n) + h(n)
 
    @property
    def g(self) -> float:
        return self.roi_acheived
 
    def label(self) -> str:
        return "{" + ", ".join(sorted(self.selected)) + "}"