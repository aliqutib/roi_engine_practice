from dataclasses import dataclass, field
import statistics

#------
from db import db


@dataclass
class ChannelProfile:

    name:str
    avg_roi:float
    avg_cost:float
    std_roi:float
    avg_conv_rate:float
    sample_count:int

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
        return self.avg_roi - (1-self.saftey_margin)
    
def build_channel_profile(db) -> Dict[str, ChannelProfile]:

    #This creates ChannelProfile Object for each channel in the database
    #Uses mongo db pipeline and aggragation with python stats

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
                #we are keeping all roi values at first step
                #without taking mean because we also need std
                "roi_values": {"$push": "$roi"}, 
                "avg_cost": {"$avg": "$budget"},
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

        avg_roi = statistics.mean(roi_values)
        std_roi = statistics.stdev(roi_values) if len(roi_values) > 1 else avg_roi*0.10

        profiles[channel_name] = ChannelProfile(
            name=channel_name,
            avg_roi=avg_roi,
            avg_cost=doc["avg_cost"],
            std_roi=std_roi,
            avg_conv_rate=doc["avg_conv_rate"],
            sample_count=doc["count"]
        )

    return profiles


