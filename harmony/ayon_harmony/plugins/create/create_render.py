# -*- coding: utf-8 -*-
"""Create render node."""
import ayon_harmony.api as harmony
from ayon_harmony.api import plugin


class CreateRender(plugin.Creator):
    """Composite node for publishing renders."""

    name = "renderDefault"
    label = "Render"
    product_type = "render"
    node_type = "WRITE"

    def __init__(self, *args, **kwargs):
        """Constructor."""
        super(CreateRender, self).__init__(*args, **kwargs)

    def setup_node(self, node):
        """Set render node."""
        self_name = self.__class__.__name__
        path = "render/{0}/{0}.".format(node.split("/")[-1])
        harmony.send(
            {
                "function": f"PypeHarmony.Creators.{self_name}.create",
                "args": [node, path]
            })
