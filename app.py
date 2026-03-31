from flask import Flask, redirect, request, session
import os
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
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        },
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )

@app.route("/")
def home():
    return """
    <h1>Sun State Digital Gmail OAuth</h1>
    <p><a href="/connect">Connect Gmail</a></p>
    """

@app.route("/connect")
def connect():
    flow = create_flow()

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    session["state"] = state
    return redirect(authorization_url)

@app.route("/oauth/callback")
def oauth_callback():
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
            "and try again with prompt=consent."
        ), 400

    return f"""
    <h2>OAuth successful</h2>
    <p>Copy this refresh token and store it securely:</p>
    <pre>{refresh_token}</pre>
    """

@app.route("/health")
def health():
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
