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
import logging
import collections
from typing import Any, Optional, Union
from dataclasses import dataclass

from ayon_core.lib import (
    AbstractAttrDef,
    EnumDef,
    BoolDef,
    prepare_template_data,
)
from ayon_core.pipeline.create import (
    CreatedInstance,
    CreatorError,
    get_product_name
)

from ayon_harmony.api.plugin import HarmonyCreator, HarmonyRenderCreator
from ayon_harmony.api.lib import get_layers_info
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
"""  # noqa E501


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
"""  # noqa E501


@dataclass
class GroupInfo:
    color: str  # #ffffff
    position: int  # 1 at bottom


class CreateRenderLayer(HarmonyRenderCreator):
    """Mark layer group as Render layer instance.

    All Harmony layers in the scene with the color group id are rendered in the
    beauty pass. To create sub passes use Render Layer creator which is
    dependent on existence of render layer instance.
    """

    label = "Render Layer"
    product_type = "render"
    product_base_type = "render"
    product_template_product_type = "renderLayer"
    identifier = "render.layer"
    icon = "fa5.images"

    # Order to be executed before Render Pass creator
    order = 90
    description = "Mark Harmony color group as one Render Layer."
    detailed_description = RENDER_LAYER_DETAILED_DESCRIPTIONS

    # Settings
    default_variants = ["Main"]
    active_on_create = True

    # - Default render pass name for beauty
    default_pass_name = "beauty"
    # - Mark by default instance for review
    mark_for_review = True

    def get_dynamic_data(
        self,
        project_name,
        folder_entity,
        task_entity,
        variant,
        host_name,
        instance
    ):
        return {
            "renderpass": self.default_pass_name,
            "renderlayer": variant,
        }

    def product_impl(self, product_name, instance_data, pre_create_data):
        group_id = pre_create_data.get("group_id")
        # This creator should run only on one group
        if group_id is None or group_id == "-1":
            selected_groups = self._get_selected_group_colors()
            if len(selected_groups) > 1:
                raise CreatorError("You have selected more than one group")

            if len(selected_groups) == 0:
                raise CreatorError("You don't have selected any group")
            group_id = tuple(selected_groups)[0]

        for instance in self.create_context.instances:
            if instance.creator_identifier != self.identifier:
                continue
            if instance["creator_attributes"]["group_id"] == group_id:
                raise CreatorError(
                    (
                        f'Group "{group_id}" is already used'
                        f' by another render layer "{instance["productName"]}"'
                    )
                )
            if instance["productName"] == product_name:
                raise CreatorError(
                    f"Product '{product_name}' already exists.")

        creator_attributes = instance_data.setdefault("creator_attributes", {})
        mark_for_review = pre_create_data.get("mark_for_review")
        if mark_for_review is None:
            mark_for_review = self.mark_for_review

        creator_attributes["group_id"] = group_id
        creator_attributes["mark_for_review"] = mark_for_review
        creator_attributes["render_target"] = pre_create_data["render_target"]

        node = self._create_nodes_for_group(group_id, product_name)
        self.log.debug(f"Created node:: {node}")
        return node

    def get_pre_create_attr_defs(self):
        enum_defs = super().get_pre_create_attr_defs()
        group_infos = get_group_infos()
        group_enum_values = [
            {"value": group.color, "label": str(group.position)}
            for group in group_infos
        ]
        group_enum_values.insert(
            0,
            {"label": "<Use selection>", "value": "-1"}
        )

        enum_defs.append(
            EnumDef("group_id", label="Group", items=group_enum_values))
        return enum_defs

    def get_instance_attr_defs(self):
        groups = get_group_infos()

        groups_enum = [
            {"value": group.color, "label": str(group.position)}
            for group in groups
        ]
        return [
            EnumDef(
                "group_id",
                label="Group",
                items=groups_enum,
                enabled=False
            ),
            BoolDef(
                "mark_for_review",
                label="Review",
                default=self.mark_for_review
            ),
            EnumDef(
                "render_target",
                items=self.rendering_targets,
                label="Render target"
            ),
        ]

    def get_product_name(
        self,
        project_name,
        folder_entity,
        task_entity,
        variant,
        host_name=None,
        instance=None,
        project_entity=None,
    ):
        if host_name is None:
            host_name = self.create_context.host_name
        if project_entity is None:
            project_entity = self.create_context.get_current_project_entity()
        dynamic_data = self.get_dynamic_data(
            project_name,
            folder_entity,
            task_entity,
            variant,
            host_name,
            instance
        )
        task_name = task_type = None
        if task_entity:
            task_name = task_entity["name"]
            task_type = task_entity["taskType"]

        get_product_name_kwargs = {}
        if getattr(get_product_name, "use_entities", False):
            get_product_name_kwargs.update({
                "folder_entity": folder_entity,
                "task_entity": task_entity,
                "product_base_type": self.product_base_type,
            })
        else:
            get_product_name_kwargs.update({
                "task_name": task_name,
                "task_type": task_type,
            })

        return get_product_name(
            project_name=project_name,
            host_name=host_name,
            product_type=self.product_template_product_type,
            variant=variant,
            dynamic_data=dynamic_data,
            project_settings=self.project_settings,
            product_base_type_filter=self.product_base_type,
            project_entity=project_entity,
            **get_product_name_kwargs
        )

    def _create_nodes_for_group(self, group_id, product_name):
        layers_data = get_layers_info()
        layers_full_names = [
            layer["fullName"]
            for layer in layers_data
            if layer["color"] == group_id
        ]

        self_name = self.__class__.__name__
        created_node = harmony.send(
            {
                "function": (
                    f"AyonHarmony.Creators.{self_name}.createLayerNodes"
                ),
                "args": [layers_full_names, product_name]
            }
        )["result"]

        return created_node

    def _get_selected_group_colors(self):
        return {
            layer["color"]
            for layer in get_layers_info()
            if layer["selected"]
        }

    def remove_instances(self, instances):
        for instance in instances:
            # There is only ever one workfile instance
            node_name = instance.transient_data["node"]
            container_data = harmony.read(node_name)
            harmony.delete_node(node_name)
            harmony.delete_node(f"{node_name}_comp")
            group_label = container_data.get("group_label")
            container_backdrop = None
            if group_label:
                container_backdrop = harmony.find_backdrop_by_name(
                    group_label
                )
            if container_backdrop:
                harmony.send(
                    {
                        "function": "AyonHarmony.removeBackdrop",
                        "args": [container_backdrop, False]
                    }
                )
            self._remove_instance_from_context(instance)


class CreateRenderPass(HarmonyRenderCreator):
    product_type = "render"
    product_base_type = "render"
    product_template_product_type = "renderPass"
    identifier = "render.pass"
    label = "Render Pass"
    icon = "fa5.image"
    description = "Mark selected Harmony layers as pass of Render Layer."
    detailed_description = RENDER_PASS_DETAILED_DESCRIPTIONS

    order = CreateRenderLayer.order + 10

    # Settings
    active_on_create = True
    default_variant = ""
    default_variants = []
    mark_for_review = True
    rename_read = True

    render_pass_template = "L{layer_index}_{variant}"
    layer_idx_offset = 10
    layer_idx_padding = 3

    def product_impl(self, product_name, instance_data, pre_create_data):
        render_layer_instance_id = pre_create_data.get(
            "render_layer_instance_id"
        )
        # This creator should run only on one group
        if (
            render_layer_instance_id is None
            or render_layer_instance_id == "-1"
        ):
            raise CreatorError("You must select layer group")

        render_layer_instance = self.create_context.instances_by_id.get(
            render_layer_instance_id
        )
        if render_layer_instance is None:
            raise CreatorError((
                "RenderLayer instance was not found"
                f" by id \"{render_layer_instance_id}\""
            ))

        layers_data = get_layers_info()
        marked_layer_name = pre_create_data.get("layer_name")
        layer = self._get_used_layer(marked_layer_name, layers_data)

        for instance in self.create_context.instances:
            if instance.creator_identifier != self.identifier:
                continue
            if instance["productName"] == product_name:
                raise CreatorError(
                    f"Product '{product_name}' already exists.")

        creator_attributes = instance_data.setdefault(
            "creator_attributes", {}
        )
        mark_for_review = pre_create_data.get("mark_for_review")
        if mark_for_review is None:
            mark_for_review = self.mark_for_review
        creator_attributes["mark_for_review"] = mark_for_review
        creator_attributes["render_target"] = pre_create_data["render_target"]
        creator_attributes["render_layer_instance_id"] = (
            render_layer_instance_id
        )

        # NOTE @iLLiCiTiT I think this should be filled dynamically
        #   in the future
        # /////////////////////////////////////////////////////////
        render_layer = instance_data.get("renderLayer")
        if not render_layer:
            render_layer = render_layer_instance["variant"]

        render_pass = instance_data.get("renderPass")
        if not render_pass:
            scene_layers = get_layers_info()
            group_id = render_layer_instance.creator_attributes["group_id"]
            filtered_layers = [
                layer
                for layer in scene_layers
                if layer["color"] == group_id
            ]
            layer_positions_in_groups = get_layer_positions_in_groups(
                filtered_layers
            )
            render_pass = get_render_pass_name(
                self.render_pass_template,
                layer_positions_in_groups[layer["name"]],
                self.layer_idx_padding,
                self.layer_idx_offset,
                instance_data["variant"],
                self.log
            )

        product_name = product_name.format_map(prepare_template_data({
            "renderpass": render_pass,
            "renderlayer": render_layer,
        }))
        # /////////////////////////////////////////////////////////

        instance_data["renderPass"] = render_pass
        instance_data["renderLayer"] = render_layer

        instance_data["layer_name"] = marked_layer_name

        node = self._create_node_for_pass(
            layer, product_name, self.rename_read
        )
        self.log.info(f"Created node:: {node}")
        return node

    def _get_selected_layers(self):
        return [
            layer
            for layer in get_layers_info()
            if layer["selected"]
        ]

    def _create_node_for_pass(self, layer, product_name, rename_read):
        self_name = self.__class__.__name__
        layer_name = layer["name"]

        created_node = harmony.send(
            {
                "function": f"AyonHarmony.Creators.{self_name}.createPassNode",
                "args": [layer_name, product_name, rename_read]
            }
        )["result"]

        return created_node

    def _get_used_layer(self, marked_layer_name, layers_data):
        if marked_layer_name is not None:
            layers_by_name = {layer["name"]: layer for layer in layers_data}
            layer = layers_by_name.get(marked_layer_name)
            if layer is None:
                raise CreatorError(
                    f"Layer with name \"{marked_layer_name}\" was not found")
        else:
            marked_layers = [
                layer
                for layer in layers_data
                if layer["selected"]
            ]

            # Raise if nothing is selected
            if not marked_layers:
                raise CreatorError(
                    "Nothing is selected. Please select layers.")
            if len(marked_layers) != 1:
                raise CreatorError(
                    "Select just 1 layer.")
            layer = marked_layers[0]

        return layer

    def get_dynamic_data(
        self,
        project_name,
        folder_entity,
        task_entity,
        variant,
        host_name,
        instance
    ):
        render_pass = None
        render_layer = None
        if instance is not None:
            render_pass = instance.get("renderPass")
            render_layer = instance.get("renderLayer")

        if not render_pass:
            render_pass = "{renderpass}"

        if not render_layer:
            render_layer = "{renderlayer}"

        return {
            "renderpass": render_pass,
            "renderlayer": render_layer,
        }

    def get_pre_create_attr_defs(self):
        # Find available Render Layers
        # - instances are created after creators reset
        enum_defs = super().get_pre_create_attr_defs()
        render_layers = self._get_render_layers_items()

        enum_defs.extend(
            [
                EnumDef(
                    "render_layer_instance_id",
                    label="Render Layer",
                    items=render_layers
                ),
            ]
        )
        return enum_defs

    def get_instance_attr_defs(self):
        render_layers = self._get_render_layers_items()
        return [
            EnumDef(
                "render_layer_instance_id",
                label="Render Layer",
                items=render_layers,
                enabled=False
            ),
            BoolDef(
                "mark_for_review",
                label="Review",
                default=self.mark_for_review
            ),
            EnumDef(
                "render_target",
                items=self.rendering_targets,
                label="Render target"
            )
        ]

    def get_product_name(
        self,
        project_name,
        folder_entity,
        task_entity,
        variant,
        host_name=None,
        instance=None,
        project_entity=None,
    ):
        if host_name is None:
            host_name = self.create_context.host_name
        if project_entity is None:
            project_entity = self.create_context.get_current_project_entity()
        dynamic_data = self.get_dynamic_data(
            project_name,
            folder_entity,
            task_entity,
            variant,
            host_name,
            instance
        )
        task_name = task_type = None
        if task_entity:
            task_name = task_entity["name"]
            task_type = task_entity["taskType"]

        get_product_name_kwargs = {}
        if getattr(get_product_name, "use_entities", False):
            get_product_name_kwargs.update({
                "folder_entity": folder_entity,
                "task_entity": task_entity,
                "product_base_type": self.product_base_type,
            })
        else:
            get_product_name_kwargs.update({
                "task_name": task_name,
                "task_type": task_type,
            })

        return get_product_name(
            project_name=project_name,
            host_name=host_name,
            product_type=self.product_template_product_type,
            variant=variant,
            dynamic_data=dynamic_data,
            project_settings=self.project_settings,
            product_base_type_filter=self.product_base_type,
            project_entity=project_entity,
            **get_product_name_kwargs
        )

    def _get_render_layers_items(self):
        current_instances = self.create_context.instances
        render_layers = [
            {"value": instance.id, "label": instance.label}
            for instance in current_instances
            if instance.creator_identifier == CreateRenderLayer.identifier
        ]
        if not render_layers:
            render_layers.append({
                "value": None,
                "label": "Create Render Layer first",
            })
        return render_layers

    def remove_instances(self, instances):
        for instance in instances:
            # There is only ever one workfile instance
            container_data = harmony.read(instance.transient_data["node"])
            if container_data["productName"] != container_data["layer_name"]:
                harmony.rename_node(
                    container_data["productName"],
                    container_data["layer_name"]
                )
            harmony.delete_node(instance.transient_data["node"])
            self._remove_instance_from_context(instance)


class AutoDetectRendeLayersPasses(HarmonyCreator):
    """Create Render Layer and Render Pass instances based on scene data.

    This is auto-detection creator which can be triggered by user to create
    instances based on information in scene. Each used color group in scene
    will be created as Render Layer where group name is used as variant and
    each Harmony layer as Render Pass where layer name is used as variant.

    Never will have any instances, all instances belong to different creators.
    """

    product_type = "render"
    product_base_type = "render"
    label = "Render Layer/Passes"
    identifier = "render.auto.detect.creator"
    # order = CreateRenderPass.order + 10
    description = "Create Render Layers and Render Passes based on scene setup"
    detailed_description = AUTODETECT_RENDER_DETAILED_DESCRIPTION

    # Settings
    default_variants = ["Main"]
    active_on_create = True

    enabled = True

    layer_name_template = {
        "enabled": False,
        "template": "G{group_index}_L{layer_index}_{variant}"
    }
    render_layer_variant_template = "G{group_index}"
    group_idx_offset = 10
    group_idx_padding = 3

    def create(self, product_name, instance_data, pre_create_data):

        project_entity = self.create_context.get_current_project_entity()
        folder_path: str = self.create_context.get_current_folder_path()
        task_name: str = self.create_context.get_current_task_name()
        folder_entity: dict[str, Any] = self.create_context.get_folder_entity(
            folder_path
        )
        task_entity: dict[str, Any] = self.create_context.get_task_entity(
            folder_path, task_name
        )

        render_layers_by_group_id: dict[int, CreatedInstance] = {}
        render_passes_by_render_layer_id: dict[int, list[CreatedInstance]] = (
            collections.defaultdict(list)
        )
        for instance in self.create_context.instances:
            if instance.creator_identifier == CreateRenderLayer.identifier:
                group_id = instance["creator_attributes"]["group_id"]
                render_layers_by_group_id[group_id] = instance
            elif instance.creator_identifier == CreateRenderPass.identifier:
                render_layer_id = (
                    instance
                    ["creator_attributes"]
                    ["render_layer_instance_id"]
                )
                render_passes_by_render_layer_id[render_layer_id].append(
                    instance
                )

        layers_by_group_id: dict[int, list[dict[str, Any]]] = (
            collections.defaultdict(list)
        )
        scene_layers: list[dict[str, Any]] = get_layers_info()
        scene_groups: list[dict[str, Any]] = get_group_infos()
        for layer in scene_layers:
            group_id = layer["color"]
            layers_by_group_id[group_id].append(layer)

        mark_layers_for_review = pre_create_data.get(
            "mark_layers_for_review", False
        )
        mark_passes_for_review = pre_create_data.get(
            "mark_passes_for_review", False
        )
        render_target = pre_create_data.get(
            "render_target", False
        )

        only_visible_groups = pre_create_data.get(
            "only_visible_groups", False
        )
        filtered_groups = self._filter_groups(
            layers_by_group_id,
            scene_groups,
            only_visible_groups
        )
        # Make sure  all render layers are created
        for group in filtered_groups:
            instance: Union[CreatedInstance, None] = (
                self._prepare_render_layer(
                    project_entity,
                    folder_entity,
                    task_entity,
                    group.color,
                    filtered_groups,
                    mark_layers_for_review,
                    render_target,
                    render_layers_by_group_id.get(group.color),
                )
            )
            if instance is not None:
                render_layers_by_group_id[group.color] = instance

        for group in filtered_groups:
            layers: list[dict[str, Any]] = layers_by_group_id[group.color]
            render_layer_instance: Union[CreatedInstance, None] = (
                render_layers_by_group_id.get(group.color)
            )
            if not layers or render_layer_instance is None:
                continue

            self._prepare_render_passes(
                project_entity,
                folder_entity,
                task_entity,
                render_layer_instance,
                layers,
                mark_passes_for_review,
                render_target,
                render_passes_by_render_layer_id[render_layer_instance.id]
            )

        self._wrap_nodes_in_backdrop()

    def _filter_groups(
        self,
        layers_by_group_id,
        scene_groups,
        only_visible_groups
    ):
        filtered_groups = []
        for group in scene_groups:
            layers: list[dict[str, Any]] = layers_by_group_id[group.color]
            if not layers:
                continue

            if only_visible_groups and not any(
                layer for layer in layers if layer["enabled"]
            ):
                continue
            filtered_groups.append(group)
        return filtered_groups

    @staticmethod
    def _get_render_layer_variant(
        template: str,
        group_position: int,
        group_idx_padding: int,
        group_idx_offset: int,
        log
    ) -> str:
        """Calculates render layer portion (G010)"""
        variant = None
        index_template = f"{{:0>{group_idx_padding}}}"
        group_pos = group_position * group_idx_offset
        try:
            group_index = index_template.format(group_pos)
            variant = template.format(
                group_index=group_index,
            )
        except Exception:
            log.warning(
                "Failed to create render layer variant",
                exc_info=True,
            )

        return variant

    def _prepare_render_layer(
        self,
        project_entity: dict[str, Any],
        folder_entity: dict[str, Any],
        task_entity: dict[str, Any],
        group_id: str,
        groups: list[GroupInfo],
        mark_for_review: bool,
        render_target: str,
        existing_instance: Optional[CreatedInstance] = None,
    ) -> Union[CreatedInstance, None]:
        match_group: Optional[dict[str, Any]] = next(
            (group for group in groups if group.color == group_id), None
        )
        if not match_group:
            return None

        task_name = task_entity["name"]
        group_idx = match_group.position
        variant: str = self._get_render_layer_variant(
            self.render_layer_variant_template,
            group_idx,
            self.group_idx_padding,
            self.group_idx_offset,
            self.log,
        )
        creator: CreateRenderLayer = self.create_context.creators[
            CreateRenderLayer.identifier
        ]
        product_name: str = creator.get_product_name(
            project_entity["name"],
            folder_entity,
            task_entity,
            variant,
            host_name=self.create_context.host_name,
            project_entity=project_entity,
        )
        if existing_instance is not None:
            existing_instance["folderPath"] = folder_entity["path"]
            existing_instance["task"] = task_name
            existing_instance["productName"] = product_name
            return existing_instance

        instance_data: dict[str, str] = {
            "folderPath": folder_entity["path"],
            "task": task_name,
            "productType": creator.product_type,
            "variant": variant,
            "group_label": variant
        }
        pre_create_data: dict[str, Any] = {
            "group_id": group_id,
            "mark_for_review": mark_for_review,
            "render_target": render_target,
        }
        return creator.create(product_name, instance_data, pre_create_data)

    def _prepare_render_passes(
        self,
        project_entity: dict[str, Any],
        folder_entity: dict[str, Any],
        task_entity: dict[str, Any],
        render_layer_instance: CreatedInstance,
        layers: list[dict[str, Any]],
        mark_for_review: bool,
        render_target: str,
        existing_render_passes: list[CreatedInstance],
    ):
        task_name = task_entity["name"]
        creator: CreateRenderPass = self.create_context.creators[
            CreateRenderPass.identifier
        ]
        render_pass_by_layer_name = {}
        for render_pass in existing_render_passes:
            render_pass_by_layer_name[render_pass["layer_name"]] = render_pass

        # Use renaming template to parse correct variant from existing layer
        #   names.
        name_regex = None
        if self.layer_name_template["enabled"]:
            template = self.layer_name_template["template"]
            fake_group = "___group___"
            fake_layer = "___layer___"
            fake_variant = "___variant___"
            try:
                name_regex = template.format(
                    layer_index=fake_layer,
                    group_index=fake_group,
                    variant=fake_variant,
                )
            except Exception:
                self.log.error(
                    "Failed to fill name regex template.",
                    exc_info=True
                )
                name_regex = ""

            for src, regex in (
                (fake_group, r"(?P<group>\d+)"),
                (fake_layer, r"(?P<layer>\d+)"),
                (fake_variant, r"(?P<variant>.*)"),
            ):
                name_regex = name_regex.replace(src, regex)
            name_regex = re.compile(name_regex)

        layer_positions_in_groups = get_layer_positions_in_groups(layers)

        for layer in layers:
            layer_name = layer["name"]
            variant = None
            render_pass = render_pass_by_layer_name.get(layer_name)
            if render_pass is not None and len(render_pass["layer_names"]) > 0:
                variant = render_pass["variant"]
            elif name_regex is not None:
                result = name_regex.match(layer_name)
                if result is not None:
                    variant = result.groupdict().get("variant")

            if not variant:
                variant = layer["name"]

            renderlayer = render_layer_instance["variant"]

            renderpass = get_render_pass_name(
                creator.render_pass_template,
                layer_positions_in_groups[layer["name"]],
                creator.layer_idx_padding,
                creator.layer_idx_offset,
                variant,
                self.log
            )
            if not render_pass:
                render_pass = {}

            render_pass["renderPass"] = renderpass
            render_pass["renderLayer"] = renderlayer

            product_name = creator.get_product_name(
                project_entity["name"],
                folder_entity,
                task_entity,
                variant,
                host_name=self.create_context.host_name,
                instance=render_pass,
                project_entity=project_entity,
            )

            instance_data: dict[str, str] = {
                "folderPath": folder_entity["path"],
                "task": task_name,
                "productType": creator.product_type,
                "variant": variant,
            }

            pre_create_data: dict[str, Any] = {
                "render_layer_instance_id": render_layer_instance.id,
                "layer_name": layer_name,
                "mark_for_review": mark_for_review,
                "render_target": render_target,
            }
            creator.create(product_name, instance_data, pre_create_data)

    def get_pre_create_attr_defs(self) -> list[AbstractAttrDef]:
        render_layer_creator: CreateRenderLayer = self.create_context.creators[
            CreateRenderLayer.identifier
        ]
        render_pass_creator: CreateRenderPass = self.create_context.creators[
            CreateRenderPass.identifier
        ]
        rendering_targets = {
            "local": "Local machine rendering",
            "farm": "Farm rendering",
        }
        return [
            BoolDef(
                "only_visible_groups",
                label="Only visible color groups",
                tooltip=(
                    "Render Layers will happen only on color"
                    " groups with visible layers."
                ),
                default=True
            ),
            BoolDef(
                "mark_layers_for_review",
                label="Mark RenderLayers for review",
                default=render_layer_creator.mark_for_review,
            ),
            BoolDef(
                "mark_passes_for_review",
                label="Mark RenderPasses for review",
                default=render_pass_creator.mark_for_review,
            ),
            EnumDef(
                "render_target",
                items=rendering_targets,
                label="Render target"
            )
        ]

    def product_impl(self, name, instance_data: dict, pre_create_data: dict):
        pass

    def _wrap_nodes_in_backdrop(self):
        """Tries to wrap all nodes of a layer group into Backdrop"""
        scene_containers = harmony.get_scene_data()
        for node_name, container in scene_containers.items():
            identifier = container["creator_identifier"]
            if identifier != CreateRenderLayer.identifier:
                continue
            group_label = container["variant"]
            group_id = container["creator_attributes"]["group_id"]
            group_color = group_id
            harmony.send(
                {
                    "function": (
                        "AyonHarmony.Creators.CreateRenderLayer.formatNodes"
                    ),
                    "args": [node_name, group_label, group_color]
                }
            )


# TODO refactor
def get_group_infos() -> list[GroupInfo]:
    """Lists all used layer colors to choose from"""
    # TODO cache this
    layers_data = get_layers_info()
    # to keep order
    ordered_colors = []
    for layer in layers_data:
        color = layer["color"]
        if color not in ordered_colors:
            ordered_colors.append(color)
    return [
        GroupInfo(color, idx + 1)
        for idx, color in enumerate(ordered_colors)
    ]


def get_group_position(
    group_id: str,
    group_infos: Optional[list[GroupInfo]] = None
) -> Optional[str]:
    """Find appropriate color for ordinal number of group"""
    if not group_infos:
        group_infos = get_group_infos()
    group_position = None
    for group_item in group_infos:
        if group_item.color == group_id:
            group_position = group_item.position
            break
    return group_position


def get_render_pass_name(
    pass_template: str,
    position_in_group: int,
    layer_idx_padding: int,
    layer_idx_offset: int,
    variant: str,
    log: logging.Logger,
) -> str:
    """Calculates render pass portion.

    It was designed to follow "L{layer_index}_{variant}"
    (L010_CHAR01_head)
    """
    new_name = None
    index_template = f"{{:0>{layer_idx_padding}}}"
    layer_pos = position_in_group * layer_idx_offset
    try:
        layer_index = index_template.format(layer_pos)
        new_name = pass_template.format(
            layer_index=layer_index,
            variant=variant
        )
    except Exception:
        log.warning("Failed to create new pass name", exc_info=True)

    return new_name


def get_layer_positions_in_groups(layers):
    layer_positions_in_groups = {}
    sorted_layers = sorted(
        layers,
        key=lambda layer: (layer["color"], layer["position"]),
        reverse=True
    )
    layer_idx_by_group = {}
    for layer in sorted_layers:
        color = layer["color"]
        layer_idx = layer_idx_by_group.setdefault(color, 1)
        layer_idx_by_group[color] += 1
        layer_positions_in_groups[layer["name"]] = layer_idx

    return layer_positions_in_groups
