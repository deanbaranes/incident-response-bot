import aiosqlite
import os
import logging
import time
import glob

logger = logging.getLogger(__name__)

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "incidents.db")


async def init_db():
    """Ensure the database directory and table exist."""
    os.makedirs(DB_DIR, exist_ok=True)

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS processed_incidents (
                    incident_id TEXT PRIMARY KEY,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
            logger.info(f"Database initialized at {DB_PATH}")

        # Run cleanup task on startup
        await cleanup_old_data(7)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def is_incident_processed(incident_id: str) -> bool:
    """Check if an incident ID has already been processed."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT 1 FROM processed_incidents WHERE incident_id = ?",
                (incident_id,),
            ) as cursor:
                result = await cursor.fetchone()
                return result is not None
    except Exception as e:
        logger.error(f"Error checking incident {incident_id} in DB: {e}")
        # In case of DB failure, we return False to allow processing (at-least-once),
        # but we could also return True to be safe. We'll return False.
        return False


async def mark_incident_processed(incident_id: str):
    """Mark an incident ID as processed by inserting it into the database."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO processed_incidents (incident_id) VALUES (?)",
                (incident_id,),
            )
            await db.commit()
    except aiosqlite.IntegrityError:
        # Expected if there's a race condition and it was already inserted
        logger.debug(f"Incident {incident_id} already exists in DB.")
    except Exception as e:
        logger.error(f"Error marking incident {incident_id} as processed in DB: {e}")


async def cleanup_old_data(days: int = 7):
    """Clean up old records from the database and orphaned screenshots."""
    try:
        # 1. Clean DB
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "DELETE FROM processed_incidents WHERE processed_at < datetime('now', ?)",
                (f"-{days} days",),
            )
            deleted_rows = cursor.rowcount
            await db.commit()
            if deleted_rows > 0:
                logger.info(f"Cleaned up {deleted_rows} old records from DB.")

        # 2. Clean screenshots directory
        screenshots_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "screenshots"
        )
        if os.path.exists(screenshots_dir):
            now = time.time()
            cutoff = now - (days * 86400)
            deleted_files = 0
            for filepath in glob.glob(os.path.join(screenshots_dir, "*.png")):
                if os.path.getmtime(filepath) < cutoff:
                    try:
                        os.remove(filepath)
                        deleted_files += 1
                    except Exception as e:
                        logger.error(f"Failed to delete {filepath}: {e}")
            if deleted_files > 0:
                logger.info(f"Cleaned up {deleted_files} old screenshots.")
    except Exception as e:
        logger.error(f"Error during global cleanup: {e}")
