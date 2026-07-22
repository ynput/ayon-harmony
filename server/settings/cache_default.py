from ayon_server.settings import BaseSettingsModel, SettingsField


def cache_enum():
    return [
        {"value": "local", "label": "Use Local"},
        {"value": "server", "label": "From Server"},
    ]


class HarmonyCacheDefaultSettings(BaseSettingsModel):
    """Settings regarding behavior on detection of newer cache."""

    force_default: bool = SettingsField(
        default=False,
        title="Force cache conflict source",
        description=(
            "When a newer local version is detected, "
            "instead of prompting a dialog, always use "
            "local or pull from server"
        )
    )

    cache_default_source: str = SettingsField(
        "server",
        enum_resolver=cache_enum,
        title="Conflict source",
        description=(
            "Use Local will always pull from locally cached file "
            "if it's newer. From server will attempt to get a known version "
            "from server."
        )
    )
