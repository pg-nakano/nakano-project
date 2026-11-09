-- TOP着地セッションの日次 セッション / CV / CVR と、FV変更日の前後N日比較
-- fv_change_date を実際の切替日に置き換えること
DECLARE fv_change_date DATE DEFAULT DATE '2026-10-01';  -- ← 要置換
DECLARE window_days   INT64 DEFAULT 28;                 -- 前後で比較する日数
DECLARE start_date DATE DEFAULT DATE_SUB(fv_change_date, INTERVAL window_days + 7 DAY);
DECLARE end_date   DATE DEFAULT CURRENT_DATE('Asia/Tokyo');

WITH ev AS (
  SELECT '美容外科' AS brand, event_date, event_name, event_timestamp, user_pseudo_id,
    (SELECT value.int_value  FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS gsid,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location') AS page_location
  FROM `shinagawa-biyou.analytics_326176248.events_*`
  WHERE _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', start_date) AND FORMAT_DATE('%Y%m%d', end_date)
  UNION ALL
  SELECT 'スキン', event_date, event_name, event_timestamp, user_pseudo_id,
    (SELECT value.int_value  FROM UNNEST(event_params) WHERE key = 'ga_session_id'),
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location')
  FROM `shinagawa-skin.analytics_327360622.events_*`
  WHERE _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', start_date) AND FORMAT_DATE('%Y%m%d', end_date)
),
sessions AS (
  SELECT
    brand,
    CONCAT(user_pseudo_id, '-', CAST(gsid AS STRING)) AS session_id,
    MIN(PARSE_DATE('%Y%m%d', event_date)) AS d,
    -- 着地ページ: セッション最初の page_view のパス
    ARRAY_AGG(
      REGEXP_EXTRACT(page_location, r'^https?://[^/]+(/[^?#]*)')
      ORDER BY event_timestamp LIMIT 1
    )[OFFSET(0)] AS landing_path,
    COUNTIF(event_name IN ('CV_カウンセリング予約完了_SP', 'CV_カウンセリング予約完了_PC')) AS cv
  FROM ev
  WHERE gsid IS NOT NULL
  GROUP BY 1, 2
),
flagged AS (
  SELECT *,
    landing_path IN ('/', '/sp/', '/sp', '/index.html') AS is_top_landing,
    CASE WHEN d < fv_change_date THEN 'before' ELSE 'after' END AS period
  FROM sessions
)
-- 1) 日次（TOP着地のみ / 全体）
SELECT 'daily' AS level, brand, is_top_landing, CAST(d AS STRING) AS d_or_period,
  COUNT(*) AS sessions, SUM(cv) AS cv,
  ROUND(SAFE_DIVIDE(SUM(cv), COUNT(*)) * 100, 2) AS cvr_pct
FROM flagged
GROUP BY 1, 2, 3, 4
UNION ALL
-- 2) FV変更日の前後 window_days 日の比較
SELECT 'before_after', brand, is_top_landing, period,
  COUNT(*), SUM(cv), ROUND(SAFE_DIVIDE(SUM(cv), COUNT(*)) * 100, 2)
FROM flagged
WHERE d BETWEEN DATE_SUB(fv_change_date, INTERVAL window_days DAY)
            AND DATE_ADD(fv_change_date, INTERVAL window_days - 1 DAY)
GROUP BY 1, 2, 3, 4
ORDER BY level, brand, is_top_landing, d_or_period;
