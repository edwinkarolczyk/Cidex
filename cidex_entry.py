"""CIDEX executable entry point."""

from __future__ import annotations

from excel_compat import install_plan_monitor_excel_fix
from excel_source_guard import install_excel_source_guard
from single_instance import SingleInstanceGuard


def main() -> None:
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
        launcher.main()
    finally:
        guard.close()


if __name__ == "__main__":
    main()
