-- 月次 セッション / CV / CVR（サイト全体・2025-11〜実行日）
-- 美容外科とスキンを UNION ALL で縦持ち
DECLARE start_date DATE DEFAULT DATE '2025-11-01';
DECLARE end_date   DATE DEFAULT CURRENT_DATE('Asia/Tokyo');

WITH biyou AS (
  SELECT
    '美容外科' AS brand,
    FORMAT_DATE('%Y-%m', PARSE_DATE('%Y%m%d', event_date)) AS ym,
    CONCAT(user_pseudo_id, '-', CAST((SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS STRING)) AS session_id,
    COUNTIF(event_name IN ('CV_カウンセリング予約完了_SP', 'CV_カウンセリング予約完了_PC')) AS cv
  FROM `shinagawa-biyou.analytics_326176248.events_*`
  WHERE _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', start_date) AND FORMAT_DATE('%Y%m%d', end_date)
  GROUP BY 1, 2, 3
),
skin AS (
  SELECT
    'スキン' AS brand,
    FORMAT_DATE('%Y-%m', PARSE_DATE('%Y%m%d', event_date)) AS ym,
    CONCAT(user_pseudo_id, '-', CAST((SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS STRING)) AS session_id,
    COUNTIF(event_name IN ('CV_カウンセリング予約完了_SP', 'CV_カウンセリング予約完了_PC')) AS cv
  FROM `shinagawa-skin.analytics_327360622.events_*`
  WHERE _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', start_date) AND FORMAT_DATE('%Y%m%d', end_date)
  GROUP BY 1, 2, 3
),
all_sessions AS (SELECT * FROM biyou UNION ALL SELECT * FROM skin)
SELECT
  brand,
  ym,
  COUNT(DISTINCT session_id) AS sessions,
  SUM(cv) AS cv,
  ROUND(SAFE_DIVIDE(SUM(cv), COUNT(DISTINCT session_id)) * 100, 2) AS cvr_pct
FROM all_sessions
GROUP BY brand, ym
ORDER BY brand, ym;
