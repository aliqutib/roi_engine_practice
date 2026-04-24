from channel_profile import build_channel_profiles
from db import db

# Build profiles and inspect them
all_profiles = build_channel_profiles(db)

print("=" * 70)
print("CHANNEL PROFILE ANALYSIS")
print("=" * 70)

for channel_name in sorted(all_profiles.keys()):
    profile = all_profiles[channel_name]
    print(f"\n{channel_name}:")
    print(f"  avg_roi:           {profile.avg_roi:.4f}")
    print(f"  avg_cost:          ${profile.avg_cost:,.2f}")
    print(f"  roi_per_dollar:    {profile.roi_per_dollar:.6f}")
    print(f"  std_roi:           {profile.std_roi:.4f}")
    print(f"  safety_margin:     {profile.saftey_margin:.4f}")
    print(f"  admissible_roi:    {profile.admissible_roi:.4f}")
    print(f"  min_cost:          ${profile.min_cost:,.2f}")
    print(f"  max_cost:          ${profile.max_cost:,.2f}")
    
    # Test roi_at_spend for different amounts
    test_spends = [10000, 50000, 100000]
    print(f"  roi_at_spend tests:")
    for spend in test_spends:
        roi = profile.roi_at_spend(spend)
        print(f"    ${spend:>6,} → ROI: {roi:.4f}")

# Show ROI per dollar ranking
print("\n" + "=" * 70)
print("RANKING BY ROI PER DOLLAR")
print("=" * 70)
sorted_channels = sorted(all_profiles.items(), 
                        key=lambda x: x[1].roi_per_dollar, 
                        reverse=True)
for i, (channel_name, profile) in enumerate(sorted_channels, 1):
    print(f"{i}. {channel_name:<20} {profile.roi_per_dollar:.6f}")
