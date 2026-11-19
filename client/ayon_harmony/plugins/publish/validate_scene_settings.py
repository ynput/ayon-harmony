# -*- coding: utf-8 -*-
"""Validate scene settings."""
import os

import pyblish.api

import ayon_harmony.api as harmony
from ayon_core.pipeline import (
    PublishXmlValidationError,
    OptionalPyblishPluginMixin
)


class ValidateSceneSettingsRepair(pyblish.api.Action):
    """Repair the instance."""

    label = "Repair"
    icon = "wrench"
    on = "failed"

    def process(self, context, plugin):
        """Repair action entry point."""
        harmony.ensure_scene_settings()
        if not os.path.exists(context.data["scenePath"]):
            self.log.info("correcting scene name")
            scene_dir = os.path.dirname(context.data["currentFile"])
            scene_path = os.path.join(
                scene_dir, os.path.basename(scene_dir) + ".xstage"
            )
            harmony.save_scene_as(scene_path)


class ValidateSceneSettings(
    OptionalPyblishPluginMixin,
    pyblish.api.InstancePlugin
):
    """Ensure the scene settings are in sync with database."""

    order = pyblish.api.ValidatorOrder
    label = "Validate Scene Settings"
    families = ["workfile"]
    hosts = ["harmony"]
    actions = [ValidateSceneSettingsRepair]
    settings_category = "harmony"
    optional = True

    def process(self, instance):
        """Plugin entry point."""
        if not self.is_active(instance.data):
            return

        invalid_settings = harmony.get_invalid_scene_settings(
            harmony.get_current_context_settings(),
            instance.context.data["task"],
            instance.context.data["folderPath"],
        )
        if invalid_settings:
            invalid_lines = [
                f"{key} expected: {expected}  found: {found}"
                for key, (expected, found) in invalid_settings.items()
            ]
            msg = "Found invalid settings:\n{}".format(
                "\n".join(invalid_lines)
            )
            formatting_data = {
                "invalid_setting_str": (
                    "<b>Found invalid settings:</b><br/>"
                    + "<br/>".join(invalid_lines)
                ),
                "invalid_keys_str": ",".join(invalid_settings),
            }
            raise PublishXmlValidationError(
                self, msg, formatting_data=formatting_data
            )

        scene_url = instance.context.data.get("scenePath")
        if not os.path.exists(scene_url):
            msg = f"Scene file {scene_url} not found (saved under wrong name)"
            formatting_data = {"scene_url": scene_url}
            raise PublishXmlValidationError(
                self,
                msg,
                key="file_not_found",
                formatting_data=formatting_data
            )
