import hashlib

from fastapi import HTTPException
from pydantic import BaseModel
from database.init_db import get_db


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------

class StructureRequest(BaseModel):
    task: str

    # create_folder / move_folder target parent
    name: str | None = None
    parent_folder: str | None = None   # folder SHA-256

    # references
    folder: str | None = None   # folder SHA-256 being acted on
    feed: str | None = None     # feed_sha256 being acted on


# ---------------------------------------------------------------------------
# Folder helpers
# ---------------------------------------------------------------------------

def _folder_belongs_to_user(cursor, folder_id: str, user_id: int) -> bool:
    cursor.execute(
        "SELECT id FROM folders WHERE id = %s AND user_id = %s",
        (folder_id, user_id),
    )
    return cursor.fetchone() is not None


def get_folder_info(folder_id: str, user_id: int) -> dict:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT
            f.id AS folder_id,
            f.name AS folder_name,
            f.description,
            f.parent_id,
            f.created_at,
            (SELECT COUNT(*) FROM feed_folders ff WHERE ff.folder_id = f.id AND ff.user_id = %s) AS feeds_count
        FROM folders f
        WHERE f.id = %s AND f.user_id = %s
        """,
        (user_id, folder_id, user_id),
    )
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Folder not found or access denied")

    return {
        "folder_id": row["folder_id"],
        "folder_name": row["folder_name"],
        "description": row["description"],
        "feeds_count": row["feeds_count"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


def _feed_belongs_to_user(cursor, feed_sha256: str, user_id: int) -> bool:
    cursor.execute(
        "SELECT 1 FROM user_subscriptions WHERE user_id = %s AND feed_sha256 = %s",
        (user_id, feed_sha256),
    )
    return cursor.fetchone() is not None


def _would_create_cycle(cursor, folder_id: str, new_parent_id: str | None) -> bool:
    if new_parent_id is None:
        return False
    if new_parent_id == folder_id:
        return True

    current: str | None = new_parent_id
    visited: set[str] = set()
    while current is not None:
        if current in visited:
            break
        visited.add(current)
        cursor.execute("SELECT parent_id FROM folders WHERE id = %s", (current,))
        row = cursor.fetchone()
        if row is None:
            break
        current = row[0]
        if current == folder_id:
            return True
    return False


def _compute_folder_id(username: str, parent_id: str | None, name: str) -> str:
    """Deterministic SHA-256 for a folder — mirrors the logic in opml.py."""
    return hashlib.sha256(
        f"{username}^{parent_id or ''}^{name}".encode()
    ).hexdigest()


# ---------------------------------------------------------------------------
# Task handlers
# ---------------------------------------------------------------------------

def _create_folder(
    cursor, user_id: int, username: str, name: str, parent_folder: str | None
) -> dict:
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Folder name must not be empty")

    name = name.strip()

    if parent_folder is not None:
        if not _folder_belongs_to_user(cursor, parent_folder, user_id):
            raise HTTPException(status_code=403, detail="Parent folder not found or access denied")

    folder_id = _compute_folder_id(username, parent_folder, name)

    cursor.execute("SELECT id FROM folders WHERE id = %s", (folder_id,))
    if cursor.fetchone():
        raise HTTPException(
            status_code=409,
            detail=f"A folder named '{name}' already exists at this level",
        )

    cursor.execute(
        "INSERT INTO folders (id, user_id, name, parent_id) VALUES (%s, %s, %s, %s)",
        (folder_id, user_id, name, parent_folder),
    )
    return {"folder_id": folder_id, "name": name, "parent_folder": parent_folder}


def _delete_folder(cursor, user_id: int, folder_id: str) -> dict:
    if not _folder_belongs_to_user(cursor, folder_id, user_id):
        raise HTTPException(status_code=403, detail="Folder not found or access denied")

    # Collect entire subtree (BFS)
    to_delete: list[str] = []
    queue: list[str] = [folder_id]
    while queue:
        current = queue.pop()
        to_delete.append(current)
        cursor.execute(
            "SELECT id FROM folders WHERE parent_id = %s AND user_id = %s",
            (current, user_id),
        )
        queue.extend(row[0] for row in cursor.fetchall())

    placeholders = ", ".join(["%s"] * len(to_delete))

    cursor.execute(
        f"DELETE FROM feed_folders WHERE user_id = %s AND folder_id IN ({placeholders})",
        (user_id, *to_delete),
    )
    unlinked = cursor.rowcount

    cursor.execute(
        f"""
        DELETE ft FROM feed_tags ft
        JOIN folders f ON f.name = ft.tag
        WHERE ft.user_id = %s AND f.id IN ({placeholders})
        """,
        (user_id, *to_delete),
    )

    cursor.execute(
        f"DELETE FROM folders WHERE id IN ({placeholders}) AND user_id = %s",
        (*to_delete, user_id),
    )

    return {"deleted_folders": to_delete, "unlinked_feeds": unlinked}


def _delete_feed(cursor, user_id: int, feed_sha256: str) -> dict:
    if not _feed_belongs_to_user(cursor, feed_sha256, user_id):
        raise HTTPException(status_code=403, detail="Feed not found or access denied")

    cursor.execute(
        "DELETE FROM feed_folders WHERE user_id = %s AND feed_sha256 = %s",
        (user_id, feed_sha256),
    )
    cursor.execute(
        "DELETE FROM feed_tags WHERE user_id = %s AND feed_sha256 = %s",
        (user_id, feed_sha256),
    )
    cursor.execute(
        "DELETE FROM user_subscriptions WHERE user_id = %s AND feed_sha256 = %s",
        (user_id, feed_sha256),
    )
    cursor.execute(
        """
        UPDATE feeds
        SET total_users = (
            SELECT COUNT(*) FROM user_subscriptions WHERE feed_sha256 = %s
        )
        WHERE feed_sha256 = %s
        """,
        (feed_sha256, feed_sha256),
    )

    return {"deleted_feed": feed_sha256}


def _move_feed(cursor, user_id: int, feed_sha256: str, target_folder_id: str | None) -> dict:
    if not _feed_belongs_to_user(cursor, feed_sha256, user_id):
        raise HTTPException(status_code=403, detail="Feed not found or access denied")

    if target_folder_id is not None:
        if not _folder_belongs_to_user(cursor, target_folder_id, user_id):
            raise HTTPException(status_code=403, detail="Target folder not found or access denied")

    # Resolve folder name for tag sync
    new_folder_name: str | None = None
    if target_folder_id is not None:
        cursor.execute("SELECT name FROM folders WHERE id = %s", (target_folder_id,))
        row = cursor.fetchone()
        new_folder_name = row[0] if row else None

    # Wipe old link unconditionally, then re-insert
    cursor.execute(
        "DELETE FROM feed_folders WHERE user_id = %s AND feed_sha256 = %s",
        (user_id, feed_sha256),
    )
    if target_folder_id is not None:
        cursor.execute(
            "INSERT INTO feed_folders (user_id, feed_sha256, folder_id) VALUES (%s, %s, %s)",
            (user_id, feed_sha256, target_folder_id),
        )

    # Sync leaf tag
    cursor.execute(
        "DELETE FROM feed_tags WHERE user_id = %s AND feed_sha256 = %s",
        (user_id, feed_sha256),
    )
    if new_folder_name:
        cursor.execute(
            "INSERT IGNORE INTO feed_tags (user_id, feed_sha256, tag) VALUES (%s, %s, %s)",
            (user_id, feed_sha256, new_folder_name),
        )

    return {
        "moved_feed":     feed_sha256,
        "to_folder_id":   target_folder_id,
        "to_folder_name": new_folder_name,
    }


def _move_folder(cursor, user_id: int, folder_id: str, new_parent_id: str | None) -> dict:
    if not _folder_belongs_to_user(cursor, folder_id, user_id):
        raise HTTPException(status_code=403, detail="Folder not found or access denied")

    if new_parent_id is not None:
        if not _folder_belongs_to_user(cursor, new_parent_id, user_id):
            raise HTTPException(status_code=403, detail="Target folder not found or access denied")

    if _would_create_cycle(cursor, folder_id, new_parent_id):
        raise HTTPException(
            status_code=400,
            detail="Cannot move a folder into one of its own descendants",
        )

    cursor.execute(
        "UPDATE folders SET parent_id = %s WHERE id = %s AND user_id = %s",
        (new_parent_id, folder_id, user_id),
    )

    return {"moved_folder": folder_id, "to_parent_id": new_parent_id}


# ---------------------------------------------------------------------------
# list_subscriptions — feeds + empty folders
# ---------------------------------------------------------------------------

def list_subscriptions(user_id: int) -> dict:
    """
    Returns all subscribed feeds WITH folder information, plus folders
    that don't have any feeds yet — so newly created folders appear
    immediately in the panel without needing to add a feed to them first.

    Empty folder entries carry the `_empty_folder: True` flag so the
    frontend knows not to render a feed row for them.
    """
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                f.feed_sha256,
                f.feed_url        AS url,
                f.feed_title      AS title,
                f.feed_icon       AS icon,
                fo.id             AS folder_id,
                fo.name           AS folder_name,
                fo.parent_id      AS folder_parent_id
            FROM user_subscriptions us
            JOIN feeds f ON f.feed_sha256 = us.feed_sha256
            LEFT JOIN feed_folders ff ON ff.user_id = us.user_id
                                     AND ff.feed_sha256 = f.feed_sha256
            LEFT JOIN folders fo ON fo.id = ff.folder_id
            WHERE us.user_id = %s
            ORDER BY fo.name, f.feed_title
            """,
            (user_id,),
        )
        feed_rows = cursor.fetchall()

        # Folders that don't appear in any user's feed_folders
        cursor.execute(
            """
            SELECT fo.id, fo.name, fo.parent_id
            FROM folders fo
            WHERE fo.user_id = %s
              AND fo.id NOT IN (
                  SELECT DISTINCT folder_id
                  FROM feed_folders
                  WHERE user_id = %s AND folder_id IS NOT NULL
              )
            ORDER BY fo.name
            """,
            (user_id, user_id),
        )
        empty_folder_rows = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    feeds = [
        {
            "feed_sha256": r["feed_sha256"],
            "url":         r["url"],
            "title":       r["title"],
            "icon":        r["icon"],
            "folder": {
                "id":        r["folder_id"],
                "name":      r["folder_name"],
                "parent_id": r["folder_parent_id"],
            } if r["folder_id"] else None,
        }
        for r in feed_rows
    ]

    empty_folders = [
        {
            "feed_sha256":   None,
            "url":           None,
            "title":         None,
            "icon":          None,
            "_empty_folder": True,
            "folder": {
                "id":        ef["id"],
                "name":      ef["name"],
                "parent_id": ef["parent_id"],
            },
        }
        for ef in empty_folder_rows
    ]

    return {"feeds": feeds + empty_folders}


# ---------------------------------------------------------------------------
# FastAPI endpoint
# ---------------------------------------------------------------------------

VALID_TASKS = {"create_folder", "delete_folder", "delete_feed", "move_feed", "move_folder"}


async def following_structure(body: StructureRequest, user: dict):
    if body.task not in VALID_TASKS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task '{body.task}'. Valid tasks: {sorted(VALID_TASKS)}",
        )

    user_id: int = user["id"]
    username: str = user["username"]
    conn = get_db()
    cursor = conn.cursor()

    try:
        match body.task:
            case "create_folder":
                if not body.name:
                    raise HTTPException(status_code=400, detail="'name' is required for create_folder")
                result = _create_folder(cursor, user_id, username, body.name, body.parent_folder)

            case "delete_folder":
                if body.folder is None:
                    raise HTTPException(status_code=400, detail="'folder' is required for delete_folder")
                result = _delete_folder(cursor, user_id, body.folder)

            case "delete_feed":
                if not body.feed:
                    raise HTTPException(status_code=400, detail="'feed' is required for delete_feed")
                result = _delete_feed(cursor, user_id, body.feed)

            case "move_feed":
                if not body.feed:
                    raise HTTPException(status_code=400, detail="'feed' is required for move_feed")
                result = _move_feed(cursor, user_id, body.feed, body.folder)

            case "move_folder":
                if body.folder is None:
                    raise HTTPException(status_code=400, detail="'folder' is required for move_folder")
                result = _move_folder(cursor, user_id, body.folder, body.parent_folder)

        conn.commit()

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Operation failed: {e}") from e

    finally:
        cursor.close()
        conn.close()

    return {"ok": True, "task": body.task, **result}