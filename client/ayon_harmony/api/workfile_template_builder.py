from __future__ import annotations

import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from qtpy import QtWidgets, QtCore

from ayon_core.pipeline import registered_host
from ayon_core.pipeline.workfile.workfile_template_builder import (
    AbstractTemplateBuilder,
    PlaceholderItem,
    PlaceholderPlugin,
)
from ayon_core.tools.utils import show_message_dialog
from ayon_core.tools.workfile_template_build import (
    WorkfileBuildPlaceholderDialog,
)
from ayon_core import style

import ayon_harmony.api as harmony


class HarmonyTemplateBuilder(AbstractTemplateBuilder):
    """Concrete implementation of AbstractTemplateBuilder for Toon Boom Harmony."""

    def __init__(self, host):
        super().__init__(host)
        self._progress_dialog = None

    def _show_progress(
        self,
        title: str,
        label: str,
        maximum: int = 0,
    ) -> QtWidgets.QProgressDialog:
        """Create, style, and immediately show a modal progress dialog.

        Args:
            title (str): Window title text.
            label (str): Initial label text shown below the bar.
            maximum (int): Bar maximum. 0 means indeterminate (busy spinner).

        Returns:
            QtWidgets.QProgressDialog: The visible dialog.
        """
        progress = QtWidgets.QProgressDialog(label, None, 0, maximum)
        progress.setStyleSheet(style.load_stylesheet())
        progress.setWindowTitle(title)
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)
        progress.show()
        QtWidgets.QApplication.processEvents(QtCore.QEventLoop.AllEvents, 50)
        return progress

    def _update_progress(
        self,
        label: str | None = None,
        value: int | None = None,
    ) -> None:
        """Update the active progress dialog and flush Qt events.

        Args:
            label (str | None): New label text, or None to leave unchanged.
            value (int | None): New bar value, or None to leave unchanged.
        """
        if not self._progress_dialog:
            return
        if label is not None:
            self._progress_dialog.setLabelText(label)
        if value is not None:
            self._progress_dialog.setValue(value)
        QtWidgets.QApplication.processEvents(QtCore.QEventLoop.AllEvents, 50)

    def import_template(self, path: str) -> bool:
        """Import a Harmony template into the current scene.

        Args:
            path (str): Absolute path to the template .tpl folder.

        Returns:
            bool: True if the template loaded successfully, False otherwise.
        """
        sig = harmony.signature("paste")
        func = """function %s(args)
        {
            var template_path = args[0];
            var drag_object = copyPaste.pasteTemplateIntoGroup(template_path, "Top", 1);
        }
        %s
        """ % (sig, sig)

        harmony.send({"function": func, "args": [path]})
        success = True
        return success

    def build_template(self, *args, **kwargs) -> None:
        """Build the workfile template with a progress dialog.

        Shows an indeterminate dialog for the full duration. The label
        transitions through "Preparing..." → "Importing template..." →
        "Populating placeholders..." via hooks in import_template().

        Args:
            *args: Forwarded to AbstractTemplateBuilder.build_template.
            **kwargs: Forwarded to AbstractTemplateBuilder.build_template.
        """
        progress = self._show_progress(
            title="Building Template",
            label="Preparing...",
            maximum=0,  # indeterminate -- duration not predictable
        )
        self._progress_dialog = progress
        try:
            super().build_template(*args, **kwargs)
        finally:
            self._progress_dialog = None
            progress.close()

    def rebuild_template(self) -> None:
        """Rebuild all placeholders in the current scene with a progress dialog."""
        placeholders = self.get_placeholders()
        total = len(placeholders)
        noun = "placeholder" if total == 1 else "placeholders"

        progress = self._show_progress(
            title="Updating Template",
            label=f"Populating {total} {noun}...",
            maximum=0,  # indeterminate
        )
        self._progress_dialog = progress
        try:
            super().rebuild_template()
        finally:
            self._progress_dialog = None
            progress.close()


class HarmonyPlaceholderPlugin(PlaceholderPlugin):
    """Base Placeholder Plugin for Toon Boom Harmony.

    Placeholder metadata is stored in two places simultaneously so that it
    survives a Harmony template export/import round-trip:

    BurnIn node is choosen cause it supports both a Peg and Output both of
    which are relinked after the placeholder is filled. It also has a nice
    text field to store the metadata.
    """

    attr_prefix: str = "AYON_placeholder_"

    def get_placeholder_node_name(self, placeholder_data: dict) -> str:
        return self.identifier.replace(".", "_")

    def create_placeholder_node(self, node_name: str | None = None) -> str:
        """Create a BurnIn node in Harmony to act as a placeholder.

        Args:
            node_name (str | None): Desired node name. Defaults to the plugin
                identifier with dots replaced by underscores.

        Returns:
            str: The node identifier for the created BurnIn node.
        """
        name = node_name or self.identifier.replace(".", "_")
        node_id = harmony.send(
            {
                "function": "AyonHarmonyAPI.createNodeContainer",
                "args": [name, "BurnIn", False],
            }
        )["result"]
        return node_id

    def create_placeholder(self, placeholder_data: dict) -> None:
        """Create a placeholder node and imprint it with placeholder metadata.

        Args:
            placeholder_data (dict): Placeholder configuration data including
                loader name, product name, and filter settings.
        """
        node_name = self.get_placeholder_node_name(placeholder_data)
        node_id = self.create_placeholder_node(node_name)

        placeholder_data["plugin_identifier"] = self.identifier
        self._imprint(node_id, placeholder_data)

    def collect_scene_placeholders(self) -> list[str]:
        """Collect all placeholder node identifiers from the current scene.

        Returns:
            list[str]: Node identifier strings for all matching placeholder
                nodes found in the current scene.
        """
        placeholder_nodes = self.builder.get_shared_populate_data(
            self.identifier
        )

        if placeholder_nodes is None:
            scene_data = harmony.get_scene_data()
            prefixed_key = self.attr_prefix + "plugin_identifier"
            placeholder_nodes = []
            found_node_ids: set[str] = set()

            for node_id, node_data in scene_data.items():
                if not isinstance(node_data, dict):
                    continue

                if (
                    node_data.get(prefixed_key) == self.identifier
                    or node_data.get("plugin_identifier") == self.identifier
                ):
                    placeholder_nodes.append(node_id)
                    found_node_ids.add(node_id)

            attr_placeholders = self._scan_burnin_nodes_for_placeholder_data()
            for node_id, attr_data in attr_placeholders.items():
                if node_id in found_node_ids:
                    # Already present in the scene JSON; nothing to do.
                    continue
                if attr_data.get("plugin_identifier") != self.identifier:
                    # Data belongs to a different plugin; skip.
                    continue

                self._imprint(node_id, attr_data)
                placeholder_nodes.append(node_id)

            self.builder.set_shared_populate_data(
                self.identifier, placeholder_nodes
            )

        return placeholder_nodes

    def collect_placeholders(self) -> list[PlaceholderItem]:
        """Collect all AYON PlaceholderItems from the current Harmony scene.

        Returns:
            list[PlaceholderItem]: All placeholder items found in the scene,
                each carrying the node identifier as ``scene_identifier`` and
                the prefix-stripped metadata dict.
        """
        output = []
        for node_id in self.collect_scene_placeholders():
            placeholder_data = self._read(node_id)
            output.append(PlaceholderItem(node_id, placeholder_data, self))
        return output

    def update_placeholder(
        self,
        placeholder_item: PlaceholderItem,
        placeholder_data: dict,
    ) -> None:
        """Update an existing placeholder node's metadata and name.

        Args:
            placeholder_item (PlaceholderItem): The placeholder to update,
                providing the current ``scene_identifier`` (node path).
            placeholder_data (dict): The updated placeholder configuration.
        """
        old_node_id = placeholder_item.scene_identifier
        self._imprint(old_node_id, placeholder_data, update=True)

        # Rename the physical node in Harmony.
        new_name = self.get_placeholder_node_name(placeholder_data)
        harmony.rename_node(old_node_id, new_name)

        # Harmony node paths follow "<parentGroup>/<nodeName>".
        parent_group = old_node_id.rsplit("/", 1)[0]
        new_node_id = f"{parent_group}/{new_name}"

        if old_node_id != new_node_id:
            scene_data = harmony.get_scene_data()
            if old_node_id in scene_data:
                scene_data[new_node_id] = scene_data.pop(old_node_id)
                harmony.set_scene_data(scene_data)

    def delete_placeholder(self, placeholder: PlaceholderItem) -> None:
        """Delete a placeholder node and its scene metadata from Harmony.

        Args:
            placeholder (PlaceholderItem): The placeholder to delete.
        """
        node_id = placeholder.scene_identifier

        # Purge the metadata entry from the scene.
        harmony.imprint(node_id, {}, remove=True)

        # Physically remove the node from the Harmony scene.
        harmony.delete_node(node_id)

    def _imprint(
        self,
        node_id: str,
        placeholder_data: dict,
        update: bool = False,
    ) -> None:
        """Write placeholder_data into the AYON scene JSON and the node's printinfo.

        Writing to both stores keeps them in sync:

        - The **Scene** entry enables fast reads during normal operation.
        - The **BurnIn ``printinfo``** entry survives template export/import,
          acting as the authoritative source when the scene JSON entry is absent.

        Args:
            node_id (str): Node identifier used as the scene data JSON key.
            placeholder_data (dict): Key/value pairs to imprint.
            update (bool): Accepted for API compatibility; no-op in Harmony.
        """
        prefixed_data = {
            f"{self.attr_prefix}{key}": value
            for key, value in placeholder_data.items()
        }
        harmony.imprint(node_id, prefixed_data)

        self._write_attr_data(node_id, placeholder_data)

    def _read(self, node_id: str) -> dict[str, Any]:
        """Read AYON placeholder metadata from the Harmony scene JSON.

        Args:
            node_id (str): Node identifier to read metadata for.

        Returns:
            dict[str, Any]: Placeholder configuration with prefix removed from
                all keys.
        """
        data = harmony.read(node_id)

        for key in list(data):
            if key.startswith(self.attr_prefix):
                value = data.pop(key)
                data[key[len(self.attr_prefix) :]] = value

        return data

    def _write_attr_data(self, node_id: str, data: dict) -> None:
        """Serialise *data* as JSON and store it in the node's ``printinfo`` attribute.

        ``node.setTextAttr`` writes to a named text attribute on a Harmony node.
        The ``printinfo`` attribute is used here because it accepts arbitrary
        freeform text

        Args:
            node_id (str): Full Harmony path of the BurnIn node to annotate.
            data (dict): Placeholder configuration to serialise and store.
        """
        payload = json.dumps(data, separators=(",", ":"))

        sig = harmony.signature("write_placeholder_attr")
        func = """function %s(args)
        {
            node.setTextAttr(args[0], "printinfo", 1, args[1]);
        }
        %s
        """ % (sig, sig)
        harmony.send({"function": func, "args": [node_id, payload]})

    def _scan_burnin_nodes_for_placeholder_data(self) -> dict[str, dict]:
        """Scan every BurnIn node in the scene for embedded AYON placeholder data.

        Returns:
            dict[str, dict]: Mapping of Harmony node path to de-serialised
                placeholder data for every BurnIn node carrying a parseable
                AYON placeholder payload.
        """
        sig = harmony.signature("scan_burnin_placeholder_attrs")
        # NOTE maybe add max-depth to this function as a failsafe
        func = """function %s(args)
        {
            var result = {};

            function scanGroup(group)
            {
                var nodeList = node.subNodes(group);
                for (var i = 0; i < nodeList.length; i++) {
                    var n = nodeList[i];

                    // Only BurnIn nodes are used as AYON placeholders.
                    if (node.type(n) === "BurnIn") {
                        var attrVal = node.getTextAttr(n, 1, "printinfo");
                        if (attrVal && attrVal.length > 0) {
                            result[n] = attrVal;
                        }
                    }

                    if (node.type(n) === "GROUP") {
                        scanGroup(n);
                    }
                }
            }

            scanGroup("Top");
            return result;
        }
        %s
        """ % (sig, sig)

        response = harmony.send({"function": func, "args": []})
        raw: dict[str, str] = response.get("result") or {}

        output: dict[str, dict] = {}
        for node_id, attr_val in raw.items():
            try:
                output[node_id] = json.loads(attr_val)
            except (ValueError, TypeError):
                # printinfo contains non-JSON text; not an AYON placeholder.
                continue

        return output


def build_workfile_template(*args, **kwargs) -> None:
    """Build the workfile template in the current Harmony scene."""
    builder = HarmonyTemplateBuilder(registered_host())
    builder.build_template(*args, **kwargs)


def update_workfile_template(*args) -> None:
    """Re-populate all placeholders in the current Harmony scene."""
    builder = HarmonyTemplateBuilder(registered_host())
    builder.rebuild_template()


def create_placeholder(*args) -> None:
    """Open the AYON Workfile Build Placeholder dialog in Harmony."""
    import time
    from ayon_harmony.api.lib import ProcessContext

    time.sleep(1)

    host = registered_host()
    builder = HarmonyTemplateBuilder(host)

    def _show():
        window = WorkfileBuildPlaceholderDialog(host, builder, parent=None)
        window.exec_()

    ProcessContext.execute_in_main_thread(_show)
    return "nothing"


def update_placeholder(*args) -> None:
    """Open the placeholder dialog in update mode for the selected node."""
    import time
    from ayon_harmony.api.lib import ProcessContext

    time.sleep(1)

    host = registered_host()
    builder = HarmonyTemplateBuilder(host)

    def _show():
        # get_placeholders() calls harmony.get_scene_data() internally.
        placeholder_items_by_id = {
            item.scene_identifier: item for item in builder.get_placeholders()
        }

        selected_nodes = (
            harmony.send(
                {
                    "function": "selection.selectedNodes",
                    "args": [],
                }
            ).get("result")
            or []
        )

        placeholder_items = [
            placeholder_items_by_id[node]
            for node in selected_nodes
            if node in placeholder_items_by_id
        ]

        if len(placeholder_items) == 0:
            show_message_dialog(
                "Workfile Placeholder Manager",
                "Please select a placeholder node.",
                "warning",
                None,
            )
            return

        if len(placeholder_items) > 1:
            show_message_dialog(
                "Workfile Placeholder Manager",
                "Too many selected placeholder nodes."
                "\nPlease select one placeholder node.",
                "warning",
                None,
            )
            return

        placeholder_item = placeholder_items[0]
        window = WorkfileBuildPlaceholderDialog(host, builder, parent=None)
        window.set_update_mode(placeholder_item)
        window.exec_()

    ProcessContext.execute_in_main_thread(_show)
    return "nothing"
