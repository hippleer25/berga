import logging
import bcrypt
from database.init_db import get_db
from auth.token import create_token

logger = logging.getLogger(__name__)


def user_login(x_user_data):
    logger.info("Login attempt for user: %s", x_user_data.username or x_user_data.email)

    if not x_user_data.username and not x_user_data.email:
        return {"status": "fail", "message": "Failed credentials"}

    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                if x_user_data.username:
                    cursor.execute("SELECT id, username, email, full_name, password_hash FROM users WHERE username = %s", (x_user_data.username,))
                else:
                    cursor.execute("SELECT id, username, email, full_name, password_hash FROM users WHERE email = %s", (x_user_data.email,))
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
