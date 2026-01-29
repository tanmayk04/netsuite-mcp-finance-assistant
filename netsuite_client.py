import os
import base64
import requests
from dotenv import load_dotenv


class NetSuiteClient:
    """
    Reusable NetSuite REST client that:
    - Reads config from .env
    - Uses refresh_token to generate a fresh access_token
    - Automatically retries once if token is rejected (401)
    """

    def __init__(self) -> None:
        load_dotenv()

        self.account_id = os.getenv("NETSUITE_ACCOUNT_ID")
        self.client_id = os.getenv("NETSUITE_CLIENT_ID")
        self.client_secret = os.getenv("NETSUITE_CLIENT_SECRET")
        self.refresh_token = os.getenv("NETSUITE_REFRESH_TOKEN")

        if not all([self.account_id, self.client_id, self.client_secret, self.refresh_token]):
            raise SystemExit("❌ Missing one or more env vars. Check your .env values.")

        # NetSuite host format: 3392496_SB2 -> 3392496-sb2
        self.host = self.account_id.lower().replace("_", "-")

        # OAuth token endpoint
        self.token_url = (
            f"https://{self.host}.suitetalk.api.netsuite.com"
            "/services/rest/auth/oauth2/v1/token"
        )

        # Precompute Basic auth (client_id:client_secret)
        self._basic_auth = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode("utf-8")
        ).decode("utf-8")

        # Optional: cache token in memory for this process
        self._access_token: str | None = None

    def _get_access_token(self) -> str:
        """
        Always fetch a NEW access token using refresh_token.
        Access tokens expire ~1 hour, so refresh token is the stable credential.
        """
        resp = requests.post(
            self.token_url,
            headers={
                "Authorization": f"Basic {self._basic_auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
            timeout=30,
        )
        resp.raise_for_status()
        token = resp.json()["access_token"]
        self._access_token = token
        return token

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Wrapper that:
        - Adds Bearer token
        - Retries once on 401 by refreshing token
        """
        token = self._access_token or self._get_access_token()

        headers = kwargs.pop("headers", {})
        headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Prefer": "transient",
            }
        )


        resp = requests.request(method, url, headers=headers, timeout=120, **kwargs)

        # If token was rejected, refresh once and retry
        if resp.status_code == 401:
            token = self._get_access_token()
            headers["Authorization"] = f"Bearer {token}"
            resp = requests.request(method, url, headers=headers, timeout=120, **kwargs)

        return resp

    def get_metadata_catalog(self) -> dict:
        """
        Safe test call to confirm auth works.
        """
        url = (
            f"https://{self.host}.suitetalk.api.netsuite.com"
            "/services/rest/record/v1/metadata-catalog"
        )
        resp = self._request("GET", url)
        resp.raise_for_status()
        return resp.json()
    
    def suiteql(self, query: str, limit: int = 100, offset: int = 0) -> dict:
        url = (
            f"https://{self.host}.suitetalk.api.netsuite.com"
            "/services/rest/query/v1/suiteql"
        )

        resp = self._request(
        "POST",
        url,
        params={"limit": limit, "offset": offset},
        json={"q": query},
        headers={"Content-Type": "application/json"},
        )

        if resp.status_code >= 400:
            print("STATUS:", resp.status_code)
            print("BODY:", resp.text)

        resp.raise_for_status()
        return resp.json()
