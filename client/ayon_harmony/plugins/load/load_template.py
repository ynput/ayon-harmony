# -*- coding: utf-8 -*-
"""Load template."""
from pathlib import Path
import tempfile
import zipfile
import shutil

import ayon_harmony.api as harmony

from ayon_core.pipeline import (
    AYON_CONTAINER_ID,
)
import os

log_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "LOG.txt")
log_path = os.path.normpath(log_path)
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

        Write metadata to note node in the backdrop for better tracking of the container and its metadata.

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

        metadata = {
            backdrop_name: {
                "schema": "openpype:container-2.0",
                "id": AYON_CONTAINER_ID,
                "name": backdrop_name,
                "namespace": namespace,
                "loader": str(self_name),
                "representation": context["representation"]["id"],
            }
        }

        harmony.ensure_metadata_in_backdrop(backdrop_name, metadata)

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
