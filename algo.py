from typing import FrozenSet, Dict, List, Tuple
import heapq
from search_node import SearchNode
from channel_profile import ChannelProfile
from channel_profile import build_channel_profiles


def compute_heuristic(
        selected: FrozenSet[str],
        budget_used: float,
        max_budget: float,
        all_profiles: Dict[str, ChannelProfile],
        #node_label: str = ""
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
        profile for channel_name, profile in all_profiles.items()

        if channel_name not in selected                     #explore node if it is not selected
        and profile.min_cost <= remaining_budget    #explore node if its cost is within 10th percentile
        and profile.admissible_roi > 0              #explore node if it provide return, benefits (utility) to goal state
    ]

    #goal state acheived / no node can be explored either with remaninig budget or in available options 
    if not candinates:
        return 0.0
    
    #Selecting canidate greedly by picking the most ROI per dollar
    candinates.sort(key=lambda p: p.roi_per_dollar, reverse=True)

    #Actual calculation of the heruistic value after finding all remaining potentials channels

    h_value = 0.0
    budget_left = remaining_budget

    for profile in candinates:
        if budget_left <= 0:
            break
        if profile.min_cost > budget_left:
            continue

        spend = min(budget_left, profile.avg_cost)
        roi = profile.roi_at_spend(spend=spend)
        h_value += roi
        budget_left -= spend

    if budget_left > 0:

        total_spent : Dict[str, float] = {
            profile.name : min(remaining_budget-budget_left, profile.avg_cost) * (1 if profile in candinates else 0)
            for profile in candinates
        }

        #total_spent = {}
        pass1_budget = budget_left
        for profile in candinates:
            spend = min(pass1_budget, profile.avg_cost)
            if profile.min_cost <= pass1_budget:
                total_spent[profile.name] = spend
                pass1_budget -= spend
            if pass1_budget <= 0:
                break
        
        max_passes = 10
        for pass_num in range(max_passes):
            if budget_left <= 0:
                break

            allocated_this_pass = False
            for profile in candinates:
                if budget_left <= 0:
                    break

                current_spend = total_spent.get(profile.name, 0.0)
                headroom = profile.max_cost - current_spend

                if headroom <= 0:
                    continue

                increment = min(budget_left, headroom)
                if increment <= profile.min_cost * 0.10:
                    continue   # too small to be meaningful (< 10% of min cost)

                new_total_spend = current_spend + increment
                roi_before = profile.roi_at_spend(current_spend)
                roi_after  = profile.roi_at_spend(new_total_spend)
                marginal_roi = roi_after - roi_before   # additional ROI from this increment

                if marginal_roi <= 0:
                    continue

                h_value += marginal_roi
                budget_left -= increment
                total_spent[profile.name] = new_total_spend
                allocated_this_pass = True

            if not allocated_this_pass:
                break

    if budget_left > 0 and candinates:
        best = candinates[0]
        fraction = budget_left / best.avg_cost
        partial  = best.admissible_roi * fraction
        h_value += partial

    return h_value

def a_star(
        max_budget:float,
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
       b. Goal test: can we still improve? If not, return.
       c. For each unselected channel that fits budget:
          - Compute g(child) = g(parent) + new_roi
          - Compute h(child) = compute_heuristic(...)
          - Push child onto open list if not in closed set
    4. Return best complete state found
 
    RETURNS:
    ────────
    (best_channels, best_roi)
    """
    print("=" * 60)
    print("PHASE 0: Building channel profiles from MongoDB...")
    print("=" * 60)
    all_profiles = build_channel_profiles(db)
    print(f"\nLoaded {len(all_profiles)} channel profiles.\n")

    root_h = compute_heuristic(
        selected=frozenset(),
        budget_used=0,
        max_budget=max_budget,
        all_profiles=all_profiles
        #node_label="Root {}"
    )

    root = SearchNode(
        neg_f= -(0+root_h),
        selected=frozenset(),
        budget_used=0.0,
        roi_acheived=0.0,
        h_value=root_h,
        spend_per_channel={}
    )

    frontier = [root]
    explored: set = set()
    best_complete = root
    nodes_expanded = 0

    while frontier:
        current = heapq.heappop(frontier)

        node_state = (
            current.selected,
            frozenset((channel, spend) for channel, spend in current.spend_per_channel.items())
            )

        if node_state in explored:
            continue

        explored.add(node_state)
        nodes_expanded += 1

        #Goal Test
        if current.roi_acheived > best_complete.roi_acheived:
            best_complete = current

        for channel_name, profile in all_profiles.items():
            budget_left = max_budget - current.budget_used
            
            #----TYPE A: Activate a new channel (low budget check) -----------
            if channel_name not in current.selected:
                # Check if we can afford the entry cost (min_cost)
                if budget_left < profile.entry_cost:
                    continue

                # Spend up to avg_cost, but capped by remaining budget
                activation_spend = min(profile.avg_cost, budget_left)
                
                new_budget = current.budget_used + activation_spend    
                new_selected = current.selected | {channel_name}
                new_spend_map = {**current.spend_per_channel, 
                                 channel_name: activation_spend}
                new_roi = current.roi_acheived + profile.roi_at_spend(activation_spend)

            #-----TYPE B: Scale up already selected channel (high budget option)-------
            else:
                current_spend = current.spend_per_channel.get(channel_name, 0.0)
                
                # Check if we can spend more (headroom bounded by max_cost)
                headroom = profile.max_cost - current_spend

                if headroom <= 0:
                    continue  # Already at max spend for this channel

                # Increment is the smaller of: remaining headroom or remaining budget
                increment = min(headroom, budget_left)
                if increment <= 0:
                    continue  # No budget or no headroom

                new_spend = current_spend + increment
                new_budget = current.budget_used + increment
                new_selected = current.selected  # same set
                new_spend_map = {**current.spend_per_channel,
                                 channel_name: new_spend}
                
                # Calculate marginal ROI with diminishing returns
                roi_before = profile.roi_at_spend(current_spend)
                roi_after = profile.roi_at_spend(new_spend)
                new_roi = current.roi_acheived + (roi_after - roi_before)

            if new_budget > max_budget:
                continue

            new_node_state = (
                new_selected,
                frozenset((ch, sp) for ch, sp in new_spend_map.items())
            )

            if new_node_state in explored:
                continue


            h_child = compute_heuristic(
                selected=new_selected,
                budget_used=new_budget,
                max_budget=max_budget,
                all_profiles=all_profiles,
            )

            g_child = new_roi
            f_child = h_child + g_child

            child = SearchNode(
                neg_f=-f_child,
                selected=new_selected,
                budget_used=new_budget,
                roi_acheived=g_child,
                h_value=h_child,
                spend_per_channel=new_spend_map
            )

            heapq.heappush(frontier, child)

    print("\n" + "=" * 60)
    print("SEARCH COMPLETE")
    print(f"  Nodes expanded:   {nodes_expanded}")
    print(f"  Optimal channels: {best_complete.label()}")
    print(f"  Total ROI:        {best_complete.roi_acheived * 100:.1f}%")
    print(f"  Budget used:      ${best_complete.budget_used:,.0f} / ${max_budget:,.0f}")
    unspent = max_budget - best_complete.budget_used
    print(f"  Unspent budget:   ${unspent:,.0f} ({unspent/max_budget*100:.1f}%)")
    print(f"  Spend per Channel A* : {best_complete.spend_per_channel}")
    print("=" * 60)

    return best_complete.selected, best_complete.roi_acheived, best_complete.budget_used