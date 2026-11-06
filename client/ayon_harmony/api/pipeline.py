import os
from pathlib import Path
import logging

from qtpy import QtWidgets

from ayon_core import style
from ayon_core.tools.utils.host_tools import (
    show_scene_inventory,
    show_workfiles,
)
import pyblish.api

from ayon_core.lib import is_headless_mode_enabled, register_event_callback
from ayon_core.host import (
    HostBase,
    IWorkfileHost,
    ILoadHost,
    IPublishHost,
)
from ayon_core.pipeline import (
    register_loader_plugin_path,
    register_creator_plugin_path,
    deregister_loader_plugin_path,
    deregister_creator_plugin_path,
    AVALON_CONTAINER_ID,
    AYON_CONTAINER_ID,
)
from ayon_core.pipeline.load import get_outdated_containers
from ayon_core.pipeline.context_tools import (
    get_current_folder_entity,
    get_current_task_entity,
)

from ayon_harmony import HARMONY_ADDON_ROOT
import ayon_harmony.api as harmony

from .lib import (
    ProcessContext,
    get_expected_settings,
    get_invalid_scene_settings,
    get_scene_data,
    is_temp_workfile,
    set_scene_data,
)
from .workio import (
    open_file,
    save_file,
    current_file,
    has_unsaved_changes,
    file_extensions,
    work_root
)

log = logging.getLogger("ayon_harmony")

PLUGINS_DIR = os.path.join(HARMONY_ADDON_ROOT, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")


class HarmonyHost(HostBase, IWorkfileHost, ILoadHost, IPublishHost):
    name = "harmony"

    _context_key = "AYON_context"

    def install(self):
        """Install Pype as host config."""
        print("Installing AYON Harmony Host ...")

        pyblish.api.register_host("harmony")
        pyblish.api.register_plugin_path(PUBLISH_PATH)
        register_loader_plugin_path(LOAD_PATH)
        register_creator_plugin_path(CREATE_PATH)

        register_event_callback("application.launched", application_launch)

    def uninstall(self):
        pyblish.api.deregister_plugin_path(PUBLISH_PATH)
        deregister_loader_plugin_path(LOAD_PATH)
        deregister_creator_plugin_path(CREATE_PATH)

    def open_workfile(self, filepath):
        return open_file(filepath)

    def save_workfile(self, filepath=None):
        return save_file(filepath)

    def work_root(self, session):
        return work_root(session)

    def get_current_workfile(self):
        return current_file()

    def workfile_has_unsaved_changes(self):
        return has_unsaved_changes()

    def get_workfile_extensions(self):
        return file_extensions()

    def get_containers(self):
        return ls()

    def get_context_data(self):
        return get_scene_data().get(self._context_key, {})

    def update_context_data(self, data, changes):
        scene_data = get_scene_data()
        context_data = scene_data.setdefault(self._context_key, {})
        context_data.update(data)
        set_scene_data(scene_data)


def set_scene_settings(settings):
    """Set correct scene settings in Harmony.

    Args:
        settings (dict): Scene settings.

    """
    harmony.send(
        {"function": "AyonHarmony.setSceneSettings", "args": settings})


def get_current_context_settings():
    """Get settings on current task from server.

    Returns:
        dict[str, Any]: Scene data.

    """
    task_attributes = get_current_task_entity()["attrib"]
    return {
        "fps": task_attributes.get("fps"),
        "frameStart": task_attributes.get("frameStart"),
        "frameEnd": task_attributes.get("frameEnd"),
        "handleStart": task_attributes.get("handleStart"),
        "handleEnd": task_attributes.get("handleEnd"),
        "resolutionWidth": task_attributes.get("resolutionWidth"),
        "resolutionHeight": task_attributes.get("resolutionHeight"),
    }


def ensure_scene_settings():
    """Apply current task settings to the current Harmony scene."""
    settings = get_current_context_settings()
    missing = [key for key, value in settings.items() if value is None]
    if missing:
        harmony.send({
            "function": "AyonHarmony.message",
            "args": "Missing attributes:\n" + "\n".join(missing),
        })
        return

    set_scene_settings(get_expected_settings(settings))


def _prompt_simple_choice(
    title, text, accept_label, reject_label, informative_text=None
):
    """Show a modal warning dialog with two choices.

    Returns:
        bool: True if the accept button was clicked, False otherwise
            (including when skipped in headless mode).
    """
    if is_headless_mode_enabled():
        return False

    msg_box = QtWidgets.QMessageBox()
    msg_box.setStyleSheet(style.load_stylesheet())
    msg_box.setIcon(QtWidgets.QMessageBox.Warning)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    if informative_text:
        msg_box.setInformativeText(informative_text)

    accept_button = msg_box.addButton(
        accept_label, QtWidgets.QMessageBox.AcceptRole
    )
    msg_box.addButton(reject_label, QtWidgets.QMessageBox.RejectRole)
    msg_box.setDefaultButton(accept_button)
    msg_box.setModal(True)
    msg_box.exec_()

    return msg_box.clickedButton() == accept_button


def prompt_outdated_containers():
    """Show outdated containers warning with option to open Scene Inventory."""
    if _prompt_simple_choice(
        title="Outdated Containers",
        text="There are outdated containers in the scene.",
        accept_label="Manage",
        reject_label="Dismiss",
    ):
        show_scene_inventory()


def prompt_new_workfile():
    """Prompt user that they are working on the temporary workfile."""
    if _prompt_simple_choice(
        title="New Workfile",
        text="You are working on a new, unsaved workfile.",
        accept_label="Open Workfiles Window",
        reject_label="Ignore",
        informative_text=(
            "Open the Workfiles window to save it, or continue working "
            "on the temporary scene."
        ),
    ):
        show_workfiles(save=True)


def prompt_scene_settings(invalid_settings: dict) -> None:
    """Ask whether to apply task scene settings to the scene.

    Args:
        invalid_settings (dict): Setting name mapped to (expected, found).

    """
    details = "\n".join(
        f"{key} expected: {expected}  found: {found}"
        for key, (expected, found) in invalid_settings.items()
    )
    if _prompt_simple_choice(
        title="Scene Settings",
        text="Scene settings differ from the task settings.",
        accept_label="Apply Task Settings",
        reject_label="Keep Current",
        informative_text=details,
    ):
        ensure_scene_settings()


def ensure_scene_settings_on_open() -> None:
    """Apply or confirm scene settings when a scene is opened.

    New scenes get the task settings applied automatically. Existing
    workfiles show a dialog when their settings differ from the task.
    """
    invalid_settings = get_invalid_scene_settings(
        get_current_context_settings(),
        get_current_task_entity()["name"],
        get_current_folder_entity()["path"],
    )
    if not invalid_settings:
        return

    if is_headless_mode_enabled():
        details = "\n".join(
            f"{key} expected: {expected}  found: {found}"
            for key, (expected, found) in invalid_settings.items()
        )
        log.warning("Scene settings differ from task settings:\n%s", details)
        return

    if not current_file():
        ensure_scene_settings()
        return

    ProcessContext.execute_in_main_thread(
        lambda: prompt_scene_settings(invalid_settings)
    )


def check_inventory():
    """Check is scene contains outdated containers.

    If it does it will colorize outdated nodes and optionally display a
    warning dialog.
    """

    outdated_containers = get_outdated_containers()
    if not outdated_containers:
        return

    # Colour nodes.
    outdated_nodes = []
    for container in outdated_containers:
        if container["loader"] == "ImageSequenceLoader":
            outdated_nodes.append(
                harmony.find_node_by_name(container["name"], "READ")
            )
    harmony.send({"function": "AyonHarmony.setColor", "args": outdated_nodes})

    ProcessContext.execute_in_main_thread(prompt_outdated_containers)


def application_launch(event):
    """Event that is executed after Harmony is launched."""
    # fills AYON_HARMONY_JS
    ayon_harmony_path = Path(__file__).parent.parent / "js" / "AyonHarmony.js"
    ayon_harmony_js = ayon_harmony_path.read_text()

    # go through js/creators, loaders and publish folders and load all scripts
    script = ""
    for item in ["creators", "loaders", "publish"]:
        dir_to_scan = Path(__file__).parent.parent / "js" / item
        for child in dir_to_scan.iterdir():
            script += child.read_text()

    # send scripts to Harmony
    harmony.send({"script": ayon_harmony_js})
    harmony.send({"script": script})
    inject_ayon_js()

    ensure_scene_settings_on_open()
    check_inventory()

    if is_temp_workfile(ProcessContext.workfile_path):
        ProcessContext.execute_in_main_thread(prompt_new_workfile())


def export_backdrop_as_template(backdrop, filepath):
    """Export Backdrop as Template (.tpl) file.

    Args:
        backdrop (list): Backdrop to export.
        filepath (str): Path where to save Template.
    """
    harmony.send({
        "function": "AyonHarmony.exportBackdropAsTemplate",
        "args": [
            backdrop,
            os.path.basename(filepath),
            os.path.dirname(filepath)
        ]
    })


def inject_ayon_js():
    """Inject AyonHarmonyAPI.js into Harmony."""
    ayon_harmony_js = Path(__file__).parent.joinpath("js/AyonHarmonyAPI.js")
    script = ayon_harmony_js.read_text()
    # send AyonHarmonyAPI.js to Harmony
    harmony.send({"script": script})


def is_container_data(data: dict) -> bool:
    """Return whether data is container data."""
    return data and data.get("id") in {AYON_CONTAINER_ID, AVALON_CONTAINER_ID}


def ls():
    """Yields containers from Harmony scene.

    Clean up scene data from orphaned containers.

    Yields:
        dict: container
    """
    scene_data = harmony.get_scene_data() or dict()
    containers_names = (
        harmony.get_all_top_names() | harmony.get_palettes_paths()
    )
    cleaned_scene_data = False
    for entity_name, entity_data in scene_data.copy().items():
        if not is_container_data(entity_data):
            continue

        # Filter orphaned containers
        if entity_name not in containers_names:
            del scene_data[entity_name]
            cleaned_scene_data = True
            continue

        if not entity_data.get("objectName"):  # backward compatibility
            entity_data["objectName"] = entity_data["name"]
        yield entity_data

    # Update scene data if cleaned
    if cleaned_scene_data:
        harmony.set_scene_data(scene_data)


def containerise(name,
                 namespace,
                 node,
                 context,
                 loader=None,
                 suffix=None,
                 nodes=None):
    """Imprint node with metadata.

    Containerisation enables a tracking of version, author and origin
    for loaded product representations.

    Arguments:
        name (str): Name of resulting assembly.
        namespace (str): Namespace under which to host container.
        node (str): Node to containerise.
        context (dict): Loaded representation full context information.
        loader (str, optional): Name of loader used to produce this container.
        suffix (str, optional): Suffix of container, defaults to `_CON`.

    Returns:
        container (str): Path of container assembly.
    """
    if not nodes:
        nodes = []

    data = {
        "schema": "openpype:container-2.0",
        "id": AYON_CONTAINER_ID,
        "name": name,
        "namespace": namespace,
        "loader": str(loader),
        "representation": context["representation"]["id"],
        "nodes": nodes,
        "project_name": context["project"]["name"],
    }

    harmony.imprint(node, data)

    return node
