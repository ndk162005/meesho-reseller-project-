-- ==========================================
-- Meesho Reseller Intelligence - SQL Queries
-- ==========================================

-- Query 1: Monthly Category Revenue and Order Count (15 rows)
-- Output: part1_sql/output/monthly_category_revenue.csv
-- Columns: month,category,revenue,n_orders
SELECT 
    CASE substr(order_date, 6, 2)
        WHEN '04' THEN 'April'
        WHEN '05' THEN 'May'
        WHEN '06' THEN 'June'
    END AS month,
    category,
    ROUND(SUM(order_value), 2) AS revenue,
    COUNT(order_id) AS n_orders
FROM orders
GROUP BY month, category
ORDER BY 
    CASE month
        WHEN 'April' THEN 1
        WHEN 'May' THEN 2
        WHEN 'June' THEN 3
    END,
    category;

-- Query 2: Regional Revenue Analysis
-- Output: part1_sql/output/region_revenue.csv
SELECT 
    r.region,
    ROUND(SUM(o.order_value), 2) AS revenue,
    COUNT(o.order_id) AS n_orders
FROM resellers r
LEFT JOIN orders o ON r.reseller_id = o.reseller_id
GROUP BY r.region
ORDER BY revenue DESC;

-- Query 3: Top 5 Resellers by Delivered Revenue
-- Output: part1_sql/output/top_resellers.csv
SELECT 
    r.reseller_id,
    r.reseller_name,
    r.region,
    ROUND(SUM(o.order_value), 2) AS delivered_revenue,
    COUNT(o.order_id) AS delivered_orders
FROM resellers r
JOIN orders o ON r.reseller_id = o.reseller_id
WHERE o.order_status = 'Delivered'
GROUP BY r.reseller_id, r.reseller_name, r.region
ORDER BY delivered_revenue DESC
LIMIT 5;

-- Query 4a: Zero-Order Resellers Identification
-- Output: part1_sql/output/zero_order_resellers.csv
SELECT 
    r.reseller_id,
    r.reseller_name,
    r.region
FROM resellers r
LEFT JOIN orders o ON r.reseller_id = o.reseller_id
GROUP BY r.reseller_id, r.reseller_name, r.region
HAVING COUNT(o.order_id) = 0;

-- Query 4b: COUNT(*) vs COUNT(order_id) Demonstration
-- Output: part1_sql/output/zero_order_count_demo.csv
SELECT 
    r.reseller_id,
    r.reseller_name,
    COUNT(*) AS count_star,
    COUNT(o.order_id) AS count_order_id
FROM resellers r
LEFT JOIN orders o ON r.reseller_id = o.reseller_id
GROUP BY r.reseller_id, r.reseller_name
ORDER BY count_order_id ASC, r.reseller_id ASC;

-- Query 5: June Delivered Average Order Value (AOV)
-- Output: part1_sql/output/june_aov.csv
SELECT 
    'June' AS month,
    ROUND(SUM(order_value), 2) AS delivered_revenue,
    COUNT(order_id) AS delivered_orders,
    ROUND(SUM(order_value) / COUNT(order_id), 2) AS aov
FROM orders
WHERE order_date LIKE '2024-06%'
  AND order_status = 'Delivered';
