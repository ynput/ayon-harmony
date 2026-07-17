from ayon_server.settings import BaseSettingsModel, SettingsField


def cache_enum():
    return [
        {"value": "local", "label": "Use Local"},
        {"value": "server", "label": "From Server"},
    ]


class HarmonyCacheDefaultSettings(BaseSettingsModel):
    """Settings regarding behavior on detection of newer cache."""

    use_default_setting: bool = SettingsField(
        default=False,
        title="Use cache conflict default source",
        description=(
            "When a newer local version is detected, "
            "instead of prompting a dialog, always use "
            "local or pull from server"
        )
    )

    cache_default: str = SettingsField(
        "server",
        enum_resolver=cache_enum,
        title="Default source",
        description=(
            "Use Local will always pull from locally cached file "
            "if it's newer. From server will attempt to get a known version "
            "from server."
        )
    )
