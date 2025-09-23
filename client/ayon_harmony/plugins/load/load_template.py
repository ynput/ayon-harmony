# -*- coding: utf-8 -*-
"""Load template."""
from pathlib import Path
import tempfile
import zipfile
import shutil

import ayon_harmony.api as harmony


class TemplateLoader(harmony.BackdropBaseLoader):
    """Load Harmony template as Backdrop container."""

    product_types = {"harmony.template"}
    representations = {"tpl"}
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

        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        backdrop_name = harmony.send(
            {
                "function": f"AyonHarmony.Loaders.{self_name}.loadContainer",
                # Published tpl name is not consistent, use first found,
                #   must be only one
                "args": next(Path(temp_dir).glob("*.tpl")).as_posix(),
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
