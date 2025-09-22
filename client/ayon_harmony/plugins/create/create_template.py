from ayon_harmony.api import plugin

import ayon_harmony.api as harmony


class CreateTemplate(plugin.HarmonyCreator):
    """Use existing Backdrop or create new one around selected nodes.
    
    Publishable template is marked as Backdrop wrapping node(s)
    """

    identifier = "io.ayon.creators.harmony.template"
    label = "Template"
    product_type = "harmony.template"
    icon = "cubes"

    def product_impl(self, name, instance_data: dict, pre_create_data: dict):
        args = [name, pre_create_data.get("use_selection") ]
        backdrop = harmony.send(
            {
                "function": "AyonHarmony.createBackdropContainer",
                "args": args
            }
        )["result"]

        return backdrop["title"]["text"]
    
    def remove_instances(self, instances):
        for instance in instances:
            container_name = instance.transient_data["node"]
            container_backdrop = harmony.find_backdrop_by_name(container_name)
            if container_backdrop:
                harmony.send(
                    {
                        "function": "AyonHarmony.removeBackdrop", 
                        "args": [container_backdrop, True]
                    }   
                )
            harmony.remove(container_name)
            self._remove_instance_from_context(instance)