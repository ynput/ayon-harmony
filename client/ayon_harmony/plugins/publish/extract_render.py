import os
import tempfile
import subprocess

import pyblish.api
import ayon_harmony.api as harmony
import ayon_core.lib

import clique


class ExtractRender(pyblish.api.InstancePlugin):
    """Produce a flattened image file from instance.
    This plug-in only takes into account the nodes connected to the composite.
    """

    label = "Extract Render"
    order = pyblish.api.ExtractorOrder
    hosts = ["harmony"]
    families = ["render"]

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
        harmony.save_scene()

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
        output, error = proc.communicate()
        self.log.info("Click on the line below to see more details.")
        self.log.info(output.decode("utf-8"))

        # Collect rendered files.
        self.log.debug(f"collecting from: {path}")
        files = os.listdir(path)
        assert files, (
            "No rendered files found, render failed."
        )
        self.log.debug(f"files there: {files}")
        collections, remainder = clique.assemble(files, minimum_items=1)
        assert not remainder, (
            "There should not be a remainder for {0}: {1}".format(
                instance.data["setMembers"][0], remainder
            )
        )
        self.log.debug(collections)
        if len(collections) > 1:
            for col in collections:
                if len(list(col)) > 1:
                    collection = col
        else:
            collection = collections[0]

        # Generate thumbnail.
        thumbnail_path = os.path.join(path, "thumbnail.png")
        args = ayon_core.lib.get_ffmpeg_tool_args(
            "ffmpeg",
            "-y",
            "-i", os.path.join(path, list(collections[0])[0]),
            "-vf", "scale=300:-1",
            "-vframes", "1",
            thumbnail_path
        )
        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE
        )

        output = process.communicate()[0]

        if process.returncode != 0:
            raise ValueError(output.decode("utf-8", errors="backslashreplace"))

        self.log.debug(output.decode("utf-8", errors="backslashreplace"))

        # Generate representations.
        extension = collection.tail[1:]
        representation = {
            "name": extension,
            "ext": extension,
            "files": list(collection),
            "stagingDir": path,
            "tags": ["review"],
            "fps": frame_rate
        }

        thumbnail = {
            "name": "thumbnail",
            "ext": "png",
            "files": os.path.basename(thumbnail_path),
            "stagingDir": path,
            "tags": ["thumbnail"]
        }
        instance.data["representations"] = [representation, thumbnail]

        if audio_path and os.path.exists(audio_path):
            instance.data["audio"] = [{"filename": audio_path}]

        # Required for extract_review plugin (L222 onwards).
        instance.data["frameStart"] = frame_start
        instance.data["frameEnd"] = frame_end
        instance.data["fps"] = frame_rate

        self.log.info(f"Extracted {instance} to {path}")
