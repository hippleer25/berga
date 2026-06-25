import logging
import bcrypt
from database.init_db import get_db
from auth.token import create_token

logger = logging.getLogger(__name__)


def user_login(x_user_data):
    username = (x_user_data.username or "").strip()
    email = (x_user_data.email or "").strip()
    logger.info("Login attempt for user: %s", username or email)

    if not username and not email:
        return {"status": "fail", "message": "Failed credentials"}

    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                if username:
                    cursor.execute("SELECT id, username, email, full_name, password_hash FROM users WHERE username = %s", (username,))
                else:
                    cursor.execute("SELECT id, username, email, full_name, password_hash FROM users WHERE email = %s ORDER BY id LIMIT 1", (email,))
                user = cursor.fetchone()
            finally:
                cursor.close()

        if user and bcrypt.checkpw(x_user_data.password.encode("utf-8"), user["password_hash"].encode("utf-8")):
            token = create_token(user["username"])
            return {
                "status": "success",
                "message": "Login realizado com sucesso!",
                "access_token": token,
                "token_type": "bearer"
            }
        else:
            return {"status": "fail", "message": "Failed credentials"}

    except Exception as e:
        logger.error("Login error: %s", e)
        return {"status": "fail", "message": "Failed credentials"}
