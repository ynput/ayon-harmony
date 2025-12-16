# -*- coding: utf-8 -*-
"""Loader for single images."""
from pathlib import Path

from ayon_core.pipeline import (
    load,
    get_representation_path,
)
import ayon_harmony.api as harmony


class ImageLoader(load.LoaderPlugin):
    """Load single images.

    Stores the imported product in a container named after the product.
    """

    product_types = {
        "shot",
        "render",
        "image",
        "plate",
        "reference",
        "review",
    }
    representations = {"jpeg", "png", "jpg", "tga", "psd", "sgi"}
    extensions = representations.copy()
    settings_category = "harmony"
    expose_only_current_frame = False

    def load(self, context, name=None, namespace=None, data=None):
        """Plugin entry point.

        Args:
            context (:class:`pyblish.api.Context`): Context.
            name (str, optional): Container name.
            namespace (str, optional): Container namespace.
            data (dict, optional): Additional data passed into loader.

        """
        filepath = Path(self.filepath_from_context(context))
        self_name = self.__class__.__name__

        image_node = harmony.send(
            {
                "function": "AyonHarmony.importImageFile",
                "args": [
                    filepath.as_posix(),
                    self.expose_only_current_frame,
                ]
            }
        )["result"]

        return harmony.containerise(
            name,
            namespace,
            image_node,
            context,
            self_name,
            nodes=[image_node]
        )

    def switch(self, container, context):
        """Switch loaded representations."""
        nodes = container.get("nodes") or []
        if not nodes:
            raise RuntimeError("Container has no nodes to switch.")
        node = nodes[-1]

        repre_entity = context["representation"]
        path = Path(get_representation_path(repre_entity))

        harmony.send(
            {
                "function": "AyonHarmony.replaceImageFile",
                "args": [node, path.as_posix()]
            }
        )

        harmony.imprint(
            node, {"representation": repre_entity["id"]}
        ) 

    def update(self, container, context):
        """Update loaded containers.

        Args:
            container (dict): Container data.
            context (dict): Representation context data.

        """
        self.switch(container, context)

    def remove(self, container):
        """Remove loaded container.

        Args:
            container (dict): Container data.

        """
        nodes = container.get("nodes") or []
        if not nodes:
            return
        node = nodes.pop()
        harmony.imprint(node, {}, remove=True)
        harmony.send(
            {"function": "AyonHarmony.deleteNode", "args": [node]}
        )
