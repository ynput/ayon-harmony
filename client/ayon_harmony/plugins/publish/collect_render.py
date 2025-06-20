# -*- coding: utf-8 -*-
"""Collect render instances in Harmony."""

import pyblish.api

from ayon_harmony.api.plugins import publish


class CollectRender(publish.CollectRenderBase):
    """Collect render instances from Harmony.

    Create regular render instances based on the ones created within the publisher.
    """

    label = "Collect Render Instances"
    order = pyblish.api.CollectorOrder + 0.01
    hosts = ["harmony"]
    families = ["render"]


class CollectFarmRender(publish.CollectRenderBase):
    """Collect farm renders."""

    label = "Collect Farm Render"
    families = ["render"]

    def add_additional_data(self, instance):
        instance["FOV"] = self._context.data["FOV"]

        return instance
