from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    ELDER = "elder"
    FACULTY = "faculty"
    ASSISTANT = "assistant"
    STUDENT = "student"


# Higher index = more authority
ROLE_HIERARCHY = {
    UserRole.STUDENT: 0,
    UserRole.ASSISTANT: 1,
    UserRole.FACULTY: 2,
    UserRole.ELDER: 3,
    UserRole.ADMIN: 4,
}


def has_permission(user_role: str, required_role: str) -> bool:
    user_level = ROLE_HIERARCHY.get(user_role, -1)
    required_level = ROLE_HIERARCHY.get(required_role, 99)
    return user_level >= required_level
