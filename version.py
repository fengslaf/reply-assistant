"""Application version metadata."""

APP_VERSION = "0.2.4"
VERSION_LABEL = "V0.2.04"
VERSION_STAGE = "public"


def get_version_info() -> dict:
    return {
        "app_version": APP_VERSION,
        "version_label": VERSION_LABEL,
        "version_stage": VERSION_STAGE,
    }


__all__ = [
    "APP_VERSION",
    "VERSION_LABEL",
    "VERSION_STAGE",
    "get_version_info",
]
