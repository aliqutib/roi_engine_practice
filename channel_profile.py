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
