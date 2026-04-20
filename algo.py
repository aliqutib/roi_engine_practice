from typing import FrozenSet, Dict
from channel_profile import ChannelProfile

def compute_heuristic(
        selected: FrozenSet[str],
        budget_used: float,
        max_budget: float,
        all_profiles: Dict[str, ChannelProfile],
        node_label: str = ""
) -> float:

    """
    DEFINING HERUISTIC VALUE IN SEARCH TREE
    =========================================================
    Given the current node (set of selected channels + budget used),
    estimate the MAXIMUM additional ROI still achievable from
    unselected channels within the remaining budget.

    PARAMETERS:
    ───────────
    selected        : frozenset of channel names already chosen at this node
    budget_used     : dollars spent so far
    max_budget      : total campaign budget constraint
    all_profiles    : precomputed ChannelProfile dict from MongoDB
    node_label      : debug string for tracing
 
    RETURNS:
    ────────
    h_value (float) : estimated max additional ROI, always ≤ true optimal
    
    """

    remaining_budget = max_budget - budget_used

    #goal state acheived
    if remaining_budget <= 0:
        return 0.0
    
    #unselected nodes in search tree
    candinates : List[ChannelProfile] = [
        profile for channel, profile in all_profiles.items()

        if name not in selected                     #explore node if it is not selected
        and profile.avg_cost <= remaining_budget    #explore node if its cost is within budget
        and profile.admissible_roi > 0              #explore node if it provide return, benefits (utility) to goal state
    ]

    #goal state acheived / no node can be explored either with remaninig budget or in available options 
    if not candinates:
        return 0.0
    
    #Selecting canidate greedly by picking the most ROI per dollar
    candidates.sort(key=lambda p: p.roi_per_dollar, reverse=True)

    #Actual calculation of the heruistic value after finding all remaining potentials channels

    h_value = 0.0
    budget_left = remaining_budget

    for profile in candinates:

        if profile.avg_cost < budget_left:
            h_value += profile.admissible_roi
            budget_left -= profile.avg_cost

        else:
            #if we can't get whole channel from the remaining budget, consider a fraction of roi gained from channel
            fraction = budget_left / profile.avg_cost
            h_value += fraction * profile.admissible_roi   #contributing only partial roi as available budget

            budget_left = 0
            break

    return h_value
