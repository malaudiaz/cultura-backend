from enum import StrEnum


class Role(StrEnum):
    ADMIN = "administrador"
    EDITOR = "editor"
    WRITER = "redactor"
    USER = "usuario"
