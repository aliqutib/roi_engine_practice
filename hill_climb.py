import random
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Tuple
from channel_profile import ChannelProfile


# ─────────────────────────────────────────────────────────────────────────────
# STATE
# Represents one possible budget split across channels.
# e.g. {"Facebook": 0.60, "YouTube": 0.25, "Instagram": 0.15}
# Fractions must always sum to 1.0
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AllocationState:
    allocations: Dict[str, float]  # channel → fraction of total budget
    total_budget: float            # total dollars available


# ─────────────────────────────────────────────────────────────────────────────
# OBJECTIVE FUNCTION
# Scores a budget split by calculating total expected ROI.
# Channels with high ROI variance (std_roi) are penalized — they are riskier
# and less likely to consistently deliver their average ROI.
# ─────────────────────────────────────────────────────────────────────────────

def compute_total_roi(state: AllocationState, profiles: Dict[str, ChannelProfile], debug: bool = False) -> float:
    total = 0.0
    if debug:
        print(f"\n  Computing ROI for allocation (total_budget=${state.total_budget:,.0f}):")
    for channel, fraction in state.allocations.items():
        profile = profiles.get(channel)
        if profile:
            spend = state.total_budget * fraction
            roi = profile.roi_at_spend(spend)
            total += roi
            
    return total


# ─────────────────────────────────────────────────────────────────────────────
# NEIGHBOUR GENERATOR
# Creates all nearby budget splits by moving `step` (e.g. 5%) from one
# channel (donor) to another (recipient).
# Invalid moves are rejected:
#   - donor can't go below 0%
#   - recipient can't exceed max_alloc cap (e.g. 60%)
# ─────────────────────────────────────────────────────────────────────────────

def get_neighbours(state: AllocationState, step: float, max_alloc: float) -> List[AllocationState]:
    neighbours = []
    channels = list(state.allocations.keys())

    for donor in channels:
        if state.allocations[donor] < step - 1e-9:  # donor must have enough to give
            continue
        for recipient in channels:
            if donor == recipient:
                continue

            # Shift `step` from donor → recipient
            new_alloc = dict(state.allocations)
            new_alloc[donor]     = round(new_alloc[donor]     - step, 10)
            new_alloc[recipient] = round(new_alloc[recipient] + step, 10)

            # Only accept if all fractions stay within [0, max_alloc]
            if all(0.0 <= v <= max_alloc for v in new_alloc.values()):
                neighbours.append(AllocationState(new_alloc, state.total_budget))

    return neighbours


# ─────────────────────────────────────────────────────────────────────────────
# HILL CLIMBING (steepest ascent + random restarts)
#
# HOW IT WORKS:
#   1. Start with an equal split across all selected channels
#   2. Look at all neighbours (small budget shifts)
#   3. Move to the neighbour with the highest ROI
#   4. Repeat until no neighbour improves ROI → local optimum reached
#   5. Restart from a random split to escape local optima
#   6. Return the best allocation found across all runs
#
# PARAMETERS:
#   selected_channels → frozenset of channel names chosen by A*
#   all_profiles      → full channel profile dict from MongoDB
#   total_budget      → total dollars to split across channels
#   step              → how much budget to shift per move (default 5%)
#   max_alloc         → max fraction any one channel can receive (default 60%)
#   random_restarts   → how many random restarts to attempt
# ─────────────────────────────────────────────────────────────────────────────

def hill_climb(
    selected_channels: FrozenSet[str],
    all_profiles: Dict[str, ChannelProfile],
    total_budget: float,
    step: float = 0.05,
    max_alloc: float = 0.60,
    random_restarts: int = 5,
    verbose: bool = True
) -> Tuple[AllocationState, float]:

    # Only keep profiles for channels A* selected
    profiles = {ch: all_profiles[ch] for ch in selected_channels if ch in all_profiles}
    channels = list(profiles.keys())

    best_state: Optional[AllocationState] = None
    best_roi = float('-inf')

    for run in range(1 + random_restarts):  # run 0 = ROI-weighted, runs 1..N = random

        # Run 0: ROI-weighted split (deterministic starting point favoring high-ROI channels)
        if run == 0:
            roi_per_dollars = {ch: profiles[ch].roi_per_dollar for ch in channels}
            total_roi_score = sum(roi_per_dollars.values())
            
            if total_roi_score > 0:
                # Allocate proportionally to ROI per dollar
                alloc = {ch: round(roi_per_dollars[ch] / total_roi_score, 10) for ch in channels}
                # Fix rounding errors
                alloc[channels[0]] = round(1.0 - sum(alloc[ch] for ch in channels[1:]), 10)
            else:
                # Fallback to equal if all ROI scores are zero
                n    = len(channels)
                base = round(1.0 / n, 10)
                alloc = {ch: base for ch in channels}
                alloc[channels[0]] = round(1.0 - base * (n - 1), 10)

        # Run 1+: random split (helps escape local optima from run 0)
        else:
            steps_total = round(1.0 / step)                        # e.g. 20 tokens for step=0.05
            cuts        = sorted(random.sample(range(1, steps_total), len(channels) - 1))
            bps         = [0] + cuts + [steps_total]
            alloc       = {ch: round((bps[i+1] - bps[i]) * step, 10) for i, ch in enumerate(channels)}

        current     = AllocationState(alloc, total_budget)
        current_roi = compute_total_roi(current, profiles)

        if verbose:
            print(f"\n[Run {run + 1}]  {'ROI-weighted start' if run == 0 else f'Random restart {run}'}")
            print(f"  Starting ROI : {current_roi*100:,.2f}%")

        # Climb: keep moving to the best neighbour until no improvement
        for iteration in range(1000):
            neighbours   = get_neighbours(current, step, max_alloc)
            best_nb      = None
            best_nb_roi  = current_roi  # neighbour must strictly beat current to move

            for nb in neighbours:
                roi = compute_total_roi(nb, profiles)
                if roi > best_nb_roi:
                    best_nb_roi, best_nb = roi, nb

            if best_nb is None:  # no improvement found → local optimum
                if verbose:
                    print(f"  → Local optimum at iteration {iteration}. ROI = {current_roi*100:,.2f}%")
                break

            current, current_roi = best_nb, best_nb_roi  # move uphill

        # Track the best result across all runs
        if current_roi > best_roi:
            best_roi, best_state = current_roi, current

    # Print final result
    if verbose:
        print("\n" + "=" * 55)
        print("  HILL CLIMBING — OPTIMISED BUDGET ALLOCATION")
        print("=" * 55)
        print(f"  Total Budget      : ${total_budget:,.2f}")
        print(f"  Expected Total ROI: {best_roi*100:,.2f}%")
        print("-" * 55)
        for ch, frac in sorted(best_state.allocations.items(), key=lambda x: x[1], reverse=True):
            print(f"  {ch:<20} {frac*100:5.1f}%  {'█' * int(frac * 40)}  ${frac * total_budget:,.0f}")
        print("=" * 55)

    return best_state, best_roi
