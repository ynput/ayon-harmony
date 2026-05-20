# -*- coding: utf-8 -*-
"""Extract template."""
import os
from pathlib import Path
import shutil

from ayon_core.pipeline import publish
import ayon_harmony.api as harmony


class ExtractTemplate(publish.Extractor):
    """Extract the connected nodes to the composite instance."""

    label = "Extract Template"
    hosts = ["harmony"]
    families = ["harmony.template"]

    def process(self, instance):
        """Plugin entry point."""
        staging_dir = self.staging_dir(instance)
        filepath = os.path.join(staging_dir, "harmony", f"{instance.name}.tpl")

        self.log.info(f"Outputting template to {staging_dir}")

        # Export template
        self.log.info(f'{instance.data["setMembers"][0]}')
        harmony.export_backdrop_as_template(
            instance.data["setMembers"][0], filepath
        )

        # Prep representation.
        shutil.make_archive(
            base_name=Path(staging_dir, instance.name),
            format="zip",
            root_dir=Path(staging_dir, "harmony"),
        )

        representation = {
            "name": "tpl",
            "ext": "zip",
            "files": f"{instance.name}.zip",
            "stagingDir": staging_dir
        }

        self.log.info(instance.data.get("representations"))
        if instance.data.get("representations"):
            instance.data["representations"].extend([representation])
        else:
            instance.data["representations"] = [representation]

        instance.data["version_name"] = "{}_{}".format(
            instance.data["productName"],
            instance.context.data["task"]
        )
