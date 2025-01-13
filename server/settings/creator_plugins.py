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
        "Composition",
        title="Regex pattern for Composite node name",
        description="Provide regex pattern to find Composite node to connect newly Write node to"
    )


class HarmonyCreatePlugins(BaseSettingsModel):
    CreateRender: CreateRenderPluginModel = SettingsField(
        title="Render",
        default_factory=CreateRenderPluginModel,
    )
    CreateFarmRender: CreateRenderPluginModel = SettingsField(
        title="Render on Farm",
        default_factory=CreateRenderPluginModel,
    )


DEFAULT_CREATE_SETTINGS = {
    "CreateRender": {
        "enabled": True,
        "default_variants": [
            "Main"
        ],
        "auto_connect": False,
        "composition_node_pattern": "Composition"
    },
    "CreateFarmRender": {
        "enabled": True,
        "default_variants": [
            "Main"
        ],
        "auto_connect": False,
        "composition_node_pattern": "Composition"
    }
}
