# -*- coding: utf-8 -*-
"""Base collector for Harmony renders."""
from pathlib import Path

from ayon_core.lib.dateutils import get_formatted_current_time
from ayon_core.pipeline import publish
import ayon_harmony.api as harmony


class CollectRenderBase(publish.AbstractCollectRender):
    """Base collector for Harmony renders."""

    # https://docs.toonboom.com/help/harmony-17/premium/reference/node/output/write-node-image-formats.html
    ext_mapping = {
        "tvg": ["TVG"],
        "tga": ["TGA", "TGA4", "TGA3", "TGA1"],
        "sgi": ["SGI", "SGI4", "SGA3", "SGA1", "SGIDP", "SGIDP4", "SGIDP3"],
        "psd": ["PSD", "PSD1", "PSD3", "PSD4", "PSDDP", "PSDDP1", "PSDDP3", "PSDDP4"],
        "yuv": ["YUV"],
        "pal": ["PAL"],
        "scan": ["SCAN"],
        "png": ["PNG", "PNG4", "PNGDP", "PNGDP3", "PNGDP4"],
        "jpg": ["JPG"],
        "bmp": ["BMP", "BMP4"],
        "opt": ["OPT", "OPT1", "OPT3", "OPT4"],
        "var": ["VAR"],
        "tif": ["TIF"],
        "dpx": [
            "DPX",
            "DPX3_8",
            "DPX3_10",
            "DPX3_12",
            "DPX3_16",
            "DPX3_10_INVERTED_CHANNELS",
            "DPX3_12_INVERTED_CHANNELS",
            "DPX3_16_INVERTED_CHANNELS",
        ],
        "exr": ["EXR"],
        "pdf": ["PDF"],
        "dtext": ["DTEX"],
    }

    def get_instances(self, context):
        """Get instances per Write node."""
        version = None
        if self.sync_workfile_version:
            version = context.data["version"]

        folder_path = context.data["folderPath"]
        instances = []

        for instance in context:
            # Check if instance should be processed
            if not self.check_process_instance(instance):
                continue

            # Get creator attributes for render target
            creator_attributes = instance.data.get("creator_attributes", {})
            render_target = creator_attributes.get("render_target", "default")

            # Create families list
            families = ["render", f"render.{render_target}", "review"]

            # Create render instance
            render_instance = self.create_render_instance(
                context=context,
                source_instance=instance,
                node=instance.data["transientData"]["node"],
                version=version,
                folder_path=folder_path,
                frame_start=instance.data.get(
                    "frameStart", context.data.get("frameStart")
                ),
                frame_end=instance.data.get("frameEnd", context.data.get("frameEnd")),
                handle_start=instance.data.get(
                    "handleStart", context.data.get("handleStart")
                ),
                handle_end=instance.data.get(
                    "handleEnd", context.data.get("handleEnd")
                ),
                product_name=instance.data["productName"],
                product_type="render",
                task=instance.data.get("task"),
                families=families,
            )

            if render_instance:
                self.log.debug(f"Creating render instance: {render_instance}")

                instances.append(render_instance)

        return instances

    def check_process_instance(self, instance):
        """Check if instance should be processed.

        Args:
            instance (pyblish.api.Instance): Instance to check

        Returns:
            bool: True if instance should be processed
        """
        if (
            not instance.data.get("active", True)
            or instance.data.get("productType") != "render"
        ):
            return False
        return True

    def create_render_instance(
        self,
        context,
        node,
        version,
        folder_path,
        frame_start,
        frame_end,
        handle_start,
        handle_end,
        product_name,
        product_type,
        task,
        enable=True,
        families=None,
        skip_review=False,
        source_instance=None,
    ) -> publish.RenderInstance:
        """Create a render instance with common Harmony settings.

        Args:
            context (pyblish.api.Context): Current context
            node (str): Node name
            version (int): Version number
            folder_path (str): Folder path of the rendered asset
            frame_start (int): Start frame
            frame_end (int): End frame
            handle_start (int): Start handle
            handle_end (int): End handle
            product_name (str): Name of the product
            product_type (str): Type of the product
            task (str, optional): Task name
            enable (bool): Whether the node is set to publish
            families (list, optional): List of families. Defaults to None
            skip_review (bool): Explicitly skip review
            source_instance (pyblish.api.Instance, optional): Source instance.
                Defaults to None

        Returns:
            RenderInstance: Created render instance
        """
        self.log.debug(
            f"Creating render instance for {product_name} with frame_start: {frame_start}, frame_end: {frame_end}, handle_start: {handle_start}, handle_end: {handle_end}"
        )
        return publish.RenderInstance(
            version=version,
            time=get_formatted_current_time(),
            source=context.data["currentFile"],
            name=product_name,
            label="{} - {}".format(product_name, product_type),
            productName=product_name,
            productType=product_type,
            family=product_type,
            families=families or [],
            folderPath=folder_path,
            task=task,
            attachTo=False,
            setMembers=[node],
            publish=enable,
            renderer=None,
            priority=50,
            resolutionWidth=context.data["resolutionWidth"],
            resolutionHeight=context.data["resolutionHeight"],
            pixelAspect=1.0,
            multipartExr=False,
            tileRendering=False,
            tilesX=0,
            tilesY=0,
            convertToScanline=False,
            frameStart=frame_start,
            frameEnd=frame_end,
            handleStart=handle_start,
            handleEnd=handle_end,
            frameStep=1,
            review=not skip_review,
            source_instance=source_instance,
        )

    def get_expected_files(self, render_instance):
        """Get list of expected files to be rendered from Harmony.

        This returns full path with file name determined by Write node
        settings.
        """
        start = render_instance.frameStart - render_instance.handleStart
        end = render_instance.frameEnd + render_instance.handleEnd
        node = render_instance.setMembers[0]

        # 0 - filename / 1 - type / 2 - zeros / 3 - start
        info = harmony.send(
            {"function": "AyonHarmony.getRenderNodeSettings", "args": node}
        )["result"]

        ext = None
        for k, v in self.ext_mapping.items():
            if info[1] in v:
                ext = k

        if not ext:
            raise AssertionError(f"Cannot determine file extension for {info[1]}")

        path = Path(render_instance.source).parent
        expected_files = []

        # '-' in name is important for Harmony17
        for frame in range(start, end + 1):
            expected_files.append(
                path
                / "{}-{}.{}".format(
                    render_instance.productName,
                    str(frame).rjust(int(info[2]) + 1, "0"),
                    ext,
                )
            )
        self.log.debug("expected_files::{}".format(expected_files))
        return expected_files
