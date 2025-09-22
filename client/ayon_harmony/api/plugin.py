import re

from ayon_core.lib import BoolDef, EnumDef
from ayon_core.pipeline import (
    Creator,
    AYON_INSTANCE_ID,
    AVALON_INSTANCE_ID,
    CreatedInstance,
    CreatorError,
    AutoCreator
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

            # Collect scene data once instead of calling `read()` per node
            scene_data = harmony.get_scene_data()
            all_top_names = harmony.get_all_top_names()
            cleaned_scene_data = False
            for entity_name, entity_data in reversed(scene_data.copy().items()):
                # Filter orphaned instances
                if entity_name not in all_top_names:
                    del scene_data[entity_name]
                    cleaned_scene_data = True
                    continue

                if entity_data.get("id") not in {
                    AYON_INSTANCE_ID, AVALON_INSTANCE_ID
                }:
                    continue

                creator_id = entity_data.get("creator_identifier")
                if creator_id is not None:
                    # creator instance
                    cache.setdefault(creator_id, []).append(entity_name)
                else:
                    # legacy instance
                    product_type = entity_data.get(
                        "productType") or entity_data.get("family")

                    if product_type is None:
                        # must be a broken instance
                        continue

                    cache_legacy.setdefault(product_type, []).append(entity_name)

            shared_data["harmony_cached_scene_data"] = scene_data
            shared_data["harmony_cached_instance_data"] = cache
            shared_data["harmony_cached_legacy_instances_names"] = cache_legacy

            # Update scene data if cleaned
            if cleaned_scene_data:
                harmony.set_scene_data(scene_data)

        return shared_data


class HarmonyCreator(Creator, HarmonyCreatorBase):
    """Creator plugin to create instances in Harmony.

    By default a Composite node is created to support any number of nodes in
    an instance, but any node type is supported.
    If the selection is used, the selected nodes will be connected to the
    created node.
    """

    settings_category = "harmony"

    def create(self, product_name, instance_data, pre_create_data):
        # Create the node
        node = self.product_impl(product_name, instance_data, pre_create_data)

        instance = CreatedInstance(
            self.product_type,
            product_name,
            instance_data,
            self
        )
        instance.transient_data["node"] = node
        harmony.imprint(node, instance.data_to_store())

        self._add_instance_to_context(instance)

        return instance

    def update_instances(self, update_list):
        for created_inst, _changes in update_list:
            node = created_inst.transient_data["node"]
            new_data = created_inst.data_to_store()

            # Use the node's active state to store the instance's active state
            active = new_data.pop("active", True)
            harmony.send(
                {"function": "AyonHarmonyAPI.setState",
                 "args": [[node], [active]]}
            )

            harmony.imprint(node, new_data)

    def remove_instances(self, instances):
        for instance in instances:
            # There is only ever one workfile instance
            harmony.delete_node(instance.transient_data["node"])
            self._remove_instance_from_context(instance)

    def collect_instances(self):
        cache = self.cache_instance_data(self.collection_shared_data)
        for node_name in cache.get("harmony_cached_instance_data").get(
                self.identifier, []):
            data = cache.get("harmony_cached_scene_data")[node_name]

            product_type = data.get("productType")
            if product_type is None:
                product_type = data["family"]
                data["productType"] = product_type
            data["family"] = product_type

            instance = CreatedInstance.from_existing(instance_data=data,
                                                     creator=self)
            instance.transient_data["node"] = node_name

            # Active state is based of the node's active state
            instance.data["active"] = harmony.send(
                {"function": "AyonHarmonyAPI.isEnabled", "args": [node_name]}
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

    def product_impl(self, name, instance_data: dict, pre_create_data: dict):
        raise NotImplementedError

    def get_pre_create_attr_defs(self):
        output = [
            BoolDef(
                "use_selection",
                tooltip="Composition for publishable instance should be "
                        "selected by default.",
                default=True,
                label="Use selection"
            ),
        ]
        return output


class HarmonyRenderCreator(HarmonyCreator):
    """Creator plugin to create render instances in Harmony.

    It creates new Composite type node from which it is rendered.
    """
    node_type = "COMPOSITE"
    # should node be auto connected to main Composite node for Harmony Advanced
    auto_connect = False
    # regex to find main Composite node
    composition_node_pattern = ""

    rendering_targets = {
        "local": "Local machine rendering",
        "farm": "Farm rendering",
    }

    def product_impl(self, name, instance_data: dict, pre_create_data: dict):
        existing_node_names = harmony.send(
            {
                "function": "AyonHarmonyAPI.getNodesNamesByType",
                "args": self.node_type
            })["result"]

        # Don't allow instances with the same name.
        name_lower = name.lower()
        for existing_name in existing_node_names:
            if name_lower == existing_name.lower():
                msg = f"Instance with name \"{name}\" already exists."
                raise CreatorError(msg)

        use_selection = pre_create_data.get("use_selection", False)
        if self.auto_connect:
            existing_comp_names = harmony.send(
                {
                    "function": "AyonHarmonyAPI.getNodesNamesByType",
                    "args": "COMPOSITE"
                })["result"]
            name_pattern = self.composition_node_pattern
            if not name_pattern:
                raise CreatorError("Composition name regex pattern "
                                   "must be filled")
            compiled_pattern = re.compile(name_pattern)
            matching_nodes = [name for name in existing_comp_names
                              if compiled_pattern.match(name)]
            if len(matching_nodes) > 1:
                self.log.warning("Multiple composition node found, "
                                 "picked first")
            elif len(matching_nodes) <= 0:
                raise CreatorError("No matching composition "
                                   "node found")
            node_name = f"/Top/{matching_nodes[0]}"

            use_selection = True
            harmony.send(
                {
                    "function": "AyonHarmonyAPI.selectNodes",
                    "args": [node_name]
                }
            )

        node = harmony.send(
            {
                "function": "AyonHarmonyAPI.createNodeContainer",
                "args": [name, self.node_type, use_selection]
            }
        )["result"]
        self.setup_node(node)

        instance_data["creator_attributes"] = {
            "render_target": pre_create_data["render_target"],
            "mark_for_review": pre_create_data["mark_for_review"]
        }

        return node

    def get_pre_create_attr_defs(self):
        output = super().get_pre_create_attr_defs()
        output.extend([
            EnumDef(
                "render_target",
                items=self.rendering_targets,
                label="Render target"
            ),
            BoolDef(
                "mark_for_review",
                label="Review",
                default=True,
            )
        ])
        return output

    def get_instance_attr_defs(self):
        return [
            EnumDef(
                "render_target",
                items=self.rendering_targets,
                label="Render target"
            ),
            BoolDef(
                "mark_for_review",
                label="Review",
                default=True,
            )
        ]


class HarmonyAutoCreator(HarmonyCreatorBase, AutoCreator):

    settings_category = "harmony"
    enabled = True

    def create(self):

        variant = None
        if self.default_variants:
            variant = self.default_variants[0]

        current_instance = next(
            (
                instance for instance in self.create_context.instances
                if instance.creator_identifier == self.identifier
            ), None)

        project_name = self.project_name
        folder_entity = self.create_context.get_current_folder_entity()
        task_entity = self.create_context.get_current_task_entity()
        host_name = self.create_context.host_name

        if current_instance is None:
            product_name = self.get_product_name(
                project_name,
                folder_entity,
                task_entity,
                variant,
                host_name,
            )
            data = {
                "folderPath": folder_entity["path"],
                "task": task_entity["name"],
                "variant": variant
            }
            data.update(
                self.get_dynamic_data(
                    project_name,
                    folder_entity,
                    task_entity,
                    variant,
                    host_name,
                    current_instance)
            )
            if not self.active_on_create:
                data["active"] = False
            self.log.info(f"Auto-creating {self.product_type} instance...")
            current_instance = CreatedInstance(
                self.product_type, product_name, data, self
            )
            self._add_instance_to_context(current_instance)
        elif (
            current_instance["folderPath"] != folder_entity["path"]
            or current_instance["task"] != task_entity["name"]
        ):
            # Update instance context if is not the same
            product_name = self.get_product_name(
                project_name,
                folder_entity,
                task_entity,
                variant,
                host_name,
            )

            current_instance["folderPath"] = folder_entity["path"]
            current_instance["task"] = task_entity["name"]
            current_instance["productName"] = product_name

        current_instance.transient_data["node"] = self._node_name

    def collect_instances(self):
        cache = self.cache_instance_data(self.collection_shared_data)
        for node in cache.get("harmony_cached_instance_data").get(
                self.identifier, []):
            data = cache.get("harmony_cached_scene_data")[node]
            created_instance = CreatedInstance.from_existing(data, self)
            created_instance.transient_data["node"] = self._node_name
            self._add_instance_to_context(created_instance)

    def update_instances(self, update_list):
        for created_inst, _changes in update_list:
            harmony.lib.imprint(self._node_name, created_inst.data_to_store())

    def remove_instances(self, instances):
        for instance in instances:
            scene_data = harmony.lib.get_scene_data()
            scene_data.pop(self._node_name, None)
            harmony.lib.set_scene_data(scene_data)

            self._remove_instance_from_context(instance)
