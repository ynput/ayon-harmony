"""Host API required Work Files tool"""
import os
from pathlib import Path
from typing import Optional
import shutil

from .lib import (
    ProcessContext,
    get_local_harmony_path,
    is_temp_workfile,
    zip_and_move,
    launch_zip_file
)

# used to lock saving until previous save is done.
save_disabled = False


def file_extensions():
    return [".zip"]


def has_unsaved_changes() -> bool:
    if current_file() and ProcessContext.server:
        return ProcessContext.server.send(
            {"function": "scene.isDirty"})["result"]

    return False


def save_file(filepath):
    global save_disabled
    if save_disabled:
        return ProcessContext.server.send(
            {
                "function": "show_message",
                "args": "Saving in progress, please wait until it finishes."
            })["result"]

    save_disabled = True
    cache_path = get_local_harmony_path(filepath)

    if ProcessContext.server:
        if os.path.exists(cache_path):
            try:
                shutil.rmtree(cache_path)
            except Exception as e:
                raise Exception(f"cannot delete {cache_path}") from e

        ProcessContext.server.send(
            {"function": "scene.saveAs", "args": [cache_path]}
        )

        zip_and_move(cache_path, filepath)

        ProcessContext.workfile_path = filepath

        scene_path = os.path.join(
            cache_path, os.path.basename(cache_path) + ".xstage"
        )
        ProcessContext.server.send(
            {"function": "AyonHarmonyAPI.addPathToWatcher", "args": scene_path}
        )
    else:
        temp_path = Path(get_local_harmony_path("temp"))
        temp_scene_file = temp_path.joinpath("temp.xstage")

        # Rename temp scene file to the new file name
        temp_scene_file = temp_scene_file.rename(
            temp_scene_file.with_name(Path(filepath).stem + ".xstage")
        )

        # Zip to work folder
        zip_and_move(temp_path, filepath)

        # Rename temp scene file back to temp.xstage
        temp_scene_file.rename(temp_path.joinpath("temp.xstage"))

        os.environ["HARMONY_NEW_WORKFILE_PATH"] = filepath.replace("\\", "/")

    save_disabled = False


def open_file(filepath):
    launch_zip_file(filepath)


def current_file() -> Optional[str]:
    """Get path of the currently opened workfile.

    Returns:
        Optional[str]: Workfile path, None for an unsaved scene.

    """
    if (workfile := ProcessContext.workfile_path) is None:
        return None

    if is_temp_workfile(workfile):
        return None

    return workfile


def work_root(session):
    return os.path.normpath(session["AYON_WORKDIR"]).replace("\\", "/")
