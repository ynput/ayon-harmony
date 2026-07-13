# -*- coding: utf-8 -*-
"""Base classes for loaders."""

from pathlib import Path
from ayon_core.pipeline import load

import ayon_harmony.api as harmony


class BackdropBaseLoader(load.LoaderPlugin):
    """Load nodes into a backdrop.

    Uses shared 'override_name' from harmony load settings (see
    HarmonyLoadPlugins.override_name).
    """

    override_name = ""
    parent_backdrop_matching = False

    @classmethod
    def apply_settings(cls, project_settings):
        super().apply_settings(project_settings)
        load_settings = (
            project_settings.get("harmony", {}).get("load", {})
        )
        cls.override_name = load_settings.get("override_name", "")
        cls.parent_backdrop_matching = load_settings.get(
            "parent_backdrop_matching", False
        )

    def _resolve_parent_backdrop_name(self, context) -> str:
        """Resolve parent backdrop name from folder hierarchy.

        Returns matching existing backdrop name (case-insensitive) or the
        most direct folder segment for backdrop creation when there is no
        existing match.
        """

        folder_path = (context.get("folder") or {}).get("path")
        # Without root "/" neither folder name
        hierarchy = Path(folder_path).parts[1:-1]
        if not hierarchy:
            return None

        scene_backdrops = harmony.send(
            {"function": "Backdrop.backdrops", "args": ["Top"]}
        )["result"]

        lower_to_original = {}
        for backdrop in scene_backdrops:
            title = backdrop.get("title", {}).get("text")
            if title and title.lower() not in lower_to_original:
                lower_to_original[title.lower()] = title

        for segment in reversed(hierarchy):
            matched_name = lower_to_original.get(segment.lower())
            if matched_name:
                return matched_name

        return hierarchy[-1]

    def load(self, context, name=None, namespace=None, data=None):
        """Plugin entry point.

        Args:
            context (:class:`pyblish.api.Context`): Context.
            name (str, optional): Container name.
            namespace (str, optional): Container namespace.
            data (dict, optional): Additional data passed into loader.

        """
        self_name = self.__class__.__name__
        filepath = self.filepath_from_context(context)

        # Override container name from shared setting
        if self.override_name:
            name = self.override_name.format(**context)

        parent_backdrop_name = None
        if self.parent_backdrop_matching:
            parent_backdrop_name = self._resolve_parent_backdrop_name(context)

        backdrop_name = harmony.send(
            {
                "function": f"AyonHarmony.Loaders.{self_name}.loadContainer",
                "args": [filepath, name, parent_backdrop_name],
            }
        )["result"]

        # We must validate the group_node
        return harmony.containerise(
            backdrop_name,
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
