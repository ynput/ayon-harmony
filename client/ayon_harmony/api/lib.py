# -*- coding: utf-8 -*-
"""Utility functions used for AYON - Harmony integration."""
from pathlib import Path
import platform
import subprocess
import threading
import os
import random
import zipfile
import sys
import filecmp
import shutil
import logging
import contextlib
import json
import signal
import time
from uuid import uuid4
import collections
from typing import Optional
from functools import lru_cache

from qtpy import QtWidgets, QtCore, QtGui

from ayon_core.lib import (
    is_using_ayon_console,
    env_value_to_bool,
    register_event_callback,
)
from ayon_core.tools.stdout_broker import StdOutBroker
from ayon_core.tools.utils import host_tools
from ayon_core import style

# Function 'save_next_version' is used by javascript integration
from ayon_core.pipeline.workfile import save_next_version  # noqa: F401

from ayon_harmony import HARMONY_ADDON_ROOT

from .server import Server

# Setup logging.
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class ProcessContext:
    server = None
    pid = None
    process = None
    application_path = None
    callback_queue = collections.deque()
    workfile_path = None
    port = None
    stdout_broker = None
    workfile_tool = None

    @classmethod
    def execute_in_main_thread(cls, func_to_call_from_main_thread):
        cls.callback_queue.append(func_to_call_from_main_thread)

    @classmethod
    def main_thread_listen(cls):
        if cls.callback_queue:
            callback = cls.callback_queue.popleft()
            callback()
        if cls.process is not None and cls.process.poll() is not None:
            log.info("Server is not running, closing")
            ProcessContext.stdout_broker.stop()


def _on_application_close():
    """Gracefully close Harmony launch process on explicit close event."""
    if (
        ProcessContext.process is not None
        and ProcessContext.process.poll() is None
    ):
        try:
            ProcessContext.process.terminate()
            ProcessContext.process.wait(timeout=10)
        except Exception:
            try:
                ProcessContext.process.kill()
            except Exception:
                pass

    if ProcessContext.server:
        try:
            ProcessContext.server.stop()
        except Exception:
            pass

    if ProcessContext.stdout_broker:
        try:
            ProcessContext.stdout_broker.stop()
        except Exception:
            pass

    QtWidgets.QApplication.quit()


def signature(postfix="func") -> str:
    """Return random ECMA6 compatible function name.

    Args:
        postfix (str): name to append to random string.
    Returns:
        str: random function name.

    """
    return "f{}_{}".format(str(uuid4()).replace("-", "_"), postfix)


class _ZipFile(zipfile.ZipFile):
    """Extended check for windows invalid characters."""

    # this is extending default zipfile table for few invalid characters
    # that can come from Mac
    _windows_illegal_characters = ":<>|\"?*\r\n\x00"
    _windows_illegal_name_trans_table = str.maketrans(
        _windows_illegal_characters,
        "_" * len(_windows_illegal_characters)
    )


def main(*subprocess_args):
    # coloring in StdOutBroker
    os.environ["AYON_LOG_NO_COLORS"] = "0"
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    icon = QtGui.QIcon(style.get_app_icon_path())
    app.setWindowIcon(icon)

    ProcessContext.stdout_broker = StdOutBroker('harmony')
    ProcessContext.stdout_broker.start()
    register_event_callback("application.close", _on_application_close)
    launch(*subprocess_args)

    loop_timer = QtCore.QTimer()
    loop_timer.setInterval(20)

    loop_timer.timeout.connect(ProcessContext.main_thread_listen)
    loop_timer.start()

    sys.exit(app.exec_())


def setup_startup_scripts():
    """Manages installation of ayon's TB_sceneOpened.js for Harmony launch.

    If a studio already has defined "TOONBOOM_GLOBAL_SCRIPT_LOCATION", copies
    the TB_sceneOpened.js to that location if the file is different.
    Otherwise, will set the env var to point to the ayon/harmony folder.

    Admins should be aware that this will overwrite TB_sceneOpened in the
    "TOONBOOM_GLOBAL_SCRIPT_LOCATION", and that if they want to have additional
    logic, they will need to one of the following:
        * Create a Harmony package to manage startup logic
        * Use TB_sceneOpenedUI.js instead to manage startup logic
        * Add their startup logic to ayon/harmony/TB_sceneOpened.js
    """
    ayon_host_dir = os.path.join(HARMONY_ADDON_ROOT, "api")
    startup_js = "TB_sceneOpened.js"

    env_location = os.getenv("TOONBOOM_GLOBAL_SCRIPT_LOCATION")
    if not env_location:
        os.environ["TOONBOOM_GLOBAL_SCRIPT_LOCATION"] = ayon_host_dir
        return

    ayon_harmony_startup = os.path.join(ayon_host_dir, startup_js)
    env_harmony_startup = os.path.join(env_location, startup_js)

    # Check if destination file exists or if files are the same
    if (
        os.path.exists(env_harmony_startup)
        and filecmp.cmp(ayon_harmony_startup, env_harmony_startup)
    ):
        return

    try:
        shutil.copy(ayon_harmony_startup, env_harmony_startup)
    except Exception:
        log.warning(
            f"Failed to copy {ayon_harmony_startup} to {env_harmony_startup}!"
            " Defaulting to AYON's TOONBOOM_GLOBAL_SCRIPT_LOCATION.",
            exc_info=True
        )

        os.environ["TOONBOOM_GLOBAL_SCRIPT_LOCATION"] = ayon_host_dir


def check_libs():
    """Check if `OpenHarmony`_ is available.

    AYON expects either path in `LIB_OPENHARMONY_PATH` or `openHarmony.js`
    present in `TOONBOOM_GLOBAL_SCRIPT_LOCATION`.

    Throws:
        RuntimeError: If openHarmony is not found.

    .. _OpenHarmony:
        https://github.com/cfourney/OpenHarmony

    """
    if os.getenv("LIB_OPENHARMONY_PATH"):
        return

    script_location = os.getenv("TOONBOOM_GLOBAL_SCRIPT_LOCATION")
    if not script_location:
        log.error(
            "Cannot find OpenHarmony library."
            " Please set path to it in LIB_OPENHARMONY_PATH"
            " environment variable."
        )
        raise RuntimeError("Missing OpenHarmony library.")

    script_path = os.path.join(script_location, "openHarmony.js")
    if os.path.exists(script_path):
        os.environ["LIB_OPENHARMONY_PATH"] = script_location


def launch(application_path, *args):
    """Set Harmony for launch.

    Launches Harmony and the server, then starts listening on the main thread
    for callbacks from the server. This is to have Qt applications run in the
    main thread.

    Args:
        application_path (str): Path to Harmony.

    """
    from ayon_core.pipeline import install_host
    from ayon_harmony.api import HarmonyHost

    install_host(HarmonyHost())

    ProcessContext.port = random.randrange(49152, 65535)
    os.environ["AYON_HARMONY_PORT"] = str(ProcessContext.port)
    ProcessContext.application_path = application_path

    # Launch Harmony.
    setup_startup_scripts()
    check_libs()

    if len(args) > 0 and (scene_path := Path(args[-1])).suffix == ".zip":
        launch_zip_file(scene_path)

    open_workfile_app = env_value_to_bool("AYON_HARMONY_WORKFILES_ON_LAUNCH")
    workfile_already_open = ProcessContext.workfile_path
    if open_workfile_app or not workfile_already_open:
        ProcessContext.workfile_tool = host_tools.get_tool_by_name(
            "workfiles"
        )
        host_tools.show_workfiles(save=True)
        ProcessContext.execute_in_main_thread(check_workfiles_tool)


def check_workfiles_tool():
    if ProcessContext.workfile_tool.isVisible():
        ProcessContext.execute_in_main_thread(check_workfiles_tool)
    elif not ProcessContext.workfile_path:
        open_empty_workfile()


def open_empty_workfile():
    zip_file = os.path.join(os.path.dirname(__file__), "temp.zip")
    temp_path = get_local_harmony_path(zip_file)
    if os.path.exists(temp_path):
        log.info(f"removing existing {temp_path}")
        try:
            shutil.rmtree(temp_path)
        except Exception as e:
            log.critical(f"cannot clear {temp_path}")
            raise Exception(f"cannot clear {temp_path}") from e

    launch_zip_file(zip_file)


def get_local_harmony_path(filepath):
    """From the provided path get the equivalent local Harmony path."""
    basename = os.path.splitext(os.path.basename(filepath))[0]
    harmony_path = os.path.join(os.path.expanduser("~"), ".ayon", "harmony")
    return os.path.join(harmony_path, basename)


def localize_file(filepath):
    """Copy file to local temp location for faster processing.

    Args:
        filepath (str): Path to the file (possibly on network).

    Returns:
        str: Path to localized file, or original if already local.
    """
    local_scene_dir_path = os.path.join(
        os.path.expanduser("~"), ".ayon", "harmony"
    )
    os.makedirs(local_scene_dir_path, exist_ok=True)

    local_zip = os.path.join(local_scene_dir_path, os.path.basename(filepath))
    log.info(f"Copying {filepath} to {local_zip}")

    copy_with_progress(filepath, local_zip)
    return local_zip


def copy_with_progress(src, dst):
    """Copy file with a progress bar dialog.

    Args:
        src (str): Source file path.
        dst (str): Destination file path.
    """
    file_size = os.path.getsize(src)

    progress = QtWidgets.QProgressDialog(
        f"Copying {os.path.basename(src)}...",
        None,
        0,
        100
    )
    progress.setStyleSheet(style.load_stylesheet())
    progress.setWindowTitle("Transferring File")
    progress.setWindowModality(QtCore.Qt.WindowModal)
    progress.setMinimumDuration(0)
    progress.setValue(0)
    progress.setCancelButton(None)

    chunk_size = 1024 * 1024  # 1MB chunks
    bytes_copied = 0

    try:
        with open(src, 'rb') as fsrc:
            with open(dst, 'wb') as fdst:
                last_process_events = time.monotonic()
                while True:
                    chunk = fsrc.read(chunk_size)
                    if not chunk:
                        break

                    fdst.write(chunk)
                    bytes_copied += len(chunk)

                    if file_size > 0:
                        percent = int((bytes_copied / file_size) * 100)
                    else:
                        # Handle empty source file gracefully
                        percent = 100

                    progress.setValue(percent)

                    # Process Qt events to keep UI responsive
                    now = time.monotonic()
                    if now - last_process_events >= 0.05:
                        QtWidgets.QApplication.processEvents(
                            QtCore.QEventLoop.AllEvents, 50
                        )
                        last_process_events = now

        shutil.copystat(src, dst)

    except Exception:
        # Remove partially written destination file to avoid corrupted state
        try:
            if os.path.exists(dst):
                os.remove(dst)
        except OSError as cleanup_error:
            # Log but don't mask the original exception
            print(
                "Warning: Failed to remove partial file "
                f"'{dst}': {cleanup_error}"
            )
        raise  # Re-raise the original exception to the caller

    finally:
        progress.close()

    log.info(f"Successfully copied {src} to {dst}")


def unzip_scene_file(filepath: str, headless: bool = False) -> str:
    """Unzip a Harmony scene file and return the path to the .xstage file.

    Args:
        filepath (str): Path to the zip file.
        headless (bool): If True, run without any UI interaction. When a
            local cache exists with the same or newer timestamp, the local
            version will be used automatically. Defaults to False.

    Returns:
        str: Path to the .xstage file.

    Raises:
        Exception: If no .xstage file is found or if the working
            folder cannot be deleted.

    """
    print(f"Localizing {filepath}")

    local_scene_dir_path = Path(get_local_harmony_path(filepath))
    scene_path = local_scene_dir_path.joinpath(
        f"{local_scene_dir_path.name}.xstage"
    )

    unzip = True
    if scene_path.exists():
        # Check remote scene is newer than local.
        if scene_path.stat().st_mtime < Path(filepath).stat().st_mtime:
            # Remote is newer, delete local and unzip
            try:
                shutil.rmtree(local_scene_dir_path)
            except Exception as e:
                log.error(e)
                raise Exception(
                    f"Cannot delete working folder: {local_scene_dir_path}"
                ) from e
            unzip = True
        elif headless:
            # Local is newer or same timestamp - use local cache automatically
            log.info(
                "Headless mode: local cache is newer or same timestamp "
                "as server version. Using local cache."
            )
            unzip = False
        else:
            # Local is newer or same timestamp - ask user
            msg_box = QtWidgets.QMessageBox()
            msg_box.setStyleSheet(style.load_stylesheet())
            msg_box.setIcon(QtWidgets.QMessageBox.Question)
            msg_box.setWindowTitle("Local cache of version exists")
            msg_box.setText(
                "A cached version of this scene exists that is newer or "
                "with the same timestamp as the server version."
            )
            msg_box.setInformativeText(
                "Do you want to use the local file or "
                "re-cache from the server?"
            )
            msg_box.setStandardButtons(
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            msg_box.setDefaultButton(QtWidgets.QMessageBox.Yes)

            msg_box.button(QtWidgets.QMessageBox.Yes).setText("Use Local")
            msg_box.button(QtWidgets.QMessageBox.No).setText("From Server")

            msg_box.setModal(True)

            result = msg_box.exec_()

            if result == QtWidgets.QMessageBox.No:
                try:
                    shutil.rmtree(local_scene_dir_path)
                except Exception as e:
                    log.error(e)
                    raise Exception(
                       f"Cannot delete working folder '{local_scene_dir_path}'"
                    ) from e
                unzip = True
            else:
                unzip = False

    if unzip:
        filepath = localize_file(filepath)
        with _ZipFile(filepath, "r") as zip_ref:
            names = zip_ref.namelist()
            main_name = next(
                Path(name).stem
                for name in names
                if name.endswith(".xstage")
            )

            # Detect if the archive is wrapped in a single root directory
            # named after `main_name`. When it is, we extract into the
            # parent of the local scene dir so the (renamed) root dir
            # becomes the local scene dir itself.
            has_root_dir = all(
                name == f"{main_name}/"
                or name.startswith(f"{main_name}/")
                for name in names
            )
            extract_root = (
                local_scene_dir_path.parent
                if has_root_dir
                else local_scene_dir_path
            )
            new_name = local_scene_dir_path.name

            for zip_info in zip_ref.infolist():
                # Only rename entries at the top level of the archive.
                # Subdirectory contents are left untouched so that
                # similarly-named paths inside the scene are preserved.
                head, sep, tail = zip_info.filename.partition("/")
                if sep:
                    # Nested path: only rename when the first segment
                    # is the archive's root directory.
                    if head == main_name:
                        zip_info.filename = f"{new_name}/{tail}"
                elif Path(head).stem == main_name:
                    # Top-level file named like `{main_name}.<ext>`.
                    zip_info.filename = f"{new_name}{Path(head).suffix}"

                zip_ref.extract(zip_info, extract_root)

                # Keep the first xstage file as the scene path
                if not scene_path and zip_info.filename.endswith(".xstage"):
                    scene_path = Path(extract_root).joinpath(zip_info.filename)

    if not scene_path:
        raise Exception("No xstage file was found.")

    return scene_path.as_posix()


def launch_zip_file(filepath):
    """Launch a Harmony application instance with the provided zip file.

    Args:
        filepath (str): Path to file.
    """
    # Close existing scene.
    if ProcessContext.pid:
        os.kill(ProcessContext.pid, signal.SIGTERM)

    # Stop server.
    if ProcessContext.server:
        ProcessContext.server.stop()

    # Launch AYON server.
    ProcessContext.server = Server(ProcessContext.port)
    ProcessContext.server.start()
    # thread = threading.Thread(target=self.server.start)
    # thread.daemon = True
    # thread.start()

    # Save workfile path for later.
    ProcessContext.workfile_path = filepath

    # Unzip the scene file and get the .xstage path
    try:
        scene_path = unzip_scene_file(filepath)
    except Exception as e:
        print(f"Error unzipping scene file: {e}")
        ProcessContext.server.stop()
        return

    print("Launching {}".format(scene_path))
    # QUESTION Could we use 'run_detached_process' from 'ayon_core.lib'?
    kwargs = {}
    if (
        platform.system().lower() == "windows"
        and not is_using_ayon_console()
    ):
        kwargs.update({
            "creationflags": subprocess.CREATE_NO_WINDOW,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL
        })

    process = subprocess.Popen(
        [ProcessContext.application_path, scene_path],
        **kwargs
    )
    ProcessContext.pid = process.pid
    ProcessContext.process = process
    ProcessContext.stdout_broker.host_connected()


def on_file_changed(path, threaded=True):
    """Threaded zipping and move of the project directory.

    This method is called when the `.xstage` file is changed.
    """
    log.debug("File changed: " + path)

    if ProcessContext.workfile_path is None:
        return

    if threaded:
        thread = threading.Thread(
            target=zip_and_move,
            args=(os.path.dirname(path), ProcessContext.workfile_path)
        )
        thread.start()
    else:
        zip_and_move(os.path.dirname(path), ProcessContext.workfile_path)


def zip_and_move(source, destination):
    """Zip a directory and move to `destination`.

    Args:
        source (str): Directory to zip and move to destination.
        destination (str): Destination file path to zip file.

    """
    zip_file = os.path.basename(source) + ".zip"
    zip_path = os.path.join(os.path.dirname(source), zip_file)

    file_list = []
    for root, dirs, files in os.walk(source):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, source)
            file_list.append((file_path, arcname))

    progress = QtWidgets.QProgressDialog(
        "Archiving scene files...",
        None,
        0,
        max(1, len(file_list))
    )
    progress.setStyleSheet(style.load_stylesheet())
    progress.setWindowTitle("Creating Archive")
    progress.setWindowModality(QtCore.Qt.WindowModal)
    progress.setMinimumDuration(0)
    progress.setCancelButton(None)

    try:
        with _ZipFile(zip_path, 'w', zipfile.ZIP_STORED) as zipf:
            last_process_events = time.monotonic()
            for idx, (file_path, arcname) in enumerate(file_list):
                zipf.write(file_path, arcname)
                progress.setValue(idx + 1)
                now = time.monotonic()
                if now - last_process_events >= 0.05:
                    QtWidgets.QApplication.processEvents(
                        QtCore.QEventLoop.AllEvents, 50
                    )
                    last_process_events = now

        with _ZipFile(zip_path) as zr:
            if zr.testzip() is not None:
                raise Exception("File archive is corrupted.")

        copy_with_progress(zip_path, destination)
        os.remove(zip_path)

    except Exception:
        if os.path.exists(zip_path):
            os.remove(zip_path)
        raise
    finally:
        progress.close()

    log.debug(f"Saved '{source}' to '{destination}'")


def show(tool_name):
    """Call show on "module_name".

    This allows to make a QApplication ahead of time and always "exec_" to
    prevent crashing.

    Args:
        module_name (str): Name of module to call "show" on.

    """
    # Requests often get doubled up when showing tools, so we wait a second
    #   for requests to be received properly.
    time.sleep(1)

    kwargs = {}
    if tool_name == "loader":
        kwargs["use_context"] = True
    elif tool_name == "publisher":
        kwargs["tab"] = "publish"
    elif tool_name == "creator":
        tool_name = "publisher"
        kwargs["tab"] = "create"

    ProcessContext.execute_in_main_thread(
        lambda: host_tools.show_tool_by_name(tool_name, **kwargs)
    )

    # Required return statement.
    return "nothing"


def get_scene_data():
    try:
        return send(
            {
                "function": "AyonHarmonyAPI.getSceneData"
            })["result"]
    except json.decoder.JSONDecodeError:
        # Means no scene metadata has been made before.
        return {}
    except KeyError:
        # Means no existing scene metadata has been made.
        return {}


def set_scene_data(data):
    """Write scene data to metadata.

    Args:
        data (dict): Data to write.

    """
    # Write scene data.
    send(
        {
            "function": "AyonHarmonyAPI.setSceneData",
            "args": data
        })


def read(node_id):
    """Read object metadata in to a dictionary.

    Args:
        node_id (str): Path to node or id of object.

    Returns:
        dict
    """
    scene_data = get_scene_data()
    if node_id in scene_data:
        return scene_data[node_id]

    return {}


def remove(node_id):
    """
        Remove node data from scene metadata.

        Args:
            node_id (str): full name (eg. 'Top/renderAnimation')
    """
    data = get_scene_data()
    del data[node_id]
    set_scene_data(data)


def delete_node(node):
    """ Physically delete node from scene. """
    send(
        {
            "function": "AyonHarmonyAPI.deleteNode",
            "args": node
        }
    )


def get_all_top_names() -> set:
    """Get all top node and backdrop names in the scene.

    Returns:
        set: Set of top node names.

    """
    nodes = send({"function": "node.subNodes", "args": ["Top"]})["result"]
    backdrops = {
        backdrop["title"]["text"]
        for backdrop in send(
            {"function": "Backdrop.backdrops", "args": ["Top"]}
        )["result"]
    }
    return set(nodes) | backdrops


def get_palettes_paths() -> set:
    """Get all palettes paths in the scene.

    Returns:
        set: Set of palettes paths.
    """
    return {pal["_path"] for pal in send(
        {"function": "AyonHarmony.getAllPalettesPaths"}
    )["result"]}


def imprint(node_id, data, remove=False):
    """Write `data` to the `node` as json.

    Arguments:
        node_id (str): Path to node or id of object.
        data (dict): Dictionary of key/value pairs.
        remove (bool): Removes the data from the scene.

    Example:
        >>> from ayon_harmony.api import lib
        >>> node = "Top/Display"
        >>> data = {"str": "something", "int": 1, "float": 0.32, "bool": True}
        >>> lib.imprint(layer, data)
    """
    scene_data = get_scene_data()

    if remove and (node_id in scene_data):
        scene_data.pop(node_id, None)
    else:
        if node_id in scene_data:
            scene_data[node_id].update(data)
        else:
            scene_data[node_id] = data

    set_scene_data(scene_data)


def send(request):
    """Public method for sending requests to Harmony."""
    return ProcessContext.server.send(request)


def select_nodes(nodes):
    """ Selects nodes in Node View """
    _ = send(
        {
            "function": "AyonHarmonyAPI.selectNodes",
            "args": nodes
        }
    )


@contextlib.contextmanager
def maintained_nodes_state(nodes):
    """Maintain nodes states during context."""
    # Collect current state.
    states = send(
        {
            "function": "AyonHarmonyAPI.areEnabled", "args": nodes
        })["result"]

    # Disable all nodes.
    send(
        {
            "function": "AyonHarmonyAPI.disableNodes", "args": nodes
        })

    try:
        yield
    finally:
        send(
            {
                "function": "AyonHarmonyAPI.setState",
                "args": [nodes, states]
            })


def save_scene(zip_and_move=True):
    """Save the Harmony scene safely.

    The built-in (to AYON) background zip and moving of the Harmony scene
    folder, interferes with server/client communication by sending two
    requests at the same time. This only happens when sending
    "scene.saveAll()". This method prevents this double request and safely
    saves the scene.

    """
    # Need to turn off the background watcher else the communication with
    # the server gets spammed with two requests at the same time.
    scene_path = send(
        {"function": "AyonHarmonyAPI.saveScene"})["result"]

    # # Manually update the remote file.
    if zip_and_move:
        on_file_changed(scene_path, threaded=False)

    # Re-enable the background watcher.
    send({"function": "AyonHarmonyAPI.enableFileWather"})


def save_scene_as(filepath):
    """Save Harmony scene as `filepath`."""
    scene_dir = os.path.dirname(filepath)
    destination = os.path.join(
        os.path.dirname(ProcessContext.workfile_path),
        os.path.splitext(os.path.basename(filepath))[0] + ".zip"
    )

    if os.path.exists(scene_dir):
        try:
            shutil.rmtree(scene_dir)
        except Exception as e:
            log.error(f"Cannot remove {scene_dir}")
            raise Exception(f"Cannot remove {scene_dir}") from e

    send(
        {"function": "scene.saveAs", "args": [scene_dir]}
    )["result"]

    zip_and_move(scene_dir, destination)

    ProcessContext.workfile_path = destination

    send(
        {"function": "AyonHarmonyAPI.addPathToWatcher", "args": filepath}
    )


def find_node_by_name(name, node_type):
    """Find node by its name.

    Args:
        name (str): Name of the Node. (without part before '/')
        node_type (str): Type of the Node.
            'READ' - for loaded data with Loaders (background)
            'GROUP' - for loaded data with Loaders (templates)
            'WRITE' - render nodes

    Returns:
        str: FQ Node name.

    """
    nodes = send(
        {"function": "node.getNodes", "args": [[node_type]]}
    )["result"]
    for node in nodes:
        node_name = node.split("/")[-1]
        if name == node_name:
            return node

    return None


def find_backdrop_by_name(name: str) -> Optional[dict]:
    """Find backdrop by its name.

    Args:
        name (str): Name of the backdrop.

    Returns:
        dict: Backdrop.
    """
    backdrops = send(
        {"function": "Backdrop.backdrops", "args": ["Top"]}
    )["result"]
    for backdrop in backdrops:
        if backdrop["title"]["text"] == name:
            return backdrop

    return None


@lru_cache(maxsize=1)
def get_layers_info(top_only: bool = True) -> list[dict[str, str]]:
    """Returns list of dicts with info about timeline layers

    'position' goes from 0 at the top and increases to bottom on timeline
    """
    layers_info = send(
        {
            "function": "AyonHarmony.getLayerInfos",
            "args": [top_only]
        }
    )["result"]
    layers_info = [layer for layer in layers_info if layer["enabled"]]
    return sorted(
        layers_info,
        key=lambda layer: layer["position"],
        reverse=True
    )


def rename_node(node_name, new_name):
    """ Rename node name """
    send(
        {
            "function": "AyonHarmony.renameNode",
            "args": [node_name, new_name]
        }
    )
