# -*- coding: utf-8 -*-
"""Load template."""
import tempfile
import zipfile
import os
import shutil
import uuid

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

        group_id = "{}".format(uuid.uuid4())

        container_backdrop = harmony.send(
            {
                "function": f"AyonHarmony.Loaders.{self_name}.loadContainer",
                "args": [os.path.join(template_path, "harmony.tpl"),
                         context["folder"]["name"],
                         context["product"]["name"],
                         group_id]
            }
        )["result"]

        # Cleanup the temp directory
        shutil.rmtree(temp_dir)

        # We must validate the group_node
        return harmony.containerise(
            name,
            namespace,
            container_backdrop,
            context,
            self_name
        )

    def update(self, container, context): # TODO: Implement this
        """Update loaded containers.

        Args:
            container (dict): Container data.
            context (dict): Representation context data.

        """
        node_name = container["name"]
        node = harmony.find_node_by_name(node_name, "GROUP")
        self_name = self.__class__.__name__

        repre_entity = context["representation"]
        if is_representation_from_latest(repre_entity):
            self._set_green(node)
        else:
            self._set_red(node)

        update_and_replace = harmony.send(
            {
                "function": f"AyonHarmony.Loaders.{self_name}."
                            "askForColumnsUpdate",
                "args": []
            }
        )["result"]

        if update_and_replace:
            # FIXME: This won't work, need to implement it.
            harmony.send(
                {
                    "function": f"AyonHarmony.Loaders.{self_name}."
                                "replaceNode",
                    "args": []
                }
            )
        else:
            self.load(
                container["context"], container["name"],
                None, container["data"])

        harmony.imprint(
            node, {"representation": repre_entity["id"]}
        )

    def remove(self, container):
        """Remove container.

        Args:
            container (dict): container definition.
        """
        backdrop = harmony.find_backdrop_by_name(container["name"])
        harmony.send(
            {"function": "AyonHarmony.removeBackdropWithContents", "args": backdrop}
        )

    def switch(self, container, context): # TODO: Implement this
        """Switch representation containers."""
        self.update(container, context)

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
