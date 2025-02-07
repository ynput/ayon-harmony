# -*- coding: utf-8 -*-
"""Load template."""
import tempfile
import zipfile
import os
import shutil

from ayon_core.pipeline import (
    load,
    get_representation_path,
)
from ayon_core.pipeline.context_tools import is_representation_from_latest
import ayon_harmony.api as harmony


class TemplateLoader(load.LoaderPlugin):
    """Load Harmony template as container.

    .. todo::

        This must be implemented properly.

    """

    product_types = {"harmony.template"}
    representations = {"*"}
    label = "Load Template"
    icon = "gift"

    def load(self, context, name=None, namespace=None, data=None):
        """Plugin entry point.

        Args:
            context (:class:`pyblish.api.Context`): Context.
            name (str, optional): Container name.
            namespace (str, optional): Container namespace.
            data (dict, optional): Additional data passed into loader.

        """
        # Load template.
        self_name = self.__class__.__name__
        temp_dir = tempfile.mkdtemp()
        zip_file = get_representation_path(context["representation"])
        template_path = os.path.join(temp_dir)
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(template_path)

        backdrop_name = harmony.send(
            {
                "function": f"AyonHarmony.Loaders.{self_name}.loadContainer",
                "args": os.path.join(template_path, "harmony.tpl")
            }
        )["result"]

        # Cleanup the temp directory
        shutil.rmtree(temp_dir)

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
        harmony.send(
            {"function": "AyonHarmony.removeBackdropWithContents", "args": container_backdrop}
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
        container = self.load(context, container["name"], container["namespace"])

        # Restore backdrop links
        harmony.send(
            {
                "function": "AyonHarmony.setNodesLinks",
                "args": backdrop_links
            }
        )

        return container

    def _set_green(self, node): # TODO refactor for backdrop
        """Set node color to green `rgba(0, 255, 0, 255)`."""
        harmony.send(
            {
                "function": "AyonHarmony.setColor",
                "args": [node, [0, 255, 0, 255]]
            })

    def _set_red(self, node): # TODO refactor for backdrop
        """Set node color to red `rgba(255, 0, 0, 255)`."""
        harmony.send(
            {
                "function": "AyonHarmony.setColor",
                "args": [node, [255, 0, 0, 255]]
            })
