import requests
from datetime import datetime, timedelta
import os

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

def get_upcoming_tasks(days=3):
    today = datetime.utcnow().date()
    deadline = today + timedelta(days=days)

    query = {
        "filter": {
            "property": "期限日",
            "date": {
                "on_or_before": deadline.isoformat()
            }
        }
    }

    res = requests.post(
        f"https://api.notion.com/v1/databases/{DATABASE_ID}/query",
        headers=headers,
        json=query
    )
    res.raise_for_status()
    data = res.json().get("results", [])

    tasks = []
    for item in data:
        title = item["properties"]["名前"]["title"][0]["plain_text"]
        due = item["properties"]["期限日"]["date"]["start"]
        tasks.append(f"{title}（期限: {due}）")

    return tasks

def notify_slack(tasks):
    if not tasks:
        return

    message = "*⏰ 期限が近いタスク*\n" + "\n".join(f"• {t}" for t in tasks)
    payload = {"text": message}
    res = requests.post(SLACK_WEBHOOK_URL, json=payload)
    res.raise_for_status()

if __name__ == "__main__":
    tasks = get_upcoming_tasks()
    notify_slack(tasks)
