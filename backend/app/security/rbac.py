from enum import Enum
from typing import List, Set

class Role(str, Enum):
    PERSONNEL = "PERSONNEL"
    WELFARE_OFFICER = "WELFARE_OFFICER"
    COMMANDER = "COMMANDER"
    ADMIN = "ADMIN"


LOCKED_ROLES: Set[str] = {
    Role.PERSONNEL.value,
    Role.WELFARE_OFFICER.value,
    Role.COMMANDER.value,
    Role.ADMIN.value,
}


def is_valid_role(role_name: str) -> bool:
    return role_name in LOCKED_ROLES
