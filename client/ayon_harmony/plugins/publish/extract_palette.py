# -*- coding: utf-8 -*-
"""Extract palette from Harmony."""
import os
import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import ayon_harmony.api as harmony
from ayon_core.pipeline import publish
from ayon_core.pipeline.publish import KnownPublishError


class ExtractPalette(publish.Extractor):
    """Extract palette."""

    label = "Extract Palette"
    hosts = ["harmony"]
    families = ["harmony.palette"]

    def process(self, instance):
        """Plugin entry point."""
        self_name = self.__class__.__name__
        result = harmony.send(
            {
                "function": f"AyonHarmony.Publish.{self_name}.getPalette",
                "args": instance.data["id"]
            })["result"]

        if not isinstance(result, list):
            self.log.error(f"Invalid reply: {result}")
            raise AssertionError("Invalid reply from server.")
        palette_name = result[0]
        palette_file = self._resolve_palette_path(Path(result[1])).as_posix()
        self.log.info(f"Got palette named {palette_name} "
                      f"and file {palette_file}.")

        tmp_thumb_path = os.path.join(os.path.dirname(palette_file),
                                      os.path.basename(palette_file)
                                      .split(".plt")[0] + "_swatches.png"
                                      )
        self.log.info(f"Temporary thumbnail path {tmp_thumb_path}")

        palette_version = str(instance.data.get("version")).zfill(3)

        self.log.info(f"Palette version {palette_version}")

        if not instance.data.get("representations"):
            instance.data["representations"] = []

        try:
            thumbnail_path = self.create_palette_thumbnail(palette_name,
                                                           palette_version,
                                                           palette_file,
                                                           tmp_thumb_path)
        except OSError as e:
            # FIXME: this happens on Mac where PIL cannot access fonts
            # for some reason.
            self.log.warning("Thumbnail generation failed")
            self.log.warning(e)
        except ValueError:
            self.log.error("Unsupported palette type for thumbnail.")

        else:
            thumbnail = {
                "name": "thumbnail",
                "ext": "png",
                "files": os.path.basename(thumbnail_path),
                "stagingDir": os.path.dirname(thumbnail_path),
                "tags": ["thumbnail"]
            }

            instance.data["representations"].append(thumbnail)

        representation = {
            "name": "plt",
            "ext": "plt",
            "files": os.path.basename(palette_file),
            "stagingDir": os.path.dirname(palette_file)
        }

        instance.data["representations"].append(representation)

    def _resolve_palette_path(self, palette_path: Path) -> Path:
        """Return the palette file path in the current scene.

        Harmony resolves palette paths once when the scene is opened. After
        the workfile is incremented during publish, the resolved path can
        point to the previous workfile folder. The path is then rebuilt from
        the current scene folder.

        Args:
            palette_path (Path): Palette path resolved by Harmony.

        Returns:
            Path: Existing palette file path.

        Raises:
            KnownPublishError: If the palette file does not exist.
        """
        if os.path.exists(palette_path):
            return palette_path

        scene_path = Path(harmony.send(
            {"function": "scene.currentProjectPath"})["result"])
        relative_parts = Path(palette_path).relative_to(
            scene_path.parent).parts[1:]
        scene_palette_path = scene_path.joinpath(*relative_parts)
        if scene_palette_path.exists():
            return scene_palette_path

        raise KnownPublishError(
            f"Palette file '{palette_path}' does not exist in the current "
            f"scene '{scene_path}'."
        )

    def create_palette_thumbnail(self,
                                 palette_name,
                                 palette_version,
                                 palette_path,
                                 dst_path):
        """Create thumbnail for palette file.

        Args:
            palette_name (str): Name of palette.
            palette_version (str): Version of palette.
            palette_path (str): Path to palette file.
            dst_path (str): Thumbnail path.

        Returns:
            str: Thumbnail path.

        """
        colors = {}

        with open(palette_path, newline='') as plt:
            plt_parser = csv.reader(plt, delimiter=" ")
            for i, line in enumerate(plt_parser):
                if i == 0:
                    continue
                while ("" in line):
                    line.remove("")
                # self.log.debug(line)
                if line[0] not in ["Solid"]:
                    raise ValueError("Unsupported palette type.")
                color_name = line[1].strip('"')
                colors[color_name] = {"type": line[0],
                                      "uuid": line[2],
                                      "rgba": (int(line[3]),
                                               int(line[4]),
                                               int(line[5]),
                                               int(line[6])),
                                      }
            plt.close()

        img_pad_top = 80
        label_pad_name = 30
        label_pad_rgb = 580
        swatch_pad_left = 300
        swatch_pad_top = 10
        swatch_w = 120
        swatch_h = 50

        image_w = 800
        image_h = (img_pad_top +
                   (len(colors.keys()) *
                    swatch_h) +
                   (swatch_pad_top *
                    len(colors.keys()))
                   )

        img = Image.new("RGBA", (image_w, image_h), "white")

        # For bg of colors with alpha, create checkerboard image
        checkers = Image.new("RGB", (swatch_w, swatch_h))
        pixels = checkers.load()

        # Make pixels white where (row+col) is odd
        for i in range(swatch_w):
            for j in range(swatch_h):
                if (i + j) % 2:
                    pixels[i, j] = (255, 255, 255)

        draw = ImageDraw.Draw(img)
        # TODO: This needs to be font included with AYON because
        # arial is not available on other platforms then Windows.
        title_font = ImageFont.truetype("arial.ttf", 28)
        label_font = ImageFont.truetype("arial.ttf", 20)

        draw.text((label_pad_name, 20),
                  "{} (v{})".format(palette_name, palette_version),
                  "black",
                  font=title_font)

        for i, name in enumerate(colors):
            rgba = colors[name]["rgba"]
            # @TODO: Fix this so alpha colors are displayed with checkboard
            # if not rgba[3] == "255":
            #     img.paste(checkers,
            #               (swatch_pad_left,
            #                img_pad_top + swatch_pad_top + (i * swatch_h))
            #               )
            #
            #     half_y = (img_pad_top + swatch_pad_top + (i * swatch_h))/2
            #
            #     draw.rectangle((
            #         swatch_pad_left,  # upper LX
            #         img_pad_top + swatch_pad_top + (i * swatch_h), # upper LY
            #         swatch_pad_left + (swatch_w * 2),  # lower RX
            #         half_y),  # lower RY
            #         fill=rgba[:-1], outline=(0, 0, 0), width=2)
            #     draw.rectangle((
            #         swatch_pad_left,  # upper LX
            #         half_y,  # upper LY
            #         swatch_pad_left + (swatch_w * 2),  # lower RX
            #         img_pad_top + swatch_h + (i * swatch_h)),  # lower RY
            #         fill=rgba, outline=(0, 0, 0), width=2)
            # else:

            draw.rectangle((
                swatch_pad_left,  # upper left x
                img_pad_top + swatch_pad_top + (i * swatch_h),  # upper left y
                swatch_pad_left + (swatch_w * 2),  # lower right x
                img_pad_top + swatch_h + (i * swatch_h)),  # lower right y
                fill=rgba, outline=(0, 0, 0), width=2)

            draw.text((label_pad_name, img_pad_top + (i * swatch_h) + swatch_pad_top + (swatch_h / 4)),  # noqa: E501
                      name,
                      "black",
                      font=label_font)

            draw.text((label_pad_rgb, img_pad_top + (i * swatch_h) + swatch_pad_top + (swatch_h / 4)),  # noqa: E501
                      str(rgba),
                      "black",
                      font=label_font)

        draw = ImageDraw.Draw(img)

        img.save(dst_path)
        return dst_path
