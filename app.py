from flask import Flask, redirect, request, session
import os
import traceback
from google_auth_oauthlib.flow import Flow

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]

def create_flow():
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI")

    if not client_id:
        raise Exception("Missing GOOGLE_CLIENT_ID")
    if not client_secret:
        raise Exception("Missing GOOGLE_CLIENT_SECRET")
    if not redirect_uri:
        raise Exception("Missing GOOGLE_REDIRECT_URI")

    return Flow.from_client_config(
        {
            "web": {
                "client_id": client_id.strip(),
                "client_secret": client_secret.strip(),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri.strip()],
            }
        },
        scopes=SCOPES,
        redirect_uri=redirect_uri.strip(),
    )

@app.route("/")
def home():
    return """
    <h1>Sun State Digital Gmail OAuth</h1>
    <p><a href="/connect">Connect Gmail</a></p>
    <p><a href="/health">Health Check</a></p>
    """

@app.route("/connect")
def connect():
    try:
        flow = create_flow()

        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )

        session["state"] = state
        return redirect(authorization_url)

    except Exception as e:
        return f"""
        <h2>/connect error</h2>
        <pre>{type(e).__name__}: {str(e)}</pre>
        <pre>{traceback.format_exc()}</pre>
        """, 500

@app.route("/oauth/callback")
def oauth_callback():
    try:
        expected_state = session.get("state")
        returned_state = request.args.get("state")

        if expected_state and returned_state and expected_state != returned_state:
            return "State mismatch. Please try again.", 400

        flow = create_flow()
        flow.fetch_token(authorization_response=request.url)

        creds = flow.credentials
        refresh_token = creds.refresh_token

        if not refresh_token:
            return (
                "No refresh token returned. Remove the app from your Google account permissions "
                "and try again."
            ), 400

        return f"""
        <h2>OAuth successful</h2>
        <p>Copy this refresh token and store it securely:</p>
        <pre>{refresh_token}</pre>
        """

    except Exception as e:
        return f"""
        <h2>/oauth/callback error</h2>
        <pre>{type(e).__name__}: {str(e)}</pre>
        <pre>{traceback.format_exc()}</pre>
        """, 500

@app.route("/health")
def health():
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
