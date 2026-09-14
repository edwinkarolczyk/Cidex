"""CIDEX executable entry point."""

from __future__ import annotations

from excel_compat import install_plan_monitor_excel_fix


def main() -> None:
    install_plan_monitor_excel_fix()

    import launcher
    from background_mode import install_background_mode
    from runtime_compat import install_runtime_fixes

    install_runtime_fixes(launcher)
    install_background_mode(launcher.EnhancedCidexApp)
    launcher.main()


if __name__ == "__main__":
    main()
