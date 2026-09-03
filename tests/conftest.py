import os

from _pytest.reports import TestReport


def pytest_runtest_logreport(report: TestReport) -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true" or not report.failed:
        return

    message = f"{report.nodeid} ({report.when})"
    escaped_message = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::error title=pytest failure::{escaped_message}", flush=True)
