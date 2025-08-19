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
