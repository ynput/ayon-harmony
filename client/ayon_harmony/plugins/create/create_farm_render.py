# -*- coding: utf-8 -*-
"""Create Composite node for render on farm."""
import ayon_harmony.api as harmony
from ayon_harmony.api import plugin


class CreateFarmRender(plugin.HarmonyCreator):
    """Composite node for publishing renders."""

    identifier = "io.ayon.creators.harmony.render.farm"
    label = "Render on Farm"
    product_type = "renderFarm"

    node_type = "WRITE"

    def setup_node(self, node):
        """Set render node."""
        path = "render/{0}/{0}.".format(node.split("/")[-1])
        harmony.send(
            {
                "function": "AyonHarmony.Creators.CreateRender.create",
                "args": [node, path]
            })
        harmony.send(
            {
                "function": "AyonHarmony.color",
                "args": [[0.9, 0.75, 0.3, 1.0]]
            }
        )
