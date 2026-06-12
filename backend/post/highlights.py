import logging

from database.init_db import get_db

logger = logging.getLogger(__name__)

MAX_HIGHLIGHT_TEXT = 1000


def get_highlights(user_id: int, item_id: str) -> list:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id, text, color, sort_order FROM highlights "
                "WHERE user_id = %s AND item_id = %s ORDER BY sort_order",
                (user_id, item_id),
            )
            return cursor.fetchall()
        finally:
            cursor.close()


def _compute_sort_order(item_id: str, text: str) -> int:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT content_html FROM article_cache WHERE item_id = %s",
                (item_id,),
            )
            row = cursor.fetchone()
            if not row or not row["content_html"]:
                return 0
            idx = row["content_html"].find(text)
            return max(idx, 0)
        finally:
            cursor.close()


def _find_overlapping(user_id: int, item_id: str, new_text: str) -> list:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id, text FROM highlights "
                "WHERE user_id = %s AND item_id = %s",
                (user_id, item_id),
            )
            existing = cursor.fetchall()
        finally:
            cursor.close()

    overlapping = []
    for row in existing:
        existing_text = row["text"]
        if new_text in existing_text or existing_text in new_text:
            overlapping.append(row)
        elif _texts_overlap(new_text, existing_text):
            overlapping.append(row)
    return overlapping


def _texts_overlap(a: str, b: str) -> bool:
    if len(a) < 4 or len(b) < 4:
        return False
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    window = max(len(shorter) // 2, 4)
    for i in range(len(shorter) - window + 1):
        if longer.find(shorter[i:i + window]) >= 0:
            return True
    return False


def _merge_texts(new_text: str, new_color: str, overlapping: list, item_id: str) -> tuple:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT content_html FROM article_cache WHERE item_id = %s",
                (item_id,),
            )
            row = cursor.fetchone()
        finally:
            cursor.close()

    if not row or not row["content_html"]:
        return new_text, new_color

    html = row["content_html"]
    all_texts = [new_text] + [r["text"] for r in overlapping]
    positions = []
    for t in all_texts:
        idx = html.find(t)
        if idx >= 0:
            positions.append((idx, idx + len(t), t))
    if not positions:
        return new_text, new_color
    positions.sort(key=lambda x: x[0])
    merged_start = positions[0][0]
    merged_end = positions[-1][1]
    merged_text = html[merged_start:merged_end]
    if len(merged_text) > MAX_HIGHLIGHT_TEXT:
        merged_text = merged_text[:MAX_HIGHLIGHT_TEXT]
    return merged_text, new_color


def create_highlight(user_id: int, item_id: str, text: str, color: str) -> dict:
    text = text.strip()
    if not text:
        return {"status": "error", "message": "Empty highlight text"}
    if len(text) > MAX_HIGHLIGHT_TEXT:
        text = text[:MAX_HIGHLIGHT_TEXT]

    overlapping = _find_overlapping(user_id, item_id, text)

    with get_db() as conn:
        cursor = conn.cursor()
        try:
            if overlapping:
                merged_text, merged_color = _merge_texts(text, color, overlapping, item_id)
                for row in overlapping:
                    cursor.execute(
                        "DELETE FROM highlights WHERE id = %s AND user_id = %s",
                        (row["id"], user_id),
                    )
                text = merged_text
                color = merged_color

            sort_order = _compute_sort_order(item_id, text)

            cursor.execute(
                "INSERT INTO highlights (user_id, item_id, text, color, sort_order) "
                "VALUES (%s, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE color = VALUES(color), sort_order = VALUES(sort_order)",
                (user_id, item_id, text, color, sort_order),
            )
            conn.commit()
            highlight_id = cursor.lastrowid

            return {
                "status": "success",
                "highlight": {
                    "id": highlight_id,
                    "text": text,
                    "color": color,
                    "sort_order": sort_order,
                },
            }
        except Exception as e:
            conn.rollback()
            logger.error("Error creating highlight: %s", e)
            return {"status": "error", "message": str(e)}
        finally:
            cursor.close()


def delete_highlight(user_id: int, highlight_id: int) -> dict:
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM highlights WHERE id = %s AND user_id = %s",
                (highlight_id, user_id),
            )
            if cursor.rowcount == 0:
                return {"status": "error", "message": "Highlight not found"}
            conn.commit()
            return {"status": "success", "deleted": highlight_id}
        except Exception as e:
            conn.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            cursor.close()
