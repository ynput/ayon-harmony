# -*- coding: utf-8 -*-
"""Create Composite node for render on farm."""
import ayon_harmony.api as harmony
from ayon_harmony.api import plugin


class CreateFarmRender(plugin.Creator):
    """Composite node for publishing renders."""

    name = "renderDefault"
    label = "Render on Farm"
    product_type = "renderFarm"
    node_type = "WRITE"

    def __init__(self, *args, **kwargs):
        """Constructor."""
        super(CreateFarmRender, self).__init__(*args, **kwargs)

    def setup_node(self, node):
        """Set render node."""
        path = "render/{0}/{0}.".format(node.split("/")[-1])
        harmony.send(
            {
                "function": "PypeHarmony.Creators.CreateRender.create",
                "args": [node, path]
            })
        harmony.send(
            {
                "function": "PypeHarmony.color",
                "args": [[0.9, 0.75, 0.3, 1.0]]
            }
        )
