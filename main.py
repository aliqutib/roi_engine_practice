from A_star import a_star
from hill_climb import hill_climb
from channel_profile import (
    build_channel_profiles,
    print_ranking_report,
    print_risk_analysis,
    print_search_results,
)
from db import db


# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION — change these values to customise the run
# ═══════════════════════════════════════════════════════════════════════════════

MAX_BUDGET = 100_000        # ← Your total marketing budget ($)

# 🔍 Search settings (Feature 3)
# Set query="" to skip name search, risk_filter="all" to show everything
SEARCH_QUERY       = ""         # e.g. "face" finds "Facebook"
SEARCH_RISK_FILTER = "all"      # "safe" | "moderate" | "risky" | "all"
SEARCH_MIN_ROI     = 0.0        # only show channels with avg_roi >= this

# 📊 Sensitivity Analysis budgets (Feature 4)
# A* + Hill Climbing will re-run for each budget to compare results
SENSITIVITY_BUDGETS = [
    MAX_BUDGET * 0.80,   # −20%
    MAX_BUDGET * 0.90,   # −10%
    MAX_BUDGET,          #  base
    MAX_BUDGET * 1.10,   # +10%
    MAX_BUDGET * 1.20,   # +20%
]


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 1 — A* picks the best channels within budget
# ═══════════════════════════════════════════════════════════════════════════════

best_channels, best_roi, budget_used = a_star(
    max_budget = MAX_BUDGET,
    db         = db,
    verbose    = True
)

# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 2 — Build channel profiles (used by all features below)
# ═══════════════════════════════════════════════════════════════════════════════

all_profiles = build_channel_profiles(db)

# ═══════════════════════════════════════════════════════════════════════════════
#  FEATURE 1 — 🏆 Channel Ranking Report
#  Shows all channels ranked by composite score (ROI efficiency + conversion)
# ═══════════════════════════════════════════════════════════════════════════════

print_ranking_report(all_profiles)

# ═══════════════════════════════════════════════════════════════════════════════
#  FEATURE 2 — ⚠️  Risk Analysis
#  Labels every channel Safe / Moderate / Risky based on ROI variance.
#  Also shows best-case and worst-case ROI projections.
# ═══════════════════════════════════════════════════════════════════════════════

print_risk_analysis(all_profiles, total_budget=MAX_BUDGET)

# ═══════════════════════════════════════════════════════════════════════════════
#  FEATURE 3 — 🔍 Channel Search & Filter
#  Search by name, filter by risk level or minimum ROI.
#  Edit SEARCH_QUERY / SEARCH_RISK_FILTER / SEARCH_MIN_ROI above to customise.
# ═══════════════════════════════════════════════════════════════════════════════

print_search_results(
    profiles    = all_profiles,
    query       = SEARCH_QUERY,
    risk_filter = SEARCH_RISK_FILTER,
    min_roi     = SEARCH_MIN_ROI,
)

# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 3 — Hill Climbing splits the FULL budget optimally across A* channels
# ═══════════════════════════════════════════════════════════════════════════════

best_state, expected_roi = hill_climb(
    selected_channels = best_channels,
    all_profiles      = all_profiles,
    total_budget      = MAX_BUDGET,
    max_alloc         = 0.25,
    verbose           = True
)

# ═══════════════════════════════════════════════════════════════════════════════
#  FEATURE 4 — 📊 Sensitivity Analysis
#  Re-runs A* + Hill Climbing at ±10% and ±20% of your budget.
#  Answers: "What if we had more or less money to spend?"
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("    SENSITIVITY ANALYSIS — How budget changes affect ROI")
print("=" * 70)
print(f"  {'Budget':>12}  {'Change':>8}  {'Channels':>8}  {'Expected ROI':>14}")
print("-" * 70)

sensitivity_results = []

for test_budget in SENSITIVITY_BUDGETS:

    # Re-run A* for this budget
    channels_s, _, _ = a_star(
        max_budget = test_budget,
        db         = db,
        verbose    = False       # silent — we only want the final numbers
    )

    # Re-run Hill Climbing for this budget
    state_s, roi_s = hill_climb(
        selected_channels = channels_s,
        all_profiles      = all_profiles,
        total_budget      = test_budget,
        max_alloc         = 0.25,
        verbose           = False
    )

    change_pct = ((test_budget - MAX_BUDGET) / MAX_BUDGET) * 100
    change_str = f"{change_pct:+.0f}%"
    n_channels = len(channels_s)

    sensitivity_results.append((test_budget, change_str, n_channels, roi_s))

    marker = " ◄ BASE" if test_budget == MAX_BUDGET else ""
    print(f"  ${test_budget:>11,.0f}  {change_str:>8}  {n_channels:>8}  ${roi_s:>13,.2f}{marker}")

print("-" * 70)

# Find best budget scenario
best_scenario = max(sensitivity_results, key=lambda x: x[3])
print(f"\n   Best ROI scenario  : ${best_scenario[0]:,.0f} budget → ${best_scenario[3]:,.2f} ROI")
print(f"   Base budget ROI    : ${expected_roi:,.2f}")

roi_diff = best_scenario[3] - expected_roi
if roi_diff > 0:
    print(f"   Potential gain     : +${roi_diff:,.2f} by adjusting budget to ${best_scenario[0]:,.0f}")
else:
    print(f"   Base budget is already the optimal scenario.")

print("=" * 70)


# ═══════════════════════════════════════════════════════════════════════════════
#  FINAL SUMMARY — Full allocation breakdown
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("    FINAL BUDGET ALLOCATION")
print("=" * 70)
print(f"  Total Budget       : ${MAX_BUDGET:,.0f}")
print(f"  Expected ROI       : ${expected_roi:,.2f}")
print(f"  Channels selected  : {len(best_channels)}")
print("-" * 70)

for channel, fraction in sorted(best_state.allocations.items(), key=lambda x: x[1], reverse=True):
    dollars = fraction * MAX_BUDGET
    p       = all_profiles.get(channel)
    risk    = p.risk_label if p else ""
    bar     = "█" * int(fraction * 40)
    print(f"  {channel:<20} {fraction * 100:5.1f}%  {bar}  ${dollars:>10,.0f}  {risk}")

print("=" * 70)