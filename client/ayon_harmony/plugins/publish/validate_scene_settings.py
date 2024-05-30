# -*- coding: utf-8 -*-
"""Validate scene settings."""
import os
import json
import re

import pyblish.api

import ayon_harmony.api as harmony
from ayon_core.pipeline import PublishXmlValidationError


class ValidateSceneSettingsRepair(pyblish.api.Action):
    """Repair the instance."""

    label = "Repair"
    icon = "wrench"
    on = "failed"

    def process(self, context, plugin):
        """Repair action entry point."""
        expected = harmony.get_current_context_settings()
        expected_settings = _update_frames(dict.copy(expected))
        expected_settings["frameStart"] = 1
        expected_settings["frameEnd"] = expected_settings["frameEnd"] + \
            expected_settings["handleEnd"]
        harmony.set_scene_settings(expected_settings)
        if not os.path.exists(context.data["scenePath"]):
            self.log.info("correcting scene name")
            scene_dir = os.path.dirname(context.data["currentFile"])
            scene_path = os.path.join(
                scene_dir, os.path.basename(scene_dir) + ".xstage"
            )
            harmony.save_scene_as(scene_path)


class ValidateSceneSettings(pyblish.api.InstancePlugin):
    """Ensure the scene settings are in sync with database."""

    order = pyblish.api.ValidatorOrder
    label = "Validate Scene Settings"
    families = ["workfile"]
    hosts = ["harmony"]
    actions = [ValidateSceneSettingsRepair]
    settings_category = "harmony"
    optional = True

    # skip frameEnd check if asset contains any of:
    frame_check_filter = ["_ch_", "_pr_", "_intd_", "_extd_"]  # regex

    # skip resolution check if Task name matches any of regex patterns
    skip_resolution_check = ["render", "Render"]  # regex

    # skip frameStart, frameEnd check if Task name matches any of regex patt.
    skip_timelines_check = []  # regex

    def process(self, instance):
        """Plugin entry point."""

        # TODO 'get_current_context_settings' could expect folder entity
        #   as an argument which is available on 'context.data["folderEntity"]'
        #   - the same approach can be used in 'ValidateSceneSettingsRepair'
        expected_settings = harmony.get_current_context_settings()
        self.log.info("scene settings from DB:{}".format(expected_settings))
        expected_settings.pop("entityType")  # not useful for the validation

        expected_settings = _update_frames(dict.copy(expected_settings))
        expected_settings["frameEndHandle"] = expected_settings["frameEnd"] +\
            expected_settings["handleEnd"]

        task_name = instance.context.data["task"]

        if (any(re.search(pattern, task_name)
                for pattern in self.skip_resolution_check)):
            self.log.info("Skipping resolution check because of "
                          "task name and pattern {}".format(
                              self.skip_resolution_check))
            expected_settings.pop("resolutionWidth")
            expected_settings.pop("resolutionHeight")

        if (any(re.search(pattern, os.getenv('AYON_TASK_NAME'))
                for pattern in self.skip_timelines_check)):
            self.log.info("Skipping frames check because of "
                          "task name and pattern {}".format(
                              self.skip_timelines_check))
            expected_settings.pop('frameStart', None)
            expected_settings.pop('frameEnd', None)
            expected_settings.pop('frameStartHandle', None)
            expected_settings.pop('frameEndHandle', None)

        folder_name = instance.context.data["folderPath"].rsplit("/", 1)[-1]
        if any(re.search(pattern, folder_name)
                for pattern in self.frame_check_filter):
            self.log.info("Skipping frames check because of "
                          "task name and pattern {}".format(
                              self.frame_check_filter))
            expected_settings.pop('frameStart', None)
            expected_settings.pop('frameEnd', None)
            expected_settings.pop('frameStartHandle', None)
            expected_settings.pop('frameEndHandle', None)

        # handle case where ftrack uses only two decimal places
        # 23.976023976023978 vs. 23.98
        fps = instance.context.data.get("frameRate")
        if isinstance(instance.context.data.get("frameRate"), float):
            fps = float(
                "{:.2f}".format(instance.context.data.get("frameRate")))

        self.log.debug("filtered settings: {}".format(expected_settings))

        current_settings = {
            "fps": fps,
            "frameStart": instance.context.data["frameStart"],
            "frameEnd": instance.context.data["frameEnd"],
            "handleStart": instance.context.data.get("handleStart"),
            "handleEnd": instance.context.data.get("handleEnd"),
            "frameStartHandle": instance.context.data.get("frameStartHandle"),
            "frameEndHandle": instance.context.data.get("frameEndHandle"),
            "resolutionWidth": instance.context.data.get("resolutionWidth"),
            "resolutionHeight": instance.context.data.get("resolutionHeight"),
        }
        self.log.debug("current scene settings {}".format(current_settings))

        invalid_settings = []
        invalid_keys = set()
        for key, value in expected_settings.items():
            if value != current_settings[key]:
                invalid_settings.append(
                    "{} expected: {}  found: {}".format(key, value,
                                                        current_settings[key]))
                invalid_keys.add(key)

        if ((expected_settings["handleStart"]
            or expected_settings["handleEnd"])
           and invalid_settings):
            msg = "Handles included in calculation. Remove handles in DB " +\
                  "or extend frame range in timeline."
            invalid_settings[-1]["reason"] = msg

        msg = "Found invalid settings:\n{}".format(
            json.dumps(invalid_settings, sort_keys=True, indent=4)
        )

        if invalid_settings:
            invalid_keys_str = ",".join(invalid_keys)
            break_str = "<br/>"
            invalid_setting_str = "<b>Found invalid settings:</b><br/>{}".\
                format(break_str.join(invalid_settings))

            formatting_data = {
                "invalid_setting_str": invalid_setting_str,
                "invalid_keys_str": invalid_keys_str
            }
            raise PublishXmlValidationError(self, msg,
                                            formatting_data=formatting_data)

        scene_url = instance.context.data.get("scenePath")
        if not os.path.exists(scene_url):
            msg = "Scene file {} not found (saved under wrong name)".format(
                scene_url
            )
            formatting_data = {
                "scene_url": scene_url
            }
            raise PublishXmlValidationError(self, msg, key="file_not_found",
                                            formatting_data=formatting_data)


def _update_frames(expected_settings):
    """
        Calculate proper frame range including handles set in DB.

        Harmony requires rendering from 1, so frame range is always moved
        to 1.
    Args:
        expected_settings (dict): pulled from DB

    Returns:
        modified expected_setting (dict)
    """
    frames_count = expected_settings["frameEnd"] - \
        expected_settings["frameStart"] + 1

    expected_settings["frameStart"] = 1.0 + expected_settings["handleStart"]
    expected_settings["frameEnd"] = \
        expected_settings["frameStart"] + frames_count - 1
    return expected_settings
