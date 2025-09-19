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
        "CreateWorkfile": {
            "enabled": True,
            "active_on_create": True,
            "default_variants": [
                "Main"
            ],
        },
        "CreateReview": {
            "enabled": False,
            "active_on_create": True,
            "default_variants": [
                "Main"
            ],
        },
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
        },
        "CreateRenderLayer": {
            "enabled": True,
            "mark_for_review": False,
            "active_on_create": True,
            "default_pass_name": "beauty",
            "default_variant": "Main",
            "default_variants": []
        },
        "CreateRenderPass": {
            "enabled": True,
            "mark_for_review": False,
            "active_on_create": True,
            "default_variant": "",
            "default_variants": [],
            "rename_read": True,
        },
        "AutoDetectRendeLayersPasses": {
            "enabled": True,
            "render_layer_variant_template": "G{group_index}",
            "group_idx_offset": 10,
            "group_idx_padding": 3,
            "render_pass_template": "L{layer_index}_{variant}",
            "layer_idx_offset": 10,
            "layer_idx_padding": 3,
            "layer_name_template":{
                "enabled": False,
                "template": "G{group_index}_L{layer_index}_{variant}"
            }
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
