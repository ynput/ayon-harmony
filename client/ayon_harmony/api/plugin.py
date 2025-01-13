import re

from ayon_core.pipeline import LegacyCreator, CreatorError
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
    node_type = "COMPOSITE"
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

        with harmony.maintained_selection() as selection:
            node = None

            if (self.options or {}).get("useSelection") and selection:
                node = harmony.send(
                    {
                        "function": "AyonHarmonyAPI.createContainer",
                        "args": [self.name, self.node_type, selection[-1]]
                    }
                )["result"]
            elif (self.auto_connect):
                    existing_comp_names = harmony.send(
                    {
                        "function": "AyonHarmonyAPI.getNodesNamesByType",
                        "args": "COMPOSITE"
                    })["result"]
                    name_pattern = self.composition_node_pattern
                    if not name_pattern:
                        raise CreatorError("Composition name regex pattern "
                                           "must be filled")
                    compiled_pattern = re.compile(name_pattern)
                    matching_nodes = [name for name in existing_comp_names
                                      if compiled_pattern.match(name)]
                    if len(matching_nodes) > 1:
                        self.log.warning("Multiple composition node found, "
                                         "picked first")
                    elif len(matching_nodes) <= 0:
                        raise CreatorError("No matching composition "
                                           "node found")
                    node_name = f"/Top/{matching_nodes[0]}"

                    node = harmony.send(
                        {
                            "function": "AyonHarmonyAPI.createContainer",
                            "args": [self.name, self.node_type, node_name]
                        }
                    )["result"]
            else:
                node = harmony.send(
                    {
                        "function": "AyonHarmonyAPI.createContainer",
                        "args": [self.name, self.node_type]
                    }
                )["result"]

            harmony.imprint(node, self.data)
            self.setup_node(node)

        return node
