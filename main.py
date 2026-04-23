from algo import a_star
from hill_climb import hill_climb
from channel_profile import build_channel_profiles
from db import db

MAX_BUDGET = 30000

# Step 1 — A* picks the best channels
best_channels, best_roi, budget_used = a_star(
    max_budget=MAX_BUDGET,
    db=db,
    verbose=True
)

# Step 2 — Build profiles for Hill Climbing
all_profiles = build_channel_profiles(db)

# Step 3 — Hill Climbing splits the budget optimally
best_state, expected_roi = hill_climb(
    selected_channels=best_channels,
    all_profiles=all_profiles,
    total_budget=budget_used,
    max_alloc=0.40,    # ← max 40% per channel forces all 4 to get share
    verbose=True
)

print("\nFINAL ALLOCATION:")
for channel, fraction in best_state.allocations.items():
    print(f"  {channel}: {fraction*100:.1f}%  → ${fraction * budget_used:,.0f}")