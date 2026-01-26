"""
token_exchange.py

Purpose:
- Exchange NetSuite OAuth authorization code
- For access token + refresh token
- Used by MCP Finance Assistant
"""

import base64
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

def basic_auth_header(client_id: str, client_secret: str) -> str:
    raw = f"{client_id}:{client_secret}".encode("utf-8")
    encoded = base64.b64encode(raw).decode("utf-8")
    return f"Basic {encoded}"


NETSUITE_ACCOUNT_ID = require_env("NETSUITE_ACCOUNT_ID")
NETSUITE_CLIENT_ID = require_env("NETSUITE_CLIENT_ID")
NETSUITE_CLIENT_SECRET = require_env("NETSUITE_CLIENT_SECRET")
NETSUITE_REDIRECT_URI = require_env("NETSUITE_REDIRECT_URI")

TOKEN_URL = (
    f"https://{NETSUITE_ACCOUNT_ID}.suitetalk.api.netsuite.com"
    "/services/rest/auth/oauth2/v1/token"
)

def build_headers() -> dict:
    return {
        "Authorization": basic_auth_header(NETSUITE_CLIENT_ID, NETSUITE_CLIENT_SECRET),
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

AUTH_CODE = require_env("NETSUITE_AUTH_CODE")

def build_token_request_body(auth_code: str) -> dict:
    """
    Build the form-encoded body for NetSuite OAuth token exchange
    """
    return {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": NETSUITE_REDIRECT_URI
    }

import requests

def exchange_auth_code_for_tokens() -> dict:
    """
    Sends the token exchange request to NetSuite and returns the JSON response.
    """
    body = build_token_request_body(AUTH_CODE)
    headers = {
        "Authorization": basic_auth_header(CLIENT_ID, CLIENT_SECRET),
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    resp = requests.post(TOKEN_URL, data=body, headers=headers, timeout=30)

    # If NetSuite returns an error, show a readable message (but DO NOT print secrets)
    if not resp.ok:
        raise RuntimeError(
            f"Token exchange failed: HTTP {resp.status_code} - {resp.text}"
        )

    return resp.json()

if __name__ == "__main__":
    result = exchange_auth_code_for_tokens()
    # Print only SAFE fields (do NOT print access_token / refresh_token)
    safe = {k: result.get(k) for k in ["token_type", "expires_in", "scope"]}
    print("Token exchange success (safe fields):", safe)

