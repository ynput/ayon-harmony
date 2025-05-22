# -*- coding: utf-8 -*-
"""Collect data for render farm renders from scene."""

from ayon_harmony.api.plugins import publish


class CollectFarmRender(publish.CollectHarmonyRender):
    """Collect farm renders."""

    label = "Collect Farm Render"
    families = ["render.farm"]

    def add_additional_data(self, instance):
        instance["FOV"] = self._context.data["FOV"]

        return instance

    def check_process_instance(self, instance):
        """Check if instance should be processed for farm rendering.

        Args:
            instance (pyblish.api.Instance): Instance to check

        Returns:
            bool: True if instance should be processed for farm rendering
        """
        if not super().check_process_instance(instance):
            return False

        creator_attributes = instance.data.get("creator_attributes", {})
        return creator_attributes.get("render_target") == "farm"
