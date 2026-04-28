from dataclasses import dataclass, field
from typing import FrozenSet


@dataclass(order=True)
class SearchNode:

    neg_f        : float                               # for getting highest f(n) using min-heap
    selected     : FrozenSet[str] = field(compare=False)
    budget_used  : float          = field(compare=False)
    roi_acheived : float          = field(compare=False)
    h_value      : float          = field(compare=False)

    @property
    def f(self) -> float:
        return -self.neg_f                             # actual f(n) = g(n) + h(n)

    @property
    def g(self) -> float:
        return self.roi_acheived                       # g(n) = ROI achieved so far

    def label(self) -> str:
        if not self.selected:
            return "{} (empty)"
        return "{" + ", ".join(sorted(self.selected)) + "}"
