"""Storage abstraction with automatic local fallback & circuit breaker.

    Frontend -> Flask -> StorageProvider -> { LocalProvider | TelegramProvider }

If Telegram API write times out or fails (e.g. slow network, ISP blocking, 
timeout errors), it automatically and seamlessly falls back to LocalProvider 
so uploads NEVER fail, and existing files remain 100% accessible.
"""
from __future__ import annotations
import json
import logging
import os
import re
import time
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

import requests
from services.time_utils import now_ist

logger = logging.getLogger(__name__)

class StorageProvider(ABC):
    name = "abstract"

    @abstractmethod
    def upload_file(self, file_bytes, filename, *, branch_code=None, folder_path=None) -> str:
        ...

    @abstractmethod
    def download_file(self, reference: str) -> bytes:
        ...

    @abstractmethod
    def delete_file(self, reference: str) -> bool:
        ...

    def replace_file(self, reference, file_bytes, filename, *,
                     branch_code=None, folder_path=None) -> str:
        new_ref = self.upload_file(file_bytes, filename,
                                   branch_code=branch_code, folder_path=folder_path)
        try:
            self.delete_file(reference)
        except Exception:
            pass
        return new_ref

_SAFE = re.compile(r"[^A-Za-z0-9._\-]+")

def _safe_name(name):
    base = os.path.basename(name or "file")
    base = _SAFE.sub("_", base).strip("._") or "file"
    return base[:180]

# ---------------------------------------------------------------------------
# Local filesystem provider (always works — 100% reliable)
# ---------------------------------------------------------------------------
class LocalProvider(StorageProvider):
    name = "local"

    def __init__(self, base_dir, telegram_fallback=None):
        self.base_dir = Path(base_dir) / "storage"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.telegram_fallback = telegram_fallback

    def _path_for(self, reference):
        _, _, rest = reference.partition(":")
        base = self.base_dir.resolve()
        target = (self.base_dir / rest).resolve()
        # Security: Prevent path traversal outside storage directory
        if not str(target).startswith(str(base)):
            raise ValueError("Path traversal attempt detected in reference.")
        return target

    def upload_file(self, file_bytes, filename, *, branch_code=None, folder_path=None):
        clean_code = _SAFE.sub("", (branch_code or "COMMON").upper()) or "COMMON"
        bucket = clean_code[:30]
        bucket_dir = (self.base_dir / bucket).resolve()
        bucket_dir.mkdir(parents=True, exist_ok=True)
        uid = uuid.uuid4().hex[:12]
        safe = _safe_name(filename)
        rel = f"{bucket}/{uid}_{safe}"
        (self.base_dir / rel).write_bytes(file_bytes)
        return f"local:{rel}"

    def download_file(self, reference):
        if not reference:
            raise FileNotFoundError("Empty storage reference.")
        if reference.startswith("tg:") and self.telegram_fallback:
            return self.telegram_fallback.download_file(reference)
        p = self._path_for(reference)
        if not p.exists():
            raise FileNotFoundError(reference)
        return p.read_bytes()

    def delete_file(self, reference):
        if not reference:
            return True
        if reference.startswith("tg:") and self.telegram_fallback:
            return self.telegram_fallback.delete_file(reference)
        try:
            p = self._path_for(reference)
            if p.exists():
                p.unlink()
                return True
        except Exception:
            pass
        return False

# ---------------------------------------------------------------------------
# Telegram provider — with automatic Local fallback & circuit breaker
# ---------------------------------------------------------------------------
class TelegramProvider(StorageProvider):
    """Store files in Telegram with automatic fallback to LocalProvider.

    Reference format stored in DB:
      - tg:<chat_id>:<message_id>:<file_id> (when stored in Telegram)
      - local:<bucket>/<uid>_<filename>      (when stored locally via fallback)
    """
    name = "telegram"
    _circuit_open_until = 0.0  # Unix timestamp until which Telegram upload is skipped

    def __init__(self, bot_token, *, chat_id=None, topics=None, branch_channels=None,
                 api_base="https://api.telegram.org", upload_folder=None):
        if not bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN required for telegram provider.")
        self.token = bot_token
        self.chat_id = str(chat_id or "").strip()
        self.topics = {}
        if isinstance(topics, dict):
            for k, v in topics.items():
                try:
                    self.topics[str(k).upper()] = int(v)
                except (ValueError, TypeError):
                    pass
        self.branch_channels = {k.upper(): str(v) for k, v in (branch_channels or {}).items()}
        self.api_base = api_base.rstrip("/")
        self.upload_folder = upload_folder or "uploads"
        self.local_provider = LocalProvider(self.upload_folder)
        self.session = requests.Session()

    def get_me(self):
        try:
            r = self.session.get(self._url("getMe"), timeout=10)
            return r.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_chat(self):
        if not self.chat_id:
            return {"ok": False, "error": "No chat_id configured"}
        try:
            r = self.session.get(self._url("getChat"), params={"chat_id": self.chat_id}, timeout=10)
            return r.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _channel_or_topic_for(self, branch_code):
        code = (branch_code or "COMMON").upper()
        if self.chat_id:
            topic_id = self.topics.get(code)
            return self.chat_id, topic_id
        if code in self.branch_channels:
            return self.branch_channels[code], None
        if "COMMON" in self.branch_channels:
            return self.branch_channels["COMMON"], None
        raise RuntimeError(f"No Telegram storage configured for branch '{code}'.")

    def _url(self, method):
        return f"{self.api_base}/bot{self.token}/{method}"

    def upload_file(self, file_bytes, filename, *, branch_code=None, folder_path=None):
        now = time.time()
        # Circuit breaker: if Telegram recently timed out, save locally directly
        if now < TelegramProvider._circuit_open_until:
            logger.info("Telegram circuit breaker active. Storing '%s' locally.", filename)
            return self.local_provider.upload_file(file_bytes, filename, branch_code=branch_code, folder_path=folder_path)

        try:
            chat_id, topic_id = self._channel_or_topic_for(branch_code)
            caption = f"[CampusDesk] {folder_path or ''}".strip()[:1000]
            files = {"document": (_safe_name(filename), file_bytes)}
            data = {"chat_id": chat_id, "caption": caption}
            if topic_id:
                data["message_thread_id"] = topic_id

            # Reasonable timeout: 6s connect, 20s write/read
            r = self.session.post(self._url("sendDocument"),
                                  data=data,
                                  files=files,
                                  timeout=(6, 20))
            if r.status_code == 200:
                payload = r.json()
                if payload.get("ok"):
                    msg = payload["result"]
                    return f"tg:{msg['chat']['id']}:{msg['message_id']}:{msg['document']['file_id']}"
                else:
                    logger.warning("Telegram sendDocument payload not ok: %s", payload)
            else:
                logger.warning("Telegram sendDocument HTTP error %s: %s", r.status_code, r.text)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, TimeoutError, OSError) as e:
            # Network write timed out or connection aborted (e.g. Indian ISP throttle / slow upload)
            logger.warning("Telegram upload connection failed (%s): %s. Opening fallback circuit for 5 minutes.", type(e).__name__, e)
            TelegramProvider._circuit_open_until = time.time() + 300
        except Exception as e:
            logger.warning("Telegram upload unexpected error (%s): %s. Falling back to local storage.", type(e).__name__, e)

        # Seamless Fallback to Local Storage — teacher upload never fails!
        logger.info("Saving '%s' via LocalProvider fallback.", filename)
        return self.local_provider.upload_file(file_bytes, filename, branch_code=branch_code, folder_path=folder_path)

    def download_file(self, reference):
        if not reference:
            raise FileNotFoundError("Empty storage reference.")

        # If reference was saved locally, serve from local storage!
        if reference.startswith("local:"):
            return self.local_provider.download_file(reference)

        parts = reference.split(":", 3)
        if len(parts) < 4:
            # Fallback check if it was a local path
            try:
                return self.local_provider.download_file(reference)
            except Exception:
                raise RuntimeError(f"Invalid Telegram reference: {reference}")

        file_id = parts[3]
        try:
            r = self.session.get(self._url("getFile"), params={"file_id": file_id}, timeout=(8, 25))
            r.raise_for_status()
            data = r.json()
            if not data.get("ok"):
                raise RuntimeError(f"getFile failed: {data}")
            file_path = data["result"]["file_path"]
            dl = self.session.get(f"{self.api_base}/file/bot{self.token}/{file_path}", timeout=(10, 60))
            dl.raise_for_status()
            return dl.content
        except Exception as e:
            logger.warning("Telegram download failed (%s): %s.", type(e).__name__, e)
            raise

    def delete_file(self, reference):
        if not reference:
            return True
        if reference.startswith("local:"):
            return self.local_provider.delete_file(reference)

        parts = reference.split(":", 3)
        if len(parts) >= 3:
            chat_id = parts[1]
            message_id = parts[2]
            try:
                self.session.post(self._url("deleteMessage"),
                                  data={"chat_id": chat_id, "message_id": message_id},
                                  timeout=10)
            except Exception:
                pass
        return True

    def backup_database(self, db_path: str) -> dict:
        """Send a snapshot of the SQLite database to the Telegram storage chat for offsite cloud backup."""
        from datetime import datetime
        p = Path(db_path)
        if not p.exists():
            return {"ok": False, "error": f"Database file {db_path} does not exist"}

        now_str = now_ist().strftime("%Y%m%d_%H%M%S")
        filename = f"campusdesk_backup_{now_str}.db"
        caption = f"💾 [CampusDesk Cloud Backup] Snapshot taken on {now_ist().strftime('%d %b %Y %H:%M:%S IST')}"
        data = {"chat_id": self.chat_id, "caption": caption}

        try:
            with open(p, "rb") as fh:
                files = {"document": (filename, fh.read())}
                r = self.session.post(self._url("sendDocument"), data=data, files=files, timeout=(10, 60))
                if not r.ok:
                    return {"ok": False, "error": r.text}
                res = r.json()
                return {"ok": True, "message_id": res.get("result", {}).get("message_id")}
        except Exception as e:
            return {"ok": False, "error": str(e)}

# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------
def get_storage_provider(app_config=None):
    cfg = app_config or {}
    provider_name = (cfg.get("STORAGE_PROVIDER") or os.environ.get("STORAGE_PROVIDER", "telegram")).lower()
    upload_folder = cfg.get("UPLOAD_FOLDER") or os.environ.get("UPLOAD_FOLDER", "uploads")
    token = cfg.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        try:
            from config import Config
            token = getattr(Config, "TELEGRAM_BOT_TOKEN", "")
        except Exception:
            token = ""

    chat_id = cfg.get("TELEGRAM_STORAGE_CHAT_ID") or os.environ.get("TELEGRAM_STORAGE_CHAT_ID", "")
    raw_topics = cfg.get("TELEGRAM_TOPICS") or os.environ.get("TELEGRAM_TOPICS", "{}")
    try:
        topics = json.loads(raw_topics) if isinstance(raw_topics, str) else (raw_topics or {})
    except json.JSONDecodeError:
        topics = {}

    try:
        raw_channels = cfg.get("TELEGRAM_BRANCH_CHANNELS") or os.environ.get("TELEGRAM_BRANCH_CHANNELS", "{}")
        channels = json.loads(raw_channels) if isinstance(raw_channels, str) else (raw_channels or {})
    except json.JSONDecodeError:
        channels = {}

    api_base = cfg.get("TELEGRAM_API_BASE") or os.environ.get("TELEGRAM_API_BASE", "https://api.telegram.org")

    tg_provider = None
    if token:
        tg_provider = TelegramProvider(
            token,
            chat_id=chat_id,
            topics=topics,
            branch_channels=channels,
            api_base=api_base,
            upload_folder=upload_folder,
        )

    if provider_name == "local" or not token:
        return LocalProvider(upload_folder, telegram_fallback=tg_provider)

    return tg_provider
