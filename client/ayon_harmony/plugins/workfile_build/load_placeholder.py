"""Harmony Load Placeholder Plugin."""

from __future__ import annotations

import ayon_harmony.api as harmony
from ayon_core.pipeline.workfile.workfile_template_builder import (
    LoadPlaceholderItem,
    PlaceholderLoadMixin,
)

from ayon_harmony.api.workfile_template_builder import HarmonyPlaceholderPlugin


class HarmonyPlaceholderLoadPlugin(
    HarmonyPlaceholderPlugin, PlaceholderLoadMixin
):
    """Workfile template plugin to create and populate Harmony load placeholders."""

    identifier = "ayon.load.placeholder"
    label = "Harmony Load"

    def get_placeholder_node_name(self, placeholder_data: dict) -> str:
        """Return a Harmony-safe name for the load placeholder node.

        Args:
            placeholder_data (dict): Placeholder configuration data.

        Returns:
            str: Name in the form ``"ayon_load_placeholder_<productName>"``.
        """
        return "{}_{}".format(
            self.identifier.replace(".", "_"),
            placeholder_data["product_name"],
        )

    def create_placeholder(self, placeholder_data: dict) -> None:
        """Create a load placeholder node and imprint it with metadata.

        Args:
            placeholder_data (dict): Placeholder configuration including
                ``loader``, ``product_name``, and filter fields.
        """
        node_name = self.get_placeholder_node_name(placeholder_data)

        loader_name: str = placeholder_data["loader"]
        loaders_by_name = self.builder.get_loaders_by_name()
        loader_class = loaders_by_name[loader_name]

        if hasattr(loader_class, "create_load_placeholder_node"):
            node_id = loader_class().create_load_placeholder_node(
                node_name,
                placeholder_data,
            )
        else:
            node_id = self.create_placeholder_node(node_name)

        placeholder_data["plugin_identifier"] = self.identifier
        self._imprint(node_id, placeholder_data)

    def populate_placeholder(self, placeholder: LoadPlaceholderItem) -> None:
        """Populate a placeholder by loading the matching AYON product."""
        self.populate_load_placeholder(placeholder)

    def repopulate_placeholder(self, placeholder: LoadPlaceholderItem) -> None:
        """Re-populate an existing placeholder (e.g. on workfile reopen)."""
        self.populate_load_placeholder(placeholder)

    def get_placeholder_options(self, options: dict | None = None) -> list:
        """Return the UI option definitions for the placeholder dialog.

        Args:
            options (dict | None): Existing option values to pre-populate.

        Returns:
            list: Option widget definitions for the WorkfileBuildPlaceholderDialog.
        """
        return self.get_load_plugin_options(options)

    def collect_placeholders(self) -> list[LoadPlaceholderItem]:
        """Collect all load placeholder items from the current Harmony scene.

        Returns:
            list[LoadPlaceholderItem]: All load placeholder items found,
                each wrapping the node identifier and its metadata.
        """
        output = []
        for node_id in self.collect_scene_placeholders():
            placeholder_data = self._read(node_id)
            output.append(LoadPlaceholderItem(node_id, placeholder_data, self))
        return output

    def load_succeed(
        self,
        placeholder: LoadPlaceholderItem,
        container: dict | str,
    ) -> None:
        """Called after a product is successfully loaded for this placeholder.

        Args:
            placeholder (LoadPlaceholderItem): The placeholder that was
                populated, providing its node identifier as scene_identifier.
            container (dict | str): The container returned by the loader.
                In Harmony this is the dict produced by harmony.containerise,
                with the node identifier stored under "objectName".
        """
        placeholder_node = placeholder.scene_identifier
        container_node = self._resolve_container_node(container)

        if not container_node:
            return

        self.transfer_node_connections(placeholder_node, container_node)

    def _resolve_container_node(self, container: dict | str) -> str:
        """Extract the Harmony node identifier from a loaded container."""
        if isinstance(container, dict):
            return container.get("objectName") or container.get("name") or ""
        return str(container)

    def transfer_node_connections(
        self,
        source_node: str,
        target_node: str,
    ) -> None:
        """Transfer all input and output connections from source to target node.

        Args:
            source_node (str): Full Harmony path of the placeholder node.
            target_node (str): Full Harmony path of the loaded container node.
        """
        sig = harmony.signature()
        func = """function %s(args)
        {
            var coord_x = node.coordX(args[0]);
            var coord_y = node.coordY(args[0]);
            node.setCoord(args[1], coord_x, coord_y);
            
            var numIn = node.numberOfInputPorts(args[0]);
            for (var i = 0; i < numIn; i++) {
                var src = node.srcNode(args[0], i);
                node.link(src, 0, args[1], i, true, true);
            }
            var numOut = node.numberOfOutputPorts(args[0]);
            if (numOut != 0) {for (var i = 0; i < numOut; i++) {
                var numLinked = node.numberOfOutputLinks(args[0], i);
                for (var j = 0; j < numLinked; j++){
                    var dst = node.dstNode(args[0], i, j);
                    node.link(args[1], i, dst, 0, true, true);
                    }
                }
            }
        }
        %s
        """ % (sig, sig)
        harmony.send({"function": func, "args": [source_node, target_node]})
