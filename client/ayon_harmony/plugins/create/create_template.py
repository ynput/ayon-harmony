from ayon_harmony.api import plugin


class CreateTemplate(plugin.HarmonyCreator):
    """Composite node for publishing to templates."""

    identifier = "io.ayon.creators.harmony.template"
    label = "Template"
    product_type = "harmony.template"