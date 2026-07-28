"""Harmony Create Placeholder Plugin."""

import ayon_harmony.api as harmony
from ayon_core.pipeline.workfile.workfile_template_builder import (
    CreatePlaceholderItem,
    PlaceholderCreateMixin,
)

from ayon_harmony.api.workfile_template_builder import HarmonyPlaceholderPlugin


class HarmonyPlaceholderCreatePlugin(
    HarmonyPlaceholderPlugin, PlaceholderCreateMixin
):
    """Workfile template plugin for Harmony "create placeholders"."""

    identifier = "ayon.create.placeholder"
    label = "Harmony Create"

    def populate_placeholder(self, placeholder: CreatePlaceholderItem) -> None:
        """Populate a placeholder by running its configured Creator."""
        self.populate_create_placeholder(placeholder)

    def repopulate_placeholder(
        self, placeholder: CreatePlaceholderItem
    ) -> None:
        """Re-populate an existing create placeholder."""
        self.populate_create_placeholder(placeholder)

    def get_placeholder_options(self, options: dict | None = None) -> list:
        """Return the UI option definitions for the placeholder dialog.

        Args:
            options (dict | None): Existing option values to pre-populate.

        Returns:
            list: Option widget definitions for WorkfileBuildPlaceholderDialog.
        """
        return self.get_create_plugin_options(options)

    def get_placeholder_node_name(self, placeholder_data: dict) -> str:
        """Return a Harmony-safe name for the create placeholder node.

        Returns:
            str: Name derived from the plugin identifier with dots replaced
                by underscores.
        """
        return self.identifier.replace(".", "_")

    def create_placeholder_node(self, node_name: str | None = None) -> str:
        """Create a BurnIn node to act as the create placeholder.

        Returns:
            str: The node identifier for the created READ node.
        """
        name = node_name or self.identifier.replace(".", "_")
        return harmony.send(
            {
                "function": "AyonHarmonyAPI.createNodeContainer",
                "args": [name, "BurnIn", False],
            }
        )["result"]

    def collect_placeholders(self) -> list[CreatePlaceholderItem]:
        """Collect all create placeholder items from the current Harmony scene.

        Returns:
            list[CreatePlaceholderItem]: All create placeholder items found,
                each wrapping the node identifier and its metadata.
        """
        output = []
        for node_id in self.collect_scene_placeholders():
            placeholder_data = self._read(node_id)
            output.append(
                CreatePlaceholderItem(node_id, placeholder_data, self)
            )
        return output
