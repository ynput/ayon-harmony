# -*- coding: utf-8 -*-
"""Load image."""

import ayon_harmony.api as harmony


class PsdLoader(harmony.BackdropBaseLoader):
    """Load Photoshop file (.psd)."""

    product_types = {"image"}
    representations = {"psd"}
    label = "Load Photoshop Layers"
    icon = "layers"
