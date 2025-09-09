"""Render Layer and Passes creators.

Render layer is main part which is represented by group in Harmony. All Harmony
layers marked with that group color are part of the render layer. To be more
specific about some parts of layer it is possible to create sub-sets of layer
which are named passes. Render pass consist of layers in same color group as
render layer but define more specific part.

For example render layer could be 'Bob' which consist of 5 Harmony layers.
- Bob has 'head' which consist of 2 Harmony layers -> Render pass 'head'
- Bob has 'body' which consist of 1 Harmony layer -> Render pass 'body'
- Bob has 'arm' which consist of 1 Harmony layer -> Render pass 'arm'
- Last layer does not belong to render pass at all

Bob will be rendered as 'beauty' of bob (all visible layers in group).
His head will be rendered too but without any other parts. The same for body
and arm.

What is this good for? Compositing has more power how the renders are used.
Can do transforms on each render pass without need to modify a re-render them
using Harmony.

The workflow may hit issues when there are used other blending modes than
default 'color' blend more. In that case it is not recommended to use this
workflow at all as other blend modes may affect all layers in clip which can't
be done.

There is special case for simple publishing of scene which is called
'render.scene'. That will use all visible layers and render them as one big
sequence.

Todos:
    Add option to extract marked layers and passes as json output format for
        AfterEffects.
"""

import re
import json
import copy
import collections
from typing import Any, Optional, Union

from ayon_core.lib import (
    prepare_template_data,
    AbstractAttrDef,
    UISeparatorDef,
    EnumDef,
    TextDef,
    BoolDef,
)
from ayon_core.pipeline.create import (
    CreatedInstance,
    CreatorError,
)
from ayon_harmony.api.plugin import HarmonyAutoCreator, HarmonyRenderCreator
import ayon_harmony.api as harmony


RENDER_LAYER_DETAILED_DESCRIPTIONS = """Render Layer is "a group of Harmony layers"

Be aware Render Layer <b>is not</b> Harmony layer.

All Harmony layers in the scene with the color group id are rendered in the
beauty pass. To create sub passes use Render Pass creator which is
dependent on existence of render layer instance.

The group can represent an asset (tree) or different part of scene that consist
of one or more Harmony layers that can be used as single item during
compositing (for example).

In some cases may be needed to have sub parts of the layer. For example 'Bob'
could be Render Layer which has 'Arm', 'Head' and 'Body' as Render Passes.
"""


RENDER_PASS_DETAILED_DESCRIPTIONS = """Render Pass is sub part of Render Layer.

Render Pass can consist of one or more Harmony layers. Render Pass must
belong to a Render Layer. Marked Harmony layers will change it's group color
to match group color of Render Layer.
"""


AUTODETECT_RENDER_DETAILED_DESCRIPTION = """Semi-automated Render Layer and Render Pass creation.

Based on information in Harmony scene will be created Render Layers and Render
Passes. All color groups used in scene will be used for Render Layer creation.
Name of the group is used as a variant.

All Harmony layers under the color group will be created as Render Pass where
layer name is used as variant.

The plugin will use all used color groups and layers, or can skip those that
are not visible.

There is option to auto-rename color groups before Render Layer creation. That
is based on settings template where is filled index of used group from bottom
to top.
"""


class CreateRenderLayer(HarmonyRenderCreator):
    """Mark layer group as Render layer instance.

    All Harmony layers in the scene with the color group id are rendered in the
    beauty pass. To create sub passes use Render Layer creator which is
    dependent on existence of render layer instance.
    """

    label = "Render Layer"
    product_type = "render"
    product_template_product_type = "renderLayer"
    identifier = "render.layer"
    icon = "fa5.images"
    settings_category = "harmony"

    # Order to be executed before Render Pass creator
    order = 90
    description = "Mark Harmony color group as one Render Layer."
    detailed_description = RENDER_LAYER_DETAILED_DESCRIPTIONS

    # Settings
    default_variants = ["Beauty"]
    active_on_create = True

    # - Default render pass name for beauty
    default_pass_name = "beauty"
    # - Mark by default instance for review
    mark_for_review = True

    def get_dynamic_data(
        self, project_name, folder_entity, task_entity, variant, host_name, instance
    ):
        return {
            "renderpass": self.default_pass_name,
            "renderlayer": variant,
        }

    def product_impl(self, product_name, instance_data, pre_create_data):
        group_name = instance_data["variant"]

        if self._use_current_context:
            project_name = self.create_context.get_current_project_name()
            folder_entity = self.create_context.get_current_folder_entity()
            task_entity = self.create_context.get_current_task_entity()
            project_entity = self.create_context.get_current_project_entity()

            product_name = self.get_product_name(
                project_name,
                folder_entity,
                task_entity,
                variant=group_name,
                project_entity=project_entity,
            )

            instance_data["folderPath"] = folder_entity["path"]
            instance_data["task"] = task_entity["name"]
            instance_data["productName"] = product_name

        group_id = pre_create_data.get("group_id")
        # This creator should run only on one group
        if group_id is None or group_id == "-1":
            selected_groups = self._get_selected_group_ids()
            if len(selected_groups) > 1:
                raise CreatorError("You have selected more than one group")

            if len(selected_groups) == 0:
                raise CreatorError("You don't have selected any group")
            group_id = tuple(selected_groups)[0]

        for instance in self.create_context.instances:
            if (
                instance.creator_identifier == self.identifier
                and instance["creator_attributes"]["group_id"] == group_id
            ):
                raise CreatorError(
                    (
                        f'Group "{group_id}" is already used'
                        f' by another render layer "{instance["productName"]}"'
                    )
                )

        creator_attributes = instance_data.setdefault("creator_attributes", {})
        mark_for_review = pre_create_data.get("mark_for_review")
        if mark_for_review is None:
            mark_for_review = self.mark_for_review
        creator_attributes["group_id"] = group_id
        creator_attributes["mark_for_review"] = mark_for_review

        node = self._create_nodes_for_group(group_id, product_name)
        self.log.info(f"node is {node}")
        return node

    def _get_groups_enum(self):
        used_colors_enum = []
        layers_data = self._get_layers_data()
        available_colors = sorted(set(layer["color"] for layer in layers_data))

        for color in available_colors:
            item = {
                "label": color,
                "value": color
            }
            used_colors_enum.append(item)

        return used_colors_enum

    def get_pre_create_attr_defs(self):
        enum_defs = super().get_pre_create_attr_defs()
        group_enum_values = self._get_groups_enum()
        group_enum_values.insert(0, {"label": "<Use selection>", "value": "-1"})
        enum_defs.append(
            EnumDef(
                "group_id",
                label="Group",
                items=group_enum_values
            )
        )
        enum_defs.append(
            BoolDef("mark_for_review", label="Review", default=self.mark_for_review),
        )
        return enum_defs

    def get_instance_attr_defs(self):
        groups_enum = self._get_groups_enum()
        return [
            EnumDef("group_id", label="Group", items=groups_enum),
            BoolDef("mark_for_review", label="Review", default=self.mark_for_review),
        ]

    def _create_nodes_for_group(self, group_id, product_name):
        layers_data = self._get_layers_data()
        layers_full_names = [
            layer["fullName"] for layer in layers_data 
            if layer["color"]==group_id
        ]
        self.log.info(f"layers_full_name::{layers_full_names}")
        self_name = self.__class__.__name__
        created_node = harmony.send(
            {
                "function": f"AyonHarmony.Creators.{self_name}.createLayerNodes",
                "args": [layers_full_names, product_name]
            }
        )["result"]

        return created_node


    def _get_layers_data(self):
        self_name = self.__class__.__name__
        layers_data = harmony.send(
            {
                "function": f"AyonHarmony.Creators.{self_name}.getLayerInfos",
                "args": []
            }
        )["result"]
        return layers_data

    def _get_selected_group_ids(self):
        return {layer["color"] for layer in self._get_layers_data() if layer["selected"]}

#     def _update_color_groups(self):
#         render_layer_instances = []
#         for instance in self.create_context.instances:
#             if instance.creator_identifier == self.identifier:
#                 render_layer_instances.append(instance)

#         if not render_layer_instances:
#             return

#         groups_by_id = {group["group_id"]: group for group in get_groups_data()}
#         grg_script_lines = []
#         for instance in render_layer_instances:
#             group_id = instance["creator_attributes"]["group_id"]
#             variant = instance["variant"]
#             group = groups_by_id[group_id]
#             if group["name"] == variant:
#                 continue

#             grg_script_lines.append(
#                 self.rename_script_template.format(
#                     clip_id=group["clip_id"],
#                     group_id=group["group_id"],
#                     r=group["red"],
#                     g=group["green"],
#                     b=group["blue"],
#                     name=variant,
#                 )
#             )

#         if grg_script_lines:
#             execute_george_through_file("\n".join(grg_script_lines))

#     def _update_renderpass_groups(self):
#         render_layer_instances = {}
#         render_pass_instances = collections.defaultdict(list)

#         for instance in self.create_context.instances:
#             if instance.creator_identifier == CreateRenderPass.identifier:
#                 render_layer_id = instance["creator_attributes"][
#                     "render_layer_instance_id"
#                 ]
#                 render_pass_instances[render_layer_id].append(instance)
#             elif instance.creator_identifier == self.identifier:
#                 render_layer_instances[instance.id] = instance

#         if not render_pass_instances or not render_layer_instances:
#             return

#         layers_data = get_layers_data()
#         layers_by_name = collections.defaultdict(list)
#         for layer in layers_data:
#             layers_by_name[layer["name"]].append(layer)

#         george_lines = []
#         for render_layer_id, instances in render_pass_instances.items():
#             render_layer_inst = render_layer_instances.get(render_layer_id)
#             if render_layer_inst is None:
#                 continue
#             group_id = render_layer_inst["creator_attributes"]["group_id"]
#             layer_names = set()
#             for instance in instances:
#                 layer_names |= set(instance["layer_names"])

#             for layer_name in layer_names:
#                 george_lines.extend(
#                     f'tv_layercolor "set" {layer["layer_id"]} {group_id}'
#                     for layer in layers_by_name[layer_name]
#                     if layer["group_id"] != group_id
#                 )
#         if george_lines:
#             execute_george_through_file("\n".join(george_lines))


# class CreateRenderPass(HarmonyCreator):
#     product_type = "render"
#     product_template_product_type = "renderPass"
#     identifier = "render.pass"
#     label = "Render Pass"
#     icon = "fa5.image"
#     description = "Mark selected Harmony layers as pass of Render Layer."
#     detailed_description = RENDER_PASS_DETAILED_DESCRIPTIONS

#     order = CreateRenderlayer.order + 10

#     # Settings
#     render_pass_template = "{variant}"
#     layer_name_template = {"enabled": False, "template": "{variant}"}
#     group_idx_offset = 10
#     group_idx_padding = 3
#     layer_idx_offset = 10
#     layer_idx_padding = 3
#     mark_for_review = True

#     def register_callbacks(self):
#         self.create_context.add_instances_added_callback(self._on_added_instance)
#         self.create_context.add_instances_removed_callback(self._on_removed_instance)
#         self.create_context.add_value_changed_callback(self._on_value_change)

#     def apply_settings(self, project_settings):
#         super().apply_settings(project_settings)
#         plugin_settings = project_settings["Harmony"]["create"]["create_render_pass"]
#         self.layer_name_template = plugin_settings["layer_name_template"]
#         self.group_idx_offset = plugin_settings["group_idx_offset"]
#         self.group_idx_padding = plugin_settings["group_idx_padding"]
#         self.layer_idx_offset = plugin_settings["layer_idx_offset"]
#         self.layer_idx_padding = plugin_settings["layer_idx_padding"]
#         self.default_variant = plugin_settings["default_variant"]
#         self.default_variants = plugin_settings["default_variants"]
#         self.mark_for_review = plugin_settings["mark_for_review"]
#         self.render_pass_template = plugin_settings["render_pass_template"]
#         self.create_allow_context_change = not self._use_current_context

#     def collect_instances(self):
#         instances_by_identifier = self._cache_and_get_instances()
#         render_layers = {
#             instance_data["instance_id"]: {
#                 "variant": instance_data["variant"],
#                 "template_data": prepare_template_data(
#                     {"renderlayer": instance_data["variant"]}
#                 ),
#             }
#             for instance_data in (instances_by_identifier[CreateRenderlayer.identifier])
#         }

#         layers_data = get_layers_data()
#         layers_count = len(layers_data)
#         layers_by_name = collections.defaultdict(list)
#         for layer in layers_data:
#             layers_by_name[layer["name"]].append(layer)

#         for instance_data in instances_by_identifier[self.identifier]:
#             instance_layers = []
#             layer_names = instance_data.setdefault("layer_names", [])
#             for layer_name in tuple(layer_names):
#                 instance_layers.extend(layers_by_name[layer_name])

#             render_layer_instance_id = instance_data.get("creator_attributes", {}).get(
#                 "render_layer_instance_id"
#             )
#             render_layer_info = render_layers.get(render_layer_instance_id, {})

#             instance = CreatedInstance.from_existing(instance_data, self)

#             instance.transient_data["instance_layers"] = instance_layers
#             instance.transient_data["layers_count"] = layers_count
#             self._add_instance_to_context(instance)
#             if self._use_current_context:
#                 self._update_instance_context(instance)

#             self.update_instance_labels(
#                 instance,
#                 layers_count,
#                 instance_layers,
#                 render_layer_info.get("variant"),
#                 render_layer_info.get("template_data"),
#             )

#             self._set_layer_name(
#                 instance["variant"],
#                 instance["layer_names"],
#                 layers_by_name,
#                 layers_count,
#             )

#     def get_dynamic_data(
#         self, project_name, folder_entity, task_entity, variant, host_name, instance
#     ):
#         dynamic_data = super().get_dynamic_data(
#             project_name, folder_entity, task_entity, variant, host_name, instance
#         )
#         dynamic_data["renderpass"] = "{renderpass}"
#         dynamic_data["renderlayer"] = "{renderlayer}"
#         return dynamic_data

#     def update_instance_labels(
#         self,
#         instance: CreatedInstance,
#         all_layers_count: int,
#         instance_layers: list[dict[str, Any]],
#         render_layer_variant: Optional[str],
#         render_layer_data: Optional[dict[str, Any]],
#     ):
#         new_group = None
#         if render_layer_variant is None:
#             render_layer_variant = "{renderlayer}"
#         else:
#             new_group = f"{self.get_group_label()} ({render_layer_variant})"

#         if render_layer_data is None:
#             product_name_data = prepare_template_data(
#                 {
#                     "renderlayer": render_layer_variant,
#                 }
#             )
#         else:
#             product_name_data = copy.deepcopy(render_layer_data)

#         # Prepare 'renderpass' value
#         render_pass_name = self._get_render_pass_name(
#             all_layers_count,
#             instance_layers,
#             instance["variant"],
#         )
#         product_name_data.update(
#             prepare_template_data({"renderpass": render_pass_name})
#         )

#         try:
#             new_label = instance["productName"].format(**product_name_data)
#         except (KeyError, ValueError):
#             new_label = None

#         instance["label"] = new_label
#         instance["group"] = new_group

#     def create(self, product_name, instance_data, pre_create_data):
#         render_layer_instance_id = pre_create_data.get("render_layer_instance_id")
#         if not render_layer_instance_id:
#             raise CreatorError(
#                 (
#                     "You cannot create a Render Pass without a Render Layer."
#                     " Please select one first"
#                 )
#             )

#         render_layer_instance = self.create_context.instances_by_id.get(
#             render_layer_instance_id
#         )
#         if render_layer_instance is None:
#             raise CreatorError(
#                 (
#                     "RenderLayer instance was not found"
#                     f' by id "{render_layer_instance_id}"'
#                 )
#             )

#         if self._use_current_context:
#             project_name = self.create_context.get_current_project_name()
#             folder_entity = self.create_context.get_current_folder_entity()
#             task_entity = self.create_context.get_current_task_entity()
#             project_entity = self.create_context.get_current_project_entity()

#             product_name = self.get_product_name(
#                 project_name,
#                 folder_entity,
#                 task_entity,
#                 variant=instance_data["variant"],
#                 project_entity=project_entity,
#             )

#             instance_data["folderPath"] = folder_entity["path"]
#             instance_data["task"] = task_entity["name"]
#             instance_data["productName"] = product_name

#         group_id = render_layer_instance["creator_attributes"]["group_id"]
#         self.log.debug("Query data from workfile.")
#         layers_data = get_layers_data()
#         layers_count = len(layers_data)

#         self.log.debug("Checking selection.")
#         # Get all selected layers and their group ids
#         marked_layer_names = pre_create_data.get("layer_names")
#         if marked_layer_names is not None:
#             layers_by_name = {layer["name"]: layer for layer in layers_data}
#             marked_layers = []
#             for layer_name in marked_layer_names:
#                 layer = layers_by_name.get(layer_name)
#                 if layer is None:
#                     raise CreatorError(f'Layer with name "{layer_name}" was not found')
#                 marked_layers.append(layer)

#         else:
#             marked_layers = [layer for layer in layers_data if layer["selected"]]

#             # Raise if nothing is selected
#             if not marked_layers:
#                 raise CreatorError("Nothing is selected. Please select layers.")

#         marked_layer_names = [layer["name"] for layer in marked_layers]

#         layers_by_name = collections.defaultdict(list)
#         for layer in marked_layers:
#             layers_by_name[layer["name"]].append(layer)

#         self._set_layer_name(
#             instance_data["variant"],
#             marked_layer_names,
#             layers_by_name,
#             layers_count,
#             group_id,
#         )

#         marked_layer_names_s = set(marked_layer_names)
#         instances_to_remove = []
#         for instance in self.create_context.instances:
#             if instance.creator_identifier != self.identifier:
#                 continue
#             cur_layer_names = set(instance["layer_names"])
#             if not cur_layer_names.intersection(marked_layer_names_s):
#                 continue
#             new_layer_names = cur_layer_names - marked_layer_names_s
#             if new_layer_names:
#                 instance["layer_names"] = list(new_layer_names)
#             else:
#                 instances_to_remove.append(instance)

#         render_pass_name = self._get_render_pass_name(
#             layers_count, marked_layers, instance_data["variant"]
#         )
#         render_layer = render_layer_instance["variant"]
#         product_name_fill_data = {
#             "renderlayer": render_layer,
#             "renderpass": render_pass_name,
#         }

#         # Format dynamic keys in product name
#         label = product_name
#         try:
#             label = label.format(**prepare_template_data(product_name_fill_data))
#         except (KeyError, ValueError):
#             pass

#         self.log.info(f'New product name is "{label}".')
#         instance_data["label"] = label
#         instance_data["group"] = f"{self.get_group_label()} ({render_layer})"
#         instance_data["layer_names"] = marked_layer_names

#         creator_attributes = instance_data.setdefault("creator_attributes", {})
#         mark_for_review = pre_create_data.get("mark_for_review")
#         if mark_for_review is None:
#             mark_for_review = self.mark_for_review
#         creator_attributes["mark_for_review"] = mark_for_review
#         creator_attributes["render_layer_instance_id"] = render_layer_instance_id

#         new_instance = CreatedInstance(
#             self.product_type, product_name, instance_data, self
#         )
#         instances_data = self._remove_and_filter_instances(instances_to_remove)
#         instances_data.append(new_instance.data_to_store())

#         self.host.write_instances(instances_data)
#         self._add_instance_to_context(new_instance)
#         self._change_layers_group(marked_layers, group_id)

#         return new_instance

#     def _change_layers_group(self, layers, group_id):
#         filtered_layers = [layer for layer in layers if layer["group_id"] != group_id]
#         if filtered_layers:
#             self.log.info(
#                 (
#                     "Changing group of "
#                     f"{','.join([layer['name'] for layer in filtered_layers])}"
#                     f" to {group_id}"
#                 )
#             )
#             george_lines = [
#                 f'tv_layercolor "set" {layer["layer_id"]} {group_id}'
#                 for layer in filtered_layers
#             ]
#             execute_george_through_file("\n".join(george_lines))

#     def _remove_and_filter_instances(self, instances_to_remove):
#         instances_data = self.host.list_instances()
#         if not instances_to_remove:
#             return instances_data

#         removed_ids = set()
#         for instance in instances_to_remove:
#             removed_ids.add(instance.id)
#             self._remove_instance_from_context(instance)

#         return [
#             instance_data
#             for instance_data in instances_data
#             if instance_data.get("instance_id") not in removed_ids
#         ]

#     def get_pre_create_attr_defs(self):
#         # Find available Render Layers
#         # - instances are created after creators reset
#         render_layers = self._get_render_layers_items()

#         return [
#             EnumDef(
#                 "render_layer_instance_id", label="Render Layer", items=render_layers
#             ),
#             BoolDef("mark_for_review", label="Review", default=self.mark_for_review),
#         ]

#     def get_attr_defs_for_instance(self, instance):
#         render_layer_instance_id = instance.creator_attributes[
#             "render_layer_instance_id"
#         ]
#         render_layers = self._get_render_layers_items()
#         default = None
#         for layer in render_layers:
#             if layer["value"] == render_layer_instance_id:
#                 default = render_layer_instance_id
#                 break

#         return [
#             EnumDef(
#                 "render_layer_instance_id",
#                 label="Render Layer",
#                 items=render_layers,
#                 default=default,
#             ),
#             BoolDef("mark_for_review", label="Review", default=self.mark_for_review),
#         ]

#     def _get_render_layers_items(self):
#         current_instances = self.create_context.instances
#         render_layers = [
#             {"value": instance.id, "label": instance.label}
#             for instance in current_instances
#             if instance.creator_identifier == CreateRenderlayer.identifier
#         ]
#         if not render_layers:
#             render_layers.append({"value": None, "label": "N/A"})
#         return render_layers

#     def _get_render_pass_name(self, all_layers_count, layers, variant):
#         max_position = 1
#         if layers:
#             max_position = max(layer["position"] for layer in layers)
#         layer_template = "{}"
#         if self.layer_idx_offset:
#             layer_template = f"{{:0>{self.layer_idx_padding}}}"

#         layer_index: str = layer_template.format(
#             (all_layers_count - max_position) * self.layer_idx_offset
#         )
#         output = "{renderpass}"
#         try:
#             output = self.render_pass_template.format(
#                 **prepare_template_data(
#                     {
#                         "variant": variant,
#                         "layer_index": layer_index,
#                     }
#                 )
#             )
#         except Exception:
#             self.log.warning("Failed to fill render pass template", exc_info=True)
#         return output

#     def _on_added_instance(self, event):
#         if any(
#             instance.creator_identifier == "render.layer"
#             for instance in event["instances"]
#         ):
#             self._update_instance_attributes()

#     def _on_removed_instance(self, event):
#         if any(
#             instance.creator_identifier == "render.layer"
#             for instance in event["instances"]
#         ):
#             self._update_instance_attributes()

#     def _on_value_change(self, event):
#         changed_ids = set()
#         for change in event["changes"]:
#             instance = change["instance"]
#             if (
#                 instance is None
#                 or instance.creator_identifier != CreateRenderlayer.identifier
#             ):
#                 continue

#             if "productName" in change["changes"]:
#                 changed_ids.add(instance.id)

#         if changed_ids:
#             self._update_instance_attributes(changed_ids)

#     def _update_instance_attributes(self, render_layer_ids=None):
#         self.create_context.create_plugin_pre_create_attr_defs_changed(
#             CreateRenderPass.identifier
#         )
#         if render_layer_ids is not None and not render_layer_ids:
#             return

#         filtered_instances = []
#         for instance in self.create_context.instances:
#             if instance.creator_identifier != self.identifier:
#                 continue
#             rl_id = instance.creator_attributes["render_layer_instance_id"]
#             if render_layer_ids is not None and rl_id not in render_layer_ids:
#                 continue
#             filtered_instances.append(instance)

#         if not filtered_instances:
#             return

#         with self.create_context.bulk_create_attr_defs_change():
#             for instance in filtered_instances:
#                 instance.set_create_attr_defs(self.get_attr_defs_for_instance(instance))

#     def _set_layer_name(
#         self,
#         variant: str,
#         layer_names: list[str],
#         layers_by_name: dict[str, list[dict[str, Any]]],
#         layers_count: int,
#         group_id: Optional[int] = None,
#     ):
#         if not self.layer_name_template["enabled"]:
#             return

#         template = self.layer_name_template["template"]

#         group_template = "{}"
#         if self.group_idx_padding:
#             group_template = f"{{:0>{self.group_idx_padding}}}"

#         layer_template = "{}"
#         if self.layer_idx_offset:
#             layer_template = f"{{:0>{self.layer_idx_padding}}}"

#         for layer_name in tuple(layer_names):
#             layers = layers_by_name.get(layer_name)
#             if not layers:
#                 continue
#             for layer in layers:
#                 # Reverse the position order
#                 layer_pos = layers_count - layer["position"]
#                 group_pos = layer["group_id"]
#                 layer_index = self.layer_idx_offset * layer_pos
#                 if group_id is not None:
#                     group_pos = group_id

#                 group_pos = group_pos * self.group_idx_offset
#                 new_name = None
#                 try:
#                     new_name = template.format(
#                         layer_index=layer_template.format(layer_index),
#                         group_index=group_template.format(group_pos),
#                         variant=variant,
#                     )
#                 except Exception:
#                     self.log.warning("Failed to create new layer name", exc_info=True)

#                 if new_name and layer["name"] != new_name:
#                     layer_id = layer["layer_id"]
#                     idx = layer_names.index(layer_name)
#                     layer_names[idx] = new_name
#                     layer["name"] = new_name
#                     execute_george(f"tv_layerrename {layer_id} {new_name}")


class HarmonyAutoDetectRenderCreator(HarmonyAutoCreator):
#     """Create Render Layer and Render Pass instances based on scene data.

#     This is auto-detection creator which can be triggered by user to create
#     instances based on information in scene. Each used color group in scene
#     will be created as Render Layer where group name is used as variant and
#     each Harmony layer as Render Pass where layer name is used as variant.

#     Never will have any instances, all instances belong to different creators.
#     """

    product_type = "render"
    label = "Render Layer/Passes"
    identifier = "render.auto.detect.creator"
    # order = CreateRenderPass.order + 10
    description = "Create Render Layers and Render Passes based on scene setup"
    detailed_description = AUTODETECT_RENDER_DETAILED_DESCRIPTION

    # Settings
    default_variants = ["Main"]
    active_on_create = True

    enabled = True
    allow_group_rename = True
    group_name_template = "G{group_index}"
    group_idx_offset = 10
    group_idx_padding = 3
    layer_name_template = {"enabled": False}

    # Placeholder node name for where we store the workfile data.
    # This does not create an actual Harmony node, but just uses this name
    # as key in the AYON Harmony scene data.
    _node_name = "__renderLayers__"

    def create(self):
        pass

#     def apply_settings(self, project_settings):
#         super().apply_settings(project_settings)
#         plugin_settings = project_settings["Harmony"]["create"]["auto_detect_render"]
#         self.enabled = plugin_settings.get("enabled", False)
#         self.allow_group_rename = plugin_settings["allow_group_rename"]
#         self.group_name_template = plugin_settings["group_name_template"]
#         self.group_idx_offset = plugin_settings["group_idx_offset"]
#         self.group_idx_padding = plugin_settings["group_idx_padding"]
#         self.create_allow_context_change = not self._use_current_context

#         render_pass_settings = project_settings["Harmony"]["create"][
#             "create_render_pass"
#         ]
#         self.layer_name_template = copy.deepcopy(
#             render_pass_settings["layer_name_template"]
#         )

#     def _rename_groups(
#         self, groups_order: list[int], scene_groups: list[dict[str, Any]]
#     ):
#         new_group_name_by_id: dict[int, str] = {}
#         groups_by_id: dict[int, dict[str, Any]] = {
#             group["group_id"]: group for group in scene_groups
#         }
#         # Count only renamed groups
#         group_template = "{}"
#         if self.group_idx_padding:
#             group_template = f"{{:0>{self.group_idx_padding}}}"

#         for idx, group_id in enumerate(groups_order):
#             group_index_value: str = group_template.format(
#                 (idx + 1) * self.group_idx_offset
#             )
#             group_name_fill_values: dict[str, str] = {
#                 "groupIdx": group_index_value,
#                 "groupidx": group_index_value,
#                 "group_idx": group_index_value,
#                 "group_index": group_index_value,
#             }

#             group_name: str = self.group_name_template.format(**group_name_fill_values)
#             group: dict[str, Any] = groups_by_id[group_id]
#             if group["name"] != group_name:
#                 new_group_name_by_id[group_id] = group_name

#         grg_lines: list[str] = []
#         for group_id, group_name in new_group_name_by_id.items():
#             group: dict[str, Any] = groups_by_id[group_id]
#             grg_line: str = ('tv_layercolor "setcolor" {} {} {} {} {} "{}"').format(
#                 group["clip_id"],
#                 group_id,
#                 group["red"],
#                 group["green"],
#                 group["blue"],
#                 group_name,
#             )
#             grg_lines.append(grg_line)
#             group["name"] = group_name

#         if grg_lines:
#             execute_george_through_file("\n".join(grg_lines))

#     def _prepare_render_layer(
#         self,
#         project_entity: dict[str, Any],
#         folder_entity: dict[str, Any],
#         task_entity: dict[str, Any],
#         group_id: int,
#         groups: list[dict[str, Any]],
#         mark_for_review: bool,
#         existing_instance: Optional[CreatedInstance] = None,
#     ) -> Union[CreatedInstance, None]:
#         match_group: Optional[dict[str, Any]] = next(
#             (group for group in groups if group["group_id"] == group_id), None
#         )
#         if not match_group:
#             return None

#         task_name = task_entity["name"]
#         variant: str = match_group["name"]
#         creator: CreateRenderlayer = self.create_context.creators[
#             CreateRenderlayer.identifier
#         ]
#         product_name: str = creator.get_product_name(
#             project_entity["name"],
#             folder_entity,
#             task_entity,
#             variant,
#             host_name=self.create_context.host_name,
#             project_entity=project_entity,
#         )
#         if existing_instance is not None:
#             existing_instance["folderPath"] = folder_entity["path"]
#             existing_instance["task"] = task_name
#             existing_instance["productName"] = product_name
#             return existing_instance

#         instance_data: dict[str, str] = {
#             "folderPath": folder_entity["path"],
#             "task": task_name,
#             "productType": creator.product_type,
#             "variant": variant,
#         }
#         pre_create_data: dict[str, Any] = {
#             "group_id": group_id,
#             "mark_for_review": mark_for_review,
#         }
#         return creator.create(product_name, instance_data, pre_create_data)

#     def _prepare_render_passes(
#         self,
#         project_entity: dict[str, Any],
#         folder_entity: dict[str, Any],
#         task_entity: dict[str, Any],
#         render_layer_instance: CreatedInstance,
#         layers: list[dict[str, Any]],
#         mark_for_review: bool,
#         existing_render_passes: list[CreatedInstance],
#     ):
#         task_name = task_entity["name"]
#         creator: CreateRenderPass = self.create_context.creators[
#             CreateRenderPass.identifier
#         ]
#         render_pass_by_layer_name = {}
#         for render_pass in existing_render_passes:
#             for layer_name in render_pass["layer_names"]:
#                 render_pass_by_layer_name[layer_name] = render_pass

#         # Use renaming template to parse correct variant from existing layer
#         #   names.
#         name_regex = None
#         if self.layer_name_template["enabled"]:
#             template = self.layer_name_template["template"]
#             fake_group = "___group___"
#             fake_layer = "___layer___"
#             fake_variant = "___variant___"
#             try:
#                 name_regex = template.format(
#                     layer_index=fake_layer,
#                     group_index=fake_group,
#                     variant=fake_variant,
#                 )
#             except Exception:
#                 self.log.error("Failed to fill name regex template.", exc_info=True)
#                 name_regex = ""

#             for src, regex in (
#                 (fake_group, r"(?P<group>\d+)"),
#                 (fake_layer, r"(?P<layer>\d+)"),
#                 (fake_variant, r"(?P<variant>.*)"),
#             ):
#                 name_regex = name_regex.replace(src, regex)
#             name_regex = re.compile(name_regex)

#         for layer in layers:
#             layer_name = layer["name"]
#             variant = None
#             render_pass = render_pass_by_layer_name.get(layer_name)
#             if render_pass is not None and len(render_pass["layer_names"]) > 0:
#                 variant = render_pass["variant"]
#             elif name_regex is not None:
#                 result = name_regex.match(layer_name)
#                 groups = {}
#                 if result is not None:
#                     groups = result.groupdict()
#                 variant = groups.get("variant")

#             if not variant:
#                 variant = layer_name

#             product_name = creator.get_product_name(
#                 project_entity["name"],
#                 folder_entity,
#                 task_entity,
#                 variant,
#                 host_name=self.create_context.host_name,
#                 instance=render_pass,
#                 project_entity=project_entity,
#             )

#             if render_pass is not None:
#                 render_pass["folderPath"] = folder_entity["path"]
#                 render_pass["task"] = task_name
#                 render_pass["productName"] = product_name
#                 continue

#             instance_data: dict[str, str] = {
#                 "folderPath": folder_entity["path"],
#                 "task": task_name,
#                 "productType": creator.product_type,
#                 "variant": variant,
#             }

#             pre_create_data: dict[str, Any] = {
#                 "render_layer_instance_id": render_layer_instance.id,
#                 "layer_names": [layer_name],
#                 "mark_for_review": mark_for_review,
#             }
#             creator.create(product_name, instance_data, pre_create_data)

#     def _filter_groups(self, layers_by_group_id, groups_order, only_visible_groups):
#         new_groups_order = []
#         for group_id in groups_order:
#             layers: list[dict[str, Any]] = layers_by_group_id[group_id]
#             if not layers:
#                 continue

#             if only_visible_groups and not any(
#                 layer for layer in layers if layer["visible"]
#             ):
#                 continue
#             new_groups_order.append(group_id)
#         return new_groups_order

    # def create(self, product_name, instance_data, pre_create_data):
    #     name = "CreateRenderLayer"
    #     with open("c:/projects/harmony1.txt", "w") as fp:
    #         fp.write("FOOOOK")
        # layers_data = harmony.send(
        #     {
        #         "function": f"AyonHarmony.Creators.{name}.getLayerInfos",
        #         "args": []
        #     }
        # )
        # self.log.info(f"layers_data::{layers_data}")
        # with open("c:/projects/harmony.txt", "w") as fp:
        #     fp.write(layers_data)
#         project_entity = self.create_context.get_current_project_entity()
#         if self._use_current_context:
#             folder_path: str = self.create_context.get_current_folder_path()
#             task_name: str = self.create_context.get_current_task_name()
#         else:
#             folder_path: str = instance_data["folderPath"]
#             task_name: str = instance_data["task"]
#         folder_entity: dict[str, Any] = self.create_context.get_folder_entity(
#             folder_path
#         )
#         task_entity: dict[str, Any] = self.create_context.get_task_entity(
#             folder_path, task_name
#         )

#         render_layers_by_group_id: dict[int, CreatedInstance] = {}
#         render_passes_by_render_layer_id: dict[int, list[CreatedInstance]] = (
#             collections.defaultdict(list)
#         )
#         for instance in self.create_context.instances:
#             if instance.creator_identifier == CreateRenderlayer.identifier:
#                 group_id = instance["creator_attributes"]["group_id"]
#                 render_layers_by_group_id[group_id] = instance
#             elif instance.creator_identifier == CreateRenderPass.identifier:
#                 render_layer_id = instance["creator_attributes"][
#                     "render_layer_instance_id"
#                 ]
#                 render_passes_by_render_layer_id[render_layer_id].append(instance)

#         layers_by_group_id: dict[int, list[dict[str, Any]]] = collections.defaultdict(
#             list
#         )
#         scene_layers: list[dict[str, Any]] = get_layers_data()
#         scene_groups: list[dict[str, Any]] = get_groups_data()
#         groups_order: list[int] = []
#         for layer in scene_layers:
#             group_id: int = layer["group_id"]
#             # Skip 'default' group
#             if group_id == 0:
#                 continue

#             layers_by_group_id[group_id].append(layer)
#             if group_id not in groups_order:
#                 groups_order.append(group_id)

#         groups_order.reverse()

#         mark_layers_for_review = pre_create_data.get("mark_layers_for_review", False)
#         mark_passes_for_review = pre_create_data.get("mark_passes_for_review", False)
#         rename_groups = pre_create_data.get("rename_groups", False)
#         only_visible_groups = pre_create_data.get("only_visible_groups", False)
#         groups_order = self._filter_groups(
#             layers_by_group_id, groups_order, only_visible_groups
#         )
#         if not groups_order:
#             return

#         if rename_groups:
#             self._rename_groups(groups_order, scene_groups)

#         # Make sure  all render layers are created
#         for group_id in groups_order:
#             instance: Union[CreatedInstance, None] = self._prepare_render_layer(
#                 project_entity,
#                 folder_entity,
#                 task_entity,
#                 group_id,
#                 scene_groups,
#                 mark_layers_for_review,
#                 render_layers_by_group_id.get(group_id),
#             )
#             if instance is not None:
#                 render_layers_by_group_id[group_id] = instance

#         for group_id in groups_order:
#             layers: list[dict[str, Any]] = layers_by_group_id[group_id]
#             render_layer_instance: Union[CreatedInstance, None] = (
#                 render_layers_by_group_id.get(group_id)
#             )
#             if not layers or render_layer_instance is None:
#                 continue

#             self._prepare_render_passes(
#                 project_entity,
#                 folder_entity,
#                 task_entity,
#                 render_layer_instance,
#                 layers,
#                 mark_passes_for_review,
#                 render_passes_by_render_layer_id[render_layer_instance.id],
#             )

#     def get_pre_create_attr_defs(self) -> list[AbstractAttrDef]:
#         render_layer_creator: CreateRenderlayer = self.create_context.creators[
#             CreateRenderlayer.identifier
#         ]
#         render_pass_creator: CreateRenderPass = self.create_context.creators[
#             CreateRenderPass.identifier
#         ]
#         output = []
#         if self.allow_group_rename:
#             output.extend(
#                 [
#                     BoolDef(
#                         "rename_groups",
#                         label="Rename color groups",
#                         tooltip="Will rename color groups using studio template",
#                         default=True,
#                     ),
#                     BoolDef(
#                         "only_visible_groups",
#                         label="Only visible color groups",
#                         tooltip=(
#                             "Render Layers and rename will happen only on color"
#                             " groups with visible layers."
#                         ),
#                         default=True,
#                     ),
#                     UISeparatorDef(),
#                 ]
#             )
#         output.extend(
#             [
#                 BoolDef(
#                     "mark_layers_for_review",
#                     label="Mark RenderLayers for review",
#                     default=render_layer_creator.mark_for_review,
#                 ),
#                 BoolDef(
#                     "mark_passes_for_review",
#                     label="Mark RenderPasses for review",
#                     default=render_pass_creator.mark_for_review,
#                 ),
#             ]
#         )
#         return output
