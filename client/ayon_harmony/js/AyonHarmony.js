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

var PARENT_BACKDROP_GRID_GAP = 100;
var PARENT_BACKDROP_PADDING = 50;
var PARENT_BACKDROP_TITLE_HEIGHT = 40;


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
 * Get information important for render output.
 * @function
 * @param nodePath {String} node path.
 * @return {array} array of render info.
 *
 * @example
 *
 * var ret = [
 *    file_prefix, // like foo/bar-
 *    type, // PNG4, ...
 *    leading_zeros, // 3 - for 0001
 *    start // start frame
 * ]
 */
AyonHarmony.getRenderNodeSettings = function(nodePath) {
    var output = [
        node.getTextAttr(
            nodePath, frame.current(), 'DRAWING_NAME'),
        node.getTextAttr(
            nodePath, frame.current(), 'DRAWING_TYPE'),
        node.getTextAttr(
            nodePath, frame.current(), 'LEADING_ZEROS'),
        node.getTextAttr(nodePath, frame.current(), 'START'),
        node.getEnable(nodePath)
    ];

    return output;
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
 * Compute bounding box of all backdrops and nodes in "Top".
 * @return {{top: number, right: number, bottom: number}|null} Bounds or null if empty.
 */
AyonHarmony.computeExistingBounds = function() {
    var existingBackdrops = Backdrop.backdrops("Top");
    var existingNodes = node.subNodes("Top");
    if (existingBackdrops.length === 0 && existingNodes.length === 0) {
        return null;
    }

    // Envelope of all backdrops and nodes
    var bounds = { top: Infinity, right: -Infinity, bottom: -Infinity };
    existingBackdrops.forEach(function(b) {
        var right = b.position.x + b.position.w;
        if (right > bounds.right) bounds.right = right;
        if (b.position.y < bounds.top) bounds.top = b.position.y;
        var bottom = b.position.y + b.position.h;
        if (bottom > bounds.bottom) bounds.bottom = bottom;
    });
    existingNodes.forEach(function(nodePath) {
        var nodeRight = node.coordX(nodePath) + node.width(nodePath);
        if (nodeRight > bounds.right) bounds.right = nodeRight;
        var nodeTop = node.coordY(nodePath);
        if (nodeTop < bounds.top) bounds.top = nodeTop;
        var nodeBottom = nodeTop + node.height(nodePath);
        if (nodeBottom > bounds.bottom) bounds.bottom = nodeBottom;
    });
    if (bounds.right === -Infinity) return null;
    return bounds;
};

/**
 * Find backdrop by name (case-insensitive).
 * @param {string} backdropName Name to search for.
 * @return {object|null} Matching backdrop object.
 */
AyonHarmony.findParentBackdrop = function(backdropName) {
    var normalizedName = String(backdropName).toLowerCase();
    var backdrops = Backdrop.backdrops("Top");
    for (var i = 0; i < backdrops.length; i++) {
        var title = backdrops[i].title && backdrops[i].title.text;
        if (title && title.toLowerCase() === normalizedName) {
            return backdrops[i];
        }
    }
    return null;
};

/**
 * Ensure a parent backdrop exists by case-insensitive name.
 * Creates one around new content bounds if not found.
 *
 * @param {string} backdropName Parent backdrop name.
 * @param {object} contentBounds Bounds of newly loaded content.
 * @return {object|null} Existing or newly created backdrop.
 */
AyonHarmony.ensureParentBackdrop = function(backdropName, contentBounds) {
    var parentBackdrop = AyonHarmony.findParentBackdrop(backdropName);
    if (parentBackdrop) {  // Existing backdrop found
        return parentBackdrop;
    }

    // Create backdrop around content bounds
    var initialArea = {
        x: contentBounds.left - PARENT_BACKDROP_PADDING,
        y: contentBounds.top - (
            PARENT_BACKDROP_TITLE_HEIGHT + PARENT_BACKDROP_PADDING
        ),
        w: (contentBounds.right - contentBounds.left)
            + (PARENT_BACKDROP_PADDING * 2),
        h: (contentBounds.bottom - contentBounds.top)
            + (PARENT_BACKDROP_PADDING * 2)
            + PARENT_BACKDROP_TITLE_HEIGHT
    };
    var safeArea = AyonHarmony.findNonOverlappingArea(initialArea);
    return Backdrop.addBackdrop(
        "Top",
        {
            "position": {
                "x": safeArea.x,
                "y": safeArea.y,
                "w": safeArea.w,
                "h": safeArea.h
            },
            "title": {
                "text": backdropName,
                "size": 14,
                "font": "Arial"
            }
        }
    );
};

/**
 * Apply an area position to a backdrop by name.
 *
 * @param {string} backdropName Backdrop title.
 * @param {object} area Position object {x, y, w, h}.
 * @return {Array} Updated backdrop list.
 */
AyonHarmony.applyAreaToBackdrop = function(backdropName, area) {
    var allBackdrops = Backdrop.backdrops("Top");
    for (var i = 0; i < allBackdrops.length; i++) {
        var title = allBackdrops[i].title && allBackdrops[i].title.text;
        if (title && title.toLowerCase() === backdropName.toLowerCase()) {
            allBackdrops[i].position.x = area.x;
            allBackdrops[i].position.y = area.y;
            allBackdrops[i].position.w = area.w;
            allBackdrops[i].position.h = area.h;
            break;
        }
    }
    Backdrop.setBackdrops("Top", allBackdrops);
    return allBackdrops;
};

/**
 * Compute bounds for a set of backdrops and nodes.
 *
 * @param {Array} backdrops Backdrop objects.
 * @param {Array<string>} nodes Node path strings.
 * @return {object} Bounding box.
 */
AyonHarmony.getContentBounds = function(backdrops, nodes) {
    var bounds = {
        left: Infinity,
        top: Infinity,
        right: -Infinity,
        bottom: -Infinity
    };
    backdrops.forEach(function(backdrop) {
        var left = backdrop.position.x;
        var top = backdrop.position.y;
        var right = left + backdrop.position.w;
        var bottom = top + backdrop.position.h;
        if (left < bounds.left) bounds.left = left;
        if (top < bounds.top) bounds.top = top;
        if (right > bounds.right) bounds.right = right;
        if (bottom > bounds.bottom) bounds.bottom = bottom;
    });
    nodes.forEach(function(nodePath) {
        var left = node.coordX(nodePath);
        var top = node.coordY(nodePath);
        var right = left + node.width(nodePath);
        var bottom = top + node.height(nodePath);
        if (left < bounds.left) bounds.left = left;
        if (top < bounds.top) bounds.top = top;
        if (right > bounds.right) bounds.right = right;
        if (bottom > bounds.bottom) bounds.bottom = bottom;
    });
    return bounds;
};

/**
 * Check if 2 rectangles intersect.
 * @param {object} a Rect {left, top, right, bottom}
 * @param {object} b Rect {left, top, right, bottom}
 * @return {boolean}
 */
AyonHarmony.rectsOverlap = function(a, b) {
    return !(a.right <= b.left || a.left >= b.right
        || a.bottom <= b.top || a.top >= b.bottom);
};

/**
 * Find a non-overlapping area in Top by shifting to the right.
 * @param {object} area Position object {x, y, w, h}.
 * @return {object} Non-overlapping position object {x, y, w, h}.
 */
AyonHarmony.findNonOverlappingArea = function(area) {
    var candidate = {
        x: area.x,
        y: area.y,
        w: area.w,
        h: area.h
    };
    var occupiedRects = [];
    Backdrop.backdrops("Top").forEach(function(backdrop) {
        occupiedRects.push({
            left: backdrop.position.x,
            top: backdrop.position.y,
            right: backdrop.position.x + backdrop.position.w,
            bottom: backdrop.position.y + backdrop.position.h
        });
    });
    node.subNodes("Top").forEach(function(nodePath) {
        occupiedRects.push({
            left: node.coordX(nodePath),
            top: node.coordY(nodePath),
            right: node.coordX(nodePath) + node.width(nodePath),
            bottom: node.coordY(nodePath) + node.height(nodePath)
        });
    });

    var safety = 0;
    while (safety < 10000) {
        safety++;
        var candidateRect = {
            left: candidate.x,
            top: candidate.y,
            right: candidate.x + candidate.w,
            bottom: candidate.y + candidate.h
        };
        var overlap = null;
        for (var i = 0; i < occupiedRects.length; i++) {
            if (AyonHarmony.rectsOverlap(candidateRect, occupiedRects[i])) {
                overlap = occupiedRects[i];
                break;
            }
        }
        if (!overlap) {
            break;
        }
        candidate.x = overlap.right + PARENT_BACKDROP_GRID_GAP;
    }
    return candidate;
};

/**
 * Prevent new content from overlapping existing content.
 * If area is passed, placement is constrained inside it and the area may be
 * expanded to fit.
 *
 * Placement preference: move right first, then below.
 *
 * @param {Array} newBackdrops New backdrop objects with .position, .title.text.
 * @param {Array<string>} newNodes New node path strings.
 * @param {object|null} area Optional area {x, y, w, h}.
 * @param {string|null} excludeBackdropName Optional backdrop name to ignore in occupancy.
 * @return {object} Object with `allBackdrops` and `area`.
 */
AyonHarmony.preventOverlap = function(
    newBackdrops, newNodes, area, excludeBackdropName
) {
    if (newBackdrops.length === 0 && newNodes.length === 0) {
        return {
            allBackdrops: Backdrop.backdrops("Top"),
            area: area || null
        };
    }

    var bounds = AyonHarmony.getContentBounds(newBackdrops, newNodes);
    if (bounds.right === -Infinity) {
        return {
            allBackdrops: Backdrop.backdrops("Top"),
            area: area || null
        };
    }

    var contentWidth = Math.max(1, bounds.right - bounds.left);
    var contentHeight = Math.max(1, bounds.bottom - bounds.top);

    var newBackdropSnapshot = {};
    newBackdrops.forEach(function(backdrop) {
        var signature = [
            backdrop.title.text,
            backdrop.position.x,
            backdrop.position.y,
            backdrop.position.w,
            backdrop.position.h
        ].join("|");
        newBackdropSnapshot[signature] = true;
    });

    var areaRect = null;
    if (area) {
        areaRect = {
            x: area.x,
            y: area.y,
            w: area.w,
            h: area.h
        };
    }

    var usable = {
        left: -Infinity,
        top: -Infinity,
        right: Infinity,
        bottom: Infinity
    };
    if (areaRect) {
        usable.left = areaRect.x + PARENT_BACKDROP_PADDING;
        usable.top = areaRect.y + PARENT_BACKDROP_TITLE_HEIGHT
            + PARENT_BACKDROP_PADDING;
        usable.right = areaRect.x + areaRect.w - PARENT_BACKDROP_PADDING;
        usable.bottom = areaRect.y + areaRect.h - PARENT_BACKDROP_PADDING;
    }

    var occupiedRects = [];
    Backdrop.backdrops("Top").forEach(function(backdrop) {
        if (excludeBackdropName && backdrop.title && backdrop.title.text
            && backdrop.title.text.toLowerCase() === excludeBackdropName.toLowerCase()) {
            return;
        }
        var signature = [
            backdrop.title.text,
            backdrop.position.x,
            backdrop.position.y,
            backdrop.position.w,
            backdrop.position.h
        ].join("|");
        if (newBackdropSnapshot[signature]) {
            return;
        }
        var rect = {
            left: backdrop.position.x,
            top: backdrop.position.y,
            right: backdrop.position.x + backdrop.position.w,
            bottom: backdrop.position.y + backdrop.position.h
        };
        if (areaRect) {
            var areaBounds = {
                left: usable.left,
                top: usable.top,
                right: usable.right,
                bottom: usable.bottom
            };
            if (!AyonHarmony.rectsOverlap(rect, areaBounds)) {
                return;
            }
        }
        occupiedRects.push(rect);
    });

    var slotWidth = contentWidth + PARENT_BACKDROP_GRID_GAP;
    var slotHeight = contentHeight + PARENT_BACKDROP_GRID_GAP;
    var candidateLeft = areaRect ? usable.left : bounds.left;
    var candidateTop = areaRect ? usable.top : bounds.top;
    var maxRight = -Infinity;
    var maxChildWidth = 0;
    var maxChildHeight = 0;
    occupiedRects.forEach(function(rect) {
        if (rect.right > maxRight) maxRight = rect.right;
        var width = rect.right - rect.left;
        var height = rect.bottom - rect.top;
        if (width > maxChildWidth) maxChildWidth = width;
        if (height > maxChildHeight) maxChildHeight = height;
    });

    if (areaRect) {
        // Keep a stable grid pitch across mixed sizes by using the larger
        // value between the new content and current children.
        slotWidth = Math.max(contentWidth, maxChildWidth) + PARENT_BACKDROP_GRID_GAP;
        slotHeight = Math.max(contentHeight, maxChildHeight) + PARENT_BACKDROP_GRID_GAP;

        var foundInsideArea = false;
        for (
            var rowTop = usable.top;
            rowTop + contentHeight <= usable.bottom;
            rowTop += slotHeight
        ) {
            for (
                var colLeft = usable.left;
                colLeft + contentWidth <= usable.right;
                colLeft += slotWidth
            ) {
                var inAreaCandidate = {
                    left: colLeft,
                    top: rowTop,
                    right: colLeft + contentWidth,
                    bottom: rowTop + contentHeight
                };
                var hasOverlap = false;
                for (var idx = 0; idx < occupiedRects.length; idx++) {
                    if (AyonHarmony.rectsOverlap(inAreaCandidate, occupiedRects[idx])) {
                        hasOverlap = true;
                        break;
                    }
                }
                if (!hasOverlap) {
                    candidateLeft = colLeft;
                    candidateTop = rowTop;
                    foundInsideArea = true;
                    break;
                }
            }
            if (foundInsideArea) {
                break;
            }
        }

        if (!foundInsideArea) {
            candidateLeft = Math.max(maxRight, usable.left) + PARENT_BACKDROP_GRID_GAP;
            candidateTop = usable.top;

            var requiredRight = candidateLeft + contentWidth + PARENT_BACKDROP_PADDING;
            var currentRight = areaRect.x + areaRect.w;
            if (requiredRight > currentRight) {
                areaRect.w = requiredRight - areaRect.x;
                usable.right = areaRect.x + areaRect.w - PARENT_BACKDROP_PADDING;
            }

            var requiredBottom = candidateTop + contentHeight + PARENT_BACKDROP_PADDING;
            var currentBottom = areaRect.y + areaRect.h;
            if (requiredBottom > currentBottom) {
                areaRect.h = requiredBottom - areaRect.y;
                usable.bottom = areaRect.y + areaRect.h - PARENT_BACKDROP_PADDING;
            }
        }
    } else {
        var safety = 0;
        while (safety < 10000) {
            safety++;
            var candidate = {
                left: candidateLeft,
                top: candidateTop,
                right: candidateLeft + contentWidth,
                bottom: candidateTop + contentHeight
            };
            var overlapRect = null;
            for (var index = 0; index < occupiedRects.length; index++) {
                if (AyonHarmony.rectsOverlap(candidate, occupiedRects[index])) {
                    overlapRect = occupiedRects[index];
                    break;
                }
            }
            if (!overlapRect) {
                break;
            }
            candidateLeft += slotWidth;
        }
    }

    var offsetX = candidateLeft - bounds.left;
    var offsetY = candidateTop - bounds.top;

    newNodes.filter(
        function(nodePath) { return node.parentNode(nodePath) === "Top"; }
    ).forEach(function(nodePath) {
        node.setCoord(
            nodePath,
            node.coordX(nodePath) + offsetX,
            node.coordY(nodePath) + offsetY
        );
    });

    var allBackdrops = Backdrop.backdrops("Top");
    newBackdrops.forEach(function(pastedBackdrop) {
        // Prefer object identity to avoid accidentally moving pre-existing
        // backdrop with the same title/coordinates.
        for (var j = 0; j < allBackdrops.length; j++) {
            if (allBackdrops[j] === pastedBackdrop) {
                allBackdrops[j].position.x += offsetX;
                allBackdrops[j].position.y += offsetY;
                return;
            }
        }
        for (var index = 0; index < allBackdrops.length; index++) {
            var backdrop = allBackdrops[index];
            if (backdrop.title.text === pastedBackdrop.title.text &&
                backdrop.position.x === pastedBackdrop.position.x &&
                backdrop.position.y === pastedBackdrop.position.y &&
                backdrop.position.w === pastedBackdrop.position.w &&
                backdrop.position.h === pastedBackdrop.position.h) {
                allBackdrops[index].position.x += offsetX;
                allBackdrops[index].position.y += offsetY;
                break;
            }
        }
    });
    Backdrop.setBackdrops("Top", allBackdrops);

    return {
        allBackdrops: allBackdrops,
        area: areaRect
    };
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
 * Create container backdrop in Harmony.
 * @function
 * @param {array} args Arguments, see example.
 * @return {string} Resulting backdrop.
 *
 * @example
 * // arguments are in following order:
 * var args = [
 *  backdropName,
 *  useSelection
 * ];
 */
AyonHarmony.createBackdropContainer = function(args) {
    var backdropName = args[0];
    var useSelection = args[1];
    var selectedBackdrops = selection.selectedBackdrops();

    if (useSelection && selectedBackdrops.length > 0) {
        // Rename root backdrop of selection
        // Sh*tty harmony API forces to rewrite all backdrops
        var rootBackdrop = AyonHarmony.getRootBackdrop(selectedBackdrops);
        var allBackdrops = Backdrop.backdrops("Top");
        var selectedBackdropIdx = allBackdrops.map(function(b) { return b.title.text; }).indexOf(rootBackdrop.title.text);
        allBackdrops[selectedBackdropIdx].title.text = backdropName;
        Backdrop.setBackdrops("Top", allBackdrops);
        return allBackdrops[selectedBackdropIdx];
    } else {
        // Create new backdrop
        return Backdrop.addBackdrop(
            "Top",
            {
                "position"    : {"x": 0, "y" :0, "w":300, "h":300},
                "title"       : {"text" : backdropName, "size" : 14, "font" : "Arial"},
                // "color"       : TODO
            }
        );
    }
};


/**
 * Get root backdrop.
 * The root backdrop is the backdrop that contains all other backdrops.
 * @function
 * @param {array} backdrops List of backdrops.
 * @return {object} Root backdrop.
 */
AyonHarmony.getRootBackdrop = function(backdrops) {
    // Sort backdrops by x, y position and width, height
    backdrops.sort(function(a, b) {
        if (a.position.x != b.position.x) return a.position.x - b.position.x;
        if (a.position.y != b.position.y) return a.position.y - b.position.y;
        if (a.position.w != b.position.w) return a.position.w - b.position.w;
        if (a.position.h != b.position.h) return a.position.h - b.position.h;
        return 0;
    });

    return backdrops[0];
}


/**
 * Substitute one node with another.
 * @function
 * @param {string} nodePath Path to node.
 * @param {string} newNodePath Path to new node to substitute with.
 */
AyonHarmony.substituteNode = function(nodePath, newNodePath) {
    var oldNode = $.scn.$node(nodePath);
    var newNode = $.scn.$node(newNodePath);

    // Links
    var allLinks = oldNode.getInLinks().concat(oldNode.getOutLinks());
    allLinks.forEach(function(link) {
        link.insertNode(newNode);
    });

    // Exposure
    if (oldNode instanceof $.oDrawingNode) {
        var oldDrawing = oldNode.getAttributeByName("DRAWING.ELEMENT");
        var newDrawing = newNode.getAttributeByName("DRAWING.ELEMENT");
        var exposureMap = [];

        // Cache old exposure first, so we can restore it exactly.
        oldDrawing.frames.forEach(function(frame) {
            if (frame.frameNumber > 0) {
                exposureMap.push({
                    frameNumber: frame.frameNumber,
                    isBlank: frame.isBlank
                });
            }
        });

        var newDrawingName = "";
        newDrawing.frames.forEach(function(frame) {
            if (frame.frameNumber > 0 && frame.value !== "") {
                newDrawingName = frame.value;
            }
        });

        // Clear all values on the new drawing.
        newDrawing.frames.forEach(function(frame) {
            if (frame.frameNumber > 0) {
                newDrawing.setValue("", frame.frameNumber);
            }
        });

        // Restore full frame-by-frame exposure.
        // Non-blank frames must be remapped to the new element drawing name.
        exposureMap.forEach(function(frameData) {
            if (frameData.isBlank) {
                newDrawing.setValue("", frameData.frameNumber);
            } else {
                newDrawing.setValue(newDrawingName, frameData.frameNumber);
            }
        });
    }

    // Position
    newNode.nodePosition = oldNode.nodePosition;

    // Delete old node
    var name = oldNode.name;
    oldNode.remove();
    newNode.name = name;
}


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
 * 
 */
AyonHarmony.removeBackdrop = function(args) {
    // Delete all nodes in backdrop
    var backdrop = args[0];
    var removeContents = args[1];
    if (removeContents){
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
    }

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
 * Import image file.
 * @function
 * @param {array} args Arguments, see example.
 * @return {string} Resulting node.
 * 
 * @example
 * // arguments are in following order:
 * var args = [
 *  filepath,
 *  exposeOnlyCurrentFrame
 * ];
 */
AyonHarmony.importImageFile = function(args) {
    var filepath = args[0];
    var exposeOnlyCurrentFrame = args[1];

    // Create in the active node group
    var activeGroup = AyonHarmony.getActiveNodeGroup();
    var drawingNode = activeGroup.importImage(filepath);

    if (exposeOnlyCurrentFrame) {
        drawing = drawingNode.getAttributeByName("DRAWING.ELEMENT");
        var currentFrame = frame.current();
        drawing.frames.forEach(function(f) {
            if (f.frameNumber == currentFrame) {
                f.isKeyframe = true;
            }
        });
        drawing.frames.forEach(function(f) {
            // Skip "0" ghost frame to avoid deleting it
            if (f.frameNumber != currentFrame && f.frameNumber != 0) {
                drawing.setValue("", f.frameNumber);
            }
        });
    }

    return drawingNode.path;
}

/**
 * Replace image file.
 * @function
 * @param {array} args Arguments, see example.
 * @return {string} Resulting node.
 * 
 * @example
 * // arguments are in following order:
 * var args = [
 *  node,
 *  filepath,
 * ];
 */
AyonHarmony.replaceImageFile = function(args) {
    var imageNodePath = args[0];
    var filePath = args[1];
    var newImageNode = null;

    $.beginUndo("AYON: Replace Image");
    try {
        newImageNode = $.scn.root.importImage(filePath);
        AyonHarmony.substituteNode(imageNodePath, newImageNode.path);
    } catch (error) {
        $.cancelUndo();
        throw error;
    }
    $.endUndo();

    return newImageNode.path;
}


/**
 * Get active node group path.
 * @function
 * @return {$.oGroupNode} Currently opened node group path, default is "Top" group if no node view is opened.
 */
AyonHarmony.getActiveNodeGroup = function() {
    var nodeView = null;
    for (var i = 0; i < 200; i++) {
        var viewName = 'View' + i;
        if (view.type(viewName) == 'Node View') {
            nodeView = viewName;
            break;
        }
    }

    var currentGroup;
    if (nodeView === null) { // No node view found
        currentGroup = $.scn.root;
    } else {
        currentGroup = $.scn.$node(view.group(nodeView));
    }

    return currentGroup;
}


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
 * Get all paths of palettes in scene.
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
 * Get palette by path.
 * @function
 * @param {string} palettePath Path to palette file.
 * @return {object} Palette object.
 */
AyonHarmony.getPaletteByPath = function(palettePath) {
    var palettes = $.scene.palettes;
    for (var i = 0; i < palettes.length; i++) {
        if (palettes[i].path == palettePath) {
            return palettes[i];
        }
    }
}

/**
 * Remove palette from scene matching its path.
 * @function
 * @param {string} palettePath Path to palette file.
 * @return {int} Index of removed palette.
 */
AyonHarmony.removePaletteByPath = function(palettePath) {
    var palette = AyonHarmony.getPaletteByPath(palettePath);
    var paletteIndex = palette.index;
    if (palette) {
        PaletteObjectManager.getScenePaletteList().removePaletteById(palette.id);
    }
    return paletteIndex;
}


/**
 * Move palette to index.
 * @function
 * @param {array} args  Arguments for template extraction.
 *
 * @example
 * // arguments are in this order:
 * var args = [palettePath, toIndex];
 */
AyonHarmony.movePaletteToIndex = function(args) {
    var palettePath = args[0];
    var palette = AyonHarmony.getPaletteByPath(palettePath);
    var toIndex = args[1];
    MessageLog.trace("zozo");
    MessageLog.trace(toIndex + " " + palette.index);

    // Move down
    if (toIndex < palette.index) {
        for (var i = palette.index; i > toIndex; i--) {
            PaletteObjectManager.getScenePaletteList().movePaletteUp(palette.id);
        }
    }
    // Move up
    else if (toIndex > palette.index) {
        for (var i = palette.index; i < toIndex; i++) {
            PaletteObjectManager.getScenePaletteList().movePaletteDown(palette.id);
        }
    }
}


/**
 * Get layers info
 * Use native Harmony API to avoid OpenHarmony wrapper overhead for better performance.
 *
 * Return information about name, fullName, selection etc.
 * @function
 * @param {boolean} [topOnly=false] If true, only return layers at the top level (not inside groups).
 * @return {object[]} Array of objects with info about node/layer.
 */
AyonHarmony.getLayerInfos = function(topOnly) {
    if (topOnly === undefined) {
        topOnly = false;
    }
    var result = [];
    var numLayers = Timeline.numLayers;

    // Build selected layers lookup
    var selectedLayers = {};
    var numSelected = Timeline.numLayerSel;
    for (var s = 0; s < numSelected; s++) {
        selectedLayers[Timeline.selToLayer(s)] = true;
    }

    // Iterate timeline layers using native API
    for (var i = 0; i < numLayers; i++) {
        // Skip non-node layers (columns, etc.)
        if (!Timeline.layerIsNode(i)) continue;

        var nodePath = Timeline.layerToNode(i);

        // Determine Group Status
        // node.parentNode(nodePath) returns the path of the parent (e.g., "Top/MyGroup")
        var parentPath = node.parentNode(nodePath);

        // In Harmony, "Top" is the root level. Anything else means it's in a group.
        var isInsideGroup = (parentPath !== "Top" && parentPath !== "");

        // Filter to top-level only if requested
        if (topOnly && isInsideGroup) continue;

        var groupName = isInsideGroup ? node.getName(parentPath) : null;

        // Get node properties using native API
        var nodeColor = node.getColor(nodePath);

        // Convert to hex format #RRGGBBAA
        var r = ("00" + nodeColor.r.toString(16)).slice(-2);
        var g = ("00" + nodeColor.g.toString(16)).slice(-2);
        var b = ("00" + nodeColor.b.toString(16)).slice(-2);
        var a = ("00" + nodeColor.a.toString(16)).slice(-2);
        var colorStr = '#' + r + g + b + a;

        result.push({
            "name": node.getName(nodePath),
            "color": colorStr,
            "fullName": nodePath,
            "selected": selectedLayers[i] === true,
            "position": i,
            "enabled": node.getEnable(nodePath),
            "isGrouped": isInsideGroup,
            "parentGroup": groupName,
            "parentPath": parentPath
        });
    }

    return result;
};

/**
 * Rename node in Harmony.
 * @function
 * @param {string} node_name  Node name.
 * @param {string} new_name  Node name.
 */
AyonHarmony.renameNode = function(args) {
    var node_name = args[0];
    var new_name = args[1];
    var existing_node = $.scene.getNodeByPath("Top/" + node_name);
    if (existing_node){
        existing_node.name = new_name;
    }
};
