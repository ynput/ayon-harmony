# -*- coding: utf-8 -*-
"""Converter for legacy Harmony products."""
from ayon_core.pipeline.create.creator_plugins import ProductConvertorPlugin
import ayon_harmony.api as harmony


class HarmonyLegacyConvertor(ProductConvertorPlugin):
    """Find and convert any legacy products in the scene.

    This Converter will find all legacy products in the scene and will
    transform them to the current system. Since the old products doesn't
    retain any information about their original creators, the only mapping
    we can do is based on their product types.

    Its limitation is that you can have multiple creators creating product
    of the same product type and there is no way to handle it. This code
    should nevertheless cover all creators that came with OpenPype.

    """
    identifier = "io.ayon.creators.harmony.legacy"
    product_type_to_id = {
        "render": "io.ayon.creators.harmony.render",
        "renderFarm": "io.ayon.creators.harmony.render",
        "template": "io.ayon.creators.harmony.template",
        "workfile": "io.ayon.creators.harmony.workfile",
    }

    def __init__(self, *args, **kwargs):
        super(HarmonyLegacyConvertor, self).__init__(*args, **kwargs)
        self.legacy_instances = {}
        self.scene_metadata = {}

    def find_instances(self):
        """Find legacy products in the scene.

        Legacy products are the ones that doesn't have `creator_identifier`
        parameter on them.

        This is using cached entries done in
        :py:meth:`~HarmonyCreatorBase.cache_instance_data()`

        """
        self.legacy_instances = self.collection_shared_data.get(
            "harmony_cached_legacy_instances_names")
        if not self.legacy_instances:
            return
        # harmony_cached_scene_data is not accessible in `convert` directly
        self.scene_metadata = self.collection_shared_data.get(
            "harmony_cached_scene_data")
        self.add_convertor_item(
            "Found {} incompatible product{}".format(
                len(self.legacy_instances),
                "s" if len(self.legacy_instances) > 1 else ""
            )
        )

    def convert(self):
        """Convert all legacy products to current.

        It is enough to add `creator_identifier` and `instance_node`.

        """
        if not self.legacy_instances:
            return

        for product_type, node_names in self.legacy_instances.items():
            if product_type in self.product_type_to_id:
                for node_name in node_names:
                    creator_identifier = self.product_type_to_id[product_type]
                    self.log.info(
                        "Converting {} to {}".format(node_name,
                                                     creator_identifier)
                    )
                    changed_data = {
                        "creator_identifier": creator_identifier,
                        "id": "ayon.create.instance",
                        "creator_attributes": {"render_target": "local"}
                    }
                    if product_type == "renderFarm":
                        node_meta = self.scene_metadata[node_name]
                        changed_data["productType"] = "render"
                        changed_data["productName"] = (
                            node_meta["productName"].replace("Farm", ""))
                        changed_data["creator_attributes"]["render_target"] = \
                            "farm"

                    harmony.imprint(node_name, data=changed_data)
