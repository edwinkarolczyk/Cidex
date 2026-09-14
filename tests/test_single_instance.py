import os
import uuid

import pytest

from single_instance import SingleInstanceGuard


def test_single_instance_mutex_blocks_second_process_slot():
    if os.name != "nt":
        pytest.skip("Windows mutex test")

    name = rf"Local\CIDEX_TEST_{uuid.uuid4().hex}"
    first = SingleInstanceGuard(name)
    second = SingleInstanceGuard(name)
    try:
        assert first.acquire() is True
        assert second.acquire() is False
    finally:
        second.close()
        first.close()
