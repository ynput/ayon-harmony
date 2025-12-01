"""Plugin converting png files from ExtractSequence into exrs.

Requires:
    ExtractSequence - source of PNG
    ExtractReview - review was already created so we can convert to any exr
"""
from __future__ import annotations

import os
import collections
import copy
from typing import Optional

import clique
import pyblish.api

from ayon_core.lib import (
    get_oiio_tool_args,
    ToolNotFoundError,
    run_subprocess,
)
from ayon_core.lib.attribute_definitions import (
    EnumDef,
    BoolDef,
    AbstractAttrDef,
)
from ayon_core.pipeline import PublishError
from ayon_core.pipeline.create import CreateContext, CreatedInstance
from ayon_core.pipeline.publish import (
    AYONPyblishPluginMixin,
    get_plugin_settings,
    apply_plugin_settings_automatically,
)


class CollectExrUserOptions(
    pyblish.api.ContextPlugin,
    AYONPyblishPluginMixin
):
    """Collect data for EXR conversion."""
    order = pyblish.api.CollectorOrder - 0.45
    label = "Collect Sequence EXR"
    hosts = ["harmony"]
    settings_category = "harmony"

    multichannel_exr = False
    user_overrides = []

    @classmethod
    def apply_settings(cls, project_settings):
        plugin_settins = get_plugin_settings(
            ExtractConvertToEXR, project_settings, cls.log, "harmony"
        )
        apply_plugin_settings_automatically(
            cls, plugin_settins, cls.log
        )

    @classmethod
    def register_create_context_callbacks(cls, create_context):
        create_context.add_value_changed_callback(cls._on_value_change)

    @classmethod
    def _on_value_change(cls, event):
        event_data = event.data
        create_context: CreateContext = event_data["create_context"]
        for change in event_data["changes"]:
            instance: Optional[CreatedInstance] = change["instance"]
            if instance is not None:
                continue

            value = change["changes"]
            for key in (
                "publish_attributes",
                cls.__name__,
                "convert_to_exr",
            ):
                value = value.get(key)
                if value is None:
                    break

            if value is not None:
                create_context.set_context_publish_plugin_attr_defs(
                    cls.__name__,
                    cls.get_attr_defs_for_context(create_context)
                )
            break

    @classmethod
    def get_attr_defs_for_context(
        cls, create_context: CreateContext
    ) -> list[AbstractAttrDef]:
        has_create_exr = "create_exr" in cls.user_overrides
        has_multichannel_exr = "multichannel_exr" in cls.user_overrides

        if not has_create_exr and not has_multichannel_exr:
            return []

        items = []
        if has_create_exr:
            items.append({"value": "skip_exr", "label": "No conversion"})

        default = "create_exr"
        items.append({"value": "create_exr", "label": "Create EXR"})
        if has_multichannel_exr:
            items.append({
                "value": "multichannel_exr",
                "label": "Create multichannel EXR"
            })
            if cls.multichannel_exr:
                default = "multichannel_exr"

        attr_defs: list[AbstractAttrDef] = [
            EnumDef(
                "convert_to_exr",
                label="Convert to EXR",
                items=items,
                default=default,
                tooltip="Convert PNGs to EXR",
            )
        ]
        current_value = (
            create_context
            .publish_attributes
            .get(cls.__name__, {})
            .get("convert_to_exr")
        )
        if current_value is None:
            current_value = default

        if (
            current_value == "multichannel_exr"
            and "keep_passes" in cls.user_overrides
        ):
            attr_defs.append(
                BoolDef(
                    "keep_passes",
                    default=False,
                    label="Keep render passes",
                )
            )

        return attr_defs

    def process(self, context):
        attr_values = self.get_attr_values_from_data(context.data)
        context.data["convertExrData"] = {
            "user_value": attr_values.get("convert_to_exr"),
            "keep_passes": attr_values.get("keep_passes"),
        }


class ExtractConvertToEXR(pyblish.api.ContextPlugin):
    # Offset to get after ExtractSequence plugin.
    order = pyblish.api.ExtractorOrder + 0.1
    label = "Extract Sequence EXR"
    hosts = ["harmony"]
    # This won't work on farm
    # - this plugin requires having render layer and all related render pass
    #   instances in a single publishing process which does not happen on farm
    #   where each instance has own publish job
    targets = ["local"]

    settings_category = "harmony"

    enabled = False

    # Replace source PNG files or just add
    replace_pngs = True
    # EXR compression
    auto_trim = True
    exr_compression = "ZIP"
    multichannel_exr = False
    keep_passes = False

    user_overrides = []

    def process(self, context):
        exr_data = context.data["convertExrData"]
        exr_user_value = exr_data["user_value"]
        keep_passes = exr_data["keep_passes"]
        # Skip if is set to be skipped
        if exr_user_value == "skip_exr":
            self.log.info(
                "EXR conversion is disabled with attributes. Skipping."
            )
            return

        # Change value to multichannel if user can change only if exr
        #   happens or not.
        if (
            exr_user_value == "create_exr"
            and "multichannel_exr" not in self.user_overrides
            and self.multichannel_exr
        ):
            exr_user_value = "multichannel_exr"

        # User value is not filled (because the user can't change it)
        if exr_user_value is None:
            exr_user_value = "create_exr"
            if self.multichannel_exr:
                exr_user_value = "multichannel_exr"

        if keep_passes is None or "keep_passes" not in self.user_overrides:
            keep_passes = self.keep_passes

        render_layer_items = []
        render_pass_items = []
        for instance in context:
            if instance.data.get("publish") is False:
                continue

            if instance.data["family"] != "render":
                continue

            if instance.data.get("farm"):
                self.log.debug(
                    "Skipping instance, is marked for farm rendering."
                )
                continue

            repres = instance.data.get("representations") or []
            src_repre = next(
                (
                    repre
                    for repre in repres
                    if repre["name"] == "png"
                ),
                None
            )
            if not src_repre:
                self.log.debug("Skipping instance, no PNG representation.")
                continue

            creator_identifier = instance.data.get("creator_identifier")
            if creator_identifier == "render.layer":
                render_layer_items.append((instance, src_repre))
            elif creator_identifier == "render.pass":
                render_pass_items.append((instance, src_repre))

        if not render_layer_items and not render_pass_items:
            return

        try:
            base_oiio_args = get_oiio_tool_args("oiiotool")
        except ToolNotFoundError:
            # Raise an exception when oiiotool is not available
            # - this can currently happen on MacOS machines
            raise PublishError(
                "OpenImageIO tool is not available on this machine."
            )

        simple_items = []
        if exr_user_value == "multichannel_exr":
            self._multichannel_exr_conversion(
                render_layer_items,
                render_pass_items,
                base_oiio_args,
                keep_passes,
            )
            if keep_passes:
                simple_items = render_pass_items
        else:
            simple_items = render_layer_items + render_pass_items

        for item in simple_items:
            instance, src_repre = item
            self._simple_exr_conversion(
                instance, src_repre, base_oiio_args
            )

    def _simple_exr_conversion(
        self, instance, repre, base_oiio_args
    ):
        repres = instance.data["representations"]

        src_filepaths = set()
        new_filenames = []

        output_arg = "-o"
        if self.auto_trim:
            output_arg = "-o:autotrim=1"
        for src_filename in repre["files"]:
            dst_filename = os.path.splitext(src_filename)[0] + ".exr"
            new_filenames.append(dst_filename)

            src_filepath = os.path.join(repre["stagingDir"], src_filename)
            dst_filepath = os.path.join(repre["stagingDir"], dst_filename)

            src_filepaths.add(src_filepath)

            args = copy.deepcopy(base_oiio_args)
            args.extend([
                src_filepath,
                "--compression", self.exr_compression,
                "-d", "uint8",
                output_arg, dst_filepath
            ])
            run_subprocess(args)

        repres.append(
            {
                "name": "exr",
                "ext": "exr",
                "files": new_filenames,
                "stagingDir": repre["stagingDir"],
                "tags": list(repre["tags"])
            }
        )

        if self.replace_pngs:
            instance.data["representations"].remove(repre)

            for filepath in src_filepaths:
                instance.context.data["cleanupFullPaths"].append(filepath)

    def _multichannel_exr_conversion(
        self,
        render_layer_items,
        render_pass_items,
        base_oiio_args,
        keep_passes,
    ):
        render_pass_items_by_layer_id = collections.defaultdict(list)
        for (instance, repre) in render_pass_items:
            creator_attributes = instance.data["creator_attributes"]
            render_layer_id = creator_attributes[
                "render_layer_instance_id"
            ]
            render_pass_items_by_layer_id[render_layer_id].append(
                (instance, repre)
            )

        for (render_layer_instance, src_layer_repre) in render_layer_items:
            render_layer_id = render_layer_instance.data["instance_id"]
            render_pass_items = render_pass_items_by_layer_id[
                render_layer_id
            ]

            layer_staging_dir = src_layer_repre["stagingDir"]
            layer_filename = src_layer_repre["files"]
            is_sequence = isinstance(layer_filename, list)
            dst_filename = None
            padding = frame_start = frame_end = None
            if is_sequence:
                cols, _ = clique.assemble(layer_filename)
                col = cols[0]
                padding = col.padding
                frame_start = min(col.indexes)
                frame_end = max(col.indexes)
                layer_filename = col.format("{head}#{tail}")

                # Prepare the destination filename for sequences
                template = col.format("{head}{padding}{tail}")
                template = os.path.splitext(template)[0] + ".exr"
                dst_filename = [
                    template % idx
                    for idx in col.indexes
                ]

            basename, _ = os.path.splitext(layer_filename)
            new_filename = f"{basename}.exr"
            if not is_sequence:
                dst_filename = new_filename

            dst_path = os.path.join(layer_staging_dir, new_filename)

            # Prepare the arguments for the oiio tool
            src_beauty_path = os.path.join(layer_staging_dir, layer_filename)

            args = copy.deepcopy(base_oiio_args)
            args.append("-no-autopremult")
            if padding is not None:
                args.extend([
                    "--frames", f"{frame_start}-{frame_end}",
                    "--framepadding", str(padding),
                ])

            args.extend([
                "-i", src_beauty_path,
                "--ch", "R,G,B,A",
            ])

            for (render_pass_instance, pass_repre) in render_pass_items:
                product_name = render_pass_instance.data["productName"]
                pass_filename = pass_repre["files"]
                if isinstance(pass_filename, list):
                    cols, _ = clique.assemble(pass_filename)
                    col = cols[0]
                    pass_filename = col.format("{head}#{tail}")
                pass_staging_dir = pass_repre["stagingDir"]
                path = os.path.join(pass_staging_dir, pass_filename)
                # Add the render pass representation
                channel_names = [f"{product_name}.{ch_n}" for ch_n in "RGBA"]
                args.extend([
                    "-i", path,
                    "--chnames", ",".join(channel_names),
                    "--chappend",
                ])

            output_arg = "-o"
            if self.auto_trim:
                output_arg = "-o:autotrim=1"

            args.extend([
                "--compression", self.exr_compression,
                "-d", "uint8",
                output_arg, dst_path,
            ])
            self.log.debug("Running oiiotool with args: %s", args)
            run_subprocess(args)

            layer_repres = render_layer_instance.data["representations"]
            layer_repres.append(
                {
                    "name": "exr",
                    "ext": "exr",
                    "files": dst_filename,
                    "stagingDir": layer_staging_dir,
                    "tags": list(src_layer_repre["tags"])
                }
            )
            context = render_layer_instance.context

            # Remove the source representation of the render layer
            if self.replace_pngs:
                layer_repres.remove(src_layer_repre)
                staging_dir = repre["stagingDir"]
                filenames = repre["files"]
                if not isinstance(filenames, list):
                    filenames = [filenames]
                src_filepaths = [
                    os.path.join(staging_dir, filename)
                    for filename in filenames
                ]
                context.data["cleanupFullPaths"].extend(src_filepaths)

            if keep_passes:
                continue

            # Remove render pass instances from the context
            # - Remove all files of all render pass representations and then
            #   the instances.
            for (render_pass_instance, _) in render_pass_items:
                render_pass_instance.data["publish"] = False
                for repre in render_pass_instance.data["representations"]:
                    staging_dir = repre["stagingDir"]
                    filenames = repre["files"]
                    if not isinstance(filenames, list):
                        filenames = [filenames]
                    src_filepaths = [
                        os.path.join(staging_dir, filename)
                        for filename in filenames
                    ]
                    context.data["cleanupFullPaths"].extend(src_filepaths)
                context.remove(render_pass_instance)
