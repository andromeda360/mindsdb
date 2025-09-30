## Note: All data is between August 1st and 2nd, 2025

# checkout_errors

SELECT eventName, contentGroup, `customEvent:event_custom`, date,
totalUsers, eventCount
FROM shoplc_web_data
(
SELECT eventName, contentGroup, `customEvent:event_custom`, date,
totalUsers(),
eventCount()
FROM report_table
WHERE date BETWEEN '2025-08-01' AND '2025-08-02'
AND eventName = 'cx_jx_experience'
AND contentGroup = 'shoppingJourney-checkout'
AND `customEvent:event_custom` = 'cannot proceed to purchase (auto)'
ORDER BY date, eventName
)

# conversion_funnel_config

SELECT eventName, date, activeUsers, totalUsers, eventCount
FROM shoplc_web_data (
SELECT eventName, date, activeUsers(), totalUsers(), eventCount()
FROM report_table
WHERE date BETWEEN '2025-08-01' AND '2025-08-02'
AND eventName IN ('session_start', 'view_cart', 'add_to_cart', 'begin_checkout', 'purchase')
ORDER BY date, eventName
)

# conversion_funnel_mobile_config

## Same syntax as above, just change the database to reflect the mobile data

SELECT eventName, date, activeUsers, totalUsers, eventCount
FROM shoplc_mobile_data (
SELECT eventName, date, activeUsers(), totalUsers(), eventCount()
FROM report_table
WHERE date BETWEEN '2025-08-01' AND '2025-08-02'
AND eventName IN ('session_start', 'view_cart', 'add_to_cart', 'begin_checkout', 'purchase')
ORDER BY date, eventName
)

# conversion_funnel_sessionsource_config

SELECT eventName, date, sessionSource, activeUsers, totalUsers, eventCount
FROM shoplc_web_data (
SELECT eventName, date, sessionSource, activeUsers(), totalUsers(), eventCount()
FROM report_table
WHERE date BETWEEN '2025-08-01' AND '2025-08-02'
AND eventName IN ('session_start', 'view_cart', 'add_to_cart', 'begin_checkout', 'purchase')
GROUP BY eventName, date, sessionSource
ORDER BY date, sessionSource, eventName
)

# conversion_funnel_sessionsource_mobile_config

## Same syntax as above, just change the database to reflect the mobile data

SELECT eventName, date, sessionSource, activeUsers, totalUsers, eventCount
FROM shoplc_mobile_data (
SELECT eventName, date, sessionSource, activeUsers(), totalUsers(), eventCount()
FROM report_table
WHERE date BETWEEN '2025-08-01' AND '2025-08-02'
AND eventName IN ('session_start', 'view_cart', 'add_to_cart', 'begin_checkout', 'purchase')
GROUP BY eventName, date, sessionSource
ORDER BY date, sessionSource, eventName
)

# marketing_items_config

# mobile_purchase_order

SELECT transactionId, date, sessionMedium, eventName,
purchaseRevenue, shippingAmount, taxAmount, transactions
FROM shoplc_web_data
(
SELECT transactionId, date, sessionMedium, eventName,
purchaseRevenue(),
shippingAmount(),
taxAmount(),
transactions()
FROM report_table
WHERE date BETWEEN '2025-08-01' AND '2025-08-02'
AND eventName = 'purchase'
AND sessionMedium IN ('cpc', 'paidsocial', 'SMS', 'Email', 'Organic', 'Referral')
ORDER BY date, transactionId
)

# mobile_purchase_order_item

SELECT transactionId, date, sessionMedium, itemName, itemId, itemBrand, itemCategory, eventName,
itemsPurchased, itemRevenue
FROM shoplc_mobile_data
(
SELECT transactionId, date, sessionMedium, itemName, itemId, itemBrand, itemCategory, eventName,
itemsPurchased(),
itemRevenue()
FROM report_table
WHERE date BETWEEN '2025-08-01' AND '2025-08-02'
AND eventName = 'purchase'
ORDER BY date, transactionId, itemId
)

# purchase_order

SELECT transactionId, date, sessionMedium, eventName,
purchaseRevenue, shippingAmount, taxAmount, transactions
FROM shoplc_web_data
(
SELECT transactionId, date, sessionMedium, eventName,
purchaseRevenue(),
shippingAmount(),
taxAmount(),
transactions()
FROM report_table
WHERE date BETWEEN '2025-08-01' AND '2025-08-02'
AND eventName = 'purchase'
ORDER BY date, transactionId
)

# purchase_order_item

SELECT transactionId, date, sessionMedium, itemName, itemId, itemBrand, itemCategory, eventName,
itemsPurchased, itemRevenue
FROM shoplc_web_data
(
SELECT transactionId, date, sessionMedium, itemName, itemId, itemBrand, itemCategory, eventName,
itemsPurchased(),
itemRevenue()
FROM report_table
WHERE date BETWEEN '2025-08-01' AND '2025-08-02'
AND eventName = 'purchase'
ORDER BY date, transactionId, itemId
)

# visitors_by_channel_config

SELECT sessionMedium, date, newUsers, totalUsers, eventCount
FROM shoplc_web_data (
SELECT sessionMedium, date, newUsers(), totalUsers(), eventCount()
FROM report_table
WHERE date BETWEEN '2025-08-01' AND '2025-08-02'
GROUP BY sessionMedium, date
ORDER BY date, sessionMedium
)

# visitors_by_channel_mobile_config

## Same syntax as above, just change the database to reflect the mobile data

SELECT sessionMedium, date, newUsers, totalUsers, eventCount
FROM shoplc_mobile_data (
SELECT sessionMedium, date, newUsers(), totalUsers(), eventCount()
FROM report_table
WHERE date BETWEEN '2025-08-01' AND '2025-08-02'
GROUP BY sessionMedium, date
ORDER BY date, sessionMedium
)

# visitors_by_channel_sessionsource_config

SELECT sessionMedium, sessionSource, date, newUsers, totalUsers, eventCount
FROM shoplc_web_data (
SELECT sessionMedium, sessionSource, date, newUsers(), totalUsers(), eventCount()
FROM report_table
WHERE date BETWEEN '2025-08-01' AND '2025-08-02'
GROUP BY sessionMedium, sessionSource, date
ORDER BY date, sessionMedium, sessionSource
)

# visitors_by_channel_sessionsource_mobile_config

## Same syntax as above, just change the database to reflect the mobile data

SELECT sessionMedium, sessionSource, date, newUsers, totalUsers, eventCount
FROM shoplc_web_data (
SELECT sessionMedium, sessionSource, date, newUsers(), totalUsers(), eventCount()
FROM report_table
WHERE date BETWEEN '2025-08-01' AND '2025-08-02'
GROUP BY sessionMedium, sessionSource, date
ORDER BY date, sessionMedium, sessionSource
)
