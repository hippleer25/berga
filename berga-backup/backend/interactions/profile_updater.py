import json
import logging
import traceback
from database.init_db import get_db
from interactions.config import LEARNING_RATE, ACTION_WEIGHTS
from database.qdrant_utils import get_article_point
from intelligence.recommendations import invalidate_cache

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

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT pos_vector, neg_vector, publisher_likes
            FROM user_vectors
            WHERE user_id = %s
            """,
            (user_id,),
        )
        row = cursor.fetchone()

        pos_vector = json.loads(row["pos_vector"])    if row and row["pos_vector"]    else None
        neg_vector = json.loads(row["neg_vector"])    if row and row["neg_vector"]    else None
        pub_likes  = json.loads(row["publisher_likes"]) if row and row["publisher_likes"] else {}

        lambda_ = LEARNING_RATE

        # ── Vetor positivo (like, saved, read) ────────────────────────────────
        if action in ("like", "saved", "read"):
            if pos_vector is None:
                pos_vector = [v * weight for v in artigo_vetor]
            else:
                pos_vector = [
                    (1 - lambda_) * pos_vector[i] + lambda_ * artigo_vetor[i] * weight
                    for i in range(len(artigo_vetor))
                ]

            # Incrementa afinidade positiva com o publisher
            if feed_sha256:
                pub_likes[feed_sha256] = pub_likes.get(feed_sha256, 0) + weight

        # ── Vetor negativo (dislike) ───────────────────────────────────────────
        # publisher_dislikes é atualizado em interactions.py — não aqui —
        # porque interactions.py tem contexto para detectar se havia like
        # anterior e decrementar publisher_likes de forma consistente.
        if action == "dislike":
            if neg_vector is None:
                neg_vector = [v * weight for v in artigo_vetor]
            else:
                neg_vector = [
                    (1 - lambda_) * neg_vector[i] + lambda_ * artigo_vetor[i] * weight
                    for i in range(len(artigo_vetor))
                ]

        # ── Persistir perfil ──────────────────────────────────────────────────
        cursor.execute(
            """
            INSERT INTO user_vectors (user_id, pos_vector, neg_vector, publisher_likes)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                pos_vector      = VALUES(pos_vector),
                neg_vector      = VALUES(neg_vector),
                publisher_likes = VALUES(publisher_likes)
            """,
            (
                user_id,
                json.dumps(pos_vector) if pos_vector is not None else None,
                json.dumps(neg_vector) if neg_vector is not None else None,
                json.dumps(pub_likes),
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
        conn.close()


def interact(user_id: int, identifier: str, action: str, update_profile: bool = True):
    """
    Processa uma interação do usuário com um artigo.

    1. Localiza o artigo no Qdrant pelo identifier (UUID ou url_hash).
    2. Registra a interação na tabela interactions.
    3. Atualiza os contadores em article_stats.
    4. Atualiza os vetores de perfil do usuário (se update_profile=True).
    5. Invalida o cache de recomendações do usuário.

    Retorna dict {"status": "success"|"error", "message": str}.
    """
    weight = ACTION_WEIGHTS.get(action, 1.0)

    point = get_article_point(identifier, with_vector=update_profile)
    if point is None:
        return {"status": "error", "message": "Artigo não encontrado no sistema"}

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        # Registrar interação
        cursor.execute(
            """
            INSERT INTO interactions (user_id, item_id, action, created_at)
            VALUES (%s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE created_at = NOW()
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

        # Atualizar contador específico
        counter_col = {
            "like":    "likes_count",
            "dislike": "dislikes_count",
            "view":    "views_count",
            "saved":   "saved_count",
            "read":    "reads_count",
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
        return {"status": "success", "message": f"{action} registrado"}

    except Exception as e:
        conn.rollback()
        logger.error("Erro em interact user_id=%s action=%s: %s", user_id, action, e)
        return {"status": "error", "message": str(e)}
    finally:
        cursor.close()
        conn.close()