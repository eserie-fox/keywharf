import os

from _pytest.config import Config
from _pytest.main import Session
from _pytest.reports import CollectReport, TestReport


def _emit_error(title: str, message: str) -> None:
    escaped_title = title.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    escaped_message = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::error title={escaped_title}::{escaped_message}", flush=True)


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

    _emit_error("pytest failure", f"{report.nodeid} ({report.when})")


def pytest_collectreport(report: CollectReport) -> None:
    if _running_in_github_actions() and report.failed:
        _emit_error("pytest collection failure", report.nodeid)


def pytest_sessionfinish(session: Session, exitstatus: int) -> None:
    if not _running_in_github_actions() or exitstatus == 0:
        return

    details = [
        f"exit={exitstatus}",
        f"collected={session.testscollected}",
        f"failed={session.testsfailed}",
    ]
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        for category in ("failed", "error"):
            for report in reporter.stats.get(category, []):
                details.append(f"{category}={report.nodeid}")

    _emit_error("pytest session failure", "; ".join(details))
