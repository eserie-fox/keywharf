import os

from _pytest.config import Config
from _pytest.main import Session
from _pytest.reports import TestReport


def _running_in_github_actions() -> bool:
    return os.environ.get("GITHUB_ACTIONS") == "true"


def pytest_configure(config: Config) -> None:
    if _running_in_github_actions():
        config.option.capture = "no"


def pytest_sessionstart(session: Session) -> None:
    del session
    if _running_in_github_actions():
        print("::notice title=pytest diagnostics::failure annotations enabled", flush=True)


def pytest_runtest_logreport(report: TestReport) -> None:
    if not _running_in_github_actions() or not report.failed:
        return

    message = f"{report.nodeid} ({report.when})"
    escaped_message = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::error title=pytest failure::{escaped_message}", flush=True)
