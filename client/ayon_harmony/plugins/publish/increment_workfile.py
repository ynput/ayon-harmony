import os

import pyblish.api

from ayon_core.host import IWorkfileHost
from ayon_core.pipeline import registered_host
from ayon_core.pipeline.publish import get_errored_plugins_from_context
from ayon_core.pipeline.workfile import save_next_version
from ayon_core.host.interfaces import SaveWorkfileOptionalData


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

        context = instance.context
        host: IWorkfileHost = registered_host()

        current_filepath: str = context.data["currentFile"]

        current_filename = os.path.basename(current_filepath)
        current_local_dir = os.path.dirname(current_filepath)
        save_next_version(
            description=(
                f"Incremented by publishing from {current_filename}"
            ),
            # Optimize the save by reducing needed queries for context
            prepared_data=SaveWorkfileOptionalData(
                project_entity=context.data["projectEntity"],
                project_settings=context.data["project_settings"],
                anatomy=context.data["anatomy"],
            )
        )
        new_scene_path = host.get_current_workfile()

        # Mark unzipped temp workfile to be deleted
        instance.context.data["cleanupFullPaths"].append(current_local_dir)

        self.log.info("Incremented workfile to: {}".format(new_scene_path))
