# -*- coding: utf-8 -*-
"""Creator plugin for creating workfiles."""
import ayon_api

from ayon_core.pipeline import CreatedInstance, AutoCreator
from ayon_harmony.api import plugin, lib


class CreateWorkfile(plugin.HarmonyCreatorBase, AutoCreator):
    """Workfile auto-creator."""
    identifier = "io.ayon.creators.harmony.workfile"
    label = "Workfile"
    product_type = "workfile"
    icon = "fa5.file"

    default_variant = "Main"

    # Placeholder node name for where we store the workfile data.
    # This does not create an actual Harmony node, but just uses this name
    # as key in the AYON Harmony scene data.
    _node_name = "__workfile__"

    def create(self):

        variant = self.default_variant
        current_instance = next(
            (
                instance for instance in self.create_context.instances
                if instance.creator_identifier == self.identifier
            ), None)

        project_name = self.project_name
        folder_path = self.create_context.get_current_folder_path()
        task_name = self.create_context.get_current_task_name()
        host_name = self.create_context.host_name

        current_folder_path = None
        if current_instance is not None:
            current_folder_path = current_instance["folderPath"]

        if current_instance is None:
            folder_entity = ayon_api.get_folder_by_path(
                project_name, folder_path
            )
            task_entity = ayon_api.get_task_by_name(
                project_name, folder_entity["id"], task_name
            )
            product_name = self.get_product_name(
                project_name,
                folder_entity,
                task_entity,
                variant,
                host_name,
            )
            data = {
                "folderPath": folder_path,
                "task": task_name,
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
            self.log.info("Auto-creating workfile instance...")
            current_instance = CreatedInstance(
                self.product_type, product_name, data, self
            )
            self._add_instance_to_context(current_instance)
        elif (
            current_folder_path != folder_path
            or current_instance["task"] != task_name
        ):
            # Update instance context if is not the same
            folder_entity = ayon_api.get_folder_by_path(
                project_name, folder_path
            )
            task_entity = ayon_api.get_task_by_name(
                project_name, folder_entity["id"], task_name
            )
            product_name = self.get_product_name(
                project_name,
                folder_entity,
                task_entity,
                variant,
                host_name,
            )

            current_instance["folderPath"] = folder_entity["path"]
            current_instance["task"] = task_name
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
            lib.imprint(self._node_name, created_inst.data_to_store())

    def remove_instances(self, instances):
        for instance in instances:
            scene_data = lib.get_scene_data()
            scene_data.pop(self._node_name, None)
            lib.set_scene_data(scene_data)

            self._remove_instance_from_context(instance)