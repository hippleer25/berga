"""
database/init_db.py — MySQL connection pool and schema management.
"""

from __future__ import annotations

import os
import re
import time
import logging
import threading

import mysql.connector
from mysql.connector import pooling, Error as MySQLError

logger = logging.getLogger(__name__)

_CHARSET = "utf8mb4"
_COLLATE = "utf8mb4_unicode_ci"

_pool: pooling.MySQLConnectionPool | None = None
_pool_lock = threading.Lock()


def _read_pool_size() -> int:
    raw = os.environ.get("DB_POOL_SIZE", "5")
    try:
        size = int(raw)
    except (ValueError, TypeError):
        logger.warning("Invalid DB_POOL_SIZE=%r, falling back to 5", raw)
        size = 5
    if size < 1:
        logger.warning("DB_POOL_SIZE=%d is too low, clamping to 1", size)
        size = 1
    return size


def _read_port() -> int:
    raw = os.environ.get("DB_PORT", "3306")
    try:
        return int(raw)
    except (ValueError, TypeError):
        raise RuntimeError(f"Invalid DB_PORT value: {raw!r}")


def _init_pool() -> pooling.MySQLConnectionPool:
    global _pool
    if _pool is not None:
        return _pool

    with _pool_lock:
        if _pool is not None:
            return _pool

        pool_size = _read_pool_size()
        db_host = os.environ.get("DB_HOST", "127.0.0.1")
        db_port = _read_port()
        db_user = os.environ.get("DB_USER")
        db_password = os.environ.get("DB_PASSWORD")
        db_name = os.environ.get("DB_NAME", "")

        logger.info(
            "Initialising MySQL connection pool (size=%d, host=%s, db=%s)",
            pool_size, db_host, db_name,
        )

        try:
            test_cnx = mysql.connector.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=db_name,
                connect_timeout=10,
            )
            try:
                logger.info("Pre-flight MySQL connection OK")
            finally:
                test_cnx.close()
        except MySQLError as exc:
            logger.error("Pre-flight MySQL connection FAILED: %s", exc)
            raise

        _pool = pooling.MySQLConnectionPool(
            pool_name="rss_pool",
            pool_size=pool_size,
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name,
            connect_timeout=10,
            autocommit=False,
            pool_reset_session=True,
            buffered=True,
        )
        logger.info("MySQL connection pool ready (size=%d)", pool_size)
        return _pool


def close_pool():
    global _pool
    with _pool_lock:
        if _pool is not None:
            try:
                _pool.closeall()
            except Exception:
                pass
            _pool = None
            logger.info("MySQL connection pool closed")


def reset_pool():
    close_pool()


def get_db():
    max_retries = 3
    delay = 2
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            conn = _init_pool().get_connection()
            try:
                conn.ping(reconnect=True, attempts=1)
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass
                raise
            return conn
        except MySQLError as err:
            last_error = err
            logger.warning(
                "DB connection attempt %d/%d failed: %s",
                attempt, max_retries, err,
            )
            if attempt < max_retries:
                time.sleep(delay)

    logger.error("Could not connect to MySQL after %d attempts", max_retries)
    raise last_error


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = %s
        AND COLUMN_NAME = %s
        """,
        (table, column),
    )
    return cursor.fetchone()[0] > 0


def _index_exists(cursor, table: str, index_name: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = %s
        AND INDEX_NAME = %s
        """,
        (table, index_name),
    )
    return cursor.fetchone()[0] > 0


def _ensure_unique_index(cursor, table: str, index_name: str, column: str) -> None:
    if not re.match(r'^\w+$', table) or not re.match(r'^\w+$', index_name) or not re.match(r'^\w+$', column):
        raise ValueError(f"Invalid identifier for unique index: {table}.{column} as {index_name}")
    if _index_exists(cursor, table, index_name):
        return
    try:
        cursor.execute(f"CREATE UNIQUE INDEX `{index_name}` ON `{table}` (`{column}`)")
        logger.info("Unique index added: %s(%s) as %s", table, column, index_name)
    except MySQLError as exc:
        logger.warning(
            "Could not create UNIQUE index %s on %s(%s): %s. "
            "Existing duplicate rows block it — clean up duplicates to enforce uniqueness.",
            index_name, table, column, exc,
        )


def _add_column_if_missing(cursor, table: str, column: str, definition: str) -> None:
    if not re.match(r'^\w+$', table) or not re.match(r'^\w+$', column):
        raise ValueError(f"Invalid table/column name: {table}.{column}")
    if not _column_exists(cursor, table, column):
        cursor.execute(f"ALTER TABLE `{table}` ADD COLUMN `{column}` {definition}")
        logger.info("Column added: %s.%s", table, column)


def _migrate_user_vectors(cursor) -> None:
    if _column_exists(cursor, "user_vectors", "publisher_affinity"):
        if not _column_exists(cursor, "user_vectors", "publisher_likes"):
            cursor.execute(
                "ALTER TABLE user_vectors "
                "RENAME COLUMN publisher_affinity TO publisher_likes"
            )
            logger.info("user_vectors: publisher_affinity renamed to publisher_likes")
        else:
            logger.warning(
                "user_vectors: publisher_affinity and publisher_likes coexist — "
                "old column ignored. Remove manually if undesired."
            )

    _add_column_if_missing(cursor, "user_vectors", "publisher_dislikes", "TEXT DEFAULT NULL")
    _add_column_if_missing(cursor, "user_vectors", "publisher_freq", "TEXT DEFAULT NULL")
    _add_column_if_missing(cursor, "user_vectors", "affinity_pos_vector", "LONGTEXT DEFAULT NULL")
    _add_column_if_missing(cursor, "user_vectors", "affinity_neg_vector", "LONGTEXT DEFAULT NULL")


def _migrate_smart_tags(cursor) -> None:
    _add_column_if_missing(cursor, "smart_tags", "centroid_vector", "LONGBLOB DEFAULT NULL")
    _add_column_if_missing(cursor, "smart_tags", "centroid_manual_count", "INT DEFAULT 0")
    _add_column_if_missing(cursor, "smart_tags", "ai_negate_threshold", "FLOAT DEFAULT NULL")
    _add_column_if_missing(cursor, "smart_tags", "ai_reinforcement_enabled", "TINYINT(1) DEFAULT 1")


def _migrate_feeds(cursor) -> None:
    _add_column_if_missing(cursor, "feeds", "last_error", "TEXT DEFAULT NULL")
    _add_column_if_missing(cursor, "feeds", "last_error_at", "DATETIME DEFAULT NULL")


_TABLE_OPTIONS = f"DEFAULT CHARSET={_CHARSET} COLLATE={_COLLATE}"


def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                full_name VARCHAR(255),
                UNIQUE KEY uq_users_email (email)
            ) {_TABLE_OPTIONS}
            """)
            _ensure_unique_index(cursor, "users", "uq_users_email", "email")
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS feeds (
                feed_sha256 VARCHAR(64) PRIMARY KEY,
                feed_url TEXT NOT NULL,
                feed_title VARCHAR(255),
                feed_link TEXT,
                feed_filename VARCHAR(255),
                feed_description TEXT,
                feed_icon VARCHAR(255),
                feed_lang VARCHAR(10),
                feed_last_update DATETIME,
                last_parsed_at DATETIME DEFAULT NULL,
                entries_count INT DEFAULT 0,
                active_users INT DEFAULT 0,
                total_users INT DEFAULT 0,
                parsed INT DEFAULT 0,
                post_count_30d INT DEFAULT 0,
                last_error TEXT DEFAULT NULL,
                last_error_at DATETIME DEFAULT NULL
            ) {_TABLE_OPTIONS}
            """)
            _migrate_feeds(cursor)
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS user_subscriptions (
                user_id INT,
                feed_sha256 VARCHAR(64),
                PRIMARY KEY (user_id, feed_sha256),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (feed_sha256) REFERENCES feeds(feed_sha256) ON DELETE CASCADE
            ) {_TABLE_OPTIONS}
            """)
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS interactions (
                user_id INT,
                item_id VARCHAR(64) NOT NULL,
                action ENUM('like', 'dislike', 'view', 'saved', 'read') NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, item_id, action),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_interactions_user (user_id),
                INDEX idx_interactions_item (item_id)
            ) {_TABLE_OPTIONS}
            """)
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS user_vectors (
                user_id INT PRIMARY KEY,
                pos_vector LONGTEXT NOT NULL,
                neg_vector LONGTEXT DEFAULT NULL,
                affinity_pos_vector LONGTEXT DEFAULT NULL,
                affinity_neg_vector LONGTEXT DEFAULT NULL,
                publisher_likes TEXT DEFAULT NULL,
                publisher_dislikes TEXT DEFAULT NULL,
                publisher_freq TEXT DEFAULT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) {_TABLE_OPTIONS}
            """)
            _migrate_user_vectors(cursor)
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS article_stats (
                item_id VARCHAR(64) PRIMARY KEY,
                likes_count INT DEFAULT 0,
                dislikes_count INT DEFAULT 0,
                views_count INT DEFAULT 0,
                saved_count INT DEFAULT 0,
                reads_count INT DEFAULT 0
            ) {_TABLE_OPTIONS}
            """)
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS folders (
                id VARCHAR(64) PRIMARY KEY,
                user_id INT NOT NULL,
                name VARCHAR(255) NOT NULL,
                parent_id VARCHAR(64) DEFAULT NULL,
                description TEXT DEFAULT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (parent_id) REFERENCES folders(id) ON DELETE CASCADE,
                UNIQUE KEY uq_user_folder (user_id, name, parent_id)
            ) {_TABLE_OPTIONS}
            """)
            _add_column_if_missing(cursor, "folders", "description", "TEXT DEFAULT NULL")
            _add_column_if_missing(cursor, "folders", "created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS feed_folders (
                user_id INT,
                feed_sha256 VARCHAR(64),
                folder_id VARCHAR(64),
                PRIMARY KEY (user_id, feed_sha256, folder_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (feed_sha256) REFERENCES feeds(feed_sha256) ON DELETE CASCADE,
                FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE CASCADE
            ) {_TABLE_OPTIONS}
            """)
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS feed_tags (
                user_id INT,
                feed_sha256 VARCHAR(64),
                tag VARCHAR(255),
                PRIMARY KEY (user_id, feed_sha256, tag),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (feed_sha256) REFERENCES feeds(feed_sha256) ON DELETE CASCADE
            ) {_TABLE_OPTIONS}
            """)
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS user_feed_overrides (
                user_id INT,
                feed_sha256 VARCHAR(64),
                custom_title VARCHAR(255),
                PRIMARY KEY (user_id, feed_sha256),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (feed_sha256) REFERENCES feeds(feed_sha256) ON DELETE CASCADE
            ) {_TABLE_OPTIONS}
            """)
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS affinity_boosts (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                term VARCHAR(500) NOT NULL,
                direction ENUM('positive', 'negative') NOT NULL,
                strength FLOAT NOT NULL DEFAULT 0.25,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_boost_user_term (user_id, term(100))
            ) {_TABLE_OPTIONS}
        """)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS smart_tags (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    color VARCHAR(7) DEFAULT NULL,
                    feed_scope JSON DEFAULT NULL,
                    folder_scope JSON DEFAULT NULL,
                    regex_pattern TEXT DEFAULT NULL,
                    regex_flags VARCHAR(16) DEFAULT NULL,
                    ai_include_terms JSON DEFAULT NULL,
                    ai_exclude_terms JSON DEFAULT NULL,
                    ai_threshold FLOAT DEFAULT 0.65,
                    enabled_layers VARCHAR(255) DEFAULT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE KEY uq_user_tag_name (user_id, name),
                    INDEX idx_smart_tags_user (user_id)
                ) {_TABLE_OPTIONS}
                """)
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS article_tags (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                item_id VARCHAR(64) NOT NULL,
                tag_id BIGINT NOT NULL,
                source ENUM('manual', 'feed', 'folder', 'regex', 'ai') NOT NULL DEFAULT 'manual',
                confidence FLOAT DEFAULT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES smart_tags(id) ON DELETE CASCADE,
                UNIQUE KEY uq_user_item_tag_source (user_id, item_id, tag_id, source),
                INDEX idx_articletags_user_item (user_id, item_id),
                INDEX idx_articletags_tag (tag_id),
                INDEX idx_articletags_source (source)
            ) {_TABLE_OPTIONS}
            """)
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS weekly_events (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                cluster_hash VARCHAR(64) NOT NULL,
                summary TEXT NOT NULL,
                article_count INT NOT NULL,
                unique_feeds INT NOT NULL,
                articles_json MEDIUMTEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uq_cluster_hash (cluster_hash),
                INDEX idx_events_updated (updated_at)
        ) {_TABLE_OPTIONS}
        """)
            _migrate_smart_tags(cursor)
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS article_cache (
                item_id VARCHAR(64) PRIMARY KEY,
                content_html MEDIUMTEXT NOT NULL,
                cached_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) {_TABLE_OPTIONS}
        """)
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS highlights (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                item_id VARCHAR(64) NOT NULL,
                text VARCHAR(1000) NOT NULL,
                color VARCHAR(7) NOT NULL,
                sort_order SMALLINT NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE KEY uq_highlight_user_item_text (user_id, item_id, text(200)),
                INDEX idx_highlights_user_item (user_id, item_id)
        ) {_TABLE_OPTIONS}
        """)
            cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS article_comments (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                item_id VARCHAR(64) NOT NULL,
                content_md MEDIUMTEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE KEY uq_comment_user_item (user_id, item_id),
                INDEX idx_comments_item (item_id)
            ) {_TABLE_OPTIONS}
            """)
            _add_column_if_missing(cursor, "interactions", "archived", "TINYINT(1) DEFAULT 0")
            conn.commit()
            logger.info("Database initialised successfully")
        except Exception as e:
            logger.error("Error initialising database: %s", e)
            conn.rollback()
            raise
        finally:
            cursor.close()
