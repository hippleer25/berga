import logging
import bcrypt
from database.init_db import get_db

logger = logging.getLogger(__name__)


def user_register(x_user_data):
    username = x_user_data.username
    if not username or not username.strip():
        return {"status": "error", "message": "Username is required"}
    username = username.strip()
    if len(username) < 2 or len(username) > 50:
        return {"status": "error", "message": "Username must be between 2 and 50 characters"}
    if not x_user_data.password or len(x_user_data.password) < 6:
        return {"status": "error", "message": "Password must be at least 6 characters"}
    email = (x_user_data.email or "").strip() or None
    full_name = (x_user_data.full_name or "").strip() or None
    logger.info("Registering user: %s", username)
    try:
        password_hash = bcrypt.hashpw(
            x_user_data.password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        with get_db() as conn:
            cursor = conn.cursor()
            try:
                sql = "INSERT INTO users (username, password_hash, email, full_name) VALUES (%s, %s, %s, %s)"
                val = (username, password_hash, email, full_name)
                cursor.execute(sql, val)
                conn.commit()
                count = cursor.rowcount
                return {"status": "success", "message": f"{count} usuário registrado com sucesso!"}
            except Exception as e:
                conn.rollback()
                err_msg = str(e)
                if "Duplicate entry" in err_msg or "UNIQUE" in err_msg.upper():
                    return {"status": "error", "message": "Username already taken"}
                logger.error("Registration error: %s", e)
                return {"status": "error", "message": "Registration failed. Please try again."}
            finally:
                cursor.close()
    except Exception as e:
        logger.error("Registration error: %s", e)
        return {"status": "error", "message": "Registration failed. Please try again."}
