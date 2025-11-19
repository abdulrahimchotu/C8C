from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode
import httpx

from app.core.config import settings

router = APIRouter()

# Define your scopes
scopes = {
    "gmail": "https://mail.google.com/",
    "drive": "https://www.googleapis.com/auth/drive",
    "calendar": "https://www.googleapis.com/auth/calendar",
}

@router.get("/")
async def google_auth(scope: str = "gmail"):
    """
    Redirects the user to Google's OAuth 2.0 server for authentication.
    """
    # pydantic-settings will raise an error on startup if these are not set,
    # but we also check for the placeholder value.
    if "your_google_client_id" in settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth credentials are not configured on the server. Please set them in the .env file."
        )

    # Validate scope parameter to prevent XSS
    if scope not in scopes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid scope parameter"
        )

    selected_scope = scopes[scope]

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
        "scope": selected_scope,
    }

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return RedirectResponse(auth_url)


@router.get("/callback")
async def callback(request: Request):
    """
    Handles the callback from Google after user authentication.
    Exchanges the authorization code for an access token.
    """
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code not found in callback."
        )

    token_data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post("https://oauth2.googleapis.com/token", data=token_data)
            response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
            
            # Return the tokens to the user
            return response.json()

        except httpx.HTTPStatusError as e:
            # Log the error details if possible
            print(f"Error exchanging token: {e.response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to exchange token with Google: {e.response.json()}"
            )
        except httpx.RequestError as e:
            print(f"Network error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Network error while communicating with Google."
            )



@router.get("/slack/")
async def slack_callback(request: Request):
    """
    Handles the callback from Slack after user authentication.
    Exchanges the authorization code for an access token.
    """
    scopes = "chat:write,channels:read"
    CLIENT_ID = settings.SLACK_CLIENT_ID
    REDIRECT_URI = settings.SLACK_REDIRECT_URI
    auth_url = f"https://slack.com/oauth/v2/authorize?client_id={CLIENT_ID}&scope={scopes}&redirect_uri={REDIRECT_URI}"
    return RedirectResponse(auth_url)


@router.get("/slack/callback")
async def slack_callback(request: Request):
    """
    Handles the callback from Slack after user authentication.
    Exchanges the authorization code for an access token.
    """
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code not found in callback."
        )

    token_data = {
        "code": code,
        "client_id": settings.SLACK_CLIENT_ID,
        "client_secret": settings.SLACK_CLIENT_SECRET,
        "redirect_uri": settings.SLACK_REDIRECT_URI,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post("https://slack.com/api/oauth.v2.access", data=token_data)
            response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes

            # Return the tokens to the user
            json = response.json()
            if json.get("ok"):
                return json.get("access_token")
            return {"error": "Failed to exchange token with Slack."}

        except httpx.HTTPStatusError as e:
            # Log the error details if possible
            print(f"Error exchanging token: {e.response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to exchange token with Slack: {e.response.json()}"
            )
        except httpx.RequestError as e:
            print(f"Network error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Network error while communicating with Slack."
            )