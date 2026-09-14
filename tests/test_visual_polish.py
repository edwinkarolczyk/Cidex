from visual_polish import monitoring_badge_style


def test_monitoring_badge_style_active() -> None:
    label, colour = monitoring_badge_style("active")
    assert label == "Monitoring aktywny"
    assert colour == "#2DD4BF"


def test_monitoring_badge_style_checking_and_error() -> None:
    assert monitoring_badge_style("checking")[0] == "Sprawdzanie…"
    assert monitoring_badge_style("error")[0] == "Błąd monitoringu"


def test_monitoring_badge_style_unknown_falls_back_to_idle() -> None:
    assert monitoring_badge_style("other") == monitoring_badge_style("idle")
