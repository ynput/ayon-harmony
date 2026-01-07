# -*- coding: utf-8 -*-
"""Create render node."""
import ayon_harmony.api as harmony
from ayon_harmony.api import plugin


class CreateRender(plugin.HarmonyRenderCreator):
    """Composite node for publishing renders."""

    identifier = "io.ayon.creators.harmony.render"
    label = "Render"
    product_type = "render"
    product_base_type = "render"
    icon = "eye"

    node_type = "WRITE"

    def setup_node(self, node):
        """Set render node."""
        self_name = self.__class__.__name__
        path = "render/{0}/{0}.".format(node.split("/")[-1])
        harmony.send(
            {
                "function": f"AyonHarmony.Creators.{self_name}.create",
                "args": [node, path]
            })
