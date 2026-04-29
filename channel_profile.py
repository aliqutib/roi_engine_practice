from dataclasses import dataclass
import statistics
import math
from typing import Dict

#------
from db import db


@dataclass
class ChannelProfile:

    name:str
    avg_roi:float
    avg_cost:float
    min_cost:float
    max_cost:float
    std_roi:float
    avg_conv_rate:float
    sample_count:int

    @property
    def entry_cost(self) -> float:
        """Minimum cost to activate this channel (10th percentile from dataset)"""
        return self.min_cost
    
    @property
    def roi_per_dollar(self) -> float:
        return self.avg_roi / self.avg_cost if self.avg_cost > 0 else 0
    
    @property
    def saftey_margin(self) -> float:
        """
        If a channel has high variance (std_roi/avg_roi is large),
        we are less confident it will hit avg_roi again → deflate more.
        
        Minimum margin is 5% even for stable channels.
        For 0 roi channel 10% Max
        Formula: margin = max(coefficient_of_variation, 0.05
        """

        if self.avg_roi == 0:
            return 0.1
        else:
            cv = self.std_roi / self.avg_roi
            return max(cv, 0.05)
    
    @property
    def admissible_roi(self) -> float:
        #applying saftey margin to make sure our algo never overestimate h(n)
        return self.avg_roi * (1 - self.saftey_margin)
    
    @property
    def avg_conversion(self) -> float:
        """Return conversion rate as a decimal (0-1 range)"""
        return self.avg_conv_rate
    
    @property
    def total_campaigns(self) -> int:
        """Total number of campaigns for this channel"""
        return self.sample_count
    
    @property
    def risk_score(self) -> float:
        """
        Risk score based on coefficient of variation (std_roi / avg_roi).
        Normalized to 0-1 range where:
        - 0 = very stable (low variance)
        - 1 = very risky (high variance)
        Uses sigmoid-like scaling: min(cv / 2.0, 1.0)
        """
        if self.avg_roi == 0:
            return 0.5  # Medium risk for zero ROI channels
        
        cv = self.std_roi / self.avg_roi
        # Normalize: cv of 2.0 or higher maps to 1.0 (high risk)
        return min(cv / 2.0, 1.0)
    
    @property
    def risk_label(self) -> str:
        """
        Categorize channel into risk tiers:
        - ✅ Safe: risk_score < 0.33
        - ⚠️ Moderate: 0.33 <= risk_score < 0.66
        - 🔴 Risky: risk_score >= 0.66
        """
        score = self.risk_score
        if score < 0.33:
            return "✅ Safe"
        elif score < 0.66:
            return "⚠️ Moderate"
        else:
            return "🔴 Risky"
    
    @property
    def best_case_roi(self) -> float:
        """
        Best-case ROI: average + 1 standard deviation
        Represents optimistic scenario (upper bound)
        """
        return self.avg_roi + self.std_roi
    
    @property
    def worst_case_roi(self) -> float:
        """
        Worst-case ROI: average - 1 standard deviation
        Represents pessimistic scenario (lower bound)
        """
        return max(self.avg_roi - self.std_roi, 0.0)  # Floor at 0
    
    def roi_at_spend(self, spend:float) -> float:
        """
            use diminishing return function (logarithmic) to 
            calculate roi if campaign budget is icrease than
            historically average cost of the campaign at specific channel
        """

        if spend <= 0 or self.avg_cost <= 0:
            return 0.0
        
        scale = spend / self.avg_cost
        scaled_roi = self.avg_roi * math.log2(1 + scale)
        return scaled_roi * (1.0 - self.saftey_margin)
    
def build_channel_profiles(db) -> Dict[str, ChannelProfile]:

    """
    This creates ChannelProfile Object for each channel in the database
    Uses mongo db pipeline and aggragation with python stats
    Returns: { "Email": ChannelProfile(...), "Social Media": ChannelProfile(...), ... }
    """
    
    mongo_pipeline = [
        {
            "$project": {
                "channel": 1,
                "roi": 1,
                "budget": 1,
                "conversion_rate":1
            }
        },
        {
            "$group" :{
                "_id": "$channel",
                "roi_values": {"$push": "$roi"},  #for std_roi
                "cost_values": {"$push": "$budget"}, #for 10th and 90th percentile of the budget
                "avg_conv_rate": {"$avg": "$conversion_rate"},
                "count": {"$sum": 1}
            }
        }
    ]

    profiles = {}
    raw_results = list(db.campaigns.aggregate(mongo_pipeline))

    for doc in raw_results:
        channel_name = doc["_id"]
        roi_values = doc["roi_values"]
        cost_values = sorted(doc["cost_values"])
        
        avg_cost = statistics.mean(cost_values)
        avg_roi = statistics.mean(roi_values)
        std_roi = statistics.stdev(roi_values) if len(roi_values) > 1 else avg_roi*0.10

        n = len(doc["cost_values"])
        min_cost = cost_values[max(0, int(0.10 * n))]       #10th percentile
        max_cost = cost_values[min(n - 1, int(0.90 * n))]   #90th percentile

        profiles[channel_name] = ChannelProfile(
            name=channel_name,
            avg_roi=avg_roi,
            avg_cost=avg_cost,
            min_cost=min_cost,
            max_cost=max_cost,
            std_roi=std_roi,
            avg_conv_rate=doc["avg_conv_rate"],
            sample_count=doc["count"]
        )

    return profiles


def rank_channels(all_profiles: Dict[str, ChannelProfile]) -> list:
    """
    Rank channels by composite score.
    
    Composite Score = 50% ROI efficiency + 30% conversion rate + 20% conservative ROI
    
    Returns: List of tuples (rank, channel_name, composite_score) sorted by score descending
    """
    
    if not all_profiles:
        return []
    
    # Normalize each metric to 0-1 range
    roi_per_dollar_values = [p.roi_per_dollar for p in all_profiles.values()]
    conversion_rates = [p.avg_conversion for p in all_profiles.values()]
    admissible_rois = [p.admissible_roi for p in all_profiles.values()]
    
    max_roi_per_dollar = max(roi_per_dollar_values) if roi_per_dollar_values else 1
    max_conversion = max(conversion_rates) if conversion_rates else 1
    max_admissible_roi = max(admissible_rois) if admissible_rois else 1
    
    scores = {}
    for name, profile in all_profiles.items():
        # Normalize each component to 0-1
        roi_efficiency = profile.roi_per_dollar / max_roi_per_dollar if max_roi_per_dollar > 0 else 0
        conversion_norm = profile.avg_conversion / max_conversion if max_conversion > 0 else 0
        roi_norm = profile.admissible_roi / max_admissible_roi if max_admissible_roi > 0 else 0
        
        # Composite score
        composite = (0.50 * roi_efficiency) + (0.30 * conversion_norm) + (0.20 * roi_norm)
        scores[name] = composite
    
    # Sort by score descending and create ranked list
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [(rank + 1, name, score) for rank, (name, score) in enumerate(ranked)]


def search_channels(
    all_profiles: Dict[str, ChannelProfile],
    search_query: str = "",
    risk_filter: str = "all",
    min_roi: float = 0.0
) -> Dict[str, ChannelProfile]:
    """
    Filter and search channels based on query and criteria.
    
    Args:
        all_profiles: Dictionary of all channel profiles
        search_query: String to match against channel name (case-insensitive)
        risk_filter: Risk level filter ("all", "safe", "moderate", "risky")
        min_roi: Minimum average ROI threshold
    
    Returns:
        Dictionary of filtered profiles matching all criteria
    """
    
    filtered = {}
    
    for name, profile in all_profiles.items():
        # Check search query (substring match, case-insensitive)
        if search_query and search_query.lower() not in name.lower():
            continue
        
        # Check risk filter
        if risk_filter != "all":
            if risk_filter == "safe" and "Safe" not in profile.risk_label:
                continue
            elif risk_filter == "moderate" and "Moderate" not in profile.risk_label:
                continue
            elif risk_filter == "risky" and "Risky" not in profile.risk_label:
                continue
        
        # Check minimum ROI threshold
        if profile.avg_roi < min_roi:
            continue
        
        filtered[name] = profile
    
    return filtered

