import pyblish.api

import ayon_harmony.api as harmony

from ayon_core.pipeline import PublishXmlValidationError


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
        display_node_name = harmony.send(
            {"function": "node.getName", "args": "Top/Display"}
        )["result"]

        if not display_node_name:
            raise PublishXmlValidationError(self, "No display node named 'Top/Display'.")
        
        instance.data["display_node_name"] = display_node_name
