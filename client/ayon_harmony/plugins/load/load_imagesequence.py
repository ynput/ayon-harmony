# -*- coding: utf-8 -*-
"""Loader for image sequences and single images."""
import os
import uuid
from pathlib import Path

import clique

from ayon_core.pipeline import load
from ayon_core.pipeline import get_representation_path
from ayon_core.pipeline.context_tools import is_representation_from_latest
import ayon_harmony.api as harmony


class ImageSequenceLoader(load.LoaderPlugin):
    """Load single image or image sequence.

    Stores the imported product in a container named after the product.
    Single images use the OpenHarmony importImageFile API; sequences use
    the ImageSequenceLoader READ-node pipeline.
    """

    label = "Load Image or Sequence"
    product_types = {
        "shot",
        "render",
        "image",
        "plate",
        "reference",
        "review",
    }
    representations = {"*"}
    extensions = {"jpeg", "png", "jpg"}
    settings_category = "harmony"
    expose_only_current_frame = False

    def load(self, context, name=None, namespace=None, data=None):
        """Plugin entry point.

        Args:
            context (:class:`pyblish.api.Context`): Context.
            name (str, optional): Container name.
            namespace (str, optional): Container namespace.
            data (dict, optional): Additional data passed into loader.

        """
        fname = Path(self.filepath_from_context(context))
        self_name = self.__class__.__name__
        collections, remainder = clique.assemble(
            os.listdir(fname.parent.as_posix())
        )
        files = []
        if collections:
            for f in list(collections[0]):
                files.append(fname.parent.joinpath(f).as_posix())
        else:
            if remainder:
                files.append(fname.parent.joinpath(remainder[0]).as_posix())
        if not files and fname.is_file():
            files = [fname.as_posix()]

        folder_name = context["folder"]["name"]
        product_name = context["product"]["name"]

        if len(files) == 1:
            # Single image: use ImageLoader JS API (OpenHarmony).
            image_node = harmony.send(
                {
                    "function": "AyonHarmony.importImageFile",
                    "args": [
                        files[0],
                        self.expose_only_current_frame,
                    ],
                }
            )["result"]
            result = harmony.containerise(
                name,
                namespace,
                image_node,
                context,
                self_name,
                nodes=[image_node],
            )
            harmony.imprint(image_node, {"image_mode": "single"})
            return result
        else:
            # Sequence: use ImageSequenceLoader JS API.
            group_id = str(uuid.uuid4())
            read_node = harmony.send(
                {
                    "function": "AyonHarmony.Loaders.ImageSequenceLoader.importFiles",  # noqa: E501
                    "args": [files, folder_name, product_name, 1, group_id],
                }
            )["result"]
            result = harmony.containerise(
                name,
                namespace,
                read_node,
                context,
                self_name,
                nodes=[read_node],
            )
            harmony.imprint(read_node, {"image_mode": "sequence"})
            return result

    def update(self, container, context):
        """Update loaded containers.

        Args:
            container (dict): Container data.
            context (dict): Representation context data.

        """
        if not (nodes := container.get("nodes")):
            return

        node = nodes[-1]
        repre_entity = context["representation"]
        path = Path(self.filepath_from_context(context))

        if container.get("image_mode") == "single":
            single_path = Path(get_representation_path(repre_entity))
            harmony.send(
                {
                    "function": "AyonHarmony.replaceImageFile",
                    "args": [node, single_path.as_posix()],
                }
            )
            harmony.imprint(node, {"representation": repre_entity["id"]})
            return

        collections, remainder = clique.assemble(os.listdir(path.parent))
        files = []
        if collections:
            for f in list(collections[0]):
                files.append(path.parent.joinpath(f).as_posix())
        else:
            if remainder:
                files.append(path.parent.joinpath(remainder[0]).as_posix())
        if not files and path.is_file():
            files = [path.as_posix()]

        harmony.send(
            {
                "function": "AyonHarmony.Loaders.ImageSequenceLoader.replaceFiles",  # noqa: E501
                "args": [files, node, 1],
            }
        )

        if is_representation_from_latest(repre_entity):
            harmony.send(
                {
                    "function": "AyonHarmony.setColor",
                    "args": [node, [0, 255, 0, 255]],
                }
            )
        else:
            harmony.send(
                {
                    "function": "AyonHarmony.setColor",
                    "args": [node, [255, 0, 0, 255]],
                }
            )

        harmony.imprint(node, {"representation": repre_entity["id"]})

    def remove(self, container):
        """Remove loaded container.

        Args:
            container (dict): Container data.

        """
        if not (nodes := container.get("nodes")):
            return
        node = nodes[-1]
        harmony.imprint(node, {}, remove=True)
        harmony.send({"function": "AyonHarmony.deleteNode", "args": [node]})

    def switch(self, container, context):
        """Switch loaded representations."""
        self.update(container, context)
