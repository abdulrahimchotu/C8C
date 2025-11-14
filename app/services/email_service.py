import base64
from email.mime.text import MIMEText
from typing import Dict
import httpx

from app.models.email import EmailSchema

GMAIL_API_URL = "https://www.googleapis.com/gmail/v1/users/me/messages/send"

async def send_email(access_token: str, email_data: EmailSchema) -> Dict:
    """
    Sends an email using the Gmail API.

    Args:
        access_token: The user's Google OAuth2 access token.
        email_data: An EmailSchema object containing the recipient, subject, and body.

    Returns:
        A dictionary containing the response from the Gmail API.
    """
    if not access_token:
        raise ValueError("Access token is missing for sending email.")

    message = MIMEText(email_data.body)
    message["to_"] = email_data.to
    message["from_"] = email_data.from_
    message["subject"] = email_data.subject

    # Encode the message in URL-safe base64
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    json_body = {"raw": encoded_message}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(GMAIL_API_URL, headers=headers, json=json_body)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        # The response from Google often contains useful error details
        print(f"Error sending email via Gmail API: {e.response.text}")
        return e.response.json()
