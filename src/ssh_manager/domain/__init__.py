"""Domain exports."""

from ssh_manager.domain.errors import SSHManagerError
from ssh_manager.domain.models import (
    LocalState,
    ManagerConfig,
    RemoteAuthenticationOption,
    RemoteEndpointOption,
    RemoteExtraConfig,
    RemoteHostDefinition,
    SSHAuthentication,
    SSHEndpoint,
    SSHExtraConfig,
    SSHHostConfig,
    STATE_SCHEMA_VERSION,
    SelectedHostState,
)
from ssh_manager.domain.results import (
    ApplyResult,
    HostMutationResult,
    IncludeInstallResult,
    InitResult,
    LocalHostStatus,
    ManagedKeyCopyPlan,
    RenderResult,
    ResolvedHostSelection,
    ValidationResult,
)

__all__ = [
    "ApplyResult",
    "HostMutationResult",
    "IncludeInstallResult",
    "InitResult",
    "LocalHostStatus",
    "LocalState",
    "ManagerConfig",
    "ManagedKeyCopyPlan",
    "RenderResult",
    "RemoteAuthenticationOption",
    "RemoteEndpointOption",
    "RemoteExtraConfig",
    "RemoteHostDefinition",
    "ResolvedHostSelection",
    "SSHAuthentication",
    "SSHEndpoint",
    "SSHExtraConfig",
    "SSHHostConfig",
    "SSHManagerError",
    "STATE_SCHEMA_VERSION",
    "SelectedHostState",
    "ValidationResult",
]
