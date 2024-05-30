"""Script wraps launch mechanism of Harmony implementations.

Arguments passed to the script are passed to launch function in host
implementation. In all cases requires host app executable and may contain
workfile or others.
"""

import os
import sys

from ayon_harmony.api.lib import main as host_main

# Get current file to locate start point of sys.argv
CURRENT_FILE = os.path.abspath(__file__)


def show_error_messagebox(title, message, detail_message=None):
    """Function will show message and process ends after closing it."""
    from qtpy import QtWidgets, QtCore
    from ayon_core import style

    app = QtWidgets.QApplication([])
    app.setStyleSheet(style.load_stylesheet())

    msgbox = QtWidgets.QMessageBox()
    msgbox.setWindowTitle(title)
    msgbox.setText(message)

    if detail_message:
        msgbox.setDetailedText(detail_message)

    msgbox.setWindowModality(QtCore.Qt.ApplicationModal)
    msgbox.show()

    sys.exit(app.exec_())


def on_invalid_args(script_not_found):
    """Show to user message box saying that something went wrong.

    Tell user that arguments to launch implementation are invalid with
    arguments details.

    Args:
        script_not_found (bool): Use different message based on this value.
    """

    title = "Invalid arguments"
    joined_args = ", ".join("\"{}\"".format(arg) for arg in sys.argv)
    if script_not_found:
        submsg = "Where couldn't find script path:\n\"{}\""
    else:
        submsg = "Expected Host executable after script path:\n\"{}\""

    message = "BUG: Got invalid arguments so can't launch Host application."
    detail_message = "Process was launched with arguments:\n{}\n\n{}".format(
        joined_args,
        submsg.format(CURRENT_FILE)
    )

    show_error_messagebox(title, message, detail_message)


def main(argv):
    # Modify current file path to find match in sys.argv which may be different
    #   on windows (different letter cases and slashes).
    modified_current_file = CURRENT_FILE.replace("\\", "/").lower()

    # Create a copy of sys argv
    sys_args = list(argv)
    after_script_idx = None
    # Find script path in sys.argv to know index of argv where host
    #   executable should be.
    for idx, item in enumerate(sys_args):
        if item.replace("\\", "/").lower() == modified_current_file:
            after_script_idx = idx + 1
            break

    # Validate that there is at least one argument after script path
    launch_args = None
    if after_script_idx is not None:
        launch_args = sys_args[after_script_idx:]

    if launch_args:
        # Launch host implementation
        host_main(*launch_args)
    else:
        # Show message box
        on_invalid_args(after_script_idx is None)


if __name__ == "__main__":
    main(sys.argv)
