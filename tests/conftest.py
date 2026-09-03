import os
from collections.abc import Generator

import pytest
from _pytest.config import Config
from _pytest.main import Session
from _pytest.reports import CollectReport, TestReport

_current_module = ""


def _emit_error(title: str, message: str) -> None:
    escaped_title = title.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    escaped_message = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::error title={escaped_title}::{escaped_message}", flush=True)


def _emit_notice(title: str, message: str) -> None:
    escaped_title = title.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    escaped_message = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::notice title={escaped_title}::{escaped_message}", flush=True)


def _running_in_github_actions() -> bool:
    return os.environ.get("GITHUB_ACTIONS") == "true"


def pytest_configure(config: Config) -> None:
    if _running_in_github_actions():
        config.option.capture = "no"


def pytest_sessionstart(session: Session) -> None:
    del session
    if _running_in_github_actions():
        _emit_notice("pytest diagnostics", "failure annotations enabled")


def pytest_runtest_logstart(nodeid: str, location: tuple[str, int | None, str]) -> None:
    del location
    global _current_module
    module = nodeid.split("::", maxsplit=1)[0]
    if _running_in_github_actions() and module != _current_module:
        _current_module = module
        _emit_notice("pytest module", module)


def pytest_runtest_logreport(report: TestReport) -> None:
    if not _running_in_github_actions() or not report.failed:
        return

    _emit_error("pytest failure", f"{report.nodeid} ({report.when})")


def pytest_collectreport(report: CollectReport) -> None:
    if _running_in_github_actions() and report.failed:
        _emit_error("pytest collection failure", report.nodeid)


def pytest_sessionfinish(session: Session, exitstatus: int) -> None:
    if not _running_in_github_actions():
        return

    details = [
        f"exit={exitstatus}",
        f"collected={session.testscollected}",
        f"failed={session.testsfailed}",
    ]
    _emit_notice("pytest session finish", "; ".join(details))
    if exitstatus == 0:
        return

    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        for category in ("failed", "error"):
            for report in reporter.stats.get(category, []):
                details.append(f"{category}={report.nodeid}")

    _emit_error("pytest session failure", "; ".join(details))


@pytest.hookimpl(hookwrapper=True)
def pytest_terminal_summary(
    terminalreporter: object,
    exitstatus: int,
    config: Config,
) -> Generator[None]:
    del terminalreporter, config
    if _running_in_github_actions():
        _emit_notice("pytest terminal summary", f"start; exit={exitstatus}")
    yield
    if _running_in_github_actions():
        _emit_notice("pytest terminal summary", f"finish; exit={exitstatus}")


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config: Config) -> None:
    del config
    if _running_in_github_actions():
        _emit_notice("pytest unconfigure", "reached")
