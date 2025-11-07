import pyblish.api

from ayon_core.pipeline import PublishXmlValidationError

import ayon_harmony.api as harmony


class ValidateTopDisplay(pyblish.api.InstancePlugin):
    """Ensures that there is an display node with `Top/Display`.

    Will be used for automatic review creation
    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Top Display"
    families = ["review"]
    hosts = ["harmony"]
    settings_category = "harmony"

    def process(self, instance):
        if instance.data["productType"] != "review":
            self.log.debug("Not primary `review` product type, skipping.")
            return

        display_node_name = harmony.send(
            {"function": "node.getName", "args": "Top/Display"}
        )["result"]

        if not display_node_name:
            raise PublishXmlValidationError(
                self, "No display node named 'Top/Display'."
            )

        instance.data["display_node_name"] = display_node_name
