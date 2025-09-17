import time

import pyblish.api
import ayon_harmony.api as harmony


class ExtractSaveScene(pyblish.api.ContextPlugin):
    """Save scene for extraction."""

    label = "Extract Save Scene"
    order = pyblish.api.ExtractorOrder - 0.49
    hosts = ["harmony"]

    def process(self, context):
        harmony.save_scene()  
        time.sleep(2)  # try to limit broken save to binary
