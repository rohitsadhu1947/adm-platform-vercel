"""
PostgreSQL-backed persistence for python-telegram-bot v21.

Stores user_data, chat_data, bot_data, conversations, and callback_data
as JSON strings in the `bot_state` table (Neon PostgreSQL).

This replaces the default in-memory storage, so ConversationHandler state
survives across Vercel cold starts and function invocations.
"""

import json
import logging
from copy import deepcopy
from typing import Dict, Optional, Tuple

from telegram.ext import BasePersistence, PersistenceInput
from telegram.ext._utils.types import ConversationDict, CDCData

logger = logging.getLogger(__name__)


class PostgresPersistence(BasePersistence):
    """Persist bot state to Neon PostgreSQL via SQLAlchemy."""

    def __init__(self, session_factory):
        super().__init__(
            store_data=PersistenceInput(
                bot_data=True,
                chat_data=True,
                user_data=True,
                callback_data=True,
            ),
            update_interval=0,  # Write immediately on every update
        )
        self._session_factory = session_factory

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self, key: str) -> Optional[str]:
        """Load a JSON string from the bot_state table by key."""
        db = self._session_factory()
        try:
            from models import BotState
            row = db.query(BotState).filter(BotState.key == key).first()
            return row.data if row else None
        except Exception as e:
            logger.error("Persistence load error for %s: %s", key, e)
            return None
        finally:
            db.close()

    def _save(self, key: str, data: str) -> None:
        """Upsert a JSON string into the bot_state table."""
        db = self._session_factory()
        try:
            from models import BotState
            row = db.query(BotState).filter(BotState.key == key).first()
            if row:
                row.data = data
            else:
                db.add(BotState(key=key, data=data))
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error("Persistence save error for %s: %s", key, e)
        finally:
            db.close()

    def _delete(self, key: str) -> None:
        """Delete a key from the bot_state table."""
        db = self._session_factory()
        try:
            from models import BotState
            db.query(BotState).filter(BotState.key == key).delete()
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error("Persistence delete error for %s: %s", key, e)
        finally:
            db.close()

    def _load_prefixed(self, prefix: str) -> Dict[str, str]:
        """Load all rows whose key starts with prefix."""
        db = self._session_factory()
        try:
            from models import BotState
            rows = db.query(BotState).filter(
                BotState.key.like(f"{prefix}%")
            ).all()
            return {row.key: row.data for row in rows}
        except Exception as e:
            logger.error("Persistence load_prefixed error for %s: %s", prefix, e)
            return {}
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Read methods (called once at Application.initialize())
    # ------------------------------------------------------------------

    async def get_user_data(self) -> Dict[int, dict]:
        """Load all user_data entries from DB."""
        result = {}
        rows = self._load_prefixed("user_data:")
        for key, data_str in rows.items():
            try:
                user_id = int(key.split(":", 1)[1])
                result[user_id] = json.loads(data_str)
            except (ValueError, json.JSONDecodeError) as e:
                logger.warning("Skipping corrupt user_data %s: %s", key, e)
        logger.info("Loaded user_data for %d users from DB", len(result))
        return result

    async def get_chat_data(self) -> Dict[int, dict]:
        """Load all chat_data entries from DB."""
        result = {}
        rows = self._load_prefixed("chat_data:")
        for key, data_str in rows.items():
            try:
                chat_id = int(key.split(":", 1)[1])
                result[chat_id] = json.loads(data_str)
            except (ValueError, json.JSONDecodeError) as e:
                logger.warning("Skipping corrupt chat_data %s: %s", key, e)
        logger.info("Loaded chat_data for %d chats from DB", len(result))
        return result

    async def get_bot_data(self) -> dict:
        """Load global bot_data from DB."""
        raw = self._load("bot_data")
        if raw:
            try:
                data = json.loads(raw)
                logger.info("Loaded bot_data from DB")
                return data
            except json.JSONDecodeError:
                logger.warning("Corrupt bot_data in DB, returning empty")
        return {}

    async def get_conversations(self, name: str) -> ConversationDict:
        """Load conversation states for a specific handler.

        ConversationDict maps Tuple[int, int] -> int (state).
        We store it as {"(user_id, chat_id)": state_int}.
        """
        raw = self._load(f"conversations:{name}")
        if not raw:
            return {}
        try:
            stored = json.loads(raw)
            # Convert string keys "(uid, cid)" back to tuple keys
            result: ConversationDict = {}
            for key_str, state in stored.items():
                # Parse "(123, 456)" format
                key_str = key_str.strip("()")
                parts = key_str.split(",")
                if len(parts) == 2:
                    k = (int(parts[0].strip()), int(parts[1].strip()))
                    result[k] = state
            logger.info("Loaded %d conversation states for handler '%s'", len(result), name)
            return result
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Corrupt conversations:%s in DB: %s", name, e)
            return {}

    async def get_callback_data(self) -> Optional[CDCData]:
        """Load callback_data from DB."""
        raw = self._load("callback_data")
        if raw:
            try:
                data = json.loads(raw)
                # CDCData is Tuple[List[Tuple[str, float, Dict]], Dict[str, str]]
                if isinstance(data, list) and len(data) == 2:
                    return (
                        [tuple(item) for item in data[0]],
                        data[1],
                    )
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("Corrupt callback_data in DB: %s", e)
        return None

    # ------------------------------------------------------------------
    # Write methods (called after every update that modifies state)
    # ------------------------------------------------------------------

    async def update_user_data(self, user_id: int, data: dict) -> None:
        """Save user_data for a specific user."""
        self._save(f"user_data:{user_id}", json.dumps(data, default=str))

    async def update_chat_data(self, chat_id: int, data: dict) -> None:
        """Save chat_data for a specific chat."""
        self._save(f"chat_data:{chat_id}", json.dumps(data, default=str))

    async def update_bot_data(self, data: dict) -> None:
        """Save global bot_data."""
        self._save("bot_data", json.dumps(data, default=str))

    async def update_conversation(
        self, name: str, key: Tuple[int, ...], new_state: Optional[int]
    ) -> None:
        """Update a single conversation state for a handler.

        If new_state is None, the conversation ended - remove the key.
        """
        # Load current conversations for this handler
        current = await self.get_conversations(name)

        if new_state is None:
            current.pop(key, None)
        else:
            current[key] = new_state

        # Convert tuple keys to strings for JSON serialization
        serializable = {str(k): v for k, v in current.items()}
        self._save(f"conversations:{name}", json.dumps(serializable))

    async def update_callback_data(self, data: CDCData) -> None:
        """Save callback_data."""
        if data is not None:
            # CDCData = Tuple[List[Tuple[str, float, Dict]], Dict[str, str]]
            serializable = [
                [list(item) for item in data[0]],
                data[1],
            ]
            self._save("callback_data", json.dumps(serializable, default=str))

    # ------------------------------------------------------------------
    # Drop methods
    # ------------------------------------------------------------------

    async def drop_user_data(self, user_id: int) -> None:
        """Delete all data for a specific user."""
        self._delete(f"user_data:{user_id}")

    async def drop_chat_data(self, chat_id: int) -> None:
        """Delete all data for a specific chat."""
        self._delete(f"chat_data:{chat_id}")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def flush(self) -> None:
        """No-op — all writes are immediate."""
        pass

    async def refresh_user_data(self, user_id: int, user_data: dict) -> dict:
        """Return the user_data as-is (no external refresh needed)."""
        return user_data

    async def refresh_chat_data(self, chat_id: int, chat_data: dict) -> dict:
        """Return the chat_data as-is (no external refresh needed)."""
        return chat_data

    async def refresh_bot_data(self, bot_data: dict) -> dict:
        """Return the bot_data as-is (no external refresh needed)."""
        return bot_data
