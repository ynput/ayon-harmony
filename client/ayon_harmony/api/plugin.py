from ayon_core.pipeline import (
    Creator, AYON_INSTANCE_ID, AVALON_INSTANCE_ID,
    CreatedInstance
)
import ayon_harmony.api as harmony


class HarmonyCreatorBase:
    @staticmethod
    def cache_instance_data(shared_data):
        """Cache instances for Creators to shared data.

        Create `maya_cached_instance_data` key when needed in shared data and
        fill it with all collected instances from the scene under its
        respective creator identifiers.

        If legacy instances are detected in the scene, create
        `maya_cached_legacy_instances` there and fill it with
        all legacy products under product type as a key.

        Args:
            Dict[str, Any]: Shared data.

        """
        if shared_data.get("harmony_cached_instance_data") is None:
            cache = dict()
            cache_legacy = dict()

            nodes = harmony.send(
                {"function": "node.subNodes", "args": ["Top"]}
            )["result"]
            for node in nodes:
                data = harmony.read(node)

                # Skip non-tagged nodes.
                if not data:
                    continue

                if data.get("id") not in {
                    AYON_INSTANCE_ID, AVALON_INSTANCE_ID
                }:
                    continue

                creator_id = data.get("creator_identifier")
                if creator_id is not None:
                    # creator instance
                    cache.setdefault(creator_id, []).append(node)
                else:
                    # legacy instance
                    family = data.get("family")
                    if family is None:
                        # must be a broken instance
                        continue

                    cache_legacy.setdefault(family, []).append(node)

            shared_data["harmony_cached_instance_data"] = cache
            shared_data["harmony_cached_legacy_instances"] = cache_legacy
        return shared_data


class HarmonyCreator(Creator, HarmonyCreatorBase):
    """Creator plugin to create instances in Harmony.

    By default a Composite node is created to support any number of nodes in
    an instance, but any node type is supported.
    If the selection is used, the selected nodes will be connected to the
    created node.
    """
    node_type = "COMPOSITE"

    settings_category = "harmony"

    def create(self, product_name, instance_data, pre_create_data):
        node = self._create(product_name, instance_data, pre_create_data)
        instance = CreatedInstance(
            self.product_type,
            product_name,
            instance_data,
            self)
        instance.transient_data["node"] = node
        self._add_instance_to_context(instance)

    def update_instances(self, update_list):
        for created_inst, _changes in update_list:
            node = created_inst
            new_data = created_inst.data_to_store()
            harmony.imprint(node, new_data)

    def remove_instances(self, instances):
        for instance in instances:
            harmony.delete_node(instance)
            self._remove_instance_from_context(instance)

    def collect_instances(self):
        data = self.cache_instance_data(self.collection_shared_data)
        for node in data.get("harmony_cached_instance_data").get(
                self.identifier, []):

            product_type = data.get("productType")
            if product_type is None:
                product_type = data["family"]
                data["productType"] = product_type
            data["family"] = product_type

            instance = CreatedInstance.from_existing(instance_data=data,
                                                     creator=self)
            instance.transient_data["node"] = node

            # TODO: Get AND SET the enable state from the node
            instance.data["publish"] = harmony.send(
                {"function": "node.getEnable", "args": [node]}
            )["result"]

            self._add_instance_to_context(instance)

    def setup_node(self, node):
        """Prepare node as container.

        Args:
            node (str): Path to node.
        """
        harmony.send(
            {
                "function": "AyonHarmonyAPI.setupNodeForCreator",
                "args": node
            }
        )

    def _create(self, name, instance_data: dict, pre_create_data: dict):
        existing_node_names = harmony.send(
            {
                "function": "AyonHarmonyAPI.getNodesNamesByType",
                "args": self.node_type
            })["result"]

        # Dont allow instances with the same name.
        msg = "Instance with name \"{}\" already exists.".format(name)
        for name in existing_node_names:
            if name.lower() == name.lower():
                harmony.send(
                    {
                        "function": "AyonHarmonyAPI.message", "args": msg
                    }
                )
                return False

        with harmony.maintained_selection() as selection:

            args = [name, self.node_type]
            if pre_create_data.get("useSelection") and selection:
                args.append(selection[-1])
            node = harmony.send(
                {
                    "function": "AyonHarmonyAPI.createContainer",
                    "args": args
                }
            )["result"]

            harmony.imprint(node, instance_data)
            self.setup_node(node)

        return node
