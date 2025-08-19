# -*- coding: utf-8 -*-
"""Export content of Display node as .mov."""
import os

from ayon_core.pipeline import publish

import ayon_harmony.api as harmony


class ExtractSourceForReview(publish.Extractor):
    """Use exporter to save .mov from Display node.
    
    Review should be created automatically, `Display`
    node is expected.
    """

    label = "Extract sources for Review"
    hosts = ["harmony"]
    families = ["review"]

    def process(self, instance):
        """Plugin entry point."""
        staging_dir = self.staging_dir(instance)
        file_name = f"{instance.name}.mov"
        filepath = os.path.join(staging_dir, file_name)
        self.log.info(f"Exporting to {filepath}")

        sig = harmony.signature()

        display_node_name = instance.data["display_node_name"]

        func = """function %s(args)
        {
            var codec = "openH264";
            var startFrame = -1; // take from timeline
            var endFrame = -1; // take from timeline
            var withSound = true;
            var resX = -1; //take from scene
            var resY = -1;
            var saveTo = args[0];
            var displayToRender = args[1];
            var generateThumbnail = false;
            var thumbnailFrame = 0;
            exporter.exportToQuicktime(
                codec,
                startFrame,
                endFrame,
                withSound,
                resX,
                resY,
                saveTo,
                displayToRender,
                generateThumbnail,
                thumbnailFrame
            )
        }
        %s
        """ % (sig, sig)
        harmony.send(
            {
                "function": func,
                "args": [filepath, display_node_name]
            }
        )

        # for global ExtractReview
        context = instance.context
        instance.data["frameStart"] = context.data["frameStart"]
        instance.data["frameEnd"] = context.data["frameEnd"]
        instance.data["fps"] = context.data["fps"]

        representation = {
            "name": "mov",
            "ext": "mov",
            "files": file_name,
            "stagingDir": staging_dir,
            "tags": ["review", "delete"]
        }
        self.log.info(f"repre::{representation}")
        instance.data["representations"] = [representation]
