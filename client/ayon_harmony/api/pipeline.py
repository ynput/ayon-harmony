import os
from pathlib import Path
import logging

import pyblish.api

from ayon_core.lib import register_event_callback
from ayon_core.host import (
    HostBase,
    IWorkfileHost,
    ILoadHost,
)
from ayon_core.pipeline import (
    register_loader_plugin_path,
    register_creator_plugin_path,
    deregister_loader_plugin_path,
    deregister_creator_plugin_path,
    AYON_CONTAINER_ID,
)
from ayon_core.pipeline.load import get_outdated_containers
from ayon_core.pipeline.context_tools import get_current_task_entity

from ayon_harmony import HARMONY_ADDON_ROOT
import ayon_harmony.api as harmony

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


class HarmonyHost(HostBase, IWorkfileHost, ILoadHost):
    name = "harmony"

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

    # def get_context_data(self):
    #     raise NotImplementedError()
    #
    # def update_context_data(self, data, changes):
    #     raise NotImplementedError()


def set_scene_settings(settings):
    """Set correct scene settings in Harmony.

    Args:
        settings (dict): Scene settings.

    Returns:
        dict: Dictionary of settings to set.

    """
    harmony.send(
        {"function": "AyonHarmony.setSceneSettings", "args": settings})


def get_current_context_settings():
    """Get settings on current task from server.

    Returns:
        dict[str, Any]: Scene data.

    """

    task_entity = get_current_task_entity()
    task_attributes = task_entity["attrib"]

    fps = task_attributes.get("fps")
    frame_start = task_attributes.get("frameStart")
    frame_end = task_attributes.get("frameEnd")
    handle_start = task_attributes.get("handleStart")
    handle_end = task_attributes.get("handleEnd")
    resolution_width = task_attributes.get("resolutionWidth")
    resolution_height = task_attributes.get("resolutionHeight")

    scene_data = {
        "fps": fps,
        "frameStart": frame_start,
        "frameEnd": frame_end,
        "handleStart": handle_start,
        "handleEnd": handle_end,
        "resolutionWidth": resolution_width,
        "resolutionHeight": resolution_height
    }

    return scene_data


def ensure_scene_settings():
    """Validate if Harmony scene has valid settings."""
    settings = get_current_context_settings()

    invalid_settings = []
    valid_settings = {}
    for key, value in settings.items():
        if value is None:
            invalid_settings.append(key)
        else:
            valid_settings[key] = value

    # Warn about missing attributes.
    if invalid_settings:
        msg = "Missing attributes:"
        for item in invalid_settings:
            msg += f"\n{item}"

        harmony.send(
            {"function": "AyonHarmony.message", "args": msg})

    set_scene_settings(valid_settings)


def check_inventory():
    """Check is scene contains outdated containers.

    If it does it will colorize outdated nodes and display warning message
    in Harmony.
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

    # Warn about outdated containers.
    msg = "There are outdated containers in the scene."
    harmony.send({"function": "AyonHarmony.message", "args": msg})


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

    # ensure_scene_settings()
    check_inventory()


def export_template(backdrops, nodes, filepath):
    """Export Template to file.

    Args:
        backdrops (list): List of backdrops to export.
        nodes (list): List of nodes to export.
        filepath (str): Path where to save Template.

    """
    harmony.send({
        "function": "AyonHarmony.exportTemplate",
        "args": [
            backdrops,
            nodes,
            os.path.basename(filepath),
            os.path.dirname(filepath)
        ]
    })


def install():
    """Install AYON Harmony as host config."""
    print("Installing AYON config ...")

    pyblish.api.register_host("harmony")
    pyblish.api.register_plugin_path(PUBLISH_PATH)
    register_loader_plugin_path(LOAD_PATH)
    register_creator_plugin_path(CREATE_PATH)
    log.info(PUBLISH_PATH)

    # Register callbacks.
    pyblish.api.register_callback(
        "instanceToggled", on_pyblish_instance_toggled
    )

    register_event_callback("application.launched", application_launch)


def uninstall():
    pyblish.api.deregister_plugin_path(PUBLISH_PATH)
    deregister_loader_plugin_path(LOAD_PATH)
    deregister_creator_plugin_path(CREATE_PATH)


def on_pyblish_instance_toggled(instance, old_value, new_value):
    """Toggle node enabling on instance toggles."""
    node = None
    if instance.data.get("setMembers"):
        node = instance.data["setMembers"][0]

    if node:
        harmony.send(
            {
                "function": "AyonHarmony.toggleInstance",
                "args": [node, new_value]
            }
        )


def inject_ayon_js():
    """Inject AyonHarmonyAPI.js into Harmony."""
    ayon_harmony_js = Path(__file__).parent.joinpath("js/AyonHarmonyAPI.js")
    script = ayon_harmony_js.read_text()
    # send AyonHarmonyAPI.js to Harmony
    harmony.send({"script": script})


def ls():
    """Yields containers from Harmony scene.

    Yields:
        dict: container
    """
    objects = harmony.get_scene_data() or {}
    for _, data in objects.items():
        # Skip non-tagged objects.
        if not data:
            continue

        # Filter to only containers.
        if "container" not in data.get("id"):
            continue

        if not data.get("objectName"):  # backward compatibility
            data["objectName"] = data["name"]
        yield data


def list_instances(remove_orphaned=True):
    """
        List all created instances from current workfile which
        will be published.

        Pulls from File > File Info

        For SubsetManager, by default it check if instance has matching node
        in the scene, if not, instance gets deleted from metadata.

        Returns:
            (list) of dictionaries matching instances format
    """
    # TODO: Remove this, refactor to new style Creators instead
    objects = harmony.get_scene_data() or {}
    instances = []
    for key, data in objects.items():
        # Skip non-tagged objects.
        if not data:
            continue

        # Filter out containers.
        if "container" in data.get("id"):
            continue

        data['uuid'] = key

        if remove_orphaned:
            node_name = key.split("/")[-1]
            located_node = harmony.find_node_by_name(node_name, 'WRITE')
            if not located_node:
                print("Removing orphaned instance {}".format(key))
                harmony.remove(key)
                continue

        instances.append(data)

    return instances


def remove_instance(instance):
    """
        Remove instance from current workfile metadata and from scene!

        Updates metadata of current file in File > File Info and removes
        icon highlight on group layer.

        For SubsetManager

        Args:
            instance (dict): instance representation from subsetmanager model
    """
    # TODO: Remove this, refactor to new style Creators instead
    node = instance.get("uuid")
    harmony.remove(node)
    harmony.delete_node(node)


def select_instance(instance):
    """
        Select instance in Node View

        Args:
            instance (dict): instance representation from subsetmanager model
    """
    # TODO: Remove this, refactor to new style Creators instead
    harmony.select_nodes([instance.get("uuid")])


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
        "nodes": nodes
    }

    harmony.imprint(node, data)

    return node
