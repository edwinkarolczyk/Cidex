from pathlib import Path

import mobile_api_launcher as launcher


class FakeProcess:
    def __init__(self):
        self.pid = 4321
        self.running = True
        self.terminated = False
        self.killed = False

    def poll(self):
        return None if self.running else 0

    def terminate(self):
        self.terminated = True
        self.running = False

    def wait(self, timeout=None):
        self.running = False
        return 0

    def kill(self):
        self.killed = True
        self.running = False


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "WM"
    (root / "data" / "zlecenia").mkdir(parents=True)
    (root / "data" / "produkty").mkdir(parents=True)
    return root


def test_source_command_uses_api_server():
    command = launcher.api_command()
    assert command[0]
    assert command[-1].endswith("api_server.py")


def test_controller_starts_and_stops_api(monkeypatch, tmp_path):
    root = _root(tmp_path)
    fake = FakeProcess()
    calls = []

    def fake_popen(command, **kwargs):
        calls.append((command, kwargs))
        return fake

    monkeypatch.setattr(launcher.subprocess, "Popen", fake_popen)
    controller = launcher.MobileApiController()

    assert controller.start(root) == 4321
    assert controller.is_running()
    assert controller.pid == 4321
    assert calls and calls[0][0][-1].endswith("api_server.py")

    controller.stop()
    assert fake.terminated
    assert not controller.is_running()
