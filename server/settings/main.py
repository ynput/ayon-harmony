from ayon_server.settings import BaseSettingsModel, SettingsField

from .imageio import HarmonyImageIOModel
from .creator_plugins import HarmonyCreatePlugins
from .publish_plugins import HarmonyPublishPlugins


class HarmonySettings(BaseSettingsModel):
    """Harmony Project Settings."""

    imageio: HarmonyImageIOModel = SettingsField(
        default_factory=HarmonyImageIOModel,
        title="OCIO config"
    )
    create: HarmonyCreatePlugins = SettingsField(
        default_factory=HarmonyCreatePlugins,
        title="Creator plugins"
    )
    publish: HarmonyPublishPlugins = SettingsField(
        default_factory=HarmonyPublishPlugins,
        title="Publish plugins"
    )


DEFAULT_HARMONY_SETTING = {
    "create": {
        "CreateRender": {
            "enabled": True,
            "default_variants": [
                "Main"
            ],
            "auto_connect": False,
            "composition_node_pattern": "Composite"
        },
        "CreateFarmRender": {
            "enabled": True,
            "default_variants": [
                "Main"
            ],
            "auto_connect": False,
            "composition_node_pattern": "Composite"
        }
    },
    "publish": {
        "CollectPalettes": {
            "allowed_tasks": [
                ".*"
            ]
        },
        "ValidateAudio": {
            "enabled": True,
            "optional": True,
            "active": True
        },
        "ValidateSceneSettings": {
            "enabled": True,
            "optional": True,
            "active": True,
            "frame_check_filter": [],
            "skip_resolution_check": [],
            "skip_timelines_check": []
        },
        "ValidateInstances": {
            "enabled": True,
            "optional": True,
            "active": True
        }
    }
}
