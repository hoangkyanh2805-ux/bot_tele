from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import TypeAlias

from dotenv import load_dotenv
from telegram import BotCommand, Message, Update
from telegram.constants import ChatMemberStatus, ChatType, UpdateType
from telegram.error import RetryAfter, TelegramError
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

ChatId: TypeAlias = int | str
LOGGER = logging.getLogger("telegram_relay")


def configure_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    value = raw_value.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} phải là true/false, hiện tại là: {raw_value!r}")


def parse_admin_ids(raw_value: str) -> frozenset[int]:
    if not raw_value.strip():
        return frozenset()
    try:
        return frozenset(int(item.strip()) for item in raw_value.split(",") if item.strip())
    except ValueError as exc:
        raise ValueError("ADMIN_IDS phải là danh sách user ID, cách nhau bằng dấu phẩy") from exc


def parse_target(value: object, source_id: int) -> ChatId:
    if isinstance(value, bool):
        raise ValueError(f"Đích của source {source_id} không được là true/false")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("@") and len(value) > 1:
            return value
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError(
                f"Đích {value!r} của source {source_id} phải là ID số hoặc @username"
            ) from exc
    raise ValueError(f"Đích của source {source_id} có kiểu dữ liệu không hợp lệ")


class MappingStore:
    def __init__(self, path: Path):
        self.path = path
        self._mappings: dict[int, tuple[ChatId, ...]] = {}
        self._allowed_destinations: tuple[ChatId, ...] = ()

    @property
    def mappings(self) -> dict[int, tuple[ChatId, ...]]:
        return dict(self._mappings)

    @property
    def allowed_destinations(self) -> tuple[ChatId, ...]:
        return self._allowed_destinations

    def destinations_for(self, source_id: int) -> tuple[ChatId, ...]:
        return self._mappings.get(source_id, ())

    def load(self) -> None:
        try:
            raw_data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ValueError(f"Không tìm thấy file mapping: {self.path}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"JSON không hợp lệ trong {self.path} (dòng {exc.lineno}, cột {exc.colno})"
            ) from exc

        if not isinstance(raw_data, dict):
            raise ValueError("File mapping phải là một JSON object")

        # Hỗ trợ tự động đọc cấu trúc cũ: {"source": [destinations]}.
        if "mappings" in raw_data or "allowed_destinations" in raw_data:
            raw_mappings = raw_data.get("mappings", {})
            raw_allowed = raw_data.get("allowed_destinations", [])
            if not isinstance(raw_mappings, dict):
                raise ValueError("Trường mappings phải là một JSON object")
            if not isinstance(raw_allowed, list):
                raise ValueError("Trường allowed_destinations phải là một mảng []")
        else:
            raw_mappings = raw_data
            raw_allowed = []

        parsed: dict[int, tuple[ChatId, ...]] = {}
        inferred_allowed: list[ChatId] = []
        for raw_source, raw_targets in raw_mappings.items():
            try:
                source_id = int(raw_source)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Source ID không hợp lệ: {raw_source!r}") from exc

            if not isinstance(raw_targets, list):
                raise ValueError(f"Danh sách đích của source {source_id} phải là một mảng []")

            targets: list[ChatId] = []
            for raw_target in raw_targets:
                target = parse_target(raw_target, source_id)
                if target == source_id:
                    raise ValueError(f"Source {source_id} không thể tự gửi lại vào chính nó")
                if target not in targets:
                    targets.append(target)
                if target not in inferred_allowed:
                    inferred_allowed.append(target)
            parsed[source_id] = tuple(targets)

        allowed: list[ChatId] = []
        for raw_target in raw_allowed:
            target = parse_target(raw_target, 0)
            if target not in allowed:
                allowed.append(target)

        # Mapping cũ chưa có allowlist: tự coi các đích đang dùng là hợp lệ.
        if not raw_allowed and "allowed_destinations" not in raw_data:
            allowed = inferred_allowed

        disallowed = [
            target
            for targets in parsed.values()
            for target in targets
            if target not in allowed
        ]
        if disallowed:
            raise ValueError(
                "Mapping chứa channel đích chưa được cấp phép: "
                + ", ".join(str(target) for target in dict.fromkeys(disallowed))
            )

        self._mappings = parsed
        self._allowed_destinations = tuple(allowed)

    def save(self) -> None:
        data = {
            "allowed_destinations": list(self._allowed_destinations),
            "mappings": {
                str(source): list(destinations)
                for source, destinations in self._mappings.items()
            },
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(self.path)

    def allow(self, destinations: list[ChatId]) -> list[ChatId]:
        allowed = list(self._allowed_destinations)
        added: list[ChatId] = []
        for destination in destinations:
            if destination not in allowed:
                allowed.append(destination)
                added.append(destination)
        self._allowed_destinations = tuple(allowed)
        return added

    def add_mapping(self, source_id: int, destinations: list[ChatId]) -> list[ChatId]:
        disallowed = [
            target for target in destinations if target not in self._allowed_destinations
        ]
        if disallowed:
            raise ValueError(
                "Channel đích chưa được /allow: "
                + ", ".join(str(target) for target in disallowed)
            )
        if source_id in destinations:
            raise ValueError("Channel nguồn không thể đồng thời là đích của chính mapping đó")

        current = list(self._mappings.get(source_id, ()))
        added: list[ChatId] = []
        for destination in destinations:
            if destination not in current:
                current.append(destination)
                added.append(destination)
        self._mappings[source_id] = tuple(current)
        return added

    def remove_mapping(
        self, source_id: int, destinations: list[ChatId] | None = None
    ) -> int:
        current = self._mappings.get(source_id, ())
        if not current:
            return 0
        if destinations is None:
            self._mappings.pop(source_id, None)
            return len(current)

        destination_set = set(destinations)
        kept = tuple(target for target in current if target not in destination_set)
        removed = len(current) - len(kept)
        if kept:
            self._mappings[source_id] = kept
        else:
            self._mappings.pop(source_id, None)
        return removed

    def describe(self) -> str:
        route_count = sum(len(targets) for targets in self._mappings.values())
        return (
            f"{len(self._mappings)} nguồn, {route_count} tuyến gửi, "
            f"{len(self._allowed_destinations)} đích được phép"
        )


@dataclass
class Settings:
    token: str
    mapping_file: Path
    admin_ids: frozenset[int]
    album_wait_seconds: float
    disable_notification: bool
    protect_content: bool
    drop_pending_updates: bool

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise ValueError("Thiếu TELEGRAM_BOT_TOKEN trong file .env")

        album_wait = float(os.getenv("ALBUM_WAIT_SECONDS", "1.0"))
        if album_wait <= 0:
            raise ValueError("ALBUM_WAIT_SECONDS phải lớn hơn 0")

        return cls(
            token=token,
            mapping_file=Path(os.getenv("MAPPINGS_FILE", "mappings.json")),
            admin_ids=parse_admin_ids(os.getenv("ADMIN_IDS", "")),
            album_wait_seconds=album_wait,
            disable_notification=env_bool("DISABLE_NOTIFICATION"),
            protect_content=env_bool("PROTECT_CONTENT"),
            drop_pending_updates=env_bool("DROP_PENDING_UPDATES"),
        )


@dataclass
class AlbumBatch:
    source_id: int
    destinations: tuple[ChatId, ...]
    message_ids: set[int] = field(default_factory=set)
    generation: int = 0


class AlbumBuffer:
    def __init__(self, wait_seconds: float):
        self.wait_seconds = wait_seconds
        self._batches: dict[tuple[int, str], AlbumBatch] = {}
        self._lock = asyncio.Lock()

    async def add(
        self,
        application: Application,
        message: Message,
        destinations: tuple[ChatId, ...],
        copy_options: dict[str, bool],
    ) -> None:
        key = (message.chat_id, message.media_group_id or "")
        async with self._lock:
            batch = self._batches.get(key)
            if batch is None:
                batch = AlbumBatch(message.chat_id, destinations)
                self._batches[key] = batch
            batch.message_ids.add(message.message_id)
            batch.destinations = destinations
            batch.generation += 1
            generation = batch.generation

        application.create_task(
            self._flush_after(application, key, generation, copy_options),
            update=None,
            name=f"album-{message.chat_id}-{message.media_group_id}-{generation}",
        )

    async def _flush_after(
        self,
        application: Application,
        key: tuple[int, str],
        generation: int,
        copy_options: dict[str, bool],
    ) -> None:
        await asyncio.sleep(self.wait_seconds)
        async with self._lock:
            batch = self._batches.get(key)
            if batch is None or batch.generation != generation:
                return
            self._batches.pop(key)

        await copy_to_destinations(
            bot=application.bot,
            source_id=batch.source_id,
            message_ids=sorted(batch.message_ids),
            destinations=batch.destinations,
            **copy_options,
        )


def retry_delay_seconds(value: float | timedelta) -> float:
    if isinstance(value, timedelta):
        return value.total_seconds()
    return float(value)


async def copy_to_destinations(
    bot,
    source_id: int,
    message_ids: list[int],
    destinations: tuple[ChatId, ...],
    disable_notification: bool,
    protect_content: bool,
) -> None:
    for destination in destinations:
        for attempt in range(2):
            try:
                if len(message_ids) == 1:
                    await bot.copy_message(
                        chat_id=destination,
                        from_chat_id=source_id,
                        message_id=message_ids[0],
                        disable_notification=disable_notification,
                        protect_content=protect_content,
                    )
                else:
                    await bot.copy_messages(
                        chat_id=destination,
                        from_chat_id=source_id,
                        message_ids=message_ids,
                        disable_notification=disable_notification,
                        protect_content=protect_content,
                    )
                LOGGER.info(
                    "Đã copy message %s từ %s tới %s",
                    message_ids,
                    source_id,
                    destination,
                )
                break
            except RetryAfter as exc:
                if attempt == 1:
                    LOGGER.exception("Telegram vẫn giới hạn tốc độ khi gửi tới %s", destination)
                    break
                delay = retry_delay_seconds(exc.retry_after) + 0.2
                LOGGER.warning("Bị giới hạn tốc độ, thử lại sau %.1f giây", delay)
                await asyncio.sleep(delay)
            except TelegramError:
                LOGGER.exception(
                    "Không thể copy message %s từ %s tới %s",
                    message_ids,
                    source_id,
                    destination,
                )
                break


def parse_chat_reference(raw_value: str) -> ChatId:
    return parse_target(raw_value, 0)


async def resolve_chat_id(bot, raw_value: str) -> int:
    reference = parse_chat_reference(raw_value)
    if isinstance(reference, int):
        return reference
    chat = await bot.get_chat(reference)
    return chat.id


async def validate_source(bot, source_id: int) -> str:
    chat = await bot.get_chat(source_id)
    if chat.type == ChatType.PRIVATE:
        raise ValueError("Nguồn phải là group, supergroup hoặc channel")
    member = await bot.get_chat_member(chat.id, bot.id)
    if member.status in {ChatMemberStatus.LEFT, ChatMemberStatus.BANNED}:
        raise ValueError(f"Bot chưa được thêm vào nguồn {source_id}")
    return chat.title or str(chat.id)


async def validate_destination(bot, raw_value: str) -> tuple[int, str]:
    reference = parse_chat_reference(raw_value)
    chat = await bot.get_chat(reference)
    if chat.type == ChatType.PRIVATE:
        raise ValueError("Đích phải là group, supergroup hoặc channel")

    member = await bot.get_chat_member(chat.id, bot.id)
    if member.status in {ChatMemberStatus.LEFT, ChatMemberStatus.BANNED}:
        raise ValueError(f"Bot chưa được thêm vào đích {chat.id}")
    if chat.type == ChatType.CHANNEL:
        if member.status != ChatMemberStatus.ADMINISTRATOR:
            raise ValueError(f"Bot phải là admin của channel đích {chat.id}")
        if getattr(member, "can_post_messages", False) is not True:
            raise ValueError(f"Bot chưa có quyền đăng bài trong channel đích {chat.id}")
    if member.status == ChatMemberStatus.RESTRICTED and not getattr(
        member, "can_send_messages", False
    ):
        raise ValueError(f"Bot đang bị hạn chế gửi tin trong group đích {chat.id}")
    return chat.id, chat.title or str(chat.id)


def create_application(settings: Settings, mappings: MappingStore) -> Application:
    album_buffer = AlbumBuffer(settings.album_wait_seconds)
    copy_options = {
        "disable_notification": settings.disable_notification,
        "protect_content": settings.protect_content,
    }

    async def require_admin(update: Update) -> Message | None:
        message = update.effective_message
        user = update.effective_user
        if message is None:
            return None
        if not settings.admin_ids:
            await message.reply_text(
                "Các lệnh cấu hình đang tắt. Hãy đặt ADMIN_IDS trong file .env."
            )
            return None
        if user is None or user.id not in settings.admin_ids:
            await message.reply_text("Bạn không có quyền thay đổi cấu hình bot.")
            return None
        return message

    async def save_changes(message: Message) -> bool:
        try:
            mappings.save()
            return True
        except OSError as exc:
            LOGGER.exception("Không thể lưu cấu hình")
            try:
                mappings.load()
            except (OSError, ValueError):
                LOGGER.exception("Không thể khôi phục cấu hình sau lỗi lưu")
            await message.reply_text(f"Không thể lưu cấu hình: {exc}")
            return False

    async def chat_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat = update.effective_chat
        if chat is None or update.effective_message is None:
            return
        await update.effective_message.reply_text(
            f"Chat ID: {chat.id}\nLoại: {chat.type}\nTên: {chat.title or chat.full_name}"
        )

    async def allow_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = await require_admin(update)
        if message is None:
            return
        if not context.args:
            await message.reply_text("Cách dùng: /allow <channel_id> [channel_id...]")
            return

        resolved: list[int] = []
        labels: list[str] = []
        try:
            for raw_target in context.args:
                target_id, title = await validate_destination(context.bot, raw_target)
                if target_id not in resolved:
                    resolved.append(target_id)
                    labels.append(f"{title} ({target_id})")
        except (TelegramError, ValueError) as exc:
            await message.reply_text(f"Không thể cấp phép: {exc}")
            return

        added = mappings.allow(resolved)
        if not added:
            await message.reply_text("Các đích này đã được cấp phép từ trước.")
            return
        if await save_changes(message):
            await message.reply_text("Đã cho phép nhận tin:\n- " + "\n- ".join(labels))

    async def map_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = await require_admin(update)
        if message is None:
            return
        if len(context.args) != 2:
            await message.reply_text("Cách dùng: /map <channel_nguồn> <channel_đích>")
            return
        try:
            source_id = await resolve_chat_id(context.bot, context.args[0])
            source_title = await validate_source(context.bot, source_id)
            destination_id, destination_title = await validate_destination(
                context.bot, context.args[1]
            )
            added = mappings.add_mapping(source_id, [destination_id])
        except (TelegramError, ValueError) as exc:
            await message.reply_text(f"Không thể tạo mapping: {exc}")
            return
        if not added:
            await message.reply_text("Mapping này đã tồn tại.")
            return
        if await save_changes(message):
            await message.reply_text(
                f"Đã map {source_title} ({source_id}) -> "
                f"{destination_title} ({destination_id})"
            )

    async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = await require_admin(update)
        if message is None:
            return
        if len(context.args) not in {1, 2}:
            await message.reply_text("Cách dùng: /remove <channel_nguồn> [channel_đích]")
            return
        try:
            source_id = await resolve_chat_id(context.bot, context.args[0])
            destinations = None
            if len(context.args) == 2:
                destinations = [await resolve_chat_id(context.bot, context.args[1])]
        except (TelegramError, ValueError) as exc:
            await message.reply_text(f"ID channel không hợp lệ: {exc}")
            return

        removed = mappings.remove_mapping(source_id, destinations)
        if not removed:
            await message.reply_text("Không tìm thấy tuyến mapping phù hợp.")
            return
        if await save_changes(message):
            await message.reply_text(f"Đã xóa {removed} tuyến mapping.")

    async def map_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = await require_admin(update)
        if message is None:
            return
        routes = mappings.mappings
        lines = ["DANH SÁCH MAPPING:"]
        lines.extend(
            f"- {source} -> {', '.join(str(target) for target in targets)}"
            for source, targets in routes.items()
        )
        if not routes:
            lines.append("- Chưa có")
        output = "\n".join(lines)
        if len(output) > 4000:
            output = output[:3970] + "\n... danh sách đã được rút gọn"
        await message.reply_text(output)

    async def relay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        if message is None:
            return

        # Tránh vòng lặp nếu Telegram/BotFather được bật chế độ nhận tin từ bot khác.
        if message.from_user is not None and message.from_user.is_bot:
            return

        destinations = mappings.destinations_for(message.chat_id)
        if not destinations:
            return

        if message.media_group_id:
            await album_buffer.add(context.application, message, destinations, copy_options)
            return

        await copy_to_destinations(
            bot=context.bot,
            source_id=message.chat_id,
            message_ids=[message.message_id],
            destinations=destinations,
            **copy_options,
        )

    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        LOGGER.exception("Lỗi chưa được xử lý khi nhận update %r", update, exc_info=context.error)

    async def post_init(application: Application) -> None:
        me = await application.bot.get_me()
        await application.bot.set_my_commands(
            [
                BotCommand("allow", "Cấp phép channel nhận tin"),
                BotCommand("map", "Mapping channel nguồn và đích"),
                BotCommand("map_list", "Xem toàn bộ mapping"),
                BotCommand("remove", "Xóa mapping"),
                BotCommand("chat_id", "Kiểm tra ID channel hiện tại"),
            ]
        )
        LOGGER.info("Bot @%s đã chạy. Mapping: %s", me.username, mappings.describe())

    application = ApplicationBuilder().token(settings.token).post_init(post_init).build()
    application.add_handler(CommandHandler("allow", allow_command))
    application.add_handler(CommandHandler("map", map_command))
    application.add_handler(CommandHandler("map_list", map_list_command))
    application.add_handler(CommandHandler("remove", remove_command))
    application.add_handler(CommandHandler("chat_id", chat_id_command))
    application.add_handler(
        MessageHandler(filters.UpdateType.MESSAGE | filters.UpdateType.CHANNEL_POST, relay)
    )
    application.add_error_handler(error_handler)
    return application


def main() -> None:
    configure_utf8_console()
    load_dotenv()
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    try:
        settings = Settings.from_env()
        mappings = MappingStore(settings.mapping_file)
        mappings.load()
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Lỗi cấu hình: {exc}") from exc

    application = create_application(settings, mappings)
    application.run_polling(
        allowed_updates=[UpdateType.MESSAGE, UpdateType.CHANNEL_POST],
        drop_pending_updates=settings.drop_pending_updates,
    )


if __name__ == "__main__":
    main()
