"""YouTube Upload API — 自動上傳視頻到 YouTube"""

from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from ..utils.config import load_config, PROJECT_ROOT

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_PATH = PROJECT_ROOT / "token.json"
CLIENT_SECRET_PATH = PROJECT_ROOT / "client_secret.json"


def get_youtube_service():
    """取得已認證的 YouTube API service"""
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET_PATH.exists():
                raise FileNotFoundError(
                    f"找不到 {CLIENT_SECRET_PATH}。"
                    "請從 Google Cloud Console 下載 OAuth2 client secret。"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_video(
    video_path: str | Path,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    category: str = "24",  # Entertainment
    privacy: str = "private",
) -> dict:
    """上傳視頻到 YouTube

    Args:
        video_path: 視頻檔案路徑
        title: 視頻標題
        description: 視頻描述
        tags: 標籤列表
        category: YouTube 分類 ID
        privacy: private | unlisted | public

    Returns:
        {video_id, url, status}
    """
    config = load_config()
    pub_config = config["publisher"]
    tags = tags or pub_config.get("tags", [])
    privacy = privacy or pub_config.get("privacy", "private")

    youtube = get_youtube_service()

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category,
            "defaultLanguage": "zh-TW",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=10 * 1024 * 1024,  # 10MB chunks
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()

    video_id = response["id"]
    return {
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "status": "uploaded",
        "privacy": privacy,
    }
