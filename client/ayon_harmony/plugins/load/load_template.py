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
    override_name = ""

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

        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        backdrop_name = harmony.send(
            {
                "function": f"AyonHarmony.Loaders.{self_name}.loadContainer",
                # Published tpl name is not consistent, use first found,
                #   must be only one
                "args": [
                    next(Path(temp_dir).glob("*.tpl")).as_posix(),
                    override_name
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
