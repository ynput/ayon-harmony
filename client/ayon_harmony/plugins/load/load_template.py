# -*- coding: utf-8 -*-
"""Load template."""
from pathlib import Path
import tempfile
import zipfile
import shutil

import ayon_harmony.api as harmony


class TemplateLoader(harmony.BackdropBaseLoader):
    """Load Harmony template as Backdrop container."""

    product_base_types = {"harmony.template"}
    product_types = product_base_types
    representations = {"*"}
    extensions = {"zip"}
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
        zip_file = self.filepath_from_context(context)

        # Override container name
        override_name = ""
        if self.override_name:
            override_name = self.override_name.format(**context)

        parent_backdrop_name = None
        if self.parent_backdrop_matching:
            parent_backdrop_name = self._resolve_parent_backdrop_name(context)

        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        backdrop_name = harmony.send(
            {
                "function": f"AyonHarmony.Loaders.{self_name}.loadContainer",
                # Published tpl name is not consistent, use first found,
                #   must be only one
                "args": [
                    next(Path(temp_dir).glob("*.tpl")).as_posix(),
                    override_name,
                    parent_backdrop_name
                ],
            }
        )["result"]

        # Cleanup the temp directory
        shutil.rmtree(temp_dir)

        # We must validate the group_node
        return harmony.containerise(
            backdrop_name,
            namespace,
            backdrop_name,
            context,
            self_name
        )

    def switch(self, container, context):
        """Switch representation containers."""
        self_name = self.__class__.__name__
        container_name = container["name"]
        container_namespace = container["namespace"]
        backdrop = harmony.find_backdrop_by_name(container_name)

        override_name = ""
        if self.override_name:
            override_name = self.override_name.format(**context)

        parent_backdrop_name = None
        if self.parent_backdrop_matching:
            parent_backdrop_name = self._resolve_parent_backdrop_name(context)

        temp_dir = tempfile.mkdtemp()
        zip_path = self.filepath_from_context(context)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)
        template_path = next(Path(temp_dir).glob("*.tpl")).as_posix()

        # Everything (snapshot, remove, load, restore) in one JS call
        new_backdrop_name = harmony.send(
            {
                "function": "AyonHarmony.switchContainer",
                "args": [
                    backdrop,
                    self_name,
                    template_path,
                    override_name,
                    parent_backdrop_name,
                ],
            }
        )["result"]

        # Cleanup the temp directory
        shutil.rmtree(temp_dir)

        harmony.remove(container_name)
        return harmony.containerise(
            new_backdrop_name,
            container_namespace,
            new_backdrop_name,
            context,
            self_name,
        )
