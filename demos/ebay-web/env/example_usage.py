import os
import sys
from typing import Any, Dict, Optional

import httpx


ADAPTER_URL = os.getenv("ADAPTER_URL", "http://localhost:9100")


def _headers(token: Optional[str]) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


def _post(path: str, payload: dict, token: Optional[str] = None) -> Dict[str, Any]:
    r = httpx.post(f"{ADAPTER_URL}{path}", json=payload, headers=_headers(token), timeout=30)
    r.raise_for_status()
    return r.json()


def _get(path: str, token: Optional[str] = None) -> Dict[str, Any]:
    r = httpx.get(f"{ADAPTER_URL}{path}", headers=_headers(token), timeout=30)
    r.raise_for_status()
    return r.json()


def main() -> int:
    print("Health:")
    print(_get("/health"))

    print("Navigate home:")
    print(_post("/navigate", {"route": "/"}))

    # Sign in
    email = os.getenv("DEMO_EMAIL", "demo@example.com")
    password = os.getenv("DEMO_PASSWORD", "demo")

    auth = _post("/auth/sign-in", {"email": email, "password": password})
    print("Sign in:")
    print(auth)

    # If upstream returns a token, use it for subsequent requests.
    token = auth.get("token") or auth.get("accessToken")
    if not token:
        # Adapter returns user but does not echo token; keep compatibility by
        # querying session which will use adapter in-memory token.
        session = _get("/session")
        print("Session (fallback):")
        print(session)
    else:
        session = _get("/session", token=token)
        print("Session:")
        print(session)

    print("Wishlist:")
    print(_get("/wishlist", token=token))

    print("Account summary:")
    print(_get("/account/summary", token=token))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
