"""
Generates a realistic synthetic dataset for the Marketing Campaign ROI project.
Produces:
  - campaigns.csv        : campaign metadata (channel, geography, segment, device, age group, dates)
  - daily_performance.csv: daily funnel metrics per campaign (impressions -> clicks -> leads -> purchases -> revenue -> cost)
  - ab_test.csv           : landing page A/B test raw visitor-level outcomes
"""

import numpy as np
import pandas as pd
from datetime import date, timedelta

rng = np.random.default_rng(42)
# 1. CAMPAIGN METADATA
channels = ["Facebook", "Google", "Email", "Instagram", "TikTok", "Affiliate"]
geographies = ["North America", "Europe", "APAC", "LATAM"]
segments = ["New Customers", "Returning Customers", "High-Value", "Price-Sensitive"]
devices = ["Mobile", "Desktop", "Tablet"]
age_groups = ["18-24", "25-34", "35-44", "45-54", "55+"]

# channel-level base performance characteristics (used to make data realistic, not uniform-random)
channel_profile = {
    "Facebook":   dict(ctr=0.018, lead_rate=0.09,  purchase_rate=0.16, cpc=0.85, aov=68),
    "Google":     dict(ctr=0.035, lead_rate=0.14,  purchase_rate=0.22, cpc=1.35, aov=74),
    "Email":      dict(ctr=0.045, lead_rate=0.20,  purchase_rate=0.28, cpc=0.15, aov=61),
    "Instagram":  dict(ctr=0.014, lead_rate=0.08,  purchase_rate=0.14, cpc=0.95, aov=59),
    "TikTok":     dict(ctr=0.021, lead_rate=0.06,  purchase_rate=0.10, cpc=0.70, aov=45),
    "Affiliate":  dict(ctr=0.026, lead_rate=0.11,  purchase_rate=0.19, cpc=1.10, aov=70),
}

N_CAMPAIGNS = 40
start_range = pd.date_range("2025-01-01", "2025-11-01", freq="15D")

campaigns = []
for i in range(1, N_CAMPAIGNS + 1):
    channel = rng.choice(channels, p=[0.25, 0.22, 0.18, 0.15, 0.12, 0.08])
    start = rng.choice(start_range)
    duration = int(rng.integers(20, 75))
    campaigns.append({
        "campaign_id": f"C{i:03d}",
        "campaign_name": f"{channel}_{rng.choice(segments).split()[0]}_{pd.Timestamp(start).strftime('%b%Y')}",
        "channel": channel,
        "geography": rng.choice(geographies, p=[0.40, 0.28, 0.22, 0.10]),
        "segment": rng.choice(segments),
        "device_focus": rng.choice(devices, p=[0.55, 0.35, 0.10]),
        "age_group": rng.choice(age_groups),
        "start_date": pd.Timestamp(start),
        "end_date": pd.Timestamp(start) + timedelta(days=duration),
        "daily_budget": round(rng.uniform(80, 900), 2),
    })

campaigns_df = pd.DataFrame(campaigns)
# 2. DAILY PERFORMANCE (funnel: impressions -> clicks -> leads -> purchases -> revenue)
rows = []
for _, camp in campaigns_df.iterrows():
    prof = channel_profile[camp["channel"]]
    days = pd.date_range(camp["start_date"], camp["end_date"], freq="D")
    # slight ramp-up/fatigue curve over the campaign lifetime
    lifecycle = np.linspace(0.8, 1.0, len(days) // 2).tolist()
    lifecycle += np.linspace(1.0, 0.65, len(days) - len(lifecycle)).tolist()

    for day, life_mult in zip(days, lifecycle):
        dow_mult = 1.15 if day.weekday() in (5, 6) else 1.0  # weekend bump for e-comm
        noise = rng.normal(1, 0.12)

        impressions = max(0, int(rng.normal(9000, 2200) * life_mult * dow_mult * noise))
        ctr = max(0.001, rng.normal(prof["ctr"], prof["ctr"] * 0.18))
        clicks = int(impressions * ctr)
        lead_rate = max(0.005, rng.normal(prof["lead_rate"], prof["lead_rate"] * 0.15))
        leads = int(clicks * lead_rate)
        purchase_rate = max(0.01, rng.normal(prof["purchase_rate"], prof["purchase_rate"] * 0.15))
        purchases = int(leads * purchase_rate)
        aov = max(15, rng.normal(prof["aov"], prof["aov"] * 0.2))
        revenue = round(purchases * aov, 2)
        cpc = max(0.05, rng.normal(prof["cpc"], prof["cpc"] * 0.1))
        cost = round(min(camp["daily_budget"], clicks * cpc), 2)

        rows.append({
            "date": day,
            "campaign_id": camp["campaign_id"],
            "impressions": impressions,
            "clicks": clicks,
            "leads": leads,
            "purchases": purchases,
            "revenue": revenue,
            "cost": cost,
        })

daily_df = pd.DataFrame(rows)
# 3. A/B TEST: Landing page control vs variant (visitor-level, aggregated to daily for realism)-
ab_start = pd.Timestamp("2025-09-01")
ab_days = pd.date_range(ab_start, periods=21, freq="D")

ab_rows = []
true_control_rate = 0.081
true_variant_rate = 0.094

for day in ab_days:
    visitors_control = int(rng.normal(950, 60))
    visitors_variant = int(rng.normal(950, 60))
    conversions_control = int(rng.binomial(visitors_control, true_control_rate))
    conversions_variant = int(rng.binomial(visitors_variant, true_variant_rate))
    ab_rows.append({"date": day, "group": "control", "visitors": visitors_control, "conversions": conversions_control})
    ab_rows.append({"date": day, "group": "variant", "visitors": visitors_variant, "conversions": conversions_variant})

ab_df = pd.DataFrame(ab_rows)
campaigns_df.to_csv("campaigns.csv", index=False)
daily_df.to_csv("daily_performance.csv", index=False)
ab_df.to_csv("ab_test.csv", index=False)

print("campaigns:", campaigns_df.shape)
print("daily_performance:", daily_df.shape)
print("ab_test:", ab_df.shape)
print(daily_df.head())
