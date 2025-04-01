import os

import pyblish.api

import ayon_harmony.api as harmony

from ayon_core.pipeline import OptionalPyblishPluginMixin, PublishXmlValidationError


class ValidateAudio(pyblish.api.InstancePlugin, OptionalPyblishPluginMixin):
    """Ensures that there is an audio file in the scene.

    If you are sure that you want to send render without audio, you can
    disable this validator before clicking on "publish"
    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Audio"
    families = ["render"]
    hosts = ["harmony"]
    settings_category = "harmony"
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        node = None
        if instance.data.get("setMembers"):
            node = instance.data["setMembers"][0]

        if not node:
            return
        
        audio_path = harmony.send(
            {"function": "AyonHarmony.getSceneSoundtrackPath"}
        )["result"]

        if not os.path.isfile(audio_path):
            raise PublishXmlValidationError(self, "No sound file found in the scene.")
        