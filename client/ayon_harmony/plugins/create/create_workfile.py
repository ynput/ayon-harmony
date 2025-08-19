# -*- coding: utf-8 -*-
"""Creator plugin for creating workfiles."""
from ayon_harmony.api.plugin import HarmonyAutoCreator


class CreateWorkfile(HarmonyAutoCreator):
    """Workfile auto-creator."""
    identifier = "io.ayon.creators.harmony.workfile"
    label = "Workfile"
    product_type = "workfile"
    icon = "fa5.file"

    default_variants = ["Main"]
    active_on_create = True

    # Placeholder node name for where we store the workfile data.
    # This does not create an actual Harmony node, but just uses this name
    # as key in the AYON Harmony scene data.
    _node_name = "__workfile__"

    def apply_settings(self, project_settings):
        plugin_settings = (
            project_settings["harmony"]["create"]["CreateWorkfile"]
        )
        self.enabled = plugin_settings["enabled"]
        self.default_variants = plugin_settings["default_variants"]
        self.active_on_create = plugin_settings["active_on_create"]
