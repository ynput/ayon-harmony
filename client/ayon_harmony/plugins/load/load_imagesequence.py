# -*- coding: utf-8 -*-
"""Loader for image sequences and single images."""
import os
import uuid
from pathlib import Path

import clique

from ayon_core.pipeline import load
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

    @staticmethod
    def _resolve_files_for_representation(target_path: Path) -> list[str]:
        """Resolve ordered file paths for the sequence containing the path.

        Picks the clique collection that includes the representation file name.
        """
        parent = target_path.parent
        names = os.listdir(parent.as_posix())
        collections, remainder = clique.assemble(names)
        basename = target_path.name
        for coll in collections:
            if basename in coll:
                return [parent.joinpath(f).as_posix() for f in coll]
        if basename in remainder:
            return [parent.joinpath(basename).as_posix()]
        elif target_path.is_file():
            return [target_path.as_posix()]
        else:
            raise RuntimeError(
                "Could not resolve image files for representation path: "
                f"{target_path}"
            )

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
        files = self._resolve_files_for_representation(fname)
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
            harmony.send(
                {
                    "function": "AyonHarmony.replaceImageFile",
                    "args": [node, path.as_posix()],
                }
            )
            harmony.imprint(node, {"representation": repre_entity["id"]})
            return

        files = self._resolve_files_for_representation(path)
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
