import json
import sys
import os
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.init_db import get_db
from interactions.config import ACTION_WEIGHTS
from interactions.profile_updater import _update_user_profile
from database.qdrant_utils import get_article_point

logger = logging.getLogger(__name__)


def sync_all_user_vectors():
    logger.info("Starting user vector synchronization from existing interactions...")

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
            SELECT user_id, item_id, action
            FROM interactions
            WHERE action IN ('like', 'dislike', 'saved', 'read')
            ORDER BY user_id, created_at ASC
            """
            cursor.execute(query)
            interactions = cursor.fetchall()

            if not interactions:
                logger.info("No interactions found to process.")
                return

            logger.info("Processing %d interactions...", len(interactions))

            count = 0
            current_user = None
            for inter in interactions:
                user_id = inter['user_id']
                item_id = inter['item_id']
                action = inter['action']
                weight = ACTION_WEIGHTS.get(action, 1.0)

                try:
                    point = get_article_point(item_id, with_vector=True)
                    if point is None:
                        logger.warning("Article %s not found in Qdrant, skipping.", item_id)
                        continue
                    _update_user_profile(user_id, point, action, weight)
                    count += 1
                    if count % 10 == 0:
                        logger.info("%d interactions processed...", count)
                except Exception as e:
                    logger.error("Error processing item %s for user %s: %s", item_id, user_id, e)

            logger.info("Synchronization complete! %d interactions processed successfully.", count)

        except Exception as e:
            logger.error("Error during synchronization: %s", e)
        finally:
            cursor.close()


if __name__ == "__main__":
    sync_all_user_vectors()
