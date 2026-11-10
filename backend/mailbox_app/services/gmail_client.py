import base64
import os
from email.mime.text import MIMEText
from decouple import config as env_config
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_PATH = env_config("GMAIL_TOKEN_PATH", default="gmail_token.json")
CLIENT_ID = env_config("GMAIL_CLIENT_ID", default="")
CLIENT_SECRET = env_config("GMAIL_CLIENT_SECRET", default="")


def _get_credentials() -> Credentials:
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_config = {
                "installed": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost"],
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())

    return creds


def _get_service():
    creds = _get_credentials()
    return build("gmail", "v1", credentials=creds)


def send_email(to: str, subject: str, body: str) -> str:
    service = _get_service()
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return sent["id"]


def get_thread_id(message_id: str) -> str | None:
    """Look up the Gmail conversation threadId for a message we just sent."""
    service = _get_service()
    msg = service.users().messages().get(userId="me", id=message_id, format="minimal").execute()
    return msg.get("threadId")


def mark_as_read(message_id: str) -> None:
    """Remove the UNREAD label so poll_replies_task doesn't reprocess this message forever."""
    service = _get_service()
    service.users().messages().modify(
        userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()


def fetch_new_replies() -> list[dict]:
    service = _get_service()
    results = service.users().messages().list(userId="me", q="is:unread in:inbox", maxResults=20).execute()
    messages = results.get("messages", [])

    replies = []
    for msg_ref in messages:
        msg = service.users().messages().get(userId="me", id=msg_ref["id"], format="full").execute()
        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
        from_email = headers.get("From", "")
        snippet = msg.get("snippet", "")
        replies.append({
            "thread_id": msg.get("threadId"),
            "from_email": from_email,
            "body": snippet,
            "message_id": msg_ref["id"],
        })
    return replies
