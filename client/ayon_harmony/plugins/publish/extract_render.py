import os
import tempfile
import subprocess

import pyblish.api
import clique

from ayon_core.pipeline.publish import PublishError, KnownPublishError

import ayon_harmony.api as harmony


class ExtractRender(pyblish.api.InstancePlugin):
    """Produce a flattened image file from instance.
    This plug-in only takes into account the nodes connected to the composite.
    """

    label = "Extract Render"
    # TODO remove decrement after ayon-core ExtractThumbnailFromSource
    #   is set later
    order = pyblish.api.ExtractorOrder - 0.0001
    hosts = ["harmony"]
    families = ["render.local"]

    def process(self, instance):
        # Collect scene data.
        application_path = instance.context.data.get("applicationPath")
        scene_path = instance.context.data.get("scenePath")
        frame_rate = instance.context.data.get("frameRate")
        # real value from timeline
        frame_start = instance.context.data.get("frameStartHandle")
        frame_end = instance.context.data.get("frameEndHandle")
        audio_path = instance.context.data.get("audioPath")

        if audio_path and os.path.exists(audio_path):
            self.log.info(f"Using audio from {audio_path}")
            instance.data["audio"] = [{"filename": audio_path}]

        instance.data["fps"] = frame_rate

        # Set output path to temp folder.
        path = tempfile.mkdtemp()
        sig = harmony.signature()
        func = """function %s(args)
        {
            node.setTextAttr(args[0], "DRAWING_NAME", 1, args[1]);
        }
        %s
        """ % (sig, sig)
        harmony.send(
            {
                "function": func,
                "args": [instance.data["setMembers"][0],
                         path + "/" + instance.data["name"]]
            }
        )
        harmony.save_scene(zip_and_move=False)

        # Execute rendering. Ignoring error cause Harmony returns error code
        # always.

        args = [application_path, "-batch",
                "-frames", str(frame_start), str(frame_end),
                scene_path]
        self.log.info(f"running: {' '.join(args)}")
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE
        )
        stdout, _stderr = proc.communicate()
        self.log.info("Click on the line below to see more details.")
        self.log.info(stdout.decode("utf-8"))

        # Collect rendered files.
        self.log.debug(f"collecting from: {path}")
        files = os.listdir(path)
        if not files:
            raise PublishError(
                "No rendered files found, render failed."
            )

        self.log.debug(f"files there: {files}")
        collections, remainder = clique.assemble(files, minimum_items=1)
        if remainder:
            member = instance.data["setMembers"][0]
            raise KnownPublishError(
                f"There should not be a remainder for {member}: {remainder}"
            )
        self.log.debug(collections)
        collection = None
        if len(collections) > 1:
            for col in collections:
                if len(list(col)) > 1:
                    collection = col
        else:
            collection = collections[0]

        if collection is None:
            raise KnownPublishError(
                "Failed to find a collection with multiple files."
            )

        thumbnail_source = os.path.join(path, list(collections[0])[0])
        instance.data["thumbnailSource"] = thumbnail_source

        # Generate representations.
        extension = collection.tail[1:]
        files = list(collection)
        representation = {
            "name": extension,
            "ext": extension,
            "files": files if len(files) > 1 else files[0],
            "stagingDir": path,
            "tags": ["review"],
            "fps": frame_rate
        }
        representations = [representation]

        instance.data["representations"] = representations

        if audio_path and os.path.exists(audio_path):
            instance.data["audio"] = [{"filename": audio_path}]

        # Required for extract_review plugin (L222 onwards).
        instance.data["frameStart"] = frame_start
        instance.data["frameEnd"] = frame_end
        instance.data["fps"] = frame_rate

        self.log.info(f"Extracted {instance} to {path}")
