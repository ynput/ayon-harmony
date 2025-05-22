# -*- coding: utf-8 -*-
"""Collect render instances in Harmony."""

import pyblish.api

from ayon_harmony.api.plugins import publish


class CollectRender(publish.CollectHarmonyRender):
    """Collect render instances from Harmony.

    Create regular render instances based on the ones created within the publisher.
    """

    label = "Collect Render Instances"
    order = pyblish.api.CollectorOrder + 0.01
    hosts = ["harmony"]
    families = ["render"]

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
