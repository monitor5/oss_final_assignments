"""이름 + 패스워드 기반의 간단한 추천 결과 저장/불러오기.

- DB 없이 JSON 파일 하나(store.json)에 저장한다. (입문자 과제 수준)
- 패스워드는 평문이 아니라 salt + SHA-256 해시로 저장한다.
- 같은 이름이 이미 있으면 패스워드가 일치해야만 저장/조회가 가능하다.
"""

import json
import os
import hashlib
import threading
from datetime import datetime

# 컨테이너 안에서는 /app/data, 로컬 실행 시에는 back/data 에 저장된다.
# 이 디렉터리는 docker-compose 에서 호스트 ./back/data 로 바인드 마운트되므로
# 컨테이너를 지우거나 서버를 재부팅해도 storage.json 은 그대로 유지된다.
DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
STORE_PATH = os.path.join(DATA_DIR, "storage.json")

# 파일 동시 접근 방지용 락
_lock = threading.Lock()

# 패스워드 해시에 섞는 고정 salt (데모용. 실서비스라면 사용자별 랜덤 salt 권장)
_SALT = "camera-match-salt-v1"


def _hash_password(password: str) -> str:
    return hashlib.sha256((_SALT + password).encode("utf-8")).hexdigest()


def _load_store() -> dict:
    if not os.path.exists(STORE_PATH):
        return {"users": {}}
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"users": {}}


def _write_store(store: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def init_store() -> None:
    """서버 시작 시 storage.json 이 없으면 빈 구조로 생성한다.
    (이미 파일이 있으면 그대로 두므로 기존 데이터가 보존된다.)"""
    if not os.path.exists(STORE_PATH):
        _write_store({"users": {}})


class AuthError(Exception):
    """이름은 있는데 패스워드가 틀린 경우."""


def save_record(name: str, password: str, record: dict) -> int:
    """(name, password) 사용자에게 record 한 건을 저장하고, 저장 후 총 개수를 반환."""
    with _lock:
        store = _load_store()
        users = store.setdefault("users", {})
        pw_hash = _hash_password(password)

        user = users.get(name)
        if user is None:
            # 신규 사용자 등록
            user = {"pw_hash": pw_hash, "records": []}
            users[name] = user
        elif user["pw_hash"] != pw_hash:
            raise AuthError("password mismatch")

        record = dict(record)
        record["saved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user["records"].append(record)

        _write_store(store)
        return len(user["records"])


def load_records(name: str, password: str) -> list:
    """(name, password) 가 맞으면 저장된 기록 리스트(최신순)를 반환."""
    with _lock:
        store = _load_store()
        user = store.get("users", {}).get(name)
        if user is None:
            return []
        if user["pw_hash"] != _hash_password(password):
            raise AuthError("password mismatch")
        return list(reversed(user["records"]))


def restore_records(name: str, password: str, records: list) -> int:
    """JSON 백업 파일에서 읽어온 기록들을 (name, password) 사용자에게 복원(추가)한다.

    신규 사용자면 등록하고, 기존 사용자면 패스워드가 일치해야 한다.
    복원 후 해당 사용자의 총 기록 개수를 반환한다.
    """
    with _lock:
        store = _load_store()
        users = store.setdefault("users", {})
        pw_hash = _hash_password(password)

        user = users.get(name)
        if user is None:
            user = {"pw_hash": pw_hash, "records": []}
            users[name] = user
        elif user["pw_hash"] != pw_hash:
            raise AuthError("password mismatch")

        for rec in records:
            rec = dict(rec)
            # 백업 파일에 저장 시각이 없으면 현재 시각으로 채운다.
            if not rec.get("saved_at"):
                rec["saved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            user["records"].append(rec)

        _write_store(store)
        return len(user["records"])
