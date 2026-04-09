"""Domain exports."""

from ssh_manager.domain.errors import SSHManagerError
from ssh_manager.domain.models import (
    ManagerConfig,
    RemoteAuthenticationOption,
    RemoteEndpointOption,
    RemoteExtraConfig,
    RemoteHostDefinition,
    SSHAuthentication,
    SSHEndpoint,
    SSHExtraConfig,
    SSHHostConfig,
)
from ssh_manager.domain.results import HostMutationResult, ValidationResult

__all__ = [
    "HostMutationResult",
    "ManagerConfig",
    "RemoteAuthenticationOption",
    "RemoteEndpointOption",
    "RemoteExtraConfig",
    "RemoteHostDefinition",
    "SSHAuthentication",
    "SSHEndpoint",
    "SSHExtraConfig",
    "SSHHostConfig",
    "SSHManagerError",
    "ValidationResult",
]
