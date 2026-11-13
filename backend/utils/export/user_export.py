"""
utils/export/user_export.py — export of a user's reading annotations
and saves (notes/comments, highlights, saved posts) as a single file
in CSV, JSON or Markdown format.

All three renderers work from the same intermediate data structure, so
the formats never drift apart. Article metadata (title, url, feed
title, publication date) is fetched in one batch from Qdrant; items
whose point is gone from the index are still exported, just without
article metadata.
"""

import csv
import io
import json
import logging
import re
import uuid
from datetime import datetime, timezone

from fastapi.responses import Response

from database.init_db import get_db
from intelligence.embeddings import get_qdrant_client, COLLECTION_NAME

logger = logging.getLogger(__name__)

FORMATS = {"json": "application/json", "csv": "text/csv", "md": "text/markdown"}
FILE_EXT = {"json": "json", "csv": "csv", "md": "md"}

CSV_COLUMNS = [
    "type",
    "item_id",
    "article_title",
    "article_url",
    "feed_title",
    "article_pub_date",
    "text",
    "color",
    "created_at",
    "updated_at",
    "archived",
]


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

def _iso(dt) -> str | None:
    """Naive DATETIME rows are UTC-aware by construction upstream; expose plain ISO."""
    return dt.isoformat() if dt else None


def _fetch_user_data(user_id: int) -> dict:
    notes, highlights, saves = [], [], []

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT item_id, content_md, created_at, updated_at
                FROM article_comments WHERE user_id = %s
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            notes = cursor.fetchall()

            cursor.execute(
                """
                SELECT item_id, text, color, sort_order, created_at
                FROM highlights WHERE user_id = %s
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            highlights = cursor.fetchall()

            cursor.execute(
                """
                SELECT item_id, created_at, archived
                FROM interactions
                WHERE user_id = %s AND action = 'saved'
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            saves = cursor.fetchall()
        finally:
            cursor.close()

    return {
        "notes": notes,
        "highlights": highlights,
        "saves": saves,
    }


# Qdrant point ids are uuid5 strings (modern rows) or sha256 hex (legacy
# rows). Anything else can't be a point id — filtering it out keeps one
# malformed id from failing the whole batched retrieve (Qdrant 400s).
_VALID_POINT_ID = re.compile(r"^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$|^[0-9a-f]{64}$")


def _fetch_article_metadata(item_ids: list[str]) -> tuple[dict[str, dict], bool]:
    """
    One batched Qdrant retrieve for every distinct item_id.
    Returns ({item_id: metadata}, metadata_available). On any Qdrant
    failure the export still works, only without article metadata.
    """
    unique_ids = [i for i in dict.fromkeys(item_ids) if _VALID_POINT_ID.match(i)]
    if not unique_ids:
        return {}, True

    try:
        client = get_qdrant_client()
        points = client.retrieve(
            collection_name=COLLECTION_NAME,
            ids=unique_ids,
            with_payload=True,
            with_vectors=False,
        )
    except Exception as exc:  # Qdrant down / collection missing — degrade, don't fail
        logger.warning("User export: article metadata unavailable (%s)", exc)
        return {}, False

    index: dict[str, dict] = {}
    for point in points:
        payload = point.payload or {}
        index[str(point.id)] = {
            "title": payload.get("title") or "",
            "url": payload.get("link") or "",
            "feed_title": payload.get("feed_title") or "",
            "pub_date": payload.get("pub_date") or "",
        }
    return index, True


def _build_export_data(user: dict) -> dict:
    user_id = user["id"]
    raw = _fetch_user_data(user_id)

    item_ids = (
        [r["item_id"] for r in raw["notes"]]
        + [r["item_id"] for r in raw["highlights"]]
        + [r["item_id"] for r in raw["saves"]]
    )
    articles, metadata_available = _fetch_article_metadata(item_ids)

    def meta(item_id: str) -> dict:
        return articles.get(item_id, {})

    notes = [
        {
            "item_id": r["item_id"],
            "article_title": meta(r["item_id"]).get("title", ""),
            "article_url": meta(r["item_id"]).get("url", ""),
            "feed_title": meta(r["item_id"]).get("feed_title", ""),
            "content_md": r["content_md"],
            "created_at": _iso(r["created_at"]),
            "updated_at": _iso(r["updated_at"]),
        }
        for r in raw["notes"]
    ]

    highlights = [
        {
            "item_id": r["item_id"],
            "article_title": meta(r["item_id"]).get("title", ""),
            "article_url": meta(r["item_id"]).get("url", ""),
            "feed_title": meta(r["item_id"]).get("feed_title", ""),
            "text": r["text"],
            "color": r["color"],
            "sort_order": r["sort_order"],
            "created_at": _iso(r["created_at"]),
        }
        for r in raw["highlights"]
    ]

    saves = [
        {
            "item_id": r["item_id"],
            "article_title": meta(r["item_id"]).get("title", ""),
            "article_url": meta(r["item_id"]).get("url", ""),
            "feed_title": meta(r["item_id"]).get("feed_title", ""),
            "article_pub_date": meta(r["item_id"]).get("pub_date", ""),
            "saved_at": _iso(r["created_at"]),
            "archived": bool(r["archived"]),
        }
        for r in raw["saves"]
    ]

    return {
        "format": "berga-user-export",
        "version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "article_metadata_available": metadata_available,
        "notes": notes,
        "highlights": highlights,
        "saves": saves,
    }


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------

def _render_json(data: dict) -> bytes:
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


def _render_csv(data: dict) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_ALL)
    writer.writerow(CSV_COLUMNS)

    for n in data["notes"]:
        writer.writerow([
            "note", n["item_id"], n["article_title"], n["article_url"],
            n["feed_title"], "", n["content_md"], "", n["created_at"],
            n["updated_at"], "",
        ])
    for h in data["highlights"]:
        writer.writerow([
            "highlight", h["item_id"], h["article_title"], h["article_url"],
            h["feed_title"], "", h["text"], h["color"], h["created_at"],
            "", "",
        ])
    for s in data["saves"]:
        writer.writerow([
            "save", s["item_id"], s["article_title"], s["article_url"],
            s["feed_title"], s["article_pub_date"], "", "", s["saved_at"],
            "", 1 if s["archived"] else 0,
        ])

    # utf-8-sig BOM so Excel opens the file with the right encoding
    return buf.getvalue().encode("utf-8-sig")


def _article_heading(item_id: str, title: str, url: str) -> str:
    if title and url:
        return f"[{title}]({url})"
    if title or url:
        return title or url
    return f"Article `{item_id}`"


def _render_markdown(data: dict) -> bytes:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    counts = (len(data["saves"]), len(data["notes"]), len(data["highlights"]))
    lines = [
        "# Berga export",
        "",
        f"_Generated {now} — {counts[0]} saved posts, {counts[1]} notes, {counts[2]} highlights_",
        "",
    ]

    if not data["article_metadata_available"]:
        lines += [
            "> Note: article titles and links were unavailable at export time "
            "(article index unreachable). Items are identified by their id.",
            "",
        ]

    lines += ["## Saved posts", ""]
    if data["saves"]:
        for s in data["saves"]:
            lines.append(f'### {_article_heading(s["item_id"], s["article_title"], s["article_url"])}')
            details = []
            if s["feed_title"]:
                details.append(s["feed_title"])
            if s["article_pub_date"]:
                details.append(f"Published {s['article_pub_date']}")
            if s["saved_at"]:
                details.append(f"Saved {s['saved_at']}")
            if s["archived"]:
                details.append("Archived")
            if details:
                lines.append(f"*{' · '.join(details)}*")
            lines.append("")
    else:
        lines += ["_None._", ""]

    lines += ["## Notes", ""]
    if data["notes"]:
        for n in data["notes"]:
            lines.append(f'### {_article_heading(n["item_id"], n["article_title"], n["article_url"])}')
            details = []
            if n["feed_title"]:
                details.append(n["feed_title"])
            if n["created_at"]:
                details.append(n["created_at"])
            if details:
                lines.append(f"*{' · '.join(details)}*")
            lines.append("")
            for content_line in (n["content_md"] or "").splitlines() or [""]:
                lines.append(f"> {content_line}".rstrip())
            lines.append("")
    else:
        lines += ["_None._", ""]

    lines += ["## Highlights", ""]
    if data["highlights"]:
        current_item = None
        for h in data["highlights"]:
            if h["item_id"] != current_item:
                current_item = h["item_id"]
                lines.append(f'### {_article_heading(h["item_id"], h["article_title"], h["article_url"])}')
                if h["created_at"]:
                    lines.append(f"*{h['created_at']}*")
                lines.append("")
            lines.append(f'- \u201c{h["text"]}\u201d')
        lines.append("")
    else:
        lines += ["_None._", ""]

    return "\n".join(lines).encode("utf-8")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def export(user: dict, fmt: str) -> Response:
    fmt = (fmt or "json").lower()
    if fmt not in FORMATS:
        return Response(
            content=json.dumps({"detail": "format must be one of: json, csv, md"}),
            status_code=400,
            media_type="application/json",
        )

    data = _build_export_data(user)

    renderer = {
        "json": _render_json,
        "csv": _render_csv,
        "md": _render_markdown,
    }[fmt]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"berga-export-{stamp}.{FILE_EXT[fmt]}"

    logger.info(
        "User data exported: user=%s format=%s notes=%s highlights=%s saves=%s",
        user["id"], fmt, len(data["notes"]), len(data["highlights"]), len(data["saves"]),
    )

    return Response(
        content=renderer(data),
        media_type=FORMATS[fmt],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
