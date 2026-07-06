from database.init_db import get_db


def userlist(user_id: int) -> dict:
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        # ── 1. All feeds the user is subscribed to, with their metadata ──────
        cursor.execute("""
            SELECT
                f.feed_sha256,
                f.feed_url,
                f.feed_title,
                f.feed_icon,
                f.feed_description,
                f.feed_lang,
                f.feed_last_update,
                f.entries_count,
                f.last_error,
                f.last_error_at
            FROM feeds f
            JOIN user_subscriptions us
                ON us.feed_sha256 = f.feed_sha256
            WHERE us.user_id = %s
        """, (user_id,))
        feeds_rows = cursor.fetchall()

        # ── 2. Tags for each feed ─────────────────────────────────────────────
        cursor.execute("""
            SELECT feed_sha256, tag
            FROM feed_tags
            WHERE user_id = %s
        """, (user_id,))
        tags_by_feed: dict[str, list[str]] = {}
        for row in cursor.fetchall():
            tags_by_feed.setdefault(row["feed_sha256"], []).append(row["tag"])

        # ── 3. Folder assignment for each feed ────────────────────────────────
        cursor.execute("""
            SELECT feed_sha256, folder_id
            FROM feed_folders
            WHERE user_id = %s
        """, (user_id,))
        folder_by_feed: dict[str, int | None] = {
            row["feed_sha256"]: row["folder_id"]
            for row in cursor.fetchall()
        }

        # ── 4. Full folder list (for building the hierarchy) ──────────────────
        cursor.execute("""
            SELECT id, name, parent_id
            FROM folders
            WHERE user_id = %s
        """, (user_id,))
        folders_rows = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    # ── Build folder map & tree ───────────────────────────────────────────────
    # folder_map: id → {id, name, parent_id, path}
    folder_map: dict[int, dict] = {
        f["id"]: {
            "id":        f["id"],
            "name":      f["name"],
            "parent_id": f["parent_id"],
            "path":      None,   # filled below
        }
        for f in folders_rows
    }

    def _folder_path(folder_id: int) -> str:
        """Returns a breadcrumb string like 'Tech > AI' for display."""
        parts = []
        fid = folder_id
        seen = set()
        while fid is not None and fid not in seen:
            seen.add(fid)
            node = folder_map.get(fid)
            if node is None:
                break
            parts.append(node["name"])
            fid = node["parent_id"]
        return " > ".join(reversed(parts))

    for fid in folder_map:
        folder_map[fid]["path"] = _folder_path(fid)

    # ── Assemble feeds ────────────────────────────────────────────────────────
    feeds_out = []
    for f in feeds_rows:
        sha = f["feed_sha256"]
        folder_id = folder_by_feed.get(sha)
        folder_info = folder_map.get(folder_id) if folder_id else None

        feeds_out.append({
            "feed_sha256":    sha,
            "url":            f["feed_url"],
            "title":          f["feed_title"],
            "icon":           f["feed_icon"],
            "description":    f["feed_description"],
            "lang":           f["feed_lang"],
            "last_update":    f["feed_last_update"].isoformat() if f["feed_last_update"] else None,
            "entries_count":  f["entries_count"],
            "last_error":     f["last_error"],
            "last_error_at":  f["last_error_at"].isoformat() if f["last_error_at"] else None,
            "tags":           tags_by_feed.get(sha, []),
            "folder": {
                "id":       folder_info["id"],
                "name":     folder_info["name"],
                "parent_id": folder_info["parent_id"],
                "path":     folder_info["path"],
            } if folder_info else None,
        })

    # ── Assemble folder tree ──────────────────────────────────────────────────
    folders_out = []
    for node in folder_map.values():
        folders_out.append({
            "id":        node["id"],
            "name":      node["name"],
            "parent_id": node["parent_id"],
            "path":      node["path"],
        })

    return {
        "feeds":   feeds_out,
        "folders": folders_out,
    }