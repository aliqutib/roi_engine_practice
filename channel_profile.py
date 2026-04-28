from dataclasses import dataclass
from typing import Dict, List, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# CHANNEL PROFILE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ChannelProfile:
    """
    Summary statistics for one marketing channel.

    channel_name    : e.g. "Facebook", "Email"
    avg_roi         : average ROI across all campaigns on this channel
    std_roi         : standard deviation of ROI (used as risk penalty)
    avg_cost        : average acquisition cost ($)
    avg_conversion  : average conversion rate (0.0 – 1.0)
    total_campaigns : number of campaigns in the dataset for this channel

    Derived properties:
      roi_per_dollar  : avg_roi / avg_cost  — efficiency used in heuristic
      admissible_roi  : avg_roi - std_roi   — conservative ROI estimate
                        never over-estimates true ROI (admissibility condition)
      risk_label      : Safe / Moderate / Risky based on coefficient of variation
      risk_score      : 0.0 (safest) → 1.0 (riskiest)
    """

    channel_name    : str
    avg_roi         : float
    std_roi         : float
    avg_cost        : float
    avg_conversion  : float
    total_campaigns : int

    # ── Existing derived properties ───────────────────────────────────────────

    @property
    def roi_per_dollar(self) -> float:
        if self.avg_cost <= 0:
            return 0.0
        return self.avg_roi / self.avg_cost

    @property
    def admissible_roi(self) -> float:
        return max(0.0, self.avg_roi - self.std_roi)

    # ── NEW: Risk properties ──────────────────────────────────────────────────

    @property
    def risk_score(self) -> float:
        """
        Coefficient of Variation (CV) = std_roi / avg_roi
        Tells us: how much does ROI fluctuate relative to its average?
        Higher CV = more unpredictable = riskier channel.
        Clamped between 0.0 and 1.0 for easy comparison.
        """
        if self.avg_roi <= 0:
            return 1.0                          # no positive ROI = max risk
        cv = self.std_roi / self.avg_roi
        return min(cv, 1.0)                     # cap at 1.0

    @property
    def risk_label(self) -> str:
        """
        Human-readable risk label based on risk_score thresholds:
          < 0.33  →  Safe      (consistent ROI, low variance)
          < 0.66  →  Moderate  (some fluctuation, acceptable)
          ≥ 0.66  →  Risky     (high variance, unpredictable)
        """
        if self.risk_score < 0.33:
            return " Safe"
        elif self.risk_score < 0.66:
            return "  Moderate"
        else:
            return " Risky"

    @property
    def best_case_roi(self) -> float:
        """Optimistic ROI: avg + 1 standard deviation"""
        return self.avg_roi + self.std_roi

    @property
    def worst_case_roi(self) -> float:
        """Pessimistic ROI: avg - 1 standard deviation (floored at 0)"""
        return max(0.0, self.avg_roi - self.std_roi)

    def __repr__(self) -> str:
        return (
            f"ChannelProfile({self.channel_name} | "
            f"avg_roi={self.avg_roi:.4f} | "
            f"std_roi={self.std_roi:.4f} | "
            f"avg_cost=${self.avg_cost:,.2f} | "
            f"roi_per_dollar={self.roi_per_dollar:.6f} | "
            f"risk={self.risk_label})"
        )


# ─────────────────────────────────────────────────────────────────────────────
# BUILD PROFILES FROM MONGODB
# ─────────────────────────────────────────────────────────────────────────────

def build_channel_profiles(db) -> Dict[str, "ChannelProfile"]:
    """
    Reads campaign records from MongoDB and builds one ChannelProfile
    per unique channel using an aggregation pipeline.
    """

    pipeline = [
        {
            "$group": {
                "_id"           : "$channel",
                "avg_roi"       : {"$avg": "$roi"},
                "std_roi"       : {"$stdDevPop": "$roi"},
                "avg_cost"      : {"$avg": "$budget"},
                "avg_conversion": {"$avg": "$conversion_rate"},
                "count"         : {"$sum": 1}
            }
        },
        {"$sort": {"avg_roi": -1}}
    ]

    results  = list(db.campaigns.aggregate(pipeline))
    profiles = {}

    for r in results:
        channel = r["_id"]
        profiles[channel] = ChannelProfile(
            channel_name    = channel,
            avg_roi         = round(r["avg_roi"], 6),
            std_roi         = round(r.get("std_roi") or 0.0, 6),
            avg_cost        = round(r["avg_cost"], 2),
            avg_conversion  = round(r["avg_conversion"], 6),
            total_campaigns = int(r["count"])
        )

    print(f"\nChannel Profiles built from MongoDB ({len(profiles)} channels):")
    for name, p in profiles.items():
        print(f"  {p}")

    return profiles


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE 1 — CHANNEL RANKING REPORT
# Scores every channel by a composite of ROI efficiency, conversion rate,
# and admissible (conservative) ROI.
# Higher composite score = better overall channel.
# ─────────────────────────────────────────────────────────────────────────────

def rank_channels(profiles: Dict[str, "ChannelProfile"]) -> List[Tuple[int, str, float]]:
    """
    Ranks all channels by a composite score:

      Composite Score = 0.5 * roi_per_dollar
                      + 0.3 * avg_conversion
                      + 0.2 * admissible_roi

    WHY THESE WEIGHTS?
      - roi_per_dollar  (50%) → efficiency is most important
      - avg_conversion  (30%) → channels that convert are valuable
      - admissible_roi  (20%) → conservative ROI avoids overconfidence

    RETURNS:
        List of (rank, channel_name, composite_score) sorted best → worst
    """

    scored = []
    for name, p in profiles.items():
        score = (
            0.5 * p.roi_per_dollar +
            0.3 * p.avg_conversion +
            0.2 * p.admissible_roi
        )
        scored.append((name, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    ranked = [(rank + 1, name, score) for rank, (name, score) in enumerate(scored)]
    return ranked


def print_ranking_report(profiles: Dict[str, "ChannelProfile"]) -> None:
    """Prints a formatted leaderboard of all channels with risk labels."""

    ranked = rank_channels(profiles)

    print("\n" + "=" * 70)
    print("    CHANNEL RANKING REPORT")
    print("=" * 70)
    print(f"  {'Rank':<6} {'Channel':<20} {'Score':>8}  {'ROI/Dollar':>10}  {'Conv%':>6}  {'Risk':<14}")
    print("-" * 70)

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}

    for rank, name, score in ranked:
        p      = profiles[name]
        medal  = medals.get(rank, f"#{rank:<2} ")
        bar    = "█" * int(score * 300)
        print(f"  {medal}  {name:<20} {score:>8.5f}  {p.roi_per_dollar:>10.6f}  {p.avg_conversion:>5.1%}  {p.risk_label}")
        print(f"        {bar}")

    print("=" * 70)


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE 2 — RISK ANALYSIS REPORT
# Classifies every channel as Safe / Moderate / Risky.
# Shows best-case and worst-case ROI projections per channel.
# ─────────────────────────────────────────────────────────────────────────────

def print_risk_analysis(profiles: Dict[str, "ChannelProfile"], total_budget: float) -> None:
    """
    Prints a full risk breakdown for every channel:
      - Risk score (0 = safest, 1 = riskiest)
      - Risk label (Safe / Moderate / Risky)
      - Best case ROI  (avg + 1 std deviation)
      - Worst case ROI (avg - 1 std deviation, floored at 0)
      - Budget exposure at avg_cost
    """

    # Group channels by risk label for a summary section
    safe_channels     = [n for n, p in profiles.items() if p.risk_score < 0.33]
    moderate_channels = [n for n, p in profiles.items() if 0.33 <= p.risk_score < 0.66]
    risky_channels    = [n for n, p in profiles.items() if p.risk_score >= 0.66]

    print("\n" + "=" * 70)
    print("     RISK ANALYSIS REPORT")
    print("=" * 70)
    print(f"  {'Channel':<20} {'Risk':<14} {'Score':>6}  {'Worst ROI':>9}  {'Avg ROI':>9}  {'Best ROI':>9}")
    print("-" * 70)

    # Sort by risk score ascending (safest first)
    sorted_profiles = sorted(profiles.items(), key=lambda x: x[1].risk_score)

    for name, p in sorted_profiles:
        print(
            f"  {name:<20} {p.risk_label:<14} {p.risk_score:>6.3f}  "
            f"{p.worst_case_roi:>9.4f}  {p.avg_roi:>9.4f}  {p.best_case_roi:>9.4f}"
        )

    print("-" * 70)
    print(f"\n  SUMMARY")
    print(f"  Safe channels     : {len(safe_channels)}  → {', '.join(safe_channels) or 'None'}")
    print(f"  Moderate channels : {len(moderate_channels)}  → {', '.join(moderate_channels) or 'None'}")
    print(f"  Risky channels    : {len(risky_channels)}  → {', '.join(risky_channels) or 'None'}")
    print("=" * 70)


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE 3 — CHANNEL SEARCH & FILTER
# Search channels by name (partial match).
# Filter by risk level or minimum ROI threshold.
# ─────────────────────────────────────────────────────────────────────────────

def search_channels(
        profiles    : Dict[str, "ChannelProfile"],
        query       : str  = "",
        risk_filter : str  = "all",       # "safe", "moderate", "risky", or "all"
        min_roi     : float = 0.0,        # minimum avg_roi to include
) -> Dict[str, "ChannelProfile"]:
    """
    Search and filter channels.

    PARAMETERS:
      query       : partial channel name to search (case-insensitive)
                    e.g. "face" matches "Facebook"
      risk_filter : filter by risk level — "safe", "moderate", "risky", "all"
      min_roi     : only include channels with avg_roi >= this value

    RETURNS:
      Filtered dict of ChannelProfile matching all criteria
    """

    results = {}

    for name, p in profiles.items():

        # Name search — case insensitive partial match
        if query and query.lower() not in name.lower():
            continue

        # Risk filter
        if risk_filter == "safe"     and p.risk_score >= 0.33:
            continue
        if risk_filter == "moderate" and not (0.33 <= p.risk_score < 0.66):
            continue
        if risk_filter == "risky"    and p.risk_score < 0.66:
            continue

        # Minimum ROI filter
        if p.avg_roi < min_roi:
            continue

        results[name] = p

    return results


def print_search_results(
        profiles    : Dict[str, "ChannelProfile"],
        query       : str   = "",
        risk_filter : str   = "all",
        min_roi     : float = 0.0,
) -> None:
    """Runs search_channels and prints the results in a clean table."""

    results = search_channels(profiles, query, risk_filter, min_roi)

    print("\n" + "=" * 70)
    print(f"  🔍  CHANNEL SEARCH RESULTS")
    if query:
        print(f"      Query      : '{query}'")
    if risk_filter != "all":
        print(f"      Risk filter: {risk_filter.capitalize()}")
    if min_roi > 0:
        print(f"      Min ROI    : {min_roi}")
    print("=" * 70)

    if not results:
        print("  No channels matched your search criteria.")
        print("=" * 70)
        return

    print(f"  Found {len(results)} channel(s):\n")
    print(f"  {'Channel':<20} {'Avg ROI':>8}  {'Risk':<14} {'Conv%':>6}  {'Avg Cost':>10}")
    print("-" * 70)

    for name, p in sorted(results.items(), key=lambda x: x[1].avg_roi, reverse=True):
        print(
            f"  {name:<20} {p.avg_roi:>8.4f}  {p.risk_label:<14} "
            f"{p.avg_conversion:>5.1%}  ${p.avg_cost:>9,.2f}"
        )

    print("=" * 70)