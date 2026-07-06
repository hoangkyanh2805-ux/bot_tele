import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from bot import MappingStore, copy_to_destinations, parse_admin_ids


class MappingStoreTests(unittest.TestCase):
    def write_mapping(self, data: object) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "mappings.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_loads_one_to_many_and_removes_duplicates(self) -> None:
        path = self.write_mapping(
            {"-1001": [-1002, "-1003", -1002, "@public_channel"]}
        )
        store = MappingStore(path)

        store.load()

        self.assertEqual(
            store.destinations_for(-1001), (-1002, -1003, "@public_channel")
        )

    def test_rejects_self_mapping(self) -> None:
        store = MappingStore(self.write_mapping({"-1001": [-1001]}))
        with self.assertRaisesRegex(ValueError, "không thể tự gửi"):
            store.load()

    def test_failed_reload_keeps_previous_mapping(self) -> None:
        path = self.write_mapping({"-1001": [-1002]})
        store = MappingStore(path)
        store.load()
        path.write_text("not-json", encoding="utf-8")

        with self.assertRaises(ValueError):
            store.load()

        self.assertEqual(store.destinations_for(-1001), (-1002,))

    def test_allow_map_remove_and_save(self) -> None:
        path = self.write_mapping(
            {"allowed_destinations": [], "mappings": {}}
        )
        store = MappingStore(path)
        store.load()

        self.assertEqual(store.allow([-1002, -1003]), [-1002, -1003])
        self.assertEqual(store.add_mapping(-1001, [-1002, -1003]), [-1002, -1003])
        removed_routes = store.remove_mapping(-1001, [-1002])
        store.save()

        self.assertEqual(removed_routes, 1)
        reloaded = MappingStore(path)
        reloaded.load()
        self.assertEqual(reloaded.allowed_destinations, (-1002, -1003))
        self.assertEqual(reloaded.destinations_for(-1001), (-1003,))

    def test_mapping_requires_allowed_destination(self) -> None:
        store = MappingStore(
            self.write_mapping({"allowed_destinations": [], "mappings": {}})
        )
        store.load()

        with self.assertRaisesRegex(ValueError, "chưa được /allow"):
            store.add_mapping(-1001, [-1002])


class AdminIdsTests(unittest.TestCase):
    def test_parses_comma_separated_ids(self) -> None:
        self.assertEqual(parse_admin_ids("123, 456"), frozenset({123, 456}))


class RelayTests(unittest.IsolatedAsyncioTestCase):
    async def test_copies_one_message_to_every_destination(self) -> None:
        bot = AsyncMock()

        await copy_to_destinations(
            bot=bot,
            source_id=-1001,
            message_ids=[42],
            destinations=(-1002, -1003, -1004),
            disable_notification=False,
            protect_content=False,
        )

        self.assertEqual(bot.copy_message.await_count, 3)
        self.assertEqual(
            [call.kwargs["chat_id"] for call in bot.copy_message.await_args_list],
            [-1002, -1003, -1004],
        )
        bot.copy_messages.assert_not_awaited()

    async def test_album_uses_copy_messages(self) -> None:
        bot = AsyncMock()

        await copy_to_destinations(
            bot=bot,
            source_id=-1001,
            message_ids=[42, 43],
            destinations=(-1002,),
            disable_notification=True,
            protect_content=False,
        )

        bot.copy_messages.assert_awaited_once()
        self.assertEqual(bot.copy_messages.await_args.kwargs["message_ids"], [42, 43])
        bot.copy_message.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
