from ayon_server.settings import BaseSettingsModel, SettingsField


class CreateRenderPluginModel(BaseSettingsModel):
    enabled: bool = SettingsField(True, title="Enabled")
    active_on_create: bool = SettingsField(True, title="Active by default")
    default_variants: list[str] = SettingsField(
        default_factory=list,
        title="Default Variants"
    )
    auto_connect: bool = SettingsField(False,
                                       title="Auto connect to Composite node")
    composition_node_pattern: str = SettingsField(
        "Composite",
        title="Regex pattern for Composite node name",
        description="Provide regex pattern to find Composite node to "
                    "connect newly Write node to"
    )


class CreateAutoPluginModel(BaseSettingsModel):
    enabled: bool = SettingsField(False, title="Enabled")
    active_on_create: bool = SettingsField(True, title="Active by default")
    default_variants: list[str] = SettingsField(
        default_factory=list,
        title="Default Variants"
    )


class CreateRenderLayerModel(BaseSettingsModel):
    mark_for_review: bool = SettingsField(True, title="Review by default")
    default_pass_name: str = SettingsField(title="Default beauty pass")
    default_variant: str = SettingsField(title="Default variant")
    default_variants: list[str] = SettingsField(
        default_factory=list, title="Default variants")


class LayerNameTemplateModel(BaseSettingsModel):
    enabled: bool = SettingsField(False, title="Enabled")
    template: str = SettingsField(
        "G{group_index}_L{layer_index}_{variant}",
        title="Layer name template",
        description=(
            "Available keys '{group_index}' '{layer_index}' '{variant}'"
        ),
        placeholder="G{group_index}_L{layer_index}_{variant}",
    )


class CreateRenderPassModel(BaseSettingsModel):
    mark_for_review: bool = SettingsField(True, title="Review by default")
    default_variant: str = SettingsField(title="Default variant")
    default_variants: list[str] = SettingsField(
        default_factory=list, title="Default variants"
    )
    render_pass_template: str = SettingsField(
        "{variant}",
        title="Render pass name template",
        description="Available keys '{layer_index}' '{variant}'",
        placeholder="L{layer_index}_{variant}",
    )
    layer_name_template: LayerNameTemplateModel = SettingsField(
        default_factory=LayerNameTemplateModel,
        title="Layer name template",
        description="Automatically change TVPaint layer name using template.",
    )

    # Template settings section
    group_idx_offset: int = SettingsField(
        10, title="Group index Offset", ge=1,
        section="Template Settings"
    )
    group_idx_padding: int = SettingsField(
        3, title="Group index Padding", ge=0
    )
    layer_idx_offset: int = SettingsField(
        10, title="Layer index Offset", ge=1
    )
    layer_idx_padding: int = SettingsField(
        3, title="Layer index Padding", ge=0
    )


class AutoDetectCreateRenderModel(BaseSettingsModel):
    """The creator to auto-detect Render Layers and Render Passes in scene.

    For Render Layers is used group name as a variant and for Render Passes is
    used TVPaint layer name.

    Group names can be renamed by their used order in scene. The renaming
    template where can be used '{group_index}' formatting key which is
    filled by "used position index of group".
    - Template: 'G{group_index}'
    - Group offset: '10'
    - Group padding: '3'

    Would create group names "G010", "G020", ...
    """

    enabled: bool = SettingsField(True)
    allow_group_rename: bool = SettingsField(title="Allow group rename")
    group_name_template: str = SettingsField(title="Group name template")
    group_idx_offset: int = SettingsField(
        10, title="Group index Offset", ge=1
    )
    group_idx_padding: int = SettingsField(
        3, title="Group index Padding", ge=0
    )


class HarmonyCreatePlugins(BaseSettingsModel):
    CreateWorkfile: CreateAutoPluginModel = SettingsField(
        title="Workfile",
        default_factory=CreateAutoPluginModel,
    )
    CreateReview: CreateAutoPluginModel = SettingsField(
        title="Review",
        default_factory=CreateAutoPluginModel,
    )
    CreateRender: CreateRenderPluginModel = SettingsField(
        title="Render",
        default_factory=CreateRenderPluginModel,
    )
    CreateFarmRender: CreateRenderPluginModel = SettingsField(
        title="Render on Farm",
        default_factory=CreateRenderPluginModel,
    )

    CreateRenderLayer: CreateRenderLayerModel = SettingsField(
        default_factory=CreateRenderLayerModel,
        title="Create Render Layer"
    )
    CreateRenderPass: CreateRenderPassModel = SettingsField(
        default_factory=CreateRenderPassModel,
        title="Create Render Pass"
    )
    AutoDetectCreateRender: AutoDetectCreateRenderModel = SettingsField(
        default_factory=AutoDetectCreateRenderModel,
        title="Auto-Detect Create Render",
    )
