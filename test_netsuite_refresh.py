"""
This script demonstrates the *correct* production-safe way to call
NetSuite SuiteTalk REST APIs using OAuth 2.0.

Key idea:
- Access tokens expire every 60 minutes
- Refresh tokens do NOT expire (unless revoked)
- So we ALWAYS generate a fresh access token before calling NetSuite
"""

import os
import base64
import requests
from dotenv import load_dotenv

# ---------------------------------------------------------
# Load environment variables from .env file
# ---------------------------------------------------------
load_dotenv()

# Long-lived configuration (safe to store in .env)
ACCOUNT_ID = os.getenv("NETSUITE_ACCOUNT_ID")        # e.g. 3392496_SB2
CLIENT_ID = os.getenv("NETSUITE_CLIENT_ID")          # OAuth client id
CLIENT_SECRET = os.getenv("NETSUITE_CLIENT_SECRET")  # OAuth client secret
REFRESH_TOKEN = os.getenv("NETSUITE_REFRESH_TOKEN")  # OAuth refresh token

# Fail fast if anything is missing
if not all([ACCOUNT_ID, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
    raise SystemExit("❌ Missing one or more env vars. Check .env values.")

# ---------------------------------------------------------
# Build NetSuite host + OAuth token endpoint
# ---------------------------------------------------------
# NetSuite requires account id in lowercase and hyphenated
# Example: 3392496_SB2 → 3392496-sb2
host = ACCOUNT_ID.lower().replace("_", "-")

# OAuth token endpoint (used to refresh access tokens)
token_url = (
    f"https://{host}.suitetalk.api.netsuite.com"
    "/services/rest/auth/oauth2/v1/token"
)

# ---------------------------------------------------------
# Prepare HTTP Basic Auth header
# ---------------------------------------------------------
# NetSuite expects:
#   Authorization: Basic base64(client_id:client_secret)
basic_auth_value = base64.b64encode(
    f"{CLIENT_ID}:{CLIENT_SECRET}".encode("utf-8")
).decode("utf-8")


# ---------------------------------------------------------
# Function: Get a NEW access token using refresh token
# ---------------------------------------------------------
def get_access_token() -> str:
    """
    Uses the refresh token to request a new access token.
    This must be done whenever the old token expires.
    """
    response = requests.post(
        token_url,
        headers={
            "Authorization": f"Basic {basic_auth_value}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": REFRESH_TOKEN,
        },
        timeout=30,
    )

    # Raise an exception if NetSuite returns an error (401, 400, etc.)
    response.raise_for_status()

    # Extract and return the short-lived access token
    return response.json()["access_token"]


# ---------------------------------------------------------
# Function: Call NetSuite metadata catalog endpoint
# ---------------------------------------------------------
def call_metadata(access_token: str) -> requests.Response:
    """
    Calls a safe read-only NetSuite endpoint using Bearer token.
    """
    url = (
        f"https://{host}.suitetalk.api.netsuite.com"
        "/services/rest/record/v1/metadata-catalog"
    )

    return requests.get(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        timeout=30,
    )


# ---------------------------------------------------------
# Main execution flow
# ---------------------------------------------------------
def main():
    # STEP 1: Always fetch a fresh access token
    access_token = get_access_token()
    print("✅ Got fresh access token")

    # STEP 2: Make an API call
    response = call_metadata(access_token)

    # STEP 3: If NetSuite rejected token, refresh once and retry
    # (best practice — avoids random 401 failures)
    if response.status_code == 401:
        print("⚠️  Token rejected, refreshing and retrying once...")
        access_token = get_access_token()
        response = call_metadata(access_token)

    # STEP 4: Print results
    print("Status:", response.status_code)
    print(response.text[:800])  # print only first part to avoid noise


# --------------------------------------------------------
# Python entry point
# --------------------------------------------------------
if __name__ == "__main__":
    main()