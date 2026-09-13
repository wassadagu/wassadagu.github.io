#!/usr/bin/env python3
"""Build the public hub index from per-media and pending mapping documents."""
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
index_path = root / "index.json"
try:
    document = json.loads(index_path.read_text(encoding="utf-8"))
except (FileNotFoundError, json.JSONDecodeError):
    document = {"title": "와 싸다구 | 오늘의 추천템", "description": "가격과 상품 정보를 확인하고 마음에 드는 상품을 만나보세요.", "items": []}
legacy = [item for item in document.get("items", []) if item.get("sharelink_url") and re.sub(r"^\\d+\\.\\s*", "", str(item.get("name", ""))).strip()]
legacy_by_media = {item.get("media_id"): item for item in legacy if item.get("media_id")}
legacy_by_item = {item.get("item_id"): item for item in legacy if item.get("item_id")}
items = {}
resolved_item_ids = set()

for path in sorted((root / "links").glob("*.json")):
    try:
        item = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        continue
    media_id = item.get("media_id") or path.stem
    if not media_id or not item.get("sharelink_url"):
        continue
    base = legacy_by_media.get(media_id) or legacy_by_item.get(item.get("item_id"), {})
    merged = dict(base)
    merged.update({key: value for key, value in item.items() if value not in (None, "")})
    if not re.sub(r"^\\d+\\.\\s*", "", str(merged.get("name", ""))).strip():
        continue
    merged["media_id"] = media_id
    merged["mapping_status"] = "MAPPED"
    items[("media", media_id)] = merged
    if merged.get("item_id"):
        resolved_item_ids.add(merged["item_id"])

for path in sorted((root / "pending").glob("*.json")):
    try:
        item = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        continue
    if not item.get("publication_key") or not item.get("sharelink_url"):
        continue
    if item.get("item_id") in resolved_item_ids:
        continue
    base = legacy_by_item.get(item.get("item_id"), {})
    merged = dict(base)
    merged.update({key: value for key, value in item.items() if value not in (None, "")})
    merged.pop("media_id", None)
    if not re.sub(r"^\\d+\\.\\s*", "", str(merged.get("name", ""))).strip():
        continue
    merged["mapping_status"] = "PENDING"
    items[("pending", item["publication_key"])] = merged

for media_id, item in legacy_by_media.items():
    items.setdefault(("media", media_id), item)

values = list(items.values())
values.sort(key=lambda item: item.get("published_at", ""))
for number, item in enumerate(values, 1):
    item["product_number"] = number
    name = re.sub(r"^\\d+\\.\\s+", "", str(item.get("name", "")))
    name = re.sub(r"^\\[\\d+\\]\\s+", "", name)
    item["name"] = f"{number}. {name}"
values.sort(key=lambda item: item.get("published_at", ""), reverse=True)
document["items"] = values
index_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
