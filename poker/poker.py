#!/usr/bin/env python3
"""ポーカー収支データベース (SQLite)

使い方:
  python poker/poker.py add 2026-11-05 133400               # 収支だけ記録
  python poker/poker.py add 2026-11-06 --in 20000 --out 35000 --hours 3 \
        --type キャッシュ --venue ○○ --stakes 1/2 --memo メモ
  python poker/poker.py list [2026-11]                        # 一覧（月指定可）
  python poker/poker.py month                                 # 月別サマリー
  python poker/poker.py delete <id>                           # 1件削除
  python poker/poker.py import-xlsx [poker/poker_bankroll.xlsx]  # Excelから取り込み
"""
import argparse
import datetime as dt
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE / "poker.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    date       TEXT    NOT NULL,              -- YYYY-MM-DD
    game_type  TEXT,                          -- キャッシュ / トーナメント / オンライン / その他
    venue      TEXT,
    stakes     TEXT,
    buy_in     INTEGER,                       -- 持ち込み額（円）
    cash_out   INTEGER,                       -- 持ち帰り額（円）
    profit     INTEGER NOT NULL,              -- 収支（円）
    hours      REAL,                          -- プレイ時間
    memo       TEXT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(date);

CREATE VIEW IF NOT EXISTS daily AS
SELECT date,
       SUM(profit)  AS profit,
       SUM(hours)   AS hours,
       COUNT(*)     AS sessions
FROM sessions GROUP BY date;

CREATE VIEW IF NOT EXISTS monthly AS
SELECT substr(date, 1, 7)                         AS month,
       SUM(profit)                                AS profit,
       SUM(hours)                                 AS hours,
       COUNT(*)                                   AS days,
       SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) AS win_days
FROM daily GROUP BY month;
"""


def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def yen(v):
    return "-" if v is None else f"{v:+,}"


def cmd_add(a):
    dt.date.fromisoformat(a.date)
    profit = a.profit
    if profit is None:
        if a.buy_in is None or a.cash_out is None:
            sys.exit("収支、または --in と --out の両方を指定してください")
        profit = a.cash_out - a.buy_in
    with connect() as con:
        cur = con.execute(
            "INSERT INTO sessions(date, game_type, venue, stakes, buy_in, cash_out, profit, hours, memo)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (a.date, a.type, a.venue, a.stakes, a.buy_in, a.cash_out, profit, a.hours, a.memo),
        )
    print(f"追加しました: id={cur.lastrowid} {a.date} {yen(profit)}円")


def cmd_list(a):
    q, p = "SELECT * FROM sessions", ()
    if a.month:
        q, p = q + " WHERE date LIKE ?", (a.month + "%",)
    total = 0
    with connect() as con:
        for r in con.execute(q + " ORDER BY date, id", p):
            total += r["profit"]
            print(f"{r['id']:>4}  {r['date']}  {yen(r['profit']):>10}  累計 {total:>10,}  "
                  f"{r['game_type'] or ''} {r['venue'] or ''} {r['memo'] or ''}".rstrip())
    print(f"合計: {yen(total)}円")


def cmd_month(a):
    cum = 0
    print(f"{'月':<8}{'収支':>12}{'時間':>7}{'日数':>5}{'勝ち':>5}{'勝率':>7}{'累計':>12}")
    with connect() as con:
        for r in con.execute("SELECT * FROM monthly ORDER BY month"):
            cum += r["profit"]
            rate = r["win_days"] / r["days"] if r["days"] else 0
            print(f"{r['month']:<8}{yen(r['profit']):>12}{(r['hours'] or 0):>7.1f}"
                  f"{r['days']:>5}{r['win_days']:>5}{rate:>7.1%}{cum:>12,}")


def cmd_delete(a):
    with connect() as con:
        n = con.execute("DELETE FROM sessions WHERE id = ?", (a.id,)).rowcount
    print("削除しました" if n else "該当なし")


def cmd_import(a):
    from openpyxl import load_workbook

    wb = load_workbook(a.path, data_only=False)
    rows = []
    for ws in wb.worksheets:
        if not ws.title.endswith("月") or "年" not in ws.title:
            continue
        for r in ws.iter_rows(min_row=5, values_only=True):
            date, _, gtype, venue, stakes, bin_, bout, profit, hours, _, _, memo = r[:12]
            if not isinstance(date, dt.datetime):
                continue
            if isinstance(profit, (int, float)):
                p = int(profit)
            elif isinstance(bin_, (int, float)) or isinstance(bout, (int, float)):
                p = int((bout or 0) - (bin_ or 0))
            else:
                continue
            rows.append((date.date().isoformat(), gtype, venue, stakes,
                         bin_, bout, p, hours, memo))
    with connect() as con:
        if con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] and not a.force:
            sys.exit("DBに既にデータがあります。上書きするなら --force を付けてください")
        con.execute("DELETE FROM sessions")
        con.executemany(
            "INSERT INTO sessions(date, game_type, venue, stakes, buy_in, cash_out, profit, hours, memo)"
            " VALUES (?,?,?,?,?,?,?,?,?)", rows)
    print(f"{len(rows)}件取り込みました")


def main():
    ap = argparse.ArgumentParser(description="ポーカー収支DB")
    sp = ap.add_subparsers(dest="cmd", required=True)

    p = sp.add_parser("add", help="記録を追加")
    p.add_argument("date", help="YYYY-MM-DD")
    p.add_argument("profit", nargs="?", type=int, help="収支（円）")
    p.add_argument("--in", dest="buy_in", type=int)
    p.add_argument("--out", dest="cash_out", type=int)
    p.add_argument("--hours", type=float)
    p.add_argument("--type")
    p.add_argument("--venue")
    p.add_argument("--stakes")
    p.add_argument("--memo")
    p.set_defaults(f=cmd_add)

    p = sp.add_parser("list", help="一覧")
    p.add_argument("month", nargs="?", help="YYYY-MM")
    p.set_defaults(f=cmd_list)

    sp.add_parser("month", help="月別サマリー").set_defaults(f=cmd_month)

    p = sp.add_parser("delete", help="削除")
    p.add_argument("id", type=int)
    p.set_defaults(f=cmd_delete)

    p = sp.add_parser("import-xlsx", help="Excelから取り込み")
    p.add_argument("path", nargs="?", default=str(HERE / "poker_bankroll.xlsx"))
    p.add_argument("--force", action="store_true")
    p.set_defaults(f=cmd_import)

    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
