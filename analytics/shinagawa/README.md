# 品川美容外科・品川スキン GA4(BigQuery) 集計SQL

作成日: 2026-11-09

## データ
- 美容外科: `shinagawa-biyou.analytics_326176248.events_*`
- スキン:   `shinagawa-skin.analytics_327360622.events_*`
- CV: `CV_カウンセリング予約完了_SP` + `CV_カウンセリング予約完了_PC`（セッション内で発生したイベント数）
- セッション: `user_pseudo_id` × `ga_session_id` のユニーク数
- 既知の欠損: 2025/4/8〜6/3 全日、2026/6/18 美容外科のみ、2025/2/3・2026/10/20-21 予約完了の記録漏れ

## 実行方法（会社Mac、gcloud認証済み前提）
```bash
# 月次 セッション/CV/CVR（両ブランド）
bq query --use_legacy_sql=false --format=csv < analytics/shinagawa/01_monthly_sessions_cv_cvr.sql > monthly.csv

# TOP着地セッションの日次CVR（FV変更の前後比較用）
bq query --use_legacy_sql=false --format=csv < analytics/shinagawa/02_top_landing_daily_cvr.sql > top_daily.csv
```
02 の `fv_change_date` は FV が切り替わった日に置き換える。日付が不明なら、まず 02 を実行して
`is_top_landing=TRUE` の日次CVRの折れ線を見て、段差の出た日を採用する。
