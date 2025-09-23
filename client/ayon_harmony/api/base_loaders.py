# -*- coding: utf-8 -*-
"""Base classes for loaders."""

from ayon_core.pipeline import (
    load,
    get_representation_path,
)
import ayon_harmony.api as harmony


class BackdropBaseLoader(load.LoaderPlugin):
    """Load nodes into a backdrop."""

    def load(self, context, name=None, namespace=None, data=None):
        """Plugin entry point.

        Args:
            context (:class:`pyblish.api.Context`): Context.
            name (str, optional): Container name.
            namespace (str, optional): Container namespace.
            data (dict, optional): Additional data passed into loader.

        """
        self_name = self.__class__.__name__
        filepath = get_representation_path(context["representation"])

        backdrop_name = harmony.send(
            {
                "function": f"AyonHarmony.Loaders.{self_name}.loadContainer",
                "args": [filepath, name],
            }
        )["result"]

        # We must validate the group_node
        return harmony.containerise(
            name,
            namespace,
            backdrop_name,
            context,
            self_name
        )

    def remove(self, container):
        """Remove container.

        Args:
            container (dict): container definition.
        """
        container_backdrop = harmony.find_backdrop_by_name(container["name"])
        if container_backdrop:
            harmony.send(
                {
                    "function": "AyonHarmony.removeBackdrop",
                    "args": [container_backdrop, True]
                }
            )
        harmony.remove(container["name"])

    def update(self, container, context):
        """Update loaded containers.

        Args:
            container (dict): Container data.
            context (dict): Representation context data.

        """
        return self.switch(container, context)

    def switch(self, container, context):
        """Switch representation containers."""
        backdrop_name = container["name"]
        backdrop = harmony.find_backdrop_by_name(backdrop_name)

        # Keep backdrop links
        backdrop_links = harmony.send(
            {
                "function": "AyonHarmony.getBackdropLinks",
                "args": backdrop,
            }
        )["result"]

        # Replace template container
        self.remove(container)  # Before load to avoid node name incrementation
        container = self.load(
            context, container["name"], container["namespace"]
        )

        # Restore backdrop links
        harmony.send(
            {
                "function": "AyonHarmony.setNodesLinks",
                "args": backdrop_links
            }
        )

        return container
