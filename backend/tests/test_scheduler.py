"""Tests for the scheduler module's lock and abort management."""

import asyncio

import pytest

from app.worker.scheduler import (
    clear_abort,
    get_abort_event,
    get_scan_lock,
    request_abort,
)


class TestScanLock:
    def test_returns_same_lock_for_same_folder(self):
        lock1 = get_scan_lock(1)
        lock2 = get_scan_lock(1)
        assert lock1 is lock2

    def test_returns_different_lock_for_different_folder(self):
        lock1 = get_scan_lock(100)
        lock2 = get_scan_lock(101)
        assert lock1 is not lock2

    def test_lock_is_asyncio_lock(self):
        lock = get_scan_lock(200)
        assert isinstance(lock, asyncio.Lock)


class TestAbortEvent:
    def test_returns_same_event_for_same_folder(self):
        ev1 = get_abort_event(300)
        ev2 = get_abort_event(300)
        assert ev1 is ev2

    def test_returns_different_event_for_different_folder(self):
        ev1 = get_abort_event(400)
        ev2 = get_abort_event(401)
        assert ev1 is not ev2

    def test_request_and_clear_abort(self):
        folder_id = 500
        ev = get_abort_event(folder_id)
        assert not ev.is_set()

        request_abort(folder_id)
        assert ev.is_set()

        clear_abort(folder_id)
        assert not ev.is_set()
