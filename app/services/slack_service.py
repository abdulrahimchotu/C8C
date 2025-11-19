import httpx
import asyncio

url = "https://slack.com/api/chat.postMessage"

async def send_slack_message(token, channel_id, message_text):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "channel": channel_id,
        "text": message_text
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        print(f"Error sending message via Slack API: {e.response.text}")
        return e.response.json()