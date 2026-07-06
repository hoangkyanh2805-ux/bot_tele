"""Copy bai moi nhat tu AZZAM sang EDRIC (chay 1 lan)."""
from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

SOURCE = -1002742276977  # AZZAM
DEST = -1001606210890  # EDRIC
ADMIN = 672890533
START_ID = 14203
MAX_SCAN = 100
MISS_LIMIT = 15


async def message_exists(bot: Bot, source: int, message_id: int) -> bool:
  try:
    forwarded = await bot.forward_message(
      chat_id=ADMIN, from_chat_id=source, message_id=message_id
    )
    await bot.delete_message(chat_id=ADMIN, message_id=forwarded.message_id)
    return True
  except TelegramError:
    return False


async def main() -> int:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("Thieu TELEGRAM_BOT_TOKEN")
        return 1

    bot = Bot(token)
    latest: int | None = None
    misses = 0

    for mid in range(START_ID, START_ID + MAX_SCAN):
        if await message_exists(bot, SOURCE, mid):
            latest = mid
            misses = 0
        else:
            misses += 1
            if misses >= MISS_LIMIT:
                break

    if latest is None:
        print("Khong tim thay bai nao.")
        return 1

    await bot.copy_message(chat_id=DEST, from_chat_id=SOURCE, message_id=latest)
    print(f"Da copy message_id={latest} AZZAM -> EDRIC")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
