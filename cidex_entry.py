"""CIDEX executable entry point."""

from __future__ import annotations

from excel_compat import install_plan_monitor_excel_fix
from single_instance import SingleInstanceGuard


def main() -> None:
    guard = SingleInstanceGuard()
    if not guard.acquire():
        guard.restore_existing_window()
        guard.close()
        return

    try:
        install_plan_monitor_excel_fix()

        import launcher
        from background_mode import install_background_mode
        from runtime_compat import install_runtime_fixes
        from search_ui import install_search_ui
        from ui_column_widths import install_column_widths

        install_runtime_fixes(launcher)
        install_search_ui(launcher.EnhancedCidexApp)
        install_column_widths(launcher.EnhancedCidexApp)
        install_background_mode(launcher.EnhancedCidexApp)
        launcher.main()
    finally:
        guard.close()


if __name__ == "__main__":
    main()
