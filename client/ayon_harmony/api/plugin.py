from ayon_core.pipeline import LegacyCreator
import ayon_harmony.api as harmony


class Creator(LegacyCreator):
    """Creator plugin to create instances in Harmony.

    By default a Composite node is created to support any number of nodes in
    an instance, but any node type is supported.
    If the selection is used, the selected nodes will be connected to the
    created node.
    """
    # TODO: Refactor to the new creator API

    defaults = ["Main"]
    node_type = "COMPOSITE"  # TODO remove this
    settings_category = "harmony"

    auto_connect = False
    composition_node_pattern = ""

    def setup_node(self, node):
        """Prepare node as container.

        Args:
            node (str): Path to node.
        """
        harmony.send(
            {
                "function": "AyonHarmonyAPI.setupNodeForCreator",
                "args": node
            }
        )

    def process(self):
        """Plugin entry point."""
        existing_node_names = harmony.send(
            {
                "function": "AyonHarmonyAPI.getNodesNamesByType",
                "args": self.node_type
            })["result"]

        # Dont allow instances with the same name.
        msg = "Instance with name \"{}\" already exists.".format(self.name)
        for name in existing_node_names:
            if self.name.lower() == name.lower():
                harmony.send(
                    {
                        "function": "AyonHarmonyAPI.message", "args": msg
                    }
                )
                return False

        backdrop = harmony.send(
            {
                "function": "AyonHarmonyAPI.createContainer",
                "args": [self.name, (self.options or {}).get("useSelection", False)]
            }
        )["result"]

        harmony.imprint(backdrop["title"]["text"], self.data)

        return backdrop
