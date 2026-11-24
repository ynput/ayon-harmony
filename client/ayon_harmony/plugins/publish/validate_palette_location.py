import pyblish.api

from ayon_core.pipeline import OptionalPyblishPluginMixin
from ayon_core.pipeline.publish import (
    ValidateContentsOrder,
    PublishXmlValidationError,
)


class ValidatePaletteLocation(
    pyblish.api.InstancePlugin,
    OptionalPyblishPluginMixin,
):
    """
    Validate that a palette is stored at scene level.

    Palettes stored at 'environment' or 'job' level
    are not versioned with the scene.
    """

    label = "Validate Palette Location"
    hosts = ["harmony"]
    families = ["harmony.palette"]
    order = ValidateContentsOrder
    optional = True

    invalid_storages = ["environment", "job"]

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        storage = instance.data.get("paletteStorage")

        if storage in self.invalid_storages:
            msg = (
                f"Found invalid palette location '{instance.name}' "
                f"is stored at '{storage}'"
            )
            formatting_data = {
                "palette_name": instance.name,
                "palette_location": storage,
            }
            raise PublishXmlValidationError(
                self, msg, formatting_data=formatting_data
            )
