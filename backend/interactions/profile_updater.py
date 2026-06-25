import json
import logging
import traceback

import numpy as np
from database.init_db import get_db
from interactions.config import LEARNING_RATE, ACTION_WEIGHTS
from database.qdrant_utils import get_article_point
from intelligence.recommendations import invalidate_cache, invalidate_interaction_cache

logger = logging.getLogger(__name__)


def _update_user_profile(user_id: int, point, action: str, weight: float):
    """
    Atualiza os vetores de perfil do usuário via EWMA (Exponentially Weighted
    Moving Average) e os contadores de afinidade com publishers.

    Vetores:
      pos_vector — média móvel das interações positivas (like, saved, read)
      neg_vector — média móvel das interações negativas (dislike)

    Publisher:
      publisher_likes — atualizado aqui para ações positivas (like, saved, read).
                        Dislikes são contabilizados em publisher_dislikes via
                        interactions.py, que tem visibilidade do contexto da
                        interação (ex: havia like anterior?).

    EWMA: novo = (1 - λ) * antigo + λ * artigo * peso
    Primeira interação: vetor = artigo * peso  (sem histórico anterior)
    """
    artigo_vetor = point.vector
    feed_sha256  = point.payload.get("feed_sha256") if point.payload else None

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT pos_vector, neg_vector, publisher_likes, publisher_dislikes
                FROM user_vectors
                WHERE user_id = %s
                """,
                (user_id,),
            )
            row = cursor.fetchone()

            pos_vector = json.loads(row["pos_vector"]) if row and row["pos_vector"] else None
            neg_vector = json.loads(row["neg_vector"]) if row and row["neg_vector"] else None
            pub_likes = json.loads(row["publisher_likes"]) if row and row["publisher_likes"] else {}
            pub_dislikes = json.loads(row["publisher_dislikes"]) if row and row["publisher_dislikes"] else {}

            lambda_ = LEARNING_RATE

            def _normalize(v: list[float]) -> list[float]:
                arr = np.array(v, dtype=np.float32)
                n = np.linalg.norm(arr)
                return (arr / n).tolist() if n > 0 else v

            # ── Vetor positivo (like, saved, read) ────────────────────────────────
            if action in ("like", "saved", "read"):
                if pos_vector is None:
                    pos_vector = [v * weight for v in artigo_vetor]
                else:
                    pos_vector = [
                        (1 - lambda_) * pos_vector[i] + lambda_ * artigo_vetor[i] * weight
                        for i in range(len(artigo_vetor))
                    ]
                pos_vector = _normalize(pos_vector)

                # Increment positive affinity with the publisher
                if feed_sha256:
                    pub_likes[feed_sha256] = pub_likes.get(feed_sha256, 0) + weight

            # ── Vetor negativo (dislike) ───────────────────────────────────────────
            if action == "dislike":
                if neg_vector is None:
                    neg_vector = [v * weight for v in artigo_vetor]
                else:
                    neg_vector = [
                        (1 - lambda_) * neg_vector[i] + lambda_ * artigo_vetor[i] * weight
                        for i in range(len(artigo_vetor))
                    ]
                neg_vector = _normalize(neg_vector)

                if feed_sha256:
                    pub_dislikes[feed_sha256] = pub_dislikes.get(feed_sha256, 0) + weight

            # ── Persistir perfil ──────────────────────────────────────────────────
            cursor.execute(
                """
                INSERT INTO user_vectors (user_id, pos_vector, neg_vector, publisher_likes, publisher_dislikes)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                pos_vector = VALUES(pos_vector),
                neg_vector = VALUES(neg_vector),
                publisher_likes = VALUES(publisher_likes),
                publisher_dislikes = VALUES(publisher_dislikes)
                """,
                (
                    user_id,
                    json.dumps(pos_vector) if pos_vector is not None else None,
                    json.dumps(neg_vector) if neg_vector is not None else None,
                    json.dumps(pub_likes),
                    json.dumps(pub_dislikes),
                ),
            )
            conn.commit()

        except Exception:
            logger.error(
                "Erro em _update_user_profile para user_id=%s action=%s:\n%s",
                user_id, action, traceback.format_exc(),
            )
            raise
        finally:
            cursor.close()


def interact(user_id: int, identifier: str, action: str, update_profile: bool = True):
    """
    Processes a user interaction with an article.

    1. Locates the article in Qdrant by identifier (UUID or url_hash).
    2. Records the interaction in the interactions table.
    3. Updates counters in article_stats.
    4. Updates the user's profile vectors (if update_profile=True).
    5. Invalidates the user's recommendations cache.

    Returns dict {"status": "success"|"error", "message": str}.
    """
    weight = ACTION_WEIGHTS.get(action, 1.0)

    point = get_article_point(identifier, with_vector=update_profile)
    if point is None:
        return {"status": "error", "message": "Article not found in the system"}

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # Registrar interação
            cursor.execute(
                "SELECT 1 FROM interactions WHERE user_id = %s AND item_id = %s AND action = %s",
                (user_id, identifier, action),
            )
            is_new_interaction = cursor.fetchone() is None

            if is_new_interaction:
                cursor.execute(
                    """
                    INSERT INTO interactions (user_id, item_id, action, created_at)
                    VALUES (%s, %s, %s, NOW())
                    """,
                    (user_id, identifier, action),
                )
            else:
                cursor.execute(
                    """
                    UPDATE interactions SET created_at = NOW()
                    WHERE user_id = %s AND item_id = %s AND action = %s
                    """,
                    (user_id, identifier, action),
                )

            # Garantir linha em article_stats
            cursor.execute(
                """
                INSERT INTO article_stats
                (item_id, likes_count, dislikes_count, views_count, saved_count, reads_count)
                VALUES (%s, 0, 0, 0, 0, 0)
                ON DUPLICATE KEY UPDATE item_id = item_id
                """,
                (identifier,),
            )

            # Atualizar contador específico (only on new interaction)
            if is_new_interaction:
                counter_col = {
                    "like": "likes_count",
                    "dislike": "dislikes_count",
                    "view": "views_count",
                    "saved": "saved_count",
                    "read": "reads_count",
                }.get(action)

                if counter_col:
                    cursor.execute(
                        f"UPDATE article_stats SET {counter_col} = {counter_col} + 1 WHERE item_id = %s",
                        (identifier,),
                    )

            conn.commit()

            # Atualizar vetores de perfil
            if update_profile and action in ("like", "dislike", "saved", "read"):
                _update_user_profile(user_id, point, action, weight)

            invalidate_cache(user_id)
            invalidate_interaction_cache(user_id)
            return {"status": "success", "message": f"{action} registrado"}

        except Exception as e:
            conn.rollback()
            logger.error("Erro em interact user_id=%s action=%s: %s", user_id, action, e)
            return {"status": "error", "message": str(e)}
        finally:
            cursor.close()