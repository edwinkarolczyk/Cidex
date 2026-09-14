"""CIDEX executable entry point."""

from __future__ import annotations

from excel_compat import install_plan_monitor_excel_fix


def main() -> None:
    install_plan_monitor_excel_fix()
    from launcher import main as launcher_main

    launcher_main()


if __name__ == "__main__":
    main()
