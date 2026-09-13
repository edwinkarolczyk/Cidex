from updater import ReleaseInfo, CidexUpdater, version_tuple


def test_version_tuple_and_newer():
    assert version_tuple("v1.2.3-beta") == (1, 2, 3)
    assert version_tuple("bad") == (0, 0, 0)
    info = ReleaseInfo("9.9.9", "https://example.invalid/Cidex.exe", 123, "CIDEX 9.9.9")
    assert CidexUpdater.is_newer(info)


def test_release_info_shape():
    info = ReleaseInfo("1.2.0", "https://example.invalid/Cidex.exe", 10, "CIDEX 1.2.0")
    assert info.version == "1.2.0"
    assert info.size == 10
