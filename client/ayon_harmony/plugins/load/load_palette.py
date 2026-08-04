from pathlib import Path
import shutil

from ayon_core.pipeline import load

import ayon_harmony.api as harmony


class LinkPaletteLoader(load.LoaderPlugin):
    """Link a palette.

    Link the palette to the scene.
    """

    label = "Link Palette"
    product_base_types = {"palette", "harmony.palette"}
    product_types = product_base_types
    representations = {"*"}
    extensions = {"plt"}
    icon = "link"

    def load(self, context, name=None, namespace=None, data=None):
        representation = context["representation"]
        repre_filepath = self.filepath_from_context(context)
        palette_path = self.load_palette(repre_filepath)

        product_name = representation["context"]["product"]["name"]
        name = product_name.replace("palette", "")

        return harmony.containerise(
            name,
            namespace,
            # Because of sh*tty Harmony API, the only consistent value is
            #   the palette path palette["id"] changes at every file opening
            #   and the index can be modified by user
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
                "function": (
                    "PaletteObjectManager.getScenePaletteList().addPalette"
                ),
                "args": Path(palette_path).with_suffix("").as_posix(),
            }
        )["result"]
        return palette_path

    def remove(self, container) -> int:
        """Remove the palette from the scene.

        Args:
            container (dict): Container data.

        Returns:
            int: Removed palette index.
        """
        palette_path = container["nodes"][0]
        removed_idx = harmony.send(
            {
                "function": "AyonHarmony.removePaletteByPath",
                "args": palette_path,
            }
        )["result"]
        harmony.remove(palette_path)

        return removed_idx

    def switch(self, container, context):
        palette_idx = self.remove(container)
        palette_path = self.load(context)

        # Move loaded palette to the index of the removed one
        harmony.send(
            {
                "function": "AyonHarmony.movePaletteToIndex",
                "args": [palette_path, palette_idx]
            }
        )

    def update(self, container, context):
        self.switch(container, context)


class ImportPaletteLoader(LinkPaletteLoader):
    """Import a palette.

    Copy the palette (and its texture folder, if any) to the scene
    directory and link it.
    """

    label = "Import Palette"
    representations = {"*"}
    extensions = {"plt"}
    icon = "gift"
    order = 0.1

    def load_palette(self, palette_path: str) -> str:
        """Import the palette to the scene.

        Copy the palette (and its texture folder, if present) to the
        scene directory and link it.

        Args:
            palette_path (str): Path to the palette.

        Returns:
            str: Palette ID.
        """
        scene_path = harmony.send(
            {"function": "scene.currentProjectPath"}
        )["result"]

        source_plt = Path(palette_path)
        destination_plt = Path(scene_path, "palette-library", source_plt.name)

        self.log.info(f"Copying palette to {destination_plt}")
        shutil.copy(source_plt, destination_plt)

        source_textures = source_plt.with_name(source_plt.stem + "_textures")
        if source_textures.is_dir():
            destination_textures = destination_plt.with_name(destination_plt.stem + "_textures")
            self.log.info(f"Copying textures to {destination_textures}")
            shutil.copytree(source_textures, destination_textures, dirs_exist_ok=True)
        else:
            self.log.debug(
                f"No texture folder found next to {source_plt}, skipping."
            )

        result = super().load_palette(destination_plt.as_posix())
        return result

    def remove(self, container) -> int:
        """Remove the imported palette from the scene.

        Removes the Harmony palette reference, then deletes the local
        copied .plt file and its texture folder from disk.

        Args:
            container (dict): Container data.

        Returns:
            int: Removed palette index.
        """
        removed_plt = super().remove(container)

        local_plt = Path(container["nodes"][0])

        if local_plt.is_file():
            self.log.info(f"Deleting local palette file {local_plt}")
            local_plt.unlink()
        else:
            self.log.warning(f"Local palette file not found: {local_plt}")

        local_textures = local_plt.with_name(local_plt.stem + "_textures")
        if local_textures.is_dir():
            self.log.info(f"Deleting local texture folder {local_textures}")
            shutil.rmtree(local_textures)
            
        return removed_plt