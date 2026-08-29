-- =====================================================================
-- MARKETING CAMPAIGN ROI & CONVERSION ANALYSIS — SQL ANALYSIS SUITE
-- Engine: SQLite (marketing.db)
-- Tables: campaigns, daily_performance, ab_test
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. CORE FUNNEL METRICS PER CAMPAIGN
--    Demonstrates: JOIN, GROUP BY, CASE WHEN (safe division), aggregate funcs
-- ---------------------------------------------------------------------
SELECT
    c.campaign_id,
    c.campaign_name,
    c.channel,
    c.geography,
    c.segment,
    SUM(d.impressions)                                       AS impressions,
    SUM(d.clicks)                                             AS clicks,
    SUM(d.leads)                                              AS leads,
    SUM(d.purchases)                                          AS purchases,
    ROUND(SUM(d.revenue), 2)                                  AS revenue,
    ROUND(SUM(d.cost), 2)                                     AS cost,
    -- CTR: clicks / impressions
    ROUND(CASE WHEN SUM(d.impressions) = 0 THEN 0
               ELSE 100.0 * SUM(d.clicks) / SUM(d.impressions) END, 3)  AS ctr_pct,
    -- CPC: cost / clicks
    ROUND(CASE WHEN SUM(d.clicks) = 0 THEN 0
               ELSE SUM(d.cost) / SUM(d.clicks) END, 2)       AS cpc,
    -- CPL: cost / leads
    ROUND(CASE WHEN SUM(d.leads) = 0 THEN 0
               ELSE SUM(d.cost) / SUM(d.leads) END, 2)        AS cpl,
    -- Conversion rate: purchases / clicks
    ROUND(CASE WHEN SUM(d.clicks) = 0 THEN 0
               ELSE 100.0 * SUM(d.purchases) / SUM(d.clicks) END, 2) AS conversion_rate_pct,
    -- CAC: cost / purchases (treating each purchase as a new customer acquisition)
    ROUND(CASE WHEN SUM(d.purchases) = 0 THEN 0
               ELSE SUM(d.cost) / SUM(d.purchases) END, 2)    AS cac,
    -- ROAS: revenue / cost
    ROUND(CASE WHEN SUM(d.cost) = 0 THEN 0
               ELSE SUM(d.revenue) / SUM(d.cost) END, 2)      AS roas,
    -- Campaign ROI %: (revenue - cost) / cost
    ROUND(CASE WHEN SUM(d.cost) = 0 THEN 0
               ELSE 100.0 * (SUM(d.revenue) - SUM(d.cost)) / SUM(d.cost) END, 1) AS roi_pct
FROM campaigns c
JOIN daily_performance d ON c.campaign_id = d.campaign_id
GROUP BY c.campaign_id, c.campaign_name, c.channel, c.geography, c.segment
ORDER BY roi_pct DESC;


-- ---------------------------------------------------------------------
-- 2. CHANNEL-LEVEL COMPARISON WITH RANKING
--    Demonstrates: CTE, window function RANK(), subquery
-- ---------------------------------------------------------------------
WITH channel_agg AS (
    SELECT
        c.channel,
        SUM(d.impressions) AS impressions,
        SUM(d.clicks)      AS clicks,
        SUM(d.leads)       AS leads,
        SUM(d.purchases)   AS purchases,
        SUM(d.revenue)     AS revenue,
        SUM(d.cost)        AS cost
    FROM campaigns c
    JOIN daily_performance d ON c.campaign_id = d.campaign_id
    GROUP BY c.channel
),
channel_metrics AS (
    SELECT
        channel,
        impressions, clicks, leads, purchases, revenue, cost,
        ROUND(100.0 * clicks / NULLIF(impressions, 0), 3)        AS ctr_pct,
        ROUND(cost / NULLIF(clicks, 0), 2)                       AS cpc,
        ROUND(cost / NULLIF(purchases, 0), 2)                    AS cac,
        ROUND(revenue / NULLIF(cost, 0), 2)                      AS roas,
        ROUND(100.0 * (revenue - cost) / NULLIF(cost, 0), 1)     AS roi_pct
    FROM channel_agg
)
SELECT
    *,
    RANK() OVER (ORDER BY roas DESC)        AS roas_rank,
    RANK() OVER (ORDER BY roi_pct DESC)     AS roi_rank,
    RANK() OVER (ORDER BY cac ASC)          AS cac_efficiency_rank
FROM channel_metrics
ORDER BY roi_pct DESC;


-- ---------------------------------------------------------------------
-- 3. MONTHLY TREND WITH MONTH-OVER-MONTH (MoM) GROWTH & RUNNING TOTAL
--    Demonstrates: date functions (strftime), window functions (LAG, SUM OVER),
--                  running total, MoM % calculation
-- ---------------------------------------------------------------------
WITH monthly AS (
    SELECT
        strftime('%Y-%m', date)   AS month,
        SUM(revenue)              AS revenue,
        SUM(cost)                 AS cost,
        SUM(purchases)            AS purchases
    FROM daily_performance
    GROUP BY strftime('%Y-%m', date)
)
SELECT
    month,
    revenue,
    cost,
    ROUND(revenue - cost, 2)                                        AS profit,
    purchases,
    -- Running total of revenue (cumulative)
    ROUND(SUM(revenue) OVER (ORDER BY month), 2)                    AS cumulative_revenue,
    -- Prior month revenue via LAG
    LAG(revenue) OVER (ORDER BY month)                              AS prior_month_revenue,
    -- Month-over-month % growth
    ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
          / NULLIF(LAG(revenue) OVER (ORDER BY month), 0), 1)       AS mom_growth_pct
FROM monthly
ORDER BY month;


-- ---------------------------------------------------------------------
-- 4. PERFORMANCE BY GEOGRAPHY x DEVICE x AGE GROUP (multi-dimensional slice)
--    Demonstrates: multiple JOIN keys via GROUP BY, CASE WHEN bucketing
-- ---------------------------------------------------------------------
SELECT
    c.geography,
    c.device_focus,
    c.age_group,
    COUNT(DISTINCT c.campaign_id)                              AS num_campaigns,
    SUM(d.revenue)                                             AS revenue,
    SUM(d.cost)                                                AS cost,
    ROUND(SUM(d.revenue) / NULLIF(SUM(d.cost), 0), 2)          AS roas,
    CASE
        WHEN SUM(d.revenue) / NULLIF(SUM(d.cost), 0) >= 3 THEN 'High Performer'
        WHEN SUM(d.revenue) / NULLIF(SUM(d.cost), 0) >= 1.5 THEN 'Solid'
        ELSE 'Underperforming'
    END AS performance_tier
FROM campaigns c
JOIN daily_performance d ON c.campaign_id = d.campaign_id
GROUP BY c.geography, c.device_focus, c.age_group
ORDER BY roas DESC;


-- ---------------------------------------------------------------------
-- 5. TOP-3 CAMPAIGNS PER CHANNEL BY ROI (window function partitioned ranking)
--    Demonstrates: PARTITION BY, ROW_NUMBER(), subquery filter
-- ---------------------------------------------------------------------
WITH ranked AS (
    SELECT
        c.channel,
        c.campaign_id,
        c.campaign_name,
        ROUND(SUM(d.revenue), 2) AS revenue,
        ROUND(SUM(d.cost), 2)    AS cost,
        ROUND(100.0 * (SUM(d.revenue) - SUM(d.cost)) / NULLIF(SUM(d.cost),0), 1) AS roi_pct,
        ROW_NUMBER() OVER (PARTITION BY c.channel ORDER BY
            100.0 * (SUM(d.revenue) - SUM(d.cost)) / NULLIF(SUM(d.cost),0) DESC) AS rn
    FROM campaigns c
    JOIN daily_performance d ON c.campaign_id = d.campaign_id
    GROUP BY c.channel, c.campaign_id, c.campaign_name
)
SELECT channel, campaign_id, campaign_name, revenue, cost, roi_pct
FROM ranked
WHERE rn <= 3
ORDER BY channel, roi_pct DESC;


-- ---------------------------------------------------------------------
-- 6. CAMPAIGNS OUTPERFORMING THE OVERALL AVERAGE ROAS (correlated subquery)
--    Demonstrates: scalar subquery in WHERE clause
-- ---------------------------------------------------------------------
SELECT
    c.campaign_id,
    c.campaign_name,
    c.channel,
    ROUND(SUM(d.revenue) / NULLIF(SUM(d.cost), 0), 2) AS roas
FROM campaigns c
JOIN daily_performance d ON c.campaign_id = d.campaign_id
GROUP BY c.campaign_id, c.campaign_name, c.channel
HAVING roas > (
    SELECT SUM(revenue) * 1.0 / SUM(cost) FROM daily_performance
)
ORDER BY roas DESC;


-- ---------------------------------------------------------------------
-- 7. A/B TEST RAW AGGREGATION (feeds Python statistical test)
--    Demonstrates: GROUP BY with SUM, simple aggregation for stats input
-- ---------------------------------------------------------------------
SELECT
    "group",
    SUM(visitors)                                      AS total_visitors,
    SUM(conversions)                                    AS total_conversions,
    ROUND(100.0 * SUM(conversions) / SUM(visitors), 2)  AS conversion_rate_pct
FROM ab_test
GROUP BY "group";
