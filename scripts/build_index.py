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

def clean_name(value):
    value = str(value or "").strip()
    while re.match(r"^\d+\.\s*", value):
        value = re.sub(r"^\d+\.\s*", "", value, count=1)
    value = re.sub(r"^\[\d+\]\s*", "", value)
    return value.strip()

def source_number(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return number if number > 0 else 0

legacy = [item for item in document.get("items", []) if item.get("sharelink_url") and clean_name(item.get("name"))]
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
    number = source_number(item.get("product_number"))
    base = legacy_by_media.get(media_id) or legacy_by_item.get(item.get("item_id"), {})
    merged = dict(base)
    merged.update({key: value for key, value in item.items() if value not in (None, "")})
    if not clean_name(merged.get("name")):
        continue
    merged["media_id"] = media_id
    merged["mapping_status"] = "MAPPED"
    if number:
        merged["product_number"] = number
    else:
        merged.pop("product_number", None)
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
    number = source_number(item.get("product_number"))
    base = legacy_by_item.get(item.get("item_id"), {})
    merged = dict(base)
    merged.update({key: value for key, value in item.items() if value not in (None, "")})
    if not clean_name(merged.get("name")):
        continue
    merged.pop("media_id", None)
    merged["mapping_status"] = "PENDING"
    if number:
        merged["product_number"] = number
    else:
        merged.pop("product_number", None)
    items[("pending", item["publication_key"])] = merged

for media_id, item in legacy_by_media.items():
    if ("media", media_id) not in items:
        legacy_item = dict(item)
        legacy_item.pop("product_number", None)
        items[("media", media_id)] = legacy_item

values = list(items.values())
for item in values:
    number = source_number(item.get("product_number"))
    name = clean_name(item.get("name"))
    if number:
        item["product_number"] = number
        item["name"] = f"{number}. {name}"
    else:
        item.pop("product_number", None)
        item["name"] = name
values.sort(key=lambda item: item.get("published_at", ""), reverse=True)
document["items"] = values
index_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
