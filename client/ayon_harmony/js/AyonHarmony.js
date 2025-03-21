/* global include */
// ***************************************************************************
// *                        AYON Harmony Host                                *
// ***************************************************************************

var LD_OPENHARMONY_PATH = System.getenv('LIB_OPENHARMONY_PATH');
LD_OPENHARMONY_PATH = LD_OPENHARMONY_PATH + '/openHarmony.js';
LD_OPENHARMONY_PATH = LD_OPENHARMONY_PATH.replace(/\\/g, "/");



/**
 * @namespace
 * @classdesc AyonHarmony encapsulate all AYON related functions.
 * @property  {Object}  loaders   Namespace for Loaders JS code.
 * @property  {Object}  Creators  Namespace for Creators JS code.
 * @property  {Object}  Publish   Namespace for Publish plugins JS code.
 */
var AyonHarmony = {
    Loaders: {},
    Creators: {},
    Publish: {}
};


/**
 * Show message in Harmony.
 * @function
 * @param {string} message  Argument containing message.
 */
AyonHarmony.message = function(message) {
    MessageBox.information(message);
};


/**
 * Set scene setting based on folder settngs.
 * @function
 * @param {obj} settings  Scene settings.
 */
AyonHarmony.setSceneSettings = function(settings) {
    if (settings.fps) {
        scene.setFrameRate(settings.fps);
    }

    if (settings.frameStart && settings.frameEnd) {
        var duration = settings.frameEnd - settings.frameStart + 1;

        if (frame.numberOf() > duration) {
            frame.remove(duration, frame.numberOf() - duration);
        }

        if (frame.numberOf() < duration) {
            frame.insert(duration, duration - frame.numberOf());
        }

        scene.setStartFrame(1);
        scene.setStopFrame(duration);
    }
    if (settings.resolutionWidth && settings.resolutionHeight) {
        scene.setDefaultResolution(
            settings.resolutionWidth, settings.resolutionHeight, 41.112
        );
    }
};


/**
 * Get scene settings.
 * @function
 * @return {array} Scene settings.
 */
AyonHarmony.getSceneSettings = function() {
    return [
        about.getApplicationPath(),
        scene.currentProjectPath(),
        scene.currentScene(),
        scene.getFrameRate(),
        scene.getStartFrame(),
        scene.getStopFrame(),
        sound.getSoundtrackAll().path(),
        scene.defaultResolutionX(),
        scene.defaultResolutionY(),
        scene.defaultResolutionFOV()
    ];
};


/**
 * Set color of nodes.
 * @function
 * @param {array} nodes List of nodes.
 * @param {array} rgba  array of RGBA components of color.
 */
AyonHarmony.setColor = function(nodes, rgba) {
    for (var i =0; i <= nodes.length - 1; ++i) {
        var color = AyonHarmony.color(rgba);
        node.setColor(nodes[i], color);
    }
};


/**
 * Extract Backdrop as Template file.
 * @function
 * @param {array} args  Arguments for template extraction.
 *
 * @example
 * // arguments are in this order:
 * var args = [backdrop, templateFilename, templateDir];
 *
 */
AyonHarmony.exportBackdropAsTemplate = function(args) {
    var backdropName = args[0];
    var backdrop = AyonHarmony._getBackdropByName(backdropName);
    if (!backdrop){
        throw new Error("Cannot find::", backdropName);
    }
    // Select backdrop and all nodes in it
    selection.clearSelection();
    selection.addBackdropToSelection(backdrop);
    selection.addNodesToSelection(Backdrop.nodes(backdrop));

    // Select subbackdrops
    AyonHarmony.getSubBackdrops(backdrop).forEach(function(b) {
        selection.addBackdropToSelection(b);
    });
    
    // Export template
    copyPaste.createTemplateFromSelection(args[1], args[2]);
};

/**
 * Returns Backdrop item for its name
 * @function
 * @param {string} backdropName
 * @return {obj} Backdrop item
 */
AyonHarmony._getBackdropByName = function(backdropName){
    var groupPath = "Top";
    var backdrops = Backdrop.backdrops(groupPath);
    if (backdrops && backdrops.length > 0) {
        for (var i = 0; i < backdrops.length; i++) {
            var backdrop = backdrops[i];
            if (backdrop["title"]["text"] == backdropName){
                return backdrop
            }
        }
    }
}

/**
 * Get subbackdrops of a backdrop.
 * @function
 * @param {object} backdrop Backdrop object as described in Backdrop class.
 * @return {array} List of subbackdrops.
 */
AyonHarmony.getSubBackdrops = function(backdrop) {
    var subBackdrops = [];
    Backdrop.backdrops(backdrop["group"]).forEach(function(b) {
        if (b["title"]["text"] != backdrop["title"]["text"]
            && backdrop["position"]["x"] < b["position"]["x"]
            && backdrop["position"]["x"] + backdrop["position"]["w"] > b["position"]["x"] + b["position"]["w"]
            && backdrop["position"]["y"] < b["position"]["y"]
            && backdrop["position"]["y"] + backdrop["position"]["h"] > b["position"]["y"] + b["position"]["h"]
        ) {
            subBackdrops.push(b);
        }
    });
    return subBackdrops;
}


/**
 * Get backdrop links.
 * A backdrop link is a link between a node in the backdrop and a node outside the backdrop.
 * @function
 * @param {object} backdrop Backdrop object as described in Backdrop class.
 * @return {array} List of nodes links.
 */
AyonHarmony.getBackdropLinks = function(backdrop) {
    var backdropNodes = Backdrop.nodes(backdrop);
    var nodesLinks = [];

    // Input links
    backdropNodes.forEach(function(n) {
        for (var i = 0; i < node.numberOfInputPorts(n); i++) {
            var link = node.srcNodeInfo(n, i);

            // Skip if no link or if it's a node from the backdrop container
            if (link == null || backdropNodes.indexOf(link.node) > -1) continue;

            nodesLinks.push({
                srcNode: link.node,
                srcPort: link.port,
                dstNode: n,
                dstPort: i,
            });
        }
    });

    // Output links
    backdropNodes.forEach(function(n) {
        for (var i = 0; i < node.numberOfOutputPorts(n); i++) {
            for (var j = 0; j < node.numberOfOutputLinks(n, i); j++) {
                var link = node.dstNodeInfo(n, i, j);

                // Skip if no link or if it's a node from the backdrop container
                if (link == null || backdropNodes.indexOf(link.node) > -1) continue;

                nodesLinks.push({
                    srcNode: n,
                    srcPort: i,
                    dstNode: link.node,
                    dstPort: link.port
                });
            }
        }
    });

    return nodesLinks;
};

/**
 * Set nodes links.
 * @function
 * @param {array} links List of nodes links.
 */
AyonHarmony.setNodesLinks = function(links) {
    links.forEach(function(l) {
        node.link(l.srcNode, l.srcPort, l.dstNode, l.dstPort);
    });
};

/**
 * Remove backdrop and its contents.
 * @function
 * @param {string} backdrop Backdrop object.
 * 
 */
AyonHarmony.removeBackdropWithContents = function(backdrop) {
    // Delete all nodes in backdrop
    Backdrop.nodes(backdrop).forEach(function(n) {
        // Unlink node first to avoid default relinking
        for (var i = 0; i < node.numberOfInputPorts(n); i++) {
            node.unlink(n, i);
        }

        AyonHarmony.deleteNode(n);
    });

    // Delete subbackdrops
    AyonHarmony.getSubBackdrops(backdrop).forEach(function(b) {
        Backdrop.removeBackdrop(b);
    });

    // Delete backdrop
    Backdrop.removeBackdrop(backdrop);
};


/**
 * Toggle instance in Harmony.
 * @function
 * @param {array} args  Instance name and value.
 */
AyonHarmony.toggleInstance = function(args) {
    node.setEnable(args[0], args[1]);
};


/**
 * Delete node in Harmony.
 * @function
 * @param {string} _node  Node name.
 */
AyonHarmony.deleteNode = function(_node) {
    node.deleteNode(_node, true, true);
};


/**
 * Copy file.
 * @function
 * @param {string}  src Source file name.
 * @param {string}  dst Destination file name.
 */
AyonHarmony.copyFile = function(src, dst) {
    var srcFile = new PermanentFile(src);
    var dstFile = new PermanentFile(dst);
    srcFile.copy(dstFile);
};


/**
 * create RGBA color from array.
 * @function
 * @param   {array}     rgba array of rgba values.
 * @return  {ColorRGBA} ColorRGBA Harmony class.
 */
AyonHarmony.color = function(rgba) {
    return new ColorRGBA(rgba[0], rgba[1], rgba[2], rgba[3]);
};


/**
 * get all dependencies for given node.
 * @function
 * @param   {string}  _node node path.
 * @return  {array}   List of dependent nodes.
 */
AyonHarmony.getDependencies = function(_node) {
    var target_node = _node;
    var numInput = node.numberOfInputPorts(target_node);
    var dependencies = [];
    for (var i = 0 ; i < numInput; i++) {
        dependencies.push(node.srcNode(target_node, i));
    }
    return dependencies;
};


/**
 * return version of running Harmony instance.
 * @function
 * @return  {array} [major_version, minor_version]
 */
AyonHarmony.getVersion = function() {
    return [
        about.getMajorVersion(),
        about.getMinorVersion()
    ];
};


/**
 * Get all palettes in scene.
 * @function
 * @return {array} List of palettes paths.
 */
AyonHarmony.getAllPalettesPaths = function() {
    var palettes = $.scene.palettes;
    var palettesPaths = [];
    for (var i = 0; i < palettes.length; i++) {
        palettesPaths.push(palettes[i].path);
    }
    return palettesPaths;
}

/**
 * Remove palette from scene matching its path.
 * @function
 * @param {string} palettePath Path to tpl file.
 */
AyonHarmony.removePaletteByPath = function(palettePath) {
    var palettes = $.scene.palettes;
    for (var i = 0; i < palettes.length; i++) {
        MessageLog.trace("Palette path::" + palettes[i].path + " == " + palettePath);
        if (palettes[i].path == palettePath) {
            PaletteObjectManager.getScenePaletteList().removePaletteById(palettes[i].id);
            break;
        }
    }
}
