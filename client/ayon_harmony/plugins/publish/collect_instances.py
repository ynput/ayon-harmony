# -*- coding: utf-8 -*-
"""Collect instances in Harmony."""
import json

import pyblish.api


class CollectInstances(pyblish.api.InstancePlugin):
    """Gather instances by nodes metadata.

    This collector takes into account assets that are associated with
    a composite node and marked with a unique identifier.
    """

    label = "Instances"
    order = pyblish.api.CollectorOrder
    hosts = ["harmony"]

    product_type_mapping = {
        "render": ["review"],
        "harmony.template": [],
        "palette": ["palette"]
    }
    pair_media = True

    def process(self, instance: pyblish.api.Instance):

        # skip render farm product type as it is collected separately
        product_type = instance.data["productType"]
        if product_type == "workfile":
            return

        node = instance.data["transientData"]["node"]

        instance.data["setMembers"] = [node]

        families = [product_type]
        families.extend(self.product_type_mapping.get(product_type, []))
        if product_type == "render":
            creator_attributes = instance.data.get("creator_attributes", {})
            render_target = creator_attributes["render_target"]
            families.append(f"render.{render_target}")

        instance.data["families"] = families

        # If set in plugin, pair the scene Version with
        # thumbnails and review media.
        if (self.pair_media and product_type == "scene"):
            instance.context.data["scene_instance"] = instance

        # Produce diagnostic message for any graphical
        # user interface interested in visualising it.
        self.log.info(
            "Processed: \"{0}\": \n{1}".format(
                instance.data["name"], json.dumps(instance.data, indent=4)
            )
        )