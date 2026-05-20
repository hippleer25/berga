import xml.etree.ElementTree as ET
from fastapi.responses import Response
from database.init_db import get_db


# ---------------------------------------------------------------------------
# Folder tree helpers
# ---------------------------------------------------------------------------

def _build_folder_tree(folders: list[dict]) -> tuple[dict, list[int]]:
    """
    Turns a flat list of folder rows into a dict keyed by folder ID,
    and returns the IDs of root folders (parent_id IS NULL) separately.
    """
    tree = {
        f["id"]: {
            "name": f["name"],
            "parent_id": f["parent_id"],
            "children": [],
            "feeds": [],
        }
        for f in folders
    }

    roots = []
    for f in folders:
        if f["parent_id"] is None:
            roots.append(f["id"])
        elif f["parent_id"] in tree:
            tree[f["parent_id"]]["children"].append(f["id"])

    return tree, roots


def _folder_to_xml(parent_el: ET.Element, folder_id: int, tree: dict) -> None:
    """Recursively writes a folder <outline> with its feeds and sub-folders."""
    node = tree[folder_id]
    folder_el = ET.SubElement(parent_el, "outline", text=node["name"])

    for feed in node["feeds"]:
        ET.SubElement(
            folder_el, "outline",
            type="rss",
            text=feed["title"] or feed["url"],
            xmlUrl=feed["url"],
        )

    for child_id in node["children"]:
        _folder_to_xml(folder_el, child_id, tree)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export(user: dict) -> Response:
    user_id = user["id"]
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id, name, parent_id FROM folders WHERE user_id = %s
        """, (user_id,))
        folders = cursor.fetchall()

        # LEFT JOIN so feeds with no folder assignment are included (folder_id = NULL)
        cursor.execute("""
            SELECT f.feed_url, f.feed_title, ff.folder_id
            FROM feeds f
            JOIN user_subscriptions us
                ON us.feed_sha256 = f.feed_sha256
               AND us.user_id = %s
            LEFT JOIN feed_folders ff
                ON ff.feed_sha256 = f.feed_sha256
               AND ff.user_id = %s
        """, (user_id, user_id))
        feeds = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    # Build in-memory folder tree and assign each feed to its node
    tree, roots = _build_folder_tree(folders)
    root_feeds = []  # feeds with no folder

    for feed in feeds:
        entry = {"url": feed["feed_url"], "title": feed["feed_title"] or ""}
        fid = feed["folder_id"]
        if fid and fid in tree:
            tree[fid]["feeds"].append(entry)
        else:
            root_feeds.append(entry)

    # Build OPML XML
    opml = ET.Element("opml", version="2.0")
    head = ET.SubElement(opml, "head")
    ET.SubElement(head, "title").text = "Berga Subscriptions"
    body = ET.SubElement(opml, "body")

    # Root-level feeds (no folder)
    for feed in root_feeds:
        ET.SubElement(
            body, "outline",
            type="rss",
            text=feed["title"] or feed["url"],
            xmlUrl=feed["url"],
        )

    # Folder tree
    for folder_id in roots:
        _folder_to_xml(body, folder_id, tree)

    xml_bytes = (
        b'<?xml version="1.0" encoding="UTF-8"?>\n'
        + ET.tostring(opml, encoding="unicode").encode("utf-8")
    )

    return Response(
        content=xml_bytes,
        media_type="text/x-opml+xml",
        headers={"Content-Disposition": "attachment; filename=subscriptions.opml"},
    )