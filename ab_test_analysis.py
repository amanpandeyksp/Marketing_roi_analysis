"""
A/B Test Analysis: Landing Page Control vs Variant
Demonstrates proper statistical rigor: two-proportion z-test, confidence
intervals, absolute/relative uplift, and translation into business impact.
"""
import numpy as np
import pandas as pd
from scipy import stats

df = pd.read_csv("ab_test.csv")

agg = df.groupby("group").agg(visitors=("visitors", "sum"),
                               conversions=("conversions", "sum")).reset_index()

n_control = int(agg.loc[agg["group"] == "control", "visitors"].iloc[0])
x_control = int(agg.loc[agg["group"] == "control", "conversions"].iloc[0])
n_variant = int(agg.loc[agg["group"] == "variant", "visitors"].iloc[0])
x_variant = int(agg.loc[agg["group"] == "variant", "conversions"].iloc[0])

p_control = x_control / n_control
p_variant = x_variant / n_variant

# ---------------------------------------------------------------
# Two-proportion z-test (pooled, two-sided)
# ---------------------------------------------------------------
p_pool = (x_control + x_variant) / (n_control + n_variant)
se_pool = np.sqrt(p_pool * (1 - p_pool) * (1 / n_control + 1 / n_variant))
z_stat = (p_variant - p_control) / se_pool
p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))

# ---------------------------------------------------------------
# Confidence interval on the difference (unpooled SE, standard for CI)
# ---------------------------------------------------------------
se_diff = np.sqrt(p_control * (1 - p_control) / n_control +
                   p_variant * (1 - p_variant) / n_variant)
diff = p_variant - p_control
ci_low = diff - 1.96 * se_diff
ci_high = diff + 1.96 * se_diff

# ---------------------------------------------------------------
# Uplift
# ---------------------------------------------------------------
absolute_uplift = diff
relative_uplift = diff / p_control

# ---------------------------------------------------------------
# Minimum sample size check (post-hoc power context):
# what sample size would have been required to detect this effect
# at 80% power, alpha=0.05, two-sided — using observed rates
# ---------------------------------------------------------------
alpha = 0.05
power = 0.80
z_alpha = stats.norm.ppf(1 - alpha / 2)
z_beta = stats.norm.ppf(power)
p_bar = (p_control + p_variant) / 2
required_n_per_group = ((z_alpha * np.sqrt(2 * p_bar * (1 - p_bar)) +
                          z_beta * np.sqrt(p_control * (1 - p_control) + p_variant * (1 - p_variant))) ** 2
                         / (diff ** 2))

# ---------------------------------------------------------------
# Business impact projection
# ---------------------------------------------------------------
# Use blended AOV from the broader campaign dataset for a realistic revenue read-through
daily = pd.read_csv("daily_performance.csv")
blended_aov = daily["revenue"].sum() / daily["purchases"].sum()

MONTHLY_LANDING_PAGE_VISITORS = 50000  # assumed traffic volume if rolled out site-wide
incremental_conversions_per_month = MONTHLY_LANDING_PAGE_VISITORS * absolute_uplift
incremental_monthly_revenue = incremental_conversions_per_month * blended_aov
incremental_annual_revenue = incremental_monthly_revenue * 12

# ---------------------------------------------------------------
# REPORT
# ---------------------------------------------------------------
print("=" * 70)
print("A/B TEST: LANDING PAGE CONTROL vs VARIANT")
print("=" * 70)
print(f"Control:  n={n_control:,}  conversions={x_control:,}  rate={p_control:.4%}")
print(f"Variant:  n={n_variant:,}  conversions={x_variant:,}  rate={p_variant:.4%}")
print("-" * 70)
print(f"Absolute uplift:        {absolute_uplift:+.4%}  ({absolute_uplift*100:+.2f} pp)")
print(f"Relative uplift:        {relative_uplift:+.2%}")
print(f"95% CI on difference:   [{ci_low:.4%}, {ci_high:.4%}]")
print(f"Z-statistic:            {z_stat:.3f}")
print(f"P-value (two-sided):    {p_value:.5f}")
print(f"Statistically significant at alpha=0.05: {p_value < 0.05}")
print(f"Required n/group for 80% power (post-hoc): {required_n_per_group:,.0f}  "
      f"(actual n/group: {n_control:,})")
print("-" * 70)
print(f"Blended AOV from campaign data: ${blended_aov:,.2f}")
print(f"Assumed monthly landing-page traffic: {MONTHLY_LANDING_PAGE_VISITORS:,}")
print(f"Projected incremental conversions/month: {incremental_conversions_per_month:,.0f}")
print(f"Projected incremental revenue/month:     ${incremental_monthly_revenue:,.0f}")
print(f"Projected incremental revenue/year:      ${incremental_annual_revenue:,.0f}")
print("=" * 70)

# Save a results dict for the dashboard to consume
results = {
    "n_control": n_control, "x_control": x_control, "p_control": p_control,
    "n_variant": n_variant, "x_variant": x_variant, "p_variant": p_variant,
    "absolute_uplift": absolute_uplift, "relative_uplift": relative_uplift,
    "ci_low": ci_low, "ci_high": ci_high,
    "z_stat": z_stat, "p_value": p_value,
    "significant": bool(p_value < 0.05),
    "required_n_per_group": required_n_per_group,
    "blended_aov": blended_aov,
    "incremental_monthly_revenue": incremental_monthly_revenue,
    "incremental_annual_revenue": incremental_annual_revenue,
}
pd.Series(results).to_json("ab_test_results.json")
print("\nSaved -> ab_test_results.json")
