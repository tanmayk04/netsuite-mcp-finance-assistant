import os
import requests
from fastapi import FastAPI, Request
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

NETSUITE_ACCOUNT = os.getenv("NETSUITE_ACCOUNT_ID")  # e.g. 3392496-sb2
CLIENT_ID = os.getenv("NETSUITE_CLIENT_ID")
CLIENT_SECRET = os.getenv("NETSUITE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("NETSUITE_REDIRECT_URI", "http://localhost:8000/oauth/callback")


@app.get("/oauth/callback")
async def oauth_callback(request: Request):
    code = request.query_params.get("code")
    error = request.query_params.get("error")
    state = request.query_params.get("state")

    if error:
        return {"ok": False, "error": error, "state": state, "query": dict(request.query_params)}

    if not code:
        return {"ok": False, "error": "missing_code", "state": state, "query": dict(request.query_params)}

    token_url = "https://3392496-sb2.suitetalk.api.netsuite.com/services/rest/auth/oauth2/v1/token"

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    resp = requests.post(token_url, data=data, timeout=30)
    import json
    try:
        body = resp.json()
    except json.decoder.JSONDecodeError:
        # JSON decoding failed, fall back to raw text
        body = {"raw": resp.text}

    return {
        "ok": resp.status_code == 200,
        "status_code": resp.status_code,
        "token_response": body,
    }