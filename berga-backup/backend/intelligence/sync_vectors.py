import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.init_db import get_db
from interactions.config import ACTION_WEIGHTS
from interactions.profile_updater import _update_user_profile
from database.qdrant_utils import get_article_point


def sync_all_user_vectors():
    print("Iniciando sincronização de vetores de usuários com base nas interações existentes...")

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
                print("Nenhuma interação encontrada para processar.")
                return

            print(f"Processando {len(interactions)} interações...")

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
                        print(f"Artigo {item_id} não encontrado no Qdrant, pulando.")
                        continue
                    _update_user_profile(user_id, point, action, weight)
                    count += 1
                    if count % 10 == 0:
                        print(f"{count} interações processadas...")
                except Exception as e:
                    print(f"Erro ao processar item {item_id} para usuário {user_id}: {e}")

            print(f"Sincronização concluída! {count} interações processadas com sucesso.")

        except Exception as e:
            print(f"Erro durante a sincronização: {e}")
        finally:
            cursor.close()


if __name__ == "__main__":
    sync_all_user_vectors()
