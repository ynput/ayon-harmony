from pathlib import Path
import shutil

from ayon_core.pipeline import (
    load,
    get_representation_path,
)
import ayon_harmony.api as harmony


class LinkPaletteLoader(load.LoaderPlugin):
    """Link a palette.

    Link the palette to the scene.
    """

    label = "Link Palette"
    product_types = {"palette", "harmony.palette"}
    representations = {"plt"}
    icon = "link"

    def load(self, context, name=None, namespace=None, data=None):
        representation = context["representation"]
        palette_path = self.load_palette(get_representation_path(representation))

        product_name = representation["context"]["product"]["name"]
        name = product_name.replace("palette", "")

        return harmony.containerise(
            name,
            namespace,
            # Because of sh*tty Harmony API, the only consistent value is the palette path
            # palette["id"] changes at every file opening and the index can be modified by user
            palette_path,
            context,
            self.__class__.__name__,
            nodes=[palette_path],
        )

    def load_palette(self, palette_path: str) -> str:
        """Link the palette to the scene.

        Args:
            palette_path (str): Path to the palette.

        Returns:
            str: Palette path.
        """
        harmony.send(
            {
                "function": "PaletteObjectManager.getScenePaletteList().addPalette",
                "args": Path(palette_path).with_suffix("").as_posix(),
            }
        )["result"]
        return palette_path

    def remove(self, container)->int:
        """Remove the palette from the scene.
        
        Args:
            container (dict): Container data.
            
        Returns:
            int: Removed palette index.
        """
        palette_path = container["nodes"][0]
        removed_idx = harmony.send(
            {"function": "AyonHarmony.removePaletteByPath", "args": palette_path}
        )["result"]
        harmony.remove(palette_path)

        return removed_idx
        
    def switch(self, container, context):
        palette_idx = self.remove(container)
        palette_path = self.load(context)

        # Move loaded palette to the index of the removed one
        harmony.send(
            {"function": "AyonHarmony.movePaletteToIndex", "args": [palette_path, palette_idx]}
        )

    def update(self, container, context):
        self.switch(container, context)


class ImportPaletteLoader(LinkPaletteLoader):
    """Import a palette.

    Copy the palette to the scene directory and link it.
    """

    label = "Import Palette"
    representations = {"plt"}
    icon = "gift"
    order = 0.1

    def load_palette(self, palette_path: str) -> str:
        """Import the palette to the scene.

        Copy the palette to the scene directory and link it.

        Args:
            palette_path (str): Path to the palette.

        Returns:
            str: Palette ID.
        """
        scene_path = harmony.send({"function": "scene.currentProjectPath"})["result"]

        dst = Path(
            scene_path,
            "palette-library",
            Path(palette_path).name,
        )

        self.log.info(f"Copying palette to {dst}")
        shutil.copy(palette_path, dst)

        return super().load_palette(dst.as_posix())
