from algo import a_star
from hill_climb import hill_climb
from channel_profile import build_channel_profiles
from db import db


MAX_BUDGET = 100000   # ← Change this to your marketing budget ($)


# ── Step 1: A* picks the best channels ───────────────────────────────────
best_channels, best_roi, budget_used = a_star(
    max_budget = MAX_BUDGET,
    db         = db,
    verbose    = True
)

# ── Step 2: Build profiles for Hill Climbing ──────────────────────────────
all_profiles = build_channel_profiles(db)

# ── Step 3: Hill Climbing splits the FULL budget optimally ────────────────
# We pass MAX_BUDGET (not budget_used) so no money is left sitting unused.
# A* tells us WHICH channels to use — Hill Climbing decides HOW MUCH each gets.
best_state, expected_roi = hill_climb(
    selected_channels = best_channels,
    all_profiles      = all_profiles,
    total_budget      = MAX_BUDGET,   # ← full budget, nothing wasted
    max_alloc         = 0.25,         # max 25% per channel → spreads across all 6
    verbose           = True
)

# ── Final Summary ──────────────────────────────────────────────────────────
print("\nFINAL ALLOCATION:")
for channel, fraction in sorted(best_state.allocations.items(), key=lambda x: x[1], reverse=True):
    print(f"  {channel}: {fraction * 100:.1f}%  → ${fraction * MAX_BUDGET:,.0f}")
