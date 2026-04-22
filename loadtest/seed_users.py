"""Create N test accounts via /auth/signup and dump JWTs to tokens.json.

Idempotent: if tokens.json has N entries, exit 0.
"""
import json
import os
import sys
from pathlib import Path
import requests

BACKEND = os.environ.get("LOADTEST_BACKEND", "http://localhost:8080")
PASSWORD = os.environ["LOADTEST_SEED_PASSWORD"]  # required, no default
N_USERS = int(os.environ.get("LOADTEST_N_USERS", "100"))
OUT = Path(__file__).with_name("tokens.json")


def signup(email: str) -> str | None:
    r = requests.post(
        f"{BACKEND}/api/v1/auth/signup",
        json={"email": email, "password": PASSWORD},
        timeout=10,
    )
    if r.status_code in (200, 201):
        return r.json().get("accessToken")
    # Already registered? Try login.
    r2 = requests.post(
        f"{BACKEND}/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
        timeout=10,
    )
    if r2.status_code == 200:
        return r2.json().get("accessToken")
    print(f"  failed {email}: signup={r.status_code} login={r2.status_code}", file=sys.stderr)
    return None


def main() -> int:
    if OUT.exists():
        existing = json.loads(OUT.read_text())
        if len(existing) >= N_USERS:
            print(f"already have {len(existing)} tokens, skipping")
            return 0

    tokens = []
    for i in range(N_USERS):
        email = f"loadtest+{i}@example.local"
        t = signup(email)
        if t:
            tokens.append({"email": email, "token": t})
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{N_USERS}")

    OUT.write_text(json.dumps(tokens, indent=2))
    print(f"wrote {len(tokens)} tokens to {OUT}")
    return 0 if len(tokens) == N_USERS else 1


if __name__ == "__main__":
    sys.exit(main())
