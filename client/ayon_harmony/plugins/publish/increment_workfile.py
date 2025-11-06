import os

import pyblish.api
from ayon_core.pipeline.publish import get_errored_plugins_from_context
from ayon_core.lib import version_up
import ayon_harmony.api as harmony


class IncrementWorkfile(pyblish.api.InstancePlugin):
    """Increment the current workfile.

    Saves the current scene with an increased version number in both
    local unzipped folder and creates zipped file in `work` area.

    Marks current unzipped folder with lower version to be deleted afterwards.
    It should be obsolete as it is fully copied to incremented folder.
    """

    label = "Increment Workfile"
    order = pyblish.api.IntegratorOrder + 9.0
    hosts = ["harmony"]
    families = ["workfile"]
    optional = True

    def process(self, instance):
        errored_plugins = get_errored_plugins_from_context(instance.context)
        if errored_plugins:
            raise RuntimeError(
                "Skipping incrementing current file because publishing failed."
            )

        current_local_dir = os.path.dirname(
            instance.context.data["currentFile"]
        )
        scene_dir = version_up(current_local_dir)

        scene_path = os.path.join(
            scene_dir, os.path.basename(scene_dir) + ".xstage"
        )

        harmony.save_scene_as(scene_path)

        # Mark unzipped temp workfile to be deleted
        instance.context.data["cleanupFullPaths"].append(current_local_dir)

        self.log.info("Incremented workfile to: {}".format(scene_path))
