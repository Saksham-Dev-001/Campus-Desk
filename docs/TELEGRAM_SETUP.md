# CampusDesk — Telegram Topic Storage Setup

Ek hi **supergroup** banayenge jisme **forum topics** honge — har branch ka
alag topic. Yahi hamara "community" storage hoga.

```

CampusDesk Storage (Supergroup with Topics)
├── #General
├── #CSE        ← CSE branch files
├── #CS         ← CS branch files
├── #AI         ← AI/ML branch files
└── #DS         ← Data Science branch files

```

---

## Step 1: Bot banao (agar nahi banaya)

1. Telegram kholo → **@BotFather** search karo
2. `/newbot` bhejo
3. Naam: `CampusDesk Storage`
4. Username: `campusdesk_storage_bot` (unique hona chahiye)
5. BotFather dega **TOKEN**:
```

1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ

```
6. Copy karo, safe rakho

---

## Step 2: Supergroup + Topics banao

1. Telegram → **New Group** → **New Group**
2. Add members: apne bot ko add karo + ek dummy account (friend/family)
3. Group ka naam: `CampusDesk Storage`
4. Group ban jaane ke baad → **Group Settings** → **Group Type** → **Supergroup** mein convert karo (Telegram auto-prompt karega)
5. **Group Settings** → **Topics** → **Enable Topics** ON karo

Ab group mein topics support karega.

---

## Step 3: 4 Topics banao

Group mein → **Topics** tab → **Create Topic**:

| Topic Name | Kaam |
|------------|------|
| `CSE` | Computer Science & Engineering files |
| `CS` | Computer Science files |
| `AIML` | Artificial Intelligence & ML files |
| `DS` | Data Science files |

General topic by default rahega.

---

## Step 4: Bot ko Admin banao

Group Settings → **Administrators** → **Add Admin** → `CampusDesk Storage` bot search karo → Add

**Permissions:**
- ✅ Send Messages
- ✅ Send Media
- ✅ Post Messages
- ✅ Delete Messages (optional)

---

## Step 5: Group Chat ID nikalo

**Easiest method:**

1. Telegram mein `@userinfobot` search karo
2. Group ke kisi bhi message ko `@userinfobot` ko **forward** karo
3. Bot reply karega:
```

Chat ID: -1001234567890

```
4. Ye **group chat ID** copy karo

---

## Step 6: Har Topic ka ID nikalo

**Method — Telegram Web se:**

1. Telegram Web kholo (web.telegram.org)
2. Group kholo → har topic pe click karo
3. URL dekho, kuch aisa dikhega:
```

https://web.telegram.org/k/#-1001234567890_5
↑    ↑
chat   topic

```
4. `_` ke baad wala number **topic ID** hai

**Example output:**
```

CSE   → 5
CS    → 7
AIML  → 9
DS    → 11

```

**Alternative method:**
- Bot ko group mein add karo
- Har topic mein ek test message post karo (jaise "test CSE")
- Browser mein kholo:
```

https://api.telegram.org/bot<TOKEN>/getUpdates

```
- Response mein `message_thread_id` milega har message ke liye

---

## Step 7: `.env` file update karo

`campusdesk/.env` file kholo aur ye daalo:

```bash
STORAGE_PROVIDER=telegram

TELEGRAM_BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ
TELEGRAM_STORAGE_CHAT_ID=-1001234567890

# Branch code → topic ID mapping
TELEGRAM_TOPICS={"CSE":5,"CS":7,"AIML":9,"DS":11}
```

**Dhyan:**

- Chat ID **negative** hoga (supergroups ke liye)
- Topic IDs **positive integer** honge
- JSON valid hona chahiye (double quotes)

---

## Step 8: Restart & Test

```
start.bat
```

**Test workflow:**

1. **teacher1** se login karo
2. **Study Material** → navigate karo: `CSE → 1st Year → Sem 1 → Section A → A2`
3. **Upload File** → koi PDF daalo
4. **Telegram kholo** → `CampusDesk Storage` group → **CSE topic** mein file dikhegi ✅
5. Student login → Download karo → kaam karna chahiye

Har branch ke liye alag topic kaam karega.

---

## Limits & Gotchas

| Limit ↕▾ | Value ↕▾ |
|---|---|
| −**Upload max (Bot API)** | 50 MB |
| −**Download max (getFile)** | **20 MB** ⚠️ |
| −**Rate limit** | 30 messages/sec |
| −**File persistence** | Unlimited (jab tak topic delete na karo) |
⚙

### 20 MB se bade files ke liye

- LocalStorage provider use karo (default)
- Ya **Local Bot API Server** self-host karo (unlimited)
- Ya Cloudflare R2 pe shift karo (storage abstraction already ready)

### Common errors

**Error:** `chat not found`
**Fix:** Chat ID galat hai. Negative sign check karo, supergroup ka -100 prefix verify karo.

**Error:** `not enough rights to send documents`
**Fix:** Bot ko group admin banao aur "Send Media" permission do.

**Error:** `message thread not found`
**Fix:** Topic ID galat hai. Topic delete ho gaya ho sakta hai. Naya topic banao, naya ID lo.

**Error:** `file is too big`
**Fix:** File 50 MB se badi hai. Chhoti file try karo ya LocalStorage use karo.

---

## Security checklist

- ✅ Bot token sirf `.env` mein — frontend mein kabhi nahi
- ✅ `.env` git mein commit mat karo (already `.gitignore` mein hai)
- ✅ Group private rakho — public invite link mat banao
- ✅ Students ko Telegram ke baare mein kuch pata nahi chalega — sirf CampusDesk use karenge
- ✅ Storage abstraction ki wajah se future mein Cloudflare R2 pe switch karna easy hai

---

## Kaise verify karo sab chal raha hai

1. `python verify.py` chalao — data check hoga
2. Teacher se PDF upload karo
3. Telegram group mein jaake **CSE topic** kholo — file dikheni chahiye
4. Student se download karo — file save honi chahiye
5. `admin/storage` page pe mapping status check karo — green dots dikhne chahiye

</BDS:create_file>

<BDS:create_file fileName="campusdesk/services/storage.py">

```python
"""CampusDesk - storage abstraction layer.

Frontend → Flask → StorageProvider → { LocalProvider | TelegramProvider }

Telegram provider uses a SINGLE supergroup with FORUM TOPICS. Each branch
maps to one topic inside that group. This is easier to manage than separate
channels and works well as a "community" storage model.

Reference format:
    tg|<chat_id>|<topic_id>|<message_id>|<file_id>
    (pipe-separated so file_id can contain colons safely)

Public API:
    get_storage_provider(app_config) -> StorageProvider
    StorageError                     - raised on storage failures
    effective_upload_mb(app_config)  - returns the effective max upload size
"""
from __future__ import annotations
import json
import os
import re
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class StorageError(Exception):
    """Raised when a storage backend fails."""

# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------
class StorageProvider(ABC):
    name = "abstract"

    @abstractmethod
    def upload_file(self, file_bytes: bytes, filename: str, *,
                    branch_code: str | None = None,
                    folder_path: str | None = None) -> str:
        """Store file, return opaque reference string."""

    @abstractmethod
    def download_file(self, reference: str) -> bytes:
        ...

    @abstractmethod
    def delete_file(self, reference: str) -> bool:
        ...

    def replace_file(self, reference: str, file_bytes: bytes, filename: str,
                     *, branch_code: str | None = None,
                     folder_path: str | None = None) -> str:
        """Store new version, best-effort delete old."""
        new_ref = self.upload_file(file_bytes, filename,
                                   branch_code=branch_code,
                                   folder_path=folder_path)
        try:
            self.delete_file(reference)
        except Exception:
            pass
        return new_ref

# ---------------------------------------------------------------------------
# Filename sanitizer
# ---------------------------------------------------------------------------
_SAFE = re.compile(r"[^A-Za-z0-9._\-]+")

def _safe_name(name: str) -> str:
    base = os.path.basename(name or "file")
    base = _SAFE.sub("_", base).strip("._") or "file"
    return base[:180]

# ---------------------------------------------------------------------------
# Local filesystem provider (default)
# ---------------------------------------------------------------------------
class LocalProvider(StorageProvider):
    name = "local"

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir) / "storage"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, reference: str) -> Path:
        _, _, rest = reference.partition(":")
        return self.base_dir / rest

    def upload_file(self, file_bytes, filename, *, branch_code=None, folder_path=None):
        bucket = (branch_code or "COMMON").upper()
        (self.base_dir / bucket).mkdir(parents=True, exist_ok=True)
        uid = uuid.uuid4().hex[:12]
        safe = _safe_name(filename)
        rel = "{}/{}__{}".format(bucket, uid, safe)
        (self.base_dir / rel).write_bytes(file_bytes)
        return "local:" + rel

    def download_file(self, reference):
        p = self._path_for(reference)
        if not p.exists():
            raise StorageError("Local file not found: " + reference)
        return p.read_bytes()

    def delete_file(self, reference):
        p = self._path_for(reference)
        if p.exists():
            p.unlink()
            return True
        return False

# ---------------------------------------------------------------------------
# Telegram provider — supergroup + forum topics
# ---------------------------------------------------------------------------
class TelegramProvider(StorageProvider):
    """Store files as documents in a supergroup's topic threads.

    Reference format:
        tg|<chat_id>|<topic_id>|<message_id>|<file_id>

    - chat_id:    supergroup id (e.g. -1001234567890)
    - topic_id:   0 for General, else the topic's message_thread_id
    - message_id: message id of the uploaded document
    - file_id:    Telegram file_id used for downloads
    """
    name = "telegram"

    def __init__(self, bot_token: str, storage_chat_id: str,
                 topics: dict, api_base: str = "https://api.telegram.org"):
        if requests is None:
            raise StorageError("`requests` library required for Telegram provider")
        if not bot_token:
            raise StorageError("TELEGRAM_BOT_TOKEN is required")
        if not storage_chat_id:
            raise StorageError("TELEGRAM_STORAGE_CHAT_ID is required")

        self.token = bot_token.strip()
        self.chat_id = str(storage_chat_id).strip()
        # Normalize topic map: {"CSE": 5, "CS": 7, ...}
        self.topics = {}
        for k, v in (topics or {}).items():
            try:
                self.topics[str(k).upper()] = int(v)
            except (TypeError, ValueError):
                continue
        self.api_base = api_base.rstrip("/")

    # ------------------------------------------------------------------ urls
    def _url(self, method: str) -> str:
        return "{}/bot{}/{}".format(self.api_base, self.token, method)

    def _file_url(self, file_path: str) -> str:
        return "{}/file/bot{}/{}".format(self.api_base, self.token, file_path)

    # ---------------------------------------------------------------- topics
    def _topic_for(self, branch_code: str | None) -> int:
        """Return message_thread_id for a branch. 0 = General topic."""
        if not branch_code:
            return 0
        return self.topics.get(branch_code.upper(), 0)

    # ---------------------------------------------------------------- upload
    def upload_file(self, file_bytes, filename, *, branch_code=None, folder_path=None):
        topic_id = self._topic_for(branch_code)
        caption_parts = ["[CampusDesk]"]
        if branch_code:
            caption_parts.append(branch_code.upper())
        if folder_path:
            caption_parts.append("· " + folder_path)
        caption = " ".join(caption_parts)[:1000]

        data = {
            "chat_id": self.chat_id,
            "caption": caption,
        }
        if topic_id:
            data["message_thread_id"] = topic_id

        files = {"document": (_safe_name(filename), file_bytes)}

        try:
            r = requests.post(self._url("sendDocument"),
                              data=data, files=files, timeout=90)
            r.raise_for_status()
        except Exception as e:
            raise StorageError("Telegram upload failed: {}".format(e))

        payload = r.json()
        if not payload.get("ok"):
            raise StorageError("Telegram rejected upload: {}".format(payload))

        msg = payload["result"]
        chat_id = msg["chat"]["id"]
        message_id = msg["message_id"]
        # Document might be missing if Telegram rejected the file type
        doc = msg.get("document")
        if not doc:
            raise StorageError("Telegram did not return a document handle")

        file_id = doc["file_id"]
        return "tg|{}|{}|{}|{}".format(chat_id, topic_id, message_id, file_id)

    # -------------------------------------------------------------- download
    def download_file(self, reference):
        parts = reference.split("|")
        if len(parts) < 5:
            raise StorageError("Invalid Telegram reference: " + reference)
        file_id = parts[4]

        try:
            r = requests.get(self._url("getFile"),
                             params={"file_id": file_id},
                             timeout=30)
            r.raise_for_status()
        except Exception as e:
            raise StorageError("getFile request failed: {}".format(e))

        data = r.json()
        if not data.get("ok"):
            raise StorageError("getFile failed: {}".format(data))

        file_path = data["result"].get("file_path")
        if not file_path:
            raise StorageError("Telegram returned no file_path")

        try:
            dl = requests.get(self._file_url(file_path), timeout=120)
            dl.raise_for_status()
        except Exception as e:
            raise StorageError("Download failed: {}".format(e))

        return dl.content

    # ---------------------------------------------------------------- delete
    def delete_file(self, reference):
        """Best-effort delete. Requires bot to be group admin."""
        parts = reference.split("|")
        if len(parts) < 5:
            return False
        chat_id = parts[1]
        message_id = parts[3]

        try:
            r = requests.post(self._url("deleteMessage"),
                              data={"chat_id": chat_id,
                                    "message_id": message_id},
                              timeout=15)
            return r.json().get("ok", False)
        except Exception:
            return False

    # ------------------------------------------------------------------ info
    def get_me(self):
        """Return bot info (used to verify token)."""
        try:
            r = requests.get(self._url("getMe"), timeout=10)
            return r.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_chat(self):
        """Return chat info (used to verify chat id)."""
        try:
            r = requests.get(self._url("getChat"),
                             params={"chat_id": self.chat_id},
                             timeout=10)
            return r.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}

# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------
def get_storage_provider(app_config) -> StorageProvider:
    provider = (app_config.get("STORAGE_PROVIDER") or "local").lower()
    if provider == "telegram":
        try:
            topics = json.loads(app_config.get("TELEGRAM_TOPICS") or "{}")
        except json.JSONDecodeError:
            topics = {}
        return TelegramProvider(
            bot_token=app_config.get("TELEGRAM_BOT_TOKEN", ""),
            storage_chat_id=app_config.get("TELEGRAM_STORAGE_CHAT_ID", ""),
            topics=topics,
            api_base=app_config.get("TELEGRAM_API_BASE",
                                    "https://api.telegram.org"),
        )
    return LocalProvider(app_config["UPLOAD_FOLDER"])

# ---------------------------------------------------------------------------
# Effective upload size
# ---------------------------------------------------------------------------
def effective_upload_mb(app_config) -> int:
    """Return the max upload size (in MB) users can actually send.

    Telegram's Bot API caps uploads around 50 MB; we cap at 45 to leave
    headroom. Local storage just uses the configured MAX_UPLOAD_MB.
    """
    configured = int(app_config.get("MAX_UPLOAD_MB", 25) or 25)
    provider = (app_config.get("STORAGE_PROVIDER") or "local").lower()
    if provider == "telegram":
        return min(configured, 45)
    return configured

