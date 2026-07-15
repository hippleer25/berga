import os
os.environ['LITELLM_LOG'] = 'WARNING'

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Optional, Literal

import hashlib
import json

from fastapi import FastAPI, Response, UploadFile, File, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from i18n.middleware import LocaleMiddleware
from fastapi.responses import StreamingResponse
from starlette.middleware.gzip import GZipMiddleware
from pydantic import BaseModel

from database import init_db
from database.init_db import close_pool
from database.qdrant_utils import ensure_payload_indexes
from auth import register as auth_register
from auth.login import user_login
from auth.token import get_current_user
from rss import parser, schedule
from feed import add, remove, info, check_subscription
from interactions.interactions import like_article, dislike_article, view_article, read_article, bulk_view_articles, save_article, unsave_article
from intelligence.recommendations import get_recommendations, get_interacted_ids_except_view, invalidate_cache as invalidate_ranking_cache, invalidate_interaction_cache, _resolve_feed_filter as _resolve_rec_feed_filter
from intelligence.recents import get_recents
from intelligence.saved import get_saved
from intelligence.similar import get_similar_articles
from intelligence.cluster import get_cached_events, compute_weekly_events, set_cached_events, CLUSTER_LIMIT, load_events_from_db
from intelligence.cluster_store import build_reverse_index, set_cluster_index
from intelligence.affinity import analyze_affinity, boost_affinity, remove_affinity_boost
from search.item.search_item import search_articles_by_text
from search.feed.search_feed_urls import feeds
from search.feed import search_feed_online
from post import load
from post import highlights as hl
from post import comments as cm
from utils.opml import opml_import, opml_export
from utils.regex_utils import validate_regex_pattern
from feed.following_structure.structure import following_structure, StructureRequest, list_subscriptions, get_folder_info
from mota import chat, article_resume

from arq import create_pool
from arq.connections import RedisSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def db_verification():
    init_db.get_db()
    init_db.init_db()
    ensure_payload_indexes()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_verification()

    for attempt in range(5):
        try:
            app.state.arq = await create_pool(
                RedisSettings(
                    host=os.getenv("REDIS_HOST", "redis"),
                    port=int(os.getenv("REDIS_PORT", 6379))
                )
            )
            break
        except Exception as e:
            logger.warning("Redis connection attempt %d failed: %s", attempt + 1, e)
            if attempt == 4:
                logger.error("Could not connect to Redis after 5 attempts — continuing without Redis")
                app.state.arq = None
            await asyncio.sleep(3)

    yield

    if app.state.arq:
        await app.state.arq.close()
    close_pool()


app = FastAPI(lifespan=lifespan)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173"
)

# Always include localhost:5173 so dev mode works regardless of .env overrides
DEFAULT_ORIGINS = {
	"http://localhost:5173",
	"http://localhost:4657",
	"http://localhost:5746",
	"http://localhost",
	"https://localhost",
	"capacitor://localhost",
	"https://localhost",
}
allowed = set(ALLOWED_ORIGINS.split(",")) | DEFAULT_ORIGINS

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(LocaleMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(allowed),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


def _etag_for(data) -> str:
    body = json.dumps(data, separators=(",", ":"), default=str).encode()
    return '"' + hashlib.sha256(body).hexdigest()[:32] + '"'

CACHE_HEADERS = {
    "recommendations": {"Cache-Control": "private, max-age=300, must-revalidate"},
    "recents": {"Cache-Control": "private, max-age=60, must-revalidate"},
    "saved": {"Cache-Control": "private, max-age=120, must-revalidate"},
    "events": {"Cache-Control": "private, max-age=21600, must-revalidate"},
    "subscriptions": {"Cache-Control": "private, max-age=300, must-revalidate"},
}

def _check_etag(request: Request, etag: str):
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})
    return None


class UserData(BaseModel):
    username: str | None = None
    password: str
    email: str | None = None
    full_name: str | None = None


def _set_auth_cookie(response: Response, token: str):
    cookie_samesite = "none" if COOKIE_SECURE else "lax"
    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        samesite=cookie_samesite,
        secure=COOKIE_SECURE,
        path="/",
        max_age=int(os.getenv("COOKIE_MAX_AGE", str(7 * 24 * 60 * 60))),
    )


class FeedRequest(BaseModel):
    url: str


class BoostRequest(BaseModel):
    term: str
    direction: Literal["positive", "negative"]
    strength: float = 0.25


class RemoveBoostRequest(BaseModel):
    term: str
    direction: Literal["positive", "negative"]


class ViewBatch(BaseModel):
    item_ids: List[str]


class ArticleInput(BaseModel):
    item_id: str = ""
    title: str = ""
    description: str = ""
    link: str = ""
    feed_title: str = ""
    pub_date: str = ""
    author: str = ""


class ChatRequest(BaseModel):
    message: str
    source_mode: Literal["local", "online", "mixed"] = "local"
    deep_reading: bool = False
    scope: Literal["mine", "all"] = "mine"
    folder_id: str | None = None
    feed_sha256: str | None = None
    articles: list[ArticleInput] = []


class HighlightRequest(BaseModel):
    text: str
    color: str


@app.post("/api/register")
def register(x_user_data: UserData, response: Response):
    result = auth_register.user_register(x_user_data)
    if result.get("status") == "error":
        response.status_code = 409 if "already taken" in result.get("message", "") else 400
        return result
    if result.get("status") == "success":
        _set_auth_cookie(response, result["access_token"])
    return result


@app.post("/api/login")
def login(x_user_data: UserData, response: Response):
    result = user_login(x_user_data)
    if result.get("status") == "fail":
        response.status_code = 401
        return result
    if result.get("status") == "success":
        _set_auth_cookie(response, result["access_token"])
    return result


@app.post("/api/logout")
def logout(response: Response):
    cookie_samesite = "none" if COOKIE_SECURE else "lax"
    response.delete_cookie(
        key="token",
        httponly=True,
        samesite=cookie_samesite,
        secure=COOKIE_SECURE,
        path="/",
    )
    return {"status": "success"}


@app.get("/api/meu-perfil")
def meu_perfil(user: dict = Depends(get_current_user)):
    return {
        "mensagem": f"Olá {user['username']}!",
        "id_no_banco": user["id"],
        "email": user["email"],
        "nome completo": user["full_name"]
    }


@app.post("/api/feed-add")
def feed_add(feed_data: FeedRequest, user: dict = Depends(get_current_user)):
    url = str(feed_data.url).strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")
    return add.subscribe(user, url)


@app.post("/api/feed-remove")
def feed_remove(feed_data: FeedRequest, user: dict = Depends(get_current_user)):
    return remove.unsubscribe(user, str(feed_data.url))

@app.get("/api/feed-subscription-check/{feed_sha256}")
def feed_subscription_check(feed_sha256: str, user: dict = Depends(get_current_user)):
    return check_subscription.user(user, feed_sha256)

@app.get("/api/list-subscriptions")
def route_list_subscriptions(request: Request, response: Response, user=Depends(get_current_user)):
    data = list_subscriptions(user["id"])
    etag = _etag_for(data)
    not_modified = _check_etag(request, etag)
    if not_modified:
        not_modified.headers.update(CACHE_HEADERS["subscriptions"])
        return not_modified
    response.headers.update(CACHE_HEADERS["subscriptions"])
    response.headers["ETag"] = etag
    return data


@app.get("/api/folder-info/{folder_id}")
def route_folder_info(folder_id: str, user=Depends(get_current_user)):
    return get_folder_info(folder_id, user["id"])


@app.get("/api/feed-info/{feed_sha256}")
def get_feed_info(feed_sha256: str, user=Depends(get_current_user)):
    return info.get_all(feed_sha256, user)


@app.post("/api/feed/parse-single")
def parse_single_feed(feed_data: FeedRequest, user: dict = Depends(get_current_user)):
    return parser.parse_and_save_feed(str(feed_data.url))


@app.post("/api/parse-user-all")
async def parse_user_all(request: Request, user: dict = Depends(get_current_user)):
    if request.app.state.arq:
        await request.app.state.arq.enqueue_job("parse_feeds_for_user", user["id"])
    else:
        asyncio.create_task(schedule.parse_user_all_async(user["id"]))
    return {"status": "accepted", "message": "Feed refresh started in background"}


@app.post("/api/cluster/refresh")
async def cluster_refresh(request: Request, user: dict = Depends(get_current_user)):
    if request.app.state.arq:
        await request.app.state.arq.enqueue_job("refresh_weekly_events")
    else:
        events = await asyncio.to_thread(compute_weekly_events)
        if events:
            reverse_index, summaries = build_reverse_index(events)
            set_cluster_index(reverse_index, summaries)
    return {"status": "accepted", "message": "Cluster refresh started"}


@app.post("/api/load-text/{item_id}")
def load_text(item_id: str, user=Depends(get_current_user)):
    return load.get(user["id"], item_id)


@app.get("/api/highlights/{item_id}")
def get_highlights(item_id: str, user=Depends(get_current_user)):
    return {"highlights": hl.get_highlights(user["id"], item_id)}


@app.post("/api/highlights/{item_id}")
def create_highlight(item_id: str, body: HighlightRequest, user=Depends(get_current_user)):
    return hl.create_highlight(user["id"], item_id, body.text, body.color)


@app.delete("/api/highlights/{highlight_id}")
def delete_highlight(highlight_id: int, user=Depends(get_current_user)):
    return hl.delete_highlight(user["id"], highlight_id)


@app.get("/api/comments/{item_id}")
def get_comment(item_id: str, user=Depends(get_current_user)):
    comment = cm.get_comment(user["id"], item_id)
    return {"comment": comment}


class CommentRequest(BaseModel):
    content_md: str


@app.post("/api/comments/{item_id}")
def save_comment(item_id: str, body: CommentRequest, user=Depends(get_current_user)):
    return cm.save_comment(user["id"], item_id, body.content_md)


@app.delete("/api/comments/{item_id}")
def delete_comment(item_id: str, user=Depends(get_current_user)):
    return cm.delete_comment(user["id"], item_id)


@app.post("/api/feed/{item_id}/like")
def like(item_id: str, user=Depends(get_current_user)):
    return like_article(user["id"], item_id)


@app.post("/api/feed/{item_id}/dislike")
def dislike(item_id: str, user=Depends(get_current_user)):
    return dislike_article(user["id"], item_id)


@app.post("/api/feed/{item_id}/view")
def view(item_id: str, user=Depends(get_current_user)):
    return view_article(user["id"], item_id)


@app.post("/api/feed/{item_id}/read")
def read(item_id: str, user=Depends(get_current_user)):
    return read_article(user["id"], item_id)


@app.post("/api/articles/views")
def bulk_view(batch: ViewBatch, user=Depends(get_current_user)):
    return bulk_view_articles(user["id"], batch.item_ids)


@app.post("/api/feed/{item_id}/save")
def save(item_id: str, user=Depends(get_current_user)):
    return save_article(user["id"], item_id)


@app.delete("/api/feed/{item_id}/save")
def unsave(item_id: str, user=Depends(get_current_user)):
    return unsave_article(user["id"], item_id)


def _enrich_with_tags(items: list[dict], user_id: int) -> list[dict]:
    if not items:
        return items
    item_ids = [it.get("item_id", "") for it in items if it.get("item_id")]
    if not item_ids:
        return items
    from database.init_db import get_db
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            fmt = ",".join(["%s"] * len(item_ids))
            cursor.execute(
                f"SELECT at.item_id, at.source, at.confidence, "
                f"st.id AS tag_id, st.name, st.color "
                f"FROM article_tags at "
                f"JOIN smart_tags st ON st.id = at.tag_id "
                f"WHERE at.user_id = %s AND at.item_id IN ({fmt})",
                [user_id] + item_ids,
            )
            rows = cursor.fetchall()
        finally:
            cursor.close()
    tag_map: dict[str, list[dict]] = {}
    for row in rows:
        iid = row["item_id"]
        tag_map.setdefault(iid, []).append({
            "tag_id": row["tag_id"],
            "name": row["name"],
            "color": row["color"],
            "source": row["source"],
        })
    for item in items:
        iid = item.get("item_id", "")
        item["tags"] = tag_map.get(iid, [])
    return items


def _item_ids_for_tag(user_id: int, tag_id: int) -> set[str] | None:
    if tag_id is None:
        return None
    from database.init_db import get_db
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT item_id FROM article_tags WHERE user_id = %s AND tag_id = %s",
                (user_id, tag_id),
            )
            return {str(row[0]) for row in cursor.fetchall()}
        finally:
            cursor.close()


def _get_tagged_items(
    item_ids: list[str],
    page: int,
    limit: int,
    feed_filter: list[str] | None = None,
) -> list[dict]:
    if not item_ids:
        return []
    from intelligence.embeddings import get_qdrant_client, COLLECTION_NAME
    from intelligence.recents import _enrich_with_feed_metadata

    client = get_qdrant_client()
    points = client.retrieve(
        collection_name=COLLECTION_NAME,
        ids=item_ids,
        with_payload=True,
        with_vectors=False,
    )

    feed_set = set(feed_filter) if feed_filter is not None else None
    results: list[dict] = []
    for point in points:
        pid = str(point.id)
        if feed_set is not None and point.payload.get("feed_sha256") not in feed_set:
            continue
        item = point.payload.copy()
        item["item_id"] = pid
        item["relevance_score"] = 0.0
        results.append(item)

    results.sort(key=lambda x: x.get("pub_timestamp") or 0, reverse=True)

    start = page * limit
    end = start + limit
    page_items = results[start:end]

    _enrich_with_feed_metadata(page_items)
    return page_items


@app.get("/api/feed/recents")
def recents(request: Request, response: Response, user=Depends(get_current_user), limit: int = 20, max_days: int = 10, folder_id: Optional[str] = None, feed_sha256: Optional[str] = None, tag_id: Optional[int] = None, page: int = 0):
    tag_item_ids = _item_ids_for_tag(user["id"], tag_id)
    if tag_item_ids is not None:
        feed_filter = _resolve_rec_feed_filter(user["id"], folder_id, feed_sha256)
        if feed_filter is not None and len(feed_filter) == 0:
            data = []
        else:
            data = _get_tagged_items(list(tag_item_ids), page=page, limit=limit, feed_filter=feed_filter)
        data = _enrich_with_tags(data, user["id"])
    else:
        exclude_ids = get_interacted_ids_except_view(user["id"])
        data = get_recents(user["id"], limit, max_days, folder_id, feed_sha256, exclude_ids=exclude_ids)
        data = _enrich_with_tags(data, user["id"])
    etag = _etag_for(data)
    not_modified = _check_etag(request, etag)
    if not_modified:
        not_modified.headers.update(CACHE_HEADERS["recents"])
        return not_modified
    response.headers.update(CACHE_HEADERS["recents"])
    response.headers["ETag"] = etag
    return data


@app.get("/api/feed/saved")
def saved(request: Request, response: Response, user=Depends(get_current_user), limit: int = 20, page: int = 0, folder_id: Optional[str] = None, feed_sha256: Optional[str] = None, tag_id: Optional[int] = None):
    tag_item_ids = _item_ids_for_tag(user["id"], tag_id)
    if tag_item_ids is not None:
        feed_filter = _resolve_rec_feed_filter(user["id"], folder_id, feed_sha256)
        if feed_filter is not None and len(feed_filter) == 0:
            data = []
        else:
            data = _get_tagged_items(list(tag_item_ids), page=page, limit=limit, feed_filter=feed_filter)
        data = _enrich_with_tags(data, user["id"])
    else:
        data = get_saved(user["id"], limit=limit, page=page, folder_id=folder_id, feed_sha256=feed_sha256)
        data = _enrich_with_tags(data, user["id"])
    etag = _etag_for(data)
    not_modified = _check_etag(request, etag)
    if not_modified:
        not_modified.headers.update(CACHE_HEADERS["saved"])
        return not_modified
    response.headers.update(CACHE_HEADERS["saved"])
    response.headers["ETag"] = etag
    return data


@app.get("/api/feed/recommendations")
def recommend(
    request: Request, response: Response,
    user=Depends(get_current_user), limit: int = 20, folder_id: Optional[str] = None, feed_sha256: Optional[str] = None, page: int = 0, tag_id: Optional[int] = None,
    exclude_ids: Optional[str] = None, refresh: int = 0,
):
    tag_item_ids = _item_ids_for_tag(user["id"], tag_id)
    if tag_item_ids is not None:
        feed_filter = _resolve_rec_feed_filter(user["id"], folder_id, feed_sha256)
        if feed_filter is not None and len(feed_filter) == 0:
            data = []
        else:
            data = _get_tagged_items(list(tag_item_ids), page=page, limit=limit, feed_filter=feed_filter)
        data = _enrich_with_tags(data, user["id"])
    else:
        # On explicit reload, drop the ranking + interaction caches so the
        # algorithm recomputes from scratch with the latest affinities/views.
        if refresh:
            invalidate_ranking_cache(user["id"])
            invalidate_interaction_cache(user["id"])
        parsed_exclude: Optional[list[str]] = None
        if exclude_ids:
            parsed_exclude = [eid.strip() for eid in exclude_ids.split(",") if eid.strip()]
        data = get_recommendations(
            user["id"], page=page, limit=limit, folder_id=folder_id, feed_sha256=feed_sha256,
            exclude_ids=parsed_exclude,
        )
        data = _enrich_with_tags(data, user["id"])
    etag = _etag_for(data)
    not_modified = _check_etag(request, etag)
    if not_modified:
        not_modified.headers.update(CACHE_HEADERS["recommendations"])
        return not_modified
    response.headers.update(CACHE_HEADERS["recommendations"])
    response.headers["ETag"] = etag
    return data


@app.get("/api/articles/{item_id}/similar")
def similar(item_id: str, limit: int = 10, threshold: float = 0.0, user=Depends(get_current_user)):
    return get_similar_articles(item_id, limit, min_similarity=threshold)


@app.get("/api/search")
def search(query: str, limit: int = 10, threshold: float = 0.0, user=Depends(get_current_user)):
    data = search_articles_by_text(query, limit, min_similarity=threshold)
    data = _enrich_with_tags(data, user["id"])
    return data


@app.get("/api/discover")
async def discover_feeds(url: str, user=Depends(get_current_user)):
    found = await feeds(url, crawl_depth=1)
    return {"feeds": found}


@app.get("/api/online-discover")
def online_discover_endpoint(query: str, user=Depends(get_current_user)):
    results = search_feed_online.discover_online(query)
    return {
        "best_match": results[0] if results else None,
        "candidates": results
    }


@app.post("/api/opml-import")
async def route_opml_import(
    request: Request,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    MAX_OPML_SIZE = 1_000_000
    content = await file.read()
    if len(content) > MAX_OPML_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 1 MB)")
    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    result = await opml_import.receive(content, user)
    if result["imported"] > 0 and request.app.state.arq:
        await request.app.state.arq.enqueue_job("parse_feeds_for_user", user["id"])
    elif result["imported"] == 0:
        raise HTTPException(status_code=400, detail="No feeds found in OPML file")
    return result


@app.get("/api/opml-export")
async def route_opml_export(user: dict = Depends(get_current_user)):
    return opml_export.export(user)


@app.post("/api/following_structure/")
async def structure_route(body: StructureRequest, request: Request, user=Depends(get_current_user)):
    return await following_structure(body, user, request)


@app.get("/api/feed/events")
async def weekly_events(request: Request, response: Response, limit: int = CLUSTER_LIMIT, user=Depends(get_current_user)):
    arq_pool = request.app.state.arq

    try:
        if arq_pool:
            cached = await get_cached_events(arq_pool)
            if cached is not None:
                payload = {"events": cached[:limit], "total": len(cached), "cached": True}
                etag = _etag_for(payload)
                not_modified = _check_etag(request, etag)
                if not_modified:
                    not_modified.headers.update(CACHE_HEADERS["events"])
                    return not_modified
                response.headers.update(CACHE_HEADERS["events"])
                response.headers["ETag"] = etag
                return payload
    except Exception as e:
        logger.warning("[CLUSTER] Redis indisponível ao ler cache: %s — trying DB", e)

    db_events = await asyncio.to_thread(load_events_from_db)
    if db_events:
        try:
            if arq_pool:
                await set_cached_events(arq_pool, db_events)
        except Exception as e:
            logger.warning("[CLUSTER] Redis indisponível ao salvar cache: %s", e)

        payload = {"events": db_events[:limit], "total": len(db_events), "cached": True}
        etag = _etag_for(payload)
        not_modified = _check_etag(request, etag)
        if not_modified:
            not_modified.headers.update(CACHE_HEADERS["events"])
            return not_modified
        response.headers.update(CACHE_HEADERS["events"])
        response.headers["ETag"] = etag
        return payload

    events = await asyncio.to_thread(compute_weekly_events, limit=limit)

    try:
        if arq_pool:
            await set_cached_events(arq_pool, events)
    except Exception as e:
        logger.warning("[CLUSTER] Redis indisponível ao salvar cache: %s — resultado não será cacheado", e)

    payload = {"events": events, "total": len(events), "cached": False}
    etag = _etag_for(payload)
    not_modified = _check_etag(request, etag)
    if not_modified:
        not_modified.headers.update(CACHE_HEADERS["events"])
        return not_modified
    response.headers.update(CACHE_HEADERS["events"])
    response.headers["ETag"] = etag
    return payload


@app.post("/api/chat")
def mota_chat(chat_request: ChatRequest, request: Request, user: dict = Depends(get_current_user)):
    logger.debug("Chat request from user %s", user.get("id"))

    # Request size validation
    if len(chat_request.articles) > 50:
        return Response(
            content='{"detail":"Too many articles (max 50)"}',
            status_code=413,
            media_type="application/json",
        )
    if len(chat_request.message) > 10000:
        return Response(
            content='{"detail":"Message too long (max 10000 chars)"}',
            status_code=413,
            media_type="application/json",
        )

    # Simple per-user rate limiting (20 messages/minute) via Redis
    user_id = user.get("id")
    if user_id:
        import time
        from mota import conversation as _conv
        client = _conv._get_client()
        if client:
            rate_key = f"mota:rate:{user_id}"
            try:
                count = client.incr(rate_key)
                if count == 1:
                    client.expire(rate_key, 60)
                if count > 20:
                    return Response(
                        content='{"detail":"Rate limit exceeded. Please wait a minute."}',
                        status_code=429,
                        media_type="application/json",
                    )
            except Exception:
                pass  # fail open if Redis is down

    gen = chat.receive(chat_request, user)
    return StreamingResponse(
        gen,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/chat/clear")
def mota_chat_clear(user: dict = Depends(get_current_user)):
    from mota import conversation
    success = conversation.clear(user["id"])
    return {"status": "ok" if success else "error"}


@app.post("/api/mota/resume/{item_id}")
def mota_resume(item_id: str, user=Depends(get_current_user)):
    gen = article_resume.get(item_id, user)
    return StreamingResponse(
        gen,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/api/affinity/analyze")
def route_analyze_affinity(term: str, user: dict = Depends(get_current_user)):
    if not term or not term.strip():
        raise HTTPException(status_code=400, detail="O parâmetro 'term' é obrigatório.")
    if len(term) > 512:
        raise HTTPException(status_code=400, detail="O termo não pode ultrapassar 512 caracteres.")
    return analyze_affinity(user["id"], term.strip())


@app.post('/api/affinity/boost')
def api_boost(body: BoostRequest, user: dict = Depends(get_current_user)):
    return boost_affinity(user["id"], body.term, body.direction, body.strength)


@app.delete('/api/affinity/boost')
def api_remove_boost(body: RemoveBoostRequest, user: dict = Depends(get_current_user)):
    return remove_affinity_boost(user["id"], body.term, body.direction)


# ── Smart Tags ────────────────────────────────────────────────────────────────

class TagCreate(BaseModel):
    name: str
    color: str | None = None
    feed_scope: list[str] | None = None
    folder_scope: list[str] | None = None
    regex_pattern: str | None = None
    regex_flags: str | None = None
    ai_include_terms: list[str] | None = None
    ai_exclude_terms: list[str] | None = None
    ai_threshold: float = 0.65
    ai_negate_threshold: float | None = None
    ai_reinforcement_enabled: bool = True
    enabled_layers: list[str] | None = None


class TagUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    feed_scope: list[str] | None = None
    folder_scope: list[str] | None = None
    regex_pattern: str | None = None
    regex_flags: str | None = None
    ai_include_terms: list[str] | None = None
    ai_exclude_terms: list[str] | None = None
    ai_threshold: float | None = None
    ai_negate_threshold: float | None = None
    ai_reinforcement_enabled: bool | None = None
    enabled_layers: list[str] | None = None


class ManualTagRequest(BaseModel):
    tag_id: int
    item_id: str


class BulkTagRequest(BaseModel):
    tag_id: int
    item_ids: list[str]


@app.get("/api/tags")
def list_tags(user: dict = Depends(get_current_user)):
    from database.init_db import get_db
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id, name, color, feed_scope, folder_scope, "
                "regex_pattern, regex_flags, ai_include_terms, ai_exclude_terms, "
                "ai_threshold, ai_negate_threshold, ai_reinforcement_enabled, "
                "enabled_layers, centroid_manual_count, created_at, updated_at "
                "FROM smart_tags WHERE user_id = %s ORDER BY name",
                (user["id"],),
            )
            return {"tags": cursor.fetchall()}
        finally:
            cursor.close()


@app.post("/api/tags")
def create_tag(body: TagCreate, user: dict = Depends(get_current_user)):
    from database.init_db import get_db
    if body.regex_pattern:
        valid, err = validate_regex_pattern(body.regex_pattern)
        if not valid:
            raise HTTPException(status_code=400, detail=f"Invalid regex: {err}")

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            import json
            cursor.execute(
                "INSERT INTO smart_tags "
                "(user_id, name, color, feed_scope, folder_scope, "
                "regex_pattern, regex_flags, ai_include_terms, ai_exclude_terms, "
                "ai_threshold, ai_negate_threshold, ai_reinforcement_enabled, enabled_layers) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    user["id"], body.name, body.color,
                    json.dumps(body.feed_scope) if body.feed_scope else None,
                    json.dumps(body.folder_scope) if body.folder_scope else None,
                    body.regex_pattern, body.regex_flags,
                    json.dumps(body.ai_include_terms) if body.ai_include_terms else None,
                    json.dumps(body.ai_exclude_terms) if body.ai_exclude_terms else None,
                    body.ai_threshold, body.ai_negate_threshold,
                    1 if body.ai_reinforcement_enabled else 0,
                    ",".join(body.enabled_layers) if body.enabled_layers else None,
                ),
            )
            conn.commit()
            tag_id = cursor.lastrowid
            cursor.execute(
                "SELECT id, name, color, feed_scope, folder_scope, "
                "regex_pattern, regex_flags, ai_include_terms, ai_exclude_terms, "
                "ai_threshold, ai_negate_threshold, ai_reinforcement_enabled, "
                "enabled_layers, centroid_manual_count, created_at, updated_at "
                "FROM smart_tags WHERE id = %s", (tag_id,),
            )
            return {"status": "success", "tag": cursor.fetchone()}
        except Exception as e:
            conn.rollback()
            if "Duplicate entry" in str(e):
                raise HTTPException(status_code=409, detail="Tag name already exists")
            raise
        finally:
            cursor.close()


@app.put("/api/tags/{tag_id}")
def update_tag(tag_id: int, body: TagUpdate, user: dict = Depends(get_current_user)):
    from database.init_db import get_db
    from database.qdrant_utils import delete_tag_phrase
    if body.regex_pattern:
        valid, err = validate_regex_pattern(body.regex_pattern)
        if not valid:
            raise HTTPException(status_code=400, detail=f"Invalid regex: {err}")

        updates = []
        params = []
        import json
        reset_centroid = False
        for field, value in body.model_dump(exclude_unset=True).items():
            if field == "enabled_layers" and isinstance(value, list):
                updates.append("enabled_layers = %s")
                params.append(",".join(value))
            elif field in ("feed_scope", "folder_scope", "ai_include_terms", "ai_exclude_terms") and isinstance(value, list):
                updates.append(f"{field} = %s")
                params.append(json.dumps(value))
                if field in ("ai_include_terms", "ai_exclude_terms"):
                    reset_centroid = True
            elif field == "ai_reinforcement_enabled":
                updates.append("ai_reinforcement_enabled = %s")
                params.append(1 if value else 0)
            else:
                updates.append(f"{field} = %s")
                params.append(value)

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        if reset_centroid:
            updates.append("centroid_vector = NULL")
            updates.append("centroid_manual_count = 0")

        params.append(user["id"])
        params.append(tag_id)

        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(
                    f"UPDATE smart_tags SET {', '.join(updates)} "
                    f"WHERE user_id = %s AND id = %s", params,
                )
                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Tag not found")
                conn.commit()
                if reset_centroid:
                    try:
                        delete_tag_phrase(tag_id)
                    except Exception:
                        pass
                cursor.execute(
                    "SELECT id, name, color, feed_scope, folder_scope, "
                    "regex_pattern, regex_flags, ai_include_terms, ai_exclude_terms, "
                    "ai_threshold, ai_negate_threshold, ai_reinforcement_enabled, "
                    "enabled_layers, centroid_manual_count, created_at, updated_at "
                    "FROM smart_tags WHERE id = %s", (tag_id,),
                )
                return {"status": "success", "tag": cursor.fetchone()}
            finally:
                cursor.close()


@app.delete("/api/tags/{tag_id}")
def delete_tag(tag_id: int, user: dict = Depends(get_current_user)):
    from database.init_db import get_db
    from database.qdrant_utils import delete_tag_phrase
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM smart_tags WHERE user_id = %s AND id = %s",
                (user["id"], tag_id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Tag not found")
            conn.commit()
            delete_tag_phrase(tag_id)
            return {"status": "success", "deleted": tag_id}
        finally:
            cursor.close()


@app.post("/api/tags/assign")
def assign_manual_tag(body: ManualTagRequest, user: dict = Depends(get_current_user)):
    from database.init_db import get_db
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id FROM smart_tags WHERE id = %s AND user_id = %s",
                (body.tag_id, user["id"]),
            )
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Tag not found")
            cursor.execute(
                "INSERT IGNORE INTO article_tags "
                "(user_id, item_id, tag_id, source) VALUES (%s, %s, %s, 'manual')",
                (user["id"], body.item_id, body.tag_id),
            )
            conn.commit()
            return {"status": "success"}
        finally:
            cursor.close()


@app.delete("/api/tags/assign")
def unassign_manual_tag(body: ManualTagRequest, user: dict = Depends(get_current_user)):
    from database.init_db import get_db
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM article_tags "
                "WHERE user_id = %s AND item_id = %s AND tag_id = %s AND source = 'manual'",
                (user["id"], body.item_id, body.tag_id),
            )
            conn.commit()
            return {"status": "success", "removed": cursor.rowcount}
        finally:
            cursor.close()


@app.post("/api/tags/assign-bulk")
def assign_bulk_tags(body: BulkTagRequest, user: dict = Depends(get_current_user)):
    from database.init_db import get_db
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id FROM smart_tags WHERE id = %s AND user_id = %s",
                (body.tag_id, user["id"]),
            )
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Tag not found")
            rows = [(user["id"], item_id, body.tag_id, "manual") for item_id in body.item_ids]
            cursor.executemany(
                "INSERT IGNORE INTO article_tags "
                "(user_id, item_id, tag_id, source) VALUES (%s, %s, %s, 'manual')",
                rows,
            )
            conn.commit()
            return {"status": "success", "assigned": cursor.rowcount}
        finally:
            cursor.close()


@app.get("/api/tags/article/{item_id}")
def article_tags(item_id: str, user: dict = Depends(get_current_user)):
    from database.init_db import get_db
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT at.tag_id, at.source, at.confidence, st.name, st.color "
                "FROM article_tags at "
                "INNER JOIN smart_tags st ON st.id = at.tag_id "
                "WHERE at.user_id = %s AND at.item_id = %s "
                "ORDER BY st.name",
                (user["id"], item_id),
            )
            return {"tags": cursor.fetchall()}
        finally:
            cursor.close()


@app.post("/api/tags/evaluate")
async def trigger_tag_evaluation(request: Request, user: dict = Depends(get_current_user)):
    if not request.app.state.arq:
        raise HTTPException(status_code=503, detail="Worker not available")
    await request.app.state.arq.enqueue_job("refresh_auto_tags")
    return {"status": "accepted", "message": "Tag evaluation queued"}
