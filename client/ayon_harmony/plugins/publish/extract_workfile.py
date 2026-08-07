# -*- coding: utf-8 -*-
"""Extract work file."""
import os
from pathlib import Path
import platform
import shutil
from zipfile import ZipFile

from ayon_core.pipeline import publish


class ExtractWorkfile(publish.Extractor):
    """Extract and zip complete workfile folder into zip."""

    label = "Extract Workfile"
    hosts = ["harmony"]
    families = ["workfile"]

    def process(self, instance):
        """Plugin entry point."""
        staging_dir = self.staging_dir(instance)
        filepath = os.path.join(staging_dir, "{}.tpl".format(instance.name))
        src = os.path.dirname(instance.context.data["currentFile"])
        # handle too long paths on windows
        current_platform = platform.system().lower()
        if current_platform == "windows":
            src = fr"\\?\{src}"
            filepath = fr"\\?\{filepath}"
        self.log.info(f"Copying to {filepath}")
        shutil.copytree(src, filepath, ignore=shutil.ignore_patterns("frames*"))

        # Prep representation.
        shutil.make_archive(
            base_name=Path(staging_dir, instance.name),
            format="zip",
            root_dir=Path(staging_dir, f"{instance.name}.tpl")
        )
        # Check if archive is ok
        with ZipFile(Path(staging_dir, f"{instance.name}.zip")) as zr:
            if zr.testzip() is not None:
                raise Exception("File archive is corrupted.")

        representation = {
            "name": "tpl",
            "ext": "zip",
            "files": f"{instance.name}.zip",
            "stagingDir": staging_dir
        }
        instance.data["representations"] = [representation]
