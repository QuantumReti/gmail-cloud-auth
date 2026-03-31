from flask import Flask, redirect, request, session
import os
import secrets
import requests
from urllib.parse import urlencode

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "").strip()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"


def missing_vars():
    missing = []
    if not GOOGLE_CLIENT_ID:
        missing.append("GOOGLE_CLIENT_ID")
    if not GOOGLE_CLIENT_SECRET:
        missing.append("GOOGLE_CLIENT_SECRET")
    if not GOOGLE_REDIRECT_URI:
        missing.append("GOOGLE_REDIRECT_URI")
    if not app.secret_key:
        missing.append("FLASK_SECRET_KEY")
    return missing


@app.route("/")
def home():
    missing = missing_vars()
    if missing:
        return f"""
        <h2>Missing environment variables</h2>
        <pre>{", ".join(missing)}</pre>
        """, 500

    return """
    <h1>Sun State Digital Gmail OAuth</h1>
    <p><a href="/connect">Connect Gmail</a></p>
    <p><a href="/health">Health Check</a></p>
    """


@app.route("/health")
def health():
    return "OK", 200


@app.route("/connect")
def connect():
    missing = missing_vars()
    if missing:
        return f"""
        <h2>Missing environment variables</h2>
        <pre>{", ".join(missing)}</pre>
        """, 500

    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }

    return redirect(f"{AUTH_URL}?{urlencode(params)}")


@app.route("/oauth/callback")
def oauth_callback():
    stored_state = session.get("oauth_state")
    returned_state = request.args.get("state")
    code = request.args.get("code")
    error = request.args.get("error")

    if error:
        return f"""
        <h2>Google returned an error</h2>
        <pre>{error}</pre>
        """, 400

    if not stored_state or not returned_state or stored_state != returned_state:
        return """
        <h2>State mismatch</h2>
        <p>Please go back and try again.</p>
        """, 400

    if not code:
        return """
        <h2>No code returned</h2>
        <p>Google did not send an authorization code.</p>
        """, 400

    token_data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    token_response = requests.post(TOKEN_URL, data=token_data, timeout=30)

    if token_response.status_code != 200:
        return f"""
        <h2>Token exchange failed</h2>
        <p>Status: {token_response.status_code}</p>
        <pre>{token_response.text}</pre>
        """, 400

    token_json = token_response.json()
    refresh_token = token_json.get("refresh_token")
    access_token = token_json.get("access_token")

    if not refresh_token:
        return f"""
        <h2>No refresh token returned</h2>
        <p>This usually means Google has already authorized this app before.</p>
        <p>Remove the app from your Google Account permissions and try again.</p>
        <pre>{token_json}</pre>
        """, 400

    return f"""
    <h2>OAuth successful</h2>
    <p>Copy this refresh token and store it securely:</p>
    <pre>{refresh_token}</pre>
    <h3>Access token</h3>
    <pre>{access_token}</pre>
    """


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
