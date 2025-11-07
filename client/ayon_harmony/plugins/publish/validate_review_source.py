import pyblish.api

from ayon_core.pipeline import PublishXmlValidationError

import ayon_harmony.api as harmony


class ValidateTopDisplay(pyblish.api.InstancePlugin):
    """Ensures that there is a display node with `Top/Display`.

    This validator is used for simplified review creation workflow.

    It requires `ayon+settings://harmony/create/CreateReview` to be enabled.
    This creator produces instance of `review` product type, artist does not
    need create any instance manually if they have a `Top/Display` node
    in the scene.
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
