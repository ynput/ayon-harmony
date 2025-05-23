# -*- coding: utf-8 -*-
"""Collect render instances in Harmony."""

import pyblish.api

from ayon_harmony.api.plugins import publish


class CollectRender(publish.CollectHarmonyRender):
    """Collect render instances from Harmony.

    Create regular render instances based on the ones created within the publisher.
    """

    label = "Collect Render Instances"
    order = pyblish.api.CollectorOrder + 0.01
    hosts = ["harmony"]
    families = ["render"]
