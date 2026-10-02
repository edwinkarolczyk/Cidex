"""CIDEX executable entry point."""

from __future__ import annotations

import sys

from excel_compat import install_plan_monitor_excel_fix
from excel_source_guard import install_excel_source_guard
from single_instance import SingleInstanceGuard


def _self_test() -> None:
    """Minimal boot/runtime test used by CI before publishing Cidex.exe."""
    import json  # noqa: F401
    import tkinter  # noqa: F401

    import openpyxl  # noqa: F401
    import pandas  # noqa: F401

    import plan_monitor  # noqa: F401
    import version  # noqa: F401


def main() -> None:
    if "--self-test" in sys.argv:
        _self_test()
        return

    guard = SingleInstanceGuard()
    if not guard.acquire():
        guard.restore_existing_window()
        guard.close()
        return

    try:
        install_plan_monitor_excel_fix()
        install_excel_source_guard()

        import launcher
        from background_mode import install_background_mode
        from plan_source_router import install_plan_source_router
        from runtime_compat import install_runtime_fixes
        from search_ui import install_search_ui
        from settings_enhancements import install_settings_enhancements
        from ui_column_widths import install_column_widths
        from visual_polish import install_visual_polish

        install_runtime_fixes(launcher)
        install_search_ui(launcher.EnhancedCidexApp)
        install_column_widths(launcher.EnhancedCidexApp)
        install_visual_polish(launcher.EnhancedCidexApp)
        install_background_mode(launcher.EnhancedCidexApp)
        install_settings_enhancements(launcher.EnhancedCidexApp)
        install_plan_source_router(launcher.EnhancedCidexApp)
        launcher.main()
    finally:
        guard.close()


if __name__ == "__main__":
    main()
