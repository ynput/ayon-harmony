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


class CreateRenderLayerModel(BaseSettingsModel):
    """Creates single instance for all Harmony layers (read node) with same color coding.
    
    Attaches all these layers to composite note and adds write node to render it.
    """
    enabled: bool = SettingsField(False)
    active_on_create: bool = SettingsField(True, title="Active by default")
    mark_for_review: bool = SettingsField(True, title="Review by default")
    default_pass_name: str = SettingsField(title="Default beauty pass")
    default_variant: str = SettingsField(title="Default variant")
    default_variants: list[str] = SettingsField(
        default_factory=list, title="Default variants")
    

class CreateRenderPassModel(BaseSettingsModel):
    """Creates instance for each layer (read node) separately.
    
    It requires RenderLayer to be triggered first to be able to select matching group.
    """
    enabled: bool = SettingsField(False)
    active_on_create: bool = SettingsField(True, title="Active by default")
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


class AutoDetectCreateRenderModel(BaseSettingsModel):
    """The creator to auto-detect Render Layers and Render Passes in scene.

    For Render Layers is used group name as a variant and for Render Passes is
    used Harmony  layer name.

    Group names are renamed by their used order in scene. The renaming
    template where can be used '{group_index}' formatting key which is
    filled by "used position index of group".
    - Template: 'G{group_index}'
    - Group offset: '10'
    - Group padding: '3'

    Would create group names "G010", "G020", ...

    If this plugin is enabled, both 'CreateRenderLayer' and 'CreateRenderPass'
    must be enabled!

    To fully use this `ayon+settings://core/tools/creator/product_name_profiles` must
    contain `{product[type]}{Task[name]}_{Renderlayer}_{Renderpass}` for product types:
    ['renderLayer', 'renderPass']!
    """

    enabled: bool = SettingsField(False)
    group_name_template: str = SettingsField(
        "G{group_index}",
        title="Group name template",
        description="How color coded group name is calculated,"
    )
    group_idx_offset: int = SettingsField(
        10, title="Group index Offset", ge=1
    )
    group_idx_padding: int = SettingsField(
        3, title="Group index Padding", ge=0
    )
    render_pass_template: str = SettingsField(
        "L{layer_index}",
        title="RenderPass name template")
    layer_idx_offset: int = SettingsField(
        10, title="Layer index Offset", ge=1
    )
    layer_idx_padding: int = SettingsField(
        3, title="Layer index Padding", ge=0
    )
    layer_name_template: LayerNameTemplateModel = SettingsField(
        default_factory=LayerNameTemplateModel,
        title="Layer name template",
        description="Final layer template to parse out variant from already renamed layers or",
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
        title="RenderLayer",
        default_factory=CreateRenderLayerModel,
    )
    CreateRenderPass: CreateRenderPassModel = SettingsField(
        default_factory=CreateRenderPassModel,
        title="RenderPass"
    )
    AutoDetectRenderCreator: AutoDetectCreateRenderModel = SettingsField(
        default_factory=AutoDetectCreateRenderModel,
        title="Auto-Detect Create Render",
    )
