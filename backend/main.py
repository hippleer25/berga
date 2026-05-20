import os
os.environ['LITELLM_LOG'] = 'WARNING'

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Optional, Literal

from fastapi import FastAPI, Response, UploadFile, File, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from i18n.middleware import LocaleMiddleware
from fastapi.responses import StreamingResponse
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
from intelligence.recommendations import get_recommendations, get_interacted_ids_except_view
from intelligence.recents import get_recents
from intelligence.similar import get_similar_articles
from intelligence.cluster import get_cached_events, compute_weekly_events, set_cached_events
from intelligence.affinity import analyze_affinity, boost_affinity, remove_affinity_boost
from search.item.search_item import search_articles_by_text
from search.feed.search_feed_urls import feeds
from search.feed import search_feed_online
from post import load
from utils.opml import opml_import, opml_export
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
    "https://berga.hippler.net.br,http://localhost:5173"
)

# Always include localhost:5173 so dev mode works regardless of .env overrides
DEFAULT_ORIGINS = {
    "http://localhost:5173",
    "http://localhost:5746",
    "http://localhost",
    "https://localhost",
    "capacitor://localhost",
}
allowed = set(ALLOWED_ORIGINS.split(",")) | DEFAULT_ORIGINS

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

app.add_middleware(LocaleMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(allowed),
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


class UserData(BaseModel):
    username: str | None = None
    password: str
    email: str | None = None
    full_name: str | None = None


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
    articles: list[ArticleInput] = []


@app.post("/api/register")
def register(x_user_data: UserData):
    return auth_register.user_register(x_user_data)


@app.post("/api/login")
def login(x_user_data: UserData, response: Response):
    result = user_login(x_user_data)
    if result.get("status") == "success":
        response.set_cookie(
            key="token",
            value=result["access_token"],
            httponly=True,
            samesite="lax",
            secure=COOKIE_SECURE,
            max_age=int(os.getenv("COOKIE_MAX_AGE", str(7 * 24 * 60 * 60)))
        )
    return result


@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(
        key="token",
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
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
def route_list_subscriptions(user=Depends(get_current_user)):
    return list_subscriptions(user["id"])


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


@app.post("/api/load-text/{item_id}")
def load_text(item_id: str, user=Depends(get_current_user)):
    return load.get(user["id"], item_id)


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


@app.get("/api/feed/recents")
def recents(user=Depends(get_current_user), limit: int = 20, max_days: int = 10, folder_id: Optional[str] = None, feed_sha256: Optional[str] = None):
    exclude_ids = get_interacted_ids_except_view(user["id"])
    return get_recents(user["id"], limit, max_days, folder_id, feed_sha256, exclude_ids=exclude_ids)


@app.get("/api/feed/recommendations")
def recommend(
    user=Depends(get_current_user),
    limit: int = 20,
    folder_id: Optional[str] = None,
    feed_sha256: Optional[str] = None,
    page: Optional[int] = 0,
):
    return get_recommendations(
        user["id"],
        page=page,
        limit=limit,
        folder_id=folder_id,
        feed_sha256=feed_sha256,
    )


@app.get("/api/articles/{item_id}/similar")
def similar(item_id: str, limit: int = 10, threshold: float = 0.0, user=Depends(get_current_user)):
    return get_similar_articles(item_id, limit, min_similarity=threshold)


@app.get("/api/search")
def search(query: str, limit: int = 10, threshold: float = 0.0, user=Depends(get_current_user)):
    return search_articles_by_text(query, limit, min_similarity=threshold)


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
async def structure_route(body: StructureRequest, user=Depends(get_current_user)):
    return await following_structure(body, user)


@app.get("/api/feed/events")
async def weekly_events(request: Request, limit: int = 100, user=Depends(get_current_user)):
    arq_pool = request.app.state.arq

    try:
        if arq_pool:
            cached = await get_cached_events(arq_pool)
            if cached:
                return {"events": cached[:limit], "total": len(cached), "cached": True}
    except Exception as e:
        logger.warning("[CLUSTER] Redis indisponível ao ler cache: %s — computando diretamente", e)

    events = await asyncio.to_thread(compute_weekly_events, limit)

    try:
        if arq_pool:
            await set_cached_events(arq_pool, events)
    except Exception as e:
        logger.warning("[CLUSTER] Redis indisponível ao salvar cache: %s — resultado não será cacheado", e)

    return {"events": events, "total": len(events), "cached": False}


@app.post("/api/chat")
def mota_chat(chat_request: ChatRequest, user: dict = Depends(get_current_user)):
    logger.debug("Chat request from user %s", user.get("id"))
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
