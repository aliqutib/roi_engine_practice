from typing import Dict, FrozenSet, List, Tuple
import heapq

from search_node import SearchNode
from channel_profile import ChannelProfile, build_channel_profiles


def compute_heuristic(
        selected    : FrozenSet[str],
        budget_used : float,
        max_budget  : float,
        all_profiles: Dict[str, ChannelProfile],
) -> float:
    """
    DEFINING HEURISTIC VALUE IN SEARCH TREE
    =========================================================
    Given the current node (set of selected channels + budget used),
    estimate the MAXIMUM additional ROI still achievable from
    unselected channels within the remaining budget.

    PARAMETERS:
    ───────────
    selected     : frozenset of channel names already chosen at this node
    budget_used  : dollars spent so far
    max_budget   : total campaign budget constraint
    all_profiles : precomputed ChannelProfile dict from MongoDB

    RETURNS:
    ────────
    h_value (float) : estimated max additional ROI, always ≤ true optimal
    """

    remaining_budget = max_budget - budget_used

    # Goal state achieved — no budget left
    if remaining_budget <= 0:
        return 0.0

    # Unselected nodes in search tree
    candidates: List[ChannelProfile] = [
        profile
        for channel_name, profile in all_profiles.items()
        if channel_name not in selected              # explore only unselected
        and profile.avg_cost <= remaining_budget     # must fit within budget
        and profile.admissible_roi > 0               # must provide positive return
    ]

    # Goal state achieved / no node can be explored
    if not candidates:
        return 0.0

    # Sort candidates greedily by ROI per dollar (best first)
    candidates.sort(key=lambda p: p.roi_per_dollar, reverse=True)

    # Calculate heuristic value
    h_value     = 0.0
    budget_left = remaining_budget

    for profile in candidates:
        if profile.avg_cost <= budget_left:
            h_value     += profile.admissible_roi
            budget_left -= profile.avg_cost
        else:
            # Partial fraction if we can't afford the full channel
            fraction = budget_left / profile.avg_cost
            h_value += fraction * profile.admissible_roi
            budget_left = 0
            break

    return h_value


def a_star(
        max_budget: float,
        db,
        verbose: bool = True
) -> Tuple[FrozenSet[str], float, float]:
    """
    A* search to find channel combination maximizing ROI within budget.

    EXECUTION FLOW:
    ───────────────
    1. Build channel profiles from MongoDB (once, before search)
    2. Initialize open list with the empty-set root node
    3. Loop:
       a. Pop node with highest f(n) from priority queue
       b. Track best complete state found so far
       c. For each unselected channel that fits budget:
          - Compute g(child) = g(parent) + channel.avg_roi
          - Compute h(child) = compute_heuristic(...)
          - Push child onto frontier if not in explored set
    4. Return best complete state found

    RETURNS:
    ────────
    (best_channels, best_roi, budget_used)
    """

    if verbose:
        print("=" * 60)
        print("PHASE 0: Building channel profiles from MongoDB...")
        print("=" * 60)

    all_profiles = build_channel_profiles(db)

    if verbose:
        print(f"\nLoaded {len(all_profiles)} channel profiles.\n")

    # Initialise root node (empty set — no channels selected yet)
    root_h = compute_heuristic(
        selected    = frozenset(),
        budget_used = 0,
        max_budget  = max_budget,
        all_profiles= all_profiles,
    )

    root = SearchNode(
        neg_f        = -(0 + root_h),
        selected     = frozenset(),
        budget_used  = 0.0,
        roi_acheived = 0.0,
        h_value      = root_h,
    )

    frontier       = [root]
    explored       = set()
    best_complete  = root
    nodes_expanded = 0

    while frontier:
        current = heapq.heappop(frontier)

        if current.selected in explored:
            continue
        explored.add(current.selected)
        nodes_expanded += 1

        # Track best complete state (highest ROI achieved so far)
        if current.roi_acheived > best_complete.roi_acheived:
            best_complete = current

        # Expand: try adding each unselected channel
        for channel_name, profile in all_profiles.items():

            if channel_name in current.selected:
                continue

            new_budget = current.budget_used + profile.avg_cost
            if new_budget > max_budget:
                continue

            new_selected = current.selected | {channel_name}

            if new_selected in explored:
                continue

            g_child = current.roi_acheived + profile.avg_roi
            h_child = compute_heuristic(
                selected    = new_selected,
                budget_used = new_budget,
                max_budget  = max_budget,
                all_profiles= all_profiles,
            )
            f_child = g_child + h_child

            child = SearchNode(
                neg_f        = -f_child,
                selected     = new_selected,
                budget_used  = new_budget,
                roi_acheived = g_child,
                h_value      = h_child,
            )

            heapq.heappush(frontier, child)

    if verbose:
        print("\n" + "=" * 60)
        print("SEARCH COMPLETE")
        print(f"  Nodes expanded    : {nodes_expanded}")
        print(f"  Optimal channels  : {best_complete.label()}")
        print(f"  Total ROI         : {best_complete.roi_acheived * 100:.1f}%")
        print(f"  Budget used       : ${best_complete.budget_used:,.0f} / ${max_budget:,.0f}")
        print("=" * 60)

    return best_complete.selected, best_complete.roi_acheived, best_complete.budget_used