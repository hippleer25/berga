"""
mota/sources.py — Numbered citation registry for the Mota chat engine.

Every article/tool result encountered during a chat turn gets a stable
number: `[1]`, `[2]`, … The synthesis prompt lists sources WITHOUT urls (ids
+ outlet + title + date) and instructs the model to cite claims inline like
`[1]`. URLs live only backend-side and are streamed to the client as a final
`sources` SSE event, so the model can never hallucinate a link.
"""

from __future__ import annotations

import re
from typing import Optional

_CITATION_RE = re.compile(r"\[(\d{1,2})\]")


class SourceRegistry:
    def __init__(self, existing: Optional[list[dict]] = None):
        # existing entries come from a previous turn (numbering continues)
        self.entries: list[dict] = list(existing or [])
        self._next_id = (max((e.get("id", 0) for e in self.entries), default=0) + 1)

    # ── Registration ─────────────────────────────────────────────────────────

    def add(self, article: dict) -> int:
        """Register an article, returning its citation id. Skips dupes by URL."""
        url = article.get("link", "") or article.get("url", "")
        if url:
            for e in self.entries:
                if e.get("url") == url:
                    return e["id"]

        entry = {
            "id": self._next_id,
            "outlet": article.get("feed_title", "") or article.get("author", "web"),
            "title": (article.get("title", "") or "Untitled")[:160],
            "date": (article.get("pub_date") or "")[:10],
            "url": url,
        }
        self.entries.append(entry)
        self._next_id += 1
        return entry["id"]

    def id_by_url(self, url: str) -> Optional[int]:
        for e in self.entries:
            if e.get("url") == url:
                return e.get("id")
        return None

    def resolve_reference(self, ref: str) -> Optional[str]:
        """Resolve '[3]' or '3' to the registered URL of source #3."""
        m = _CITATION_RE.fullmatch((ref or "").strip())
        if not m:
            return None
        wanted = int(m.group(1))
        for e in self.entries:
            if e["id"] == wanted:
                return e.get("url")
        return None

    # ── Prompt rendering ─────────────────────────────────────────────────────

    def prompt_block(self) -> str:
        """Compact numbered list for the synthesis prompt (no URLs — token cheap)."""
        if not self.entries:
            return ""
        lines = []
        for e in self.entries:
            date = f" ({e['date']})" if e.get("date") else ""
            lines.append(f"[{e['id']}] {e['outlet']} — {e['title']}{date}")
        return "Available sources for citation:\n" + "\n".join(lines)

    # ── Post-processing ──────────────────────────────────────────────────────

    def cited_ids(self, answer_text: str) -> set[int]:
        valid_max = max((e["id"] for e in self.entries), default=0)
        cited = set()
        for m in _CITATION_RE.finditer(answer_text or ""):
            n = int(m.group(1))
            if 1 <= n <= valid_max and any(e["id"] == n for e in self.entries):
                cited.add(n)
        return cited

    def cited_entries(self, answer_text: str) -> list[dict]:
        cited = self.cited_ids(answer_text)
        return [e for e in self.entries if e["id"] in cited]

    def sse_payload(self, answer_text: str) -> Optional[list[dict]]:
        """Payload for the `sources` SSE event. None when nothing was cited/known."""
        cited = self.cited_entries(answer_text)
        if not cited:
            return None
        return [
            {
                "id": e["id"],
                "outlet": e["outlet"],
                "title": e["title"],
                "url": e["url"],
                "date": e["date"],
            }
            for e in cited
        ]
