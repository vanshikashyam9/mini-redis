"""
Basic tests for mini_redis's command handlers.

These call the cmd_* functions directly (not over a real socket) so they run
fast and don't need the server actually listening on a port. This is testing
the "brain" of the project — the logic each command follows.
"""

import time
import unittest

import mini_redis


class MiniRedisTests(unittest.TestCase):
    def setUp(self):
        # Clear the store before every test so tests don't leak into each other.
        mini_redis.store.clear()
        mini_redis.expiry.clear()

    def test_ping_without_message(self):
        response = mini_redis.cmd_ping([])
        self.assertEqual(response, b"+PONG\r\n")

    def test_ping_with_message(self):
        response = mini_redis.cmd_ping(["hello"])
        self.assertEqual(response, b"$5\r\nhello\r\n")

    def test_set_then_get(self):
        mini_redis.cmd_set(["name", "Vanshika"])
        response = mini_redis.cmd_get(["name"])
        self.assertEqual(response, b"$8\r\nVanshika\r\n")

    def test_get_missing_key_returns_nil(self):
        response = mini_redis.cmd_get(["doesnotexist"])
        self.assertEqual(response, b"$-1\r\n")

    def test_del_removes_key(self):
        mini_redis.cmd_set(["name", "Vanshika"])
        count = mini_redis.cmd_del(["name"])
        self.assertEqual(count, b":1\r\n")
        # after deleting, GET should return nil again
        self.assertEqual(mini_redis.cmd_get(["name"]), b"$-1\r\n")

    def test_exists(self):
        mini_redis.cmd_set(["name", "Vanshika"])
        self.assertEqual(mini_redis.cmd_exists(["name"]), b":1\r\n")
        self.assertEqual(mini_redis.cmd_exists(["ghost"]), b":0\r\n")

    def test_set_with_expiry_then_expires(self):
        # set a key that expires almost immediately
        mini_redis.cmd_set(["temp", "value", "EX", "1"])
        # right away it should still be there
        self.assertEqual(mini_redis.cmd_get(["temp"]), b"$5\r\nvalue\r\n")

        # wait for it to expire
        time.sleep(1.2)
        self.assertEqual(mini_redis.cmd_get(["temp"]), b"$-1\r\n")

    def test_expire_on_existing_key(self):
        mini_redis.cmd_set(["name", "Vanshika"])
        response = mini_redis.cmd_expire(["name", "30"])
        self.assertEqual(response, b":1\r\n")

    def test_expire_on_missing_key(self):
        response = mini_redis.cmd_expire(["ghost", "30"])
        self.assertEqual(response, b":0\r\n")


if __name__ == "__main__":
    unittest.main()
