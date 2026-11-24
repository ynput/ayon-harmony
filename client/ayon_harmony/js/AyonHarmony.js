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
 * Check whether one backdrop fully contains another.
 * @param {object} container Backdrop object with .position.
 * @param {object} child Backdrop object with .position.
 * @return {boolean}
 */
AyonHarmony.backdropContains = function(container, child) {
    if (!container || !child || !container.position || !child.position) {
        return false;
    }
    return container.position.x <= child.position.x
        && container.position.y <= child.position.y
        && (container.position.x + container.position.w)
            >= (child.position.x + child.position.w)
        && (container.position.y + container.position.h)
            >= (child.position.y + child.position.h);
};

/**
 * Find backdrop that contains all other backdrops.
 * @param {Array} backdrops Backdrop objects.
 * @return {object|null} Backdrop containing all others, if any.
 */
AyonHarmony.findBackdropContainingAll = function(backdrops) {
    if (!backdrops || backdrops.length === 0) {
        return null;
    }
    if (backdrops.length === 1) {
        return backdrops[0];
    }
    for (var i = 0; i < backdrops.length; i++) {
        var candidate = backdrops[i];
        var containsAll = true;
        for (var j = 0; j < backdrops.length; j++) {
            if (i === j) {
                continue;
            }
            if (!AyonHarmony.backdropContains(candidate, backdrops[j])) {
                containsAll = false;
                break;
            }
        }
        if (containsAll) {
            return candidate;
        }
    }
    return null;
};

/**
 * Find largest backdrop by area.
 * @param {Array} backdrops Backdrop objects.
 * @return {object|null} Largest backdrop.
 */
AyonHarmony.findLargestBackdrop = function(backdrops) {
    if (!backdrops || backdrops.length === 0) {
        return null;
    }
    var largest = backdrops[0];
    for (var i = 1; i < backdrops.length; i++) {
        var currentArea = backdrops[i].position.w * backdrops[i].position.h;
        var largestArea = largest.position.w * largest.position.h;
        if (currentArea > largestArea) {
            largest = backdrops[i];
        }
    }
    return largest;
};

/**
 * Find main backdrop from a collection.
 * Main backdrop is one containing all others, otherwise the largest.
 * @param {Array} backdrops Backdrop objects.
 * @return {object|null} Main backdrop.
 */
AyonHarmony.findMainBackdrop = function(backdrops) {
    var containing = AyonHarmony.findBackdropContainingAll(backdrops);
    if (containing) {
        return containing;
    }
    return AyonHarmony.findLargestBackdrop(backdrops);
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

    // Also treat existing top-level nodes as occupied space so that new
    // content is not placed on top of them even when no backdrops are present.
    var newNodeSet = {};
    newNodes.forEach(function(n) { newNodeSet[n] = true; });
    node.subNodes("Top").forEach(function(nodePath) {
        if (newNodeSet[nodePath]) { return; }
        var rect = {
            left: node.coordX(nodePath),
            top: node.coordY(nodePath),
            right: node.coordX(nodePath) + node.width(nodePath),
            bottom: node.coordY(nodePath) + node.height(nodePath)
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
        var slotWidth = Math.max(contentWidth, maxChildWidth) + PARENT_BACKDROP_GRID_GAP;
        var slotHeight = Math.max(contentHeight, maxChildHeight) + PARENT_BACKDROP_GRID_GAP;

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
            candidateLeft = overlapRect.right + PARENT_BACKDROP_GRID_GAP;
        }
    }

    var offsetX = candidateLeft - bounds.left;
    var offsetY = candidateTop - bounds.top;

    newNodes.forEach(function(nodePath) {
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
 * Collect a node path and all its descendants into `acc` (parent-first order).
 *
 * @function
 * @param {Array<string>} paths Node paths to walk.
 * @param {Array<string>} acc   Accumulator.
 * @return {Array<string>} Accumulator.
 */
AyonHarmony.collectNodePaths = function(paths, acc) {
    paths.forEach(function(p) {
        acc.push(p);
        var subs = node.subNodes(p);
        if (subs && subs.length > 0) {
            AyonHarmony.collectNodePaths(subs, acc);
        }
    });
    return acc;
};


/**
 * Capture the full node tree of a backdrop (structure + attribute snapshots).
 * Parent-first order so that nodes can be recreated before their children.
 *
 * @function
 * @param {object} backdrop Backdrop object.
 * @return {Array<object>} Entries with path, name, parent, type, x, y, snapshot.
 */
AyonHarmony.captureNodeTree = function(backdrop) {
    var entries = [];
    AyonHarmony.collectNodePaths(Backdrop.nodes(backdrop), []).forEach(
        function(p) {
            var oN = $.scene.getNodeByPath(p);
            if (!oN) {
                return;
            }
            entries.push({
                path: p,
                name: oN.name,
                parent: node.parentNode(p),
                type: oN.type,
                x: node.coordX(p),
                y: node.coordY(p),
                snapshot: AyonHarmony.getAttributeSnapshot(oN)
            });
        }
    );
    return entries;
};


/**
 * Capture every link that touches a backdrop node (internal and external).
 *
 * @function
 * @param {object} backdrop Backdrop object.
 * @return {Array<object>} List of links {srcNode, srcPort, dstNode, dstPort}.
 */
AyonHarmony.captureBackdropLinks = function(backdrop) {
    var allNodes = AyonHarmony.collectNodePaths(Backdrop.nodes(backdrop), []);
    var seen = {};
    var links = [];

    // Deal with a link only once
    function addLink(src, srcPort, dst, dstPort) {
        var key = src + "|" + srcPort + "|" + dst + "|" + dstPort;
        if (seen[key]) {
            return;
        }
        seen[key] = true;
        links.push({
            srcNode: src,
            srcPort: srcPort,
            dstNode: dst,
            dstPort: dstPort
        });
    }

    // Input links
    allNodes.forEach(function(n) {
        for (var i = 0; i < node.numberOfInputPorts(n); i++) {
            var inLink = node.srcNodeInfo(n, i);
            if (inLink == null) continue;
            addLink(inLink.node, inLink.port, n, i);
        }
    });

    // Output links
    allNodes.forEach(function(n) {
        for (var i = 0; i < node.numberOfOutputPorts(n); i++) {
            for (var j = 0; j < node.numberOfOutputLinks(n, i); j++) {
                var outLink = node.dstNodeInfo(n, i, j);
                if (outLink == null) continue;
                addLink(n, i, outLink.node, outLink.port);
            }
        }
    });

    return links;
};


/**
 * Restore a node tree captured by captureNodeTree() onto a freshly loaded
 * backdrop.
 *
 * Harmony appends a `_N` suffix to a pasted node when its name collides, so a
 * freshly loaded node may be `X_1` where the captured one was `X`. Matching
 * therefore tries the exact path first and then the suffixed variants. Once a
 * node is matched, its original name is restored (after Harmony's dedup has
 * done its job) so attributes and links line up with the captured tree.
 *
 * Nodes with no match at all are user-added and are recreated under their
 * original parent with their original position and attributes.
 *
 * @function
 * @param {Array<object>} entries  Entries from captureNodeTree().
 * @param {Array<string>} newPaths Paths of the freshly loaded nodes.
 * @return {object} Mapping of captured paths to their current path.
 */
AyonHarmony.restoreNodeTree = function(entries, newPaths) {
    var existing = {};
    newPaths.forEach(function(p) { existing[p] = true; });

    var pathMap = {};  // old path -> current path
    var used = {};     // current path already consumed by a match

    function typeMatches(path, type) {
        return node.type(path) === type;
    }

    // Find a freshly loaded node matching an old entry. Exact name first, then
    // the `_N` variants Harmony produces on name collisions.
    function findMatch(entry, parentPath) {
        var base = (parentPath ? parentPath + "/" : "") + entry.name;
        if (existing[base] && !used[base] && typeMatches(base, entry.type)) {
            return base;
        }
        for (var n = 1; n < 1000; n++) {
            var candidate = base + "_" + n;
            if (existing[candidate] && !used[candidate]
                && typeMatches(candidate, entry.type)) {
                return candidate;
            }
        }
        return null;
    }

    // Renaming a node also moves its descendants, so keep the lookup table in
    // sync for the children that will be processed next.
    function remapPaths(oldPath, newPath) {
        [existing, used].forEach(function(set) {
            Object.keys(set).forEach(function(k) {
                if (k === oldPath) {
                    delete set[k];
                    set[newPath] = true;
                } else if (k.indexOf(oldPath + "/") === 0) {
                    delete set[k];
                    set[newPath + k.substring(oldPath.length)] = true;
                }
            });
        });
    }

    entries.forEach(function(entry) {
        var parentPath = pathMap[entry.parent] || entry.parent;
        var matchPath = findMatch(entry, parentPath);

        if (matchPath) {
            used[matchPath] = true;
            var oN = $.scene.getNodeByPath(matchPath);
            AyonHarmony.applyAttributeSnapshot(oN, entry.snapshot);
            if (node.coordX(matchPath) !== entry.x
                || node.coordY(matchPath) !== entry.y) {
                node.setCoord(matchPath, entry.x, entry.y);
            }
            // Restore the original name.
            if (matchPath !== entry.path) {
                oN.name = entry.name;
                if (oN.path !== matchPath) {
                    remapPaths(matchPath, oN.path);
                    used[oN.path] = true;
                    matchPath = oN.path;
                }
            }
            pathMap[entry.path] = matchPath;
            return;
        }

        // Missing node: user-added, recreate it under its original parent.
        if (!$.scene.getNodeByPath(parentPath)) {
            return;
        }
        var createdPath = node.add(
            parentPath, entry.name, entry.type, entry.x, entry.y, 0
        );
        node.setCoord(createdPath, entry.x, entry.y);
        AyonHarmony.applyAttributeSnapshot(
            $.scene.getNodeByPath(createdPath), entry.snapshot
        );
        existing[createdPath] = true;
        used[createdPath] = true;
        pathMap[entry.path] = createdPath;
    });

    return pathMap;
};


/**
 * Reconcile the links of a switched container with the captured wiring.
 *
 * Links between preserved nodes (matched or recreated) that the captured tree
 * did not have are removed, and captured links that are missing are added.
 * Correct links are left untouched, since unlinking/re-linking them perturbs
 * Multi-Port ports. Links involving brand-new representation nodes are left
 * alone; external links are restored.
 *
 * @function
 * @param {Array<object>} links   Links from captureBackdropLinks().
 * @param {object}        pathMap Mapping from restoreNodeTree().
 */
AyonHarmony.restoreNodeLinks = function(links, pathMap) {
    function linkKey(src, srcPort, dst, dstPort) {
        return src + "|" + srcPort + "|" + dst + "|" + dstPort;
    }

    // Current paths of every node that was preserved across the switch.
    var preserved = {};
    Object.keys(pathMap).forEach(function(oldPath) {
        var newPath = pathMap[oldPath];
        if ($.scene.getNodeByPath(newPath)) {
            preserved[newPath] = true;
        }
    });

    // Captured wiring, remapped to the current paths.
    var captured = {};
    links.forEach(function(l) {
        var src = pathMap[l.srcNode] || l.srcNode;
        var dst = pathMap[l.dstNode] || l.dstNode;
        captured[linkKey(src, l.srcPort, dst, l.dstPort)] = {
            src: src, srcPort: l.srcPort, dst: dst, dstPort: l.dstPort
        };
    });

    // Remove links between preserved nodes that the captured tree did not have
    // (e.g. a representation link bypassing a node the user inserted).
    Object.keys(preserved).forEach(function(dst) {
        for (var i = 0; i < node.numberOfInputPorts(dst); i++) {
            var current = node.srcNodeInfo(dst, i);
            if (current == null || !preserved[current.node]) {
                continue;
            }
            if (!captured[linkKey(current.node, current.port, dst, i)]) {
                node.unlink(dst, i);
                i--;  // ports shift after unlink
            }
        }
    });

    // Add captured links that are currently missing.
    Object.keys(captured).forEach(function(k) {
        var l = captured[k];
        if (!$.scene.getNodeByPath(l.src) || !$.scene.getNodeByPath(l.dst)) {
            return;
        }
        var current = node.srcNodeInfo(l.dst, l.dstPort);
        if (current != null && current.node === l.src
            && current.port === l.srcPort) {
            return;  // already wired
        }
        node.link(l.src, l.srcPort, l.dst, l.dstPort);
    });
};


/**
 * Capture a snapshot of a node's attribute values, including animation
 * keyframes and drawing substitutions. Pair with applyAttributeSnapshot().
 *
 * Ported from OpenHarmony's oNode so the vendored library stays untouched.
 *
 * @function
 * @param {object} oNode oNode instance (from $.scene.getNodeByPath).
 * @return {object} Plain object mapping attribute keywords to captured values.
 */
AyonHarmony.getAttributeSnapshot = function(oNode) {
    var snapshot = {};

    // Capture per-keyframe interpolation metadata (tangent handles, ease,
    // continuity). Only BEZIER/EASE columns expose handles; 3DPATH and
    // QUATERNION_PATH delegate to their velocity curve (BEZIER or EASE).
    function captureKeyframeEase(frameObject, easeType) {
        if (easeType !== "BEZIER" && easeType !== "EASE") return null;
        try {
            var rawEase = frameObject.ease;
            if (!rawEase) return null;
            var capturedEase = {
                x: rawEase.x,
                y: rawEase.y,
                constant: rawEase.constant,
                continuity: rawEase.continuity
            };
            if (easeType === "BEZIER" && rawEase.easeIn && rawEase.easeOut) {
                capturedEase.easeIn = { x: rawEase.easeIn.x, y: rawEase.easeIn.y };
                capturedEase.easeOut = { x: rawEase.easeOut.x, y: rawEase.easeOut.y };
            } else if (easeType === "EASE" && rawEase.easeIn && rawEase.easeOut) {
                capturedEase.easeIn = {
                    point: rawEase.easeIn.point,
                    angle: rawEase.easeIn.angle
                };
                capturedEase.easeOut = {
                    point: rawEase.easeOut.point,
                    angle: rawEase.easeOut.angle
                };
            }
            return capturedEase;
        } catch (_easeError) {
            return null;
        }
    }

    function captureAttr(attr) {
        // --- Drawing substitution column: record each distinct drawing change ---
        if (attr.type === "ELEMENT") {
            var elementCol = attr.column;
            if (elementCol) {
                var elementColName = elementCol.uniqueName;
                var sceneLen = $.scene.length;
                var elementData = [];
                var prev = null;
                for (var frame = 1; frame <= sceneLen; frame++) {
                    var drawingName = column.getEntry(elementColName, 1, frame);
                    // Blanks ("") are intentional exposure gaps
                    if (drawingName === null || drawingName === undefined) drawingName = "";
                    if (prev === null || drawingName !== prev) {
                        elementData.push({ f: frame, v: drawingName });
                        prev = drawingName;
                    }
                }
                // Record the column's display name.
                var capturedColumnDisplay = null;
                try { capturedColumnDisplay = column.getDisplayName(elementColName); } catch (_dn) {}
                if (elementData.length > 0) {
                    snapshot[attr.keyword] = {
                        __anim: true,
                        keys: elementData,
                        colType: "DRAWING",
                        columnDisplay: capturedColumnDisplay
                    };
                }
            }
            return;
        }

        // --- Compound attribute: recurse into sub-attributes ---
        var subs = attr.subAttributes;
        if (subs && subs.length > 0) {
            for (var subIndex = 0; subIndex < subs.length; subIndex++) captureAttr(subs[subIndex]);
            return;
        }

        // --- Animated column: store each keyframe value + ease metadata ---
        var col = attr.column;
        if (col) {
            if (col.type === "EXPR") return;
            var keyframes = col.keyframes;
            if (keyframes && keyframes.length > 0) {
                var columnEaseType = col.easeType;
                var keyData = [];
                for (var keyIndex = 0; keyIndex < keyframes.length; keyIndex++) {
                    var keyframe = keyframes[keyIndex];
                    var keyValue = keyframe.value;
                    // Normalise vector values to a plain {x,y,z} object.
                    if (keyValue !== null && typeof keyValue === 'object' && typeof keyValue.x === 'number') {
                        keyValue = {
                            x: keyValue.x,
                            y: keyValue.y,
                            z: (typeof keyValue.z === 'number') ? keyValue.z : 0
                        };
                    }
                    var capturedKey = { f: keyframe.frameNumber, v: keyValue };
                    var capturedEase = captureKeyframeEase(keyframe, columnEaseType);
                    if (capturedEase) capturedKey.ease = capturedEase;
                    keyData.push(capturedKey);
                }
                if (keyData.length > 0) {
                    snapshot[attr.keyword] = {
                        __anim: true,
                        keys: keyData,
                        colType: col.type,
                        easeType: columnEaseType
                    };
                    return;
                }
            }
        }

        // --- Static value: store as-is, skip XML-blob strings ---
        var staticValue = attr.getValue();
        if (typeof staticValue === 'string' && staticValue.charAt(0) === '<') return;
        snapshot[attr.keyword] = staticValue;
    }

    var attrs = oNode.attributes;
    for (var attrKey in attrs) {
        try { captureAttr(attrs[attrKey]); } catch (_attrError) {}
    }

    return snapshot;
};


/**
 * Apply a snapshot produced by getAttributeSnapshot() to a node's attributes.
 * Each attribute is applied independently; failures log a message.
 *
 * Ported from OpenHarmony's oNode so the vendored library stays untouched.
 *
 * @function
 * @param {object} oNode    oNode instance (from $.scene.getNodeByPath).
 * @param {object} snapshot Object from getAttributeSnapshot().
 * @return {object} oNode, for chaining.
 */
AyonHarmony.applyAttributeSnapshot = function(oNode, snapshot) {
    // Early-out for nodes that captured no attributes (Multi-Port-In/Out, etc.).
    var hasAnyKey = false;
    for (var probeKey in snapshot) { hasAnyKey = true; break; }
    if (!hasAnyKey) return oNode;

    function applyEaseAt(columnName, easeType, easeData) {
        if (!columnName || !easeData) return;
        try {
            var continuity = easeData.continuity || "SMOOTH";
            var isConstant = !!easeData.constant;
            if (easeType === "BEZIER") {
                var bezierEaseIn = (easeData.easeIn && typeof easeData.easeIn.x === 'number')
                    ? easeData.easeIn
                    : { x: easeData.x, y: easeData.y };
                var bezierEaseOut = (easeData.easeOut && typeof easeData.easeOut.x === 'number')
                    ? easeData.easeOut
                    : { x: easeData.x, y: easeData.y };
                func.setBezierPoint(
                    columnName,
                    easeData.x,
                    easeData.y,
                    bezierEaseIn.x,
                    bezierEaseIn.y,
                    bezierEaseOut.x,
                    bezierEaseOut.y,
                    isConstant,
                    continuity
                );
            } else if (easeType === "EASE") {
                var velocityEaseIn = (easeData.easeIn && typeof easeData.easeIn.point === 'number')
                    ? easeData.easeIn
                    : { point: 0, angle: 0 };
                var velocityEaseOut = (easeData.easeOut && typeof easeData.easeOut.point === 'number')
                    ? easeData.easeOut
                    : { point: 0, angle: 0 };
                func.setEasePoint(
                    columnName,
                    easeData.x,
                    easeData.y,
                    velocityEaseIn.point,
                    velocityEaseIn.angle,
                    velocityEaseOut.point,
                    velocityEaseOut.angle,
                    isConstant,
                    continuity
                );
            }
        } catch (_applyEaseError) {}
    }

    for (var keyword in snapshot) {
        try {
            var attr = oNode.getAttributeByName(keyword);
            if (!attr) continue;

            var snapVal = snapshot[keyword];
            var isAnimatedSnapshot = (
                snapVal && typeof snapVal === 'object' && snapVal.__anim === true
            );

            // Static value fast-path: no native `attr.column` lookup needed.
            if (!isAnimatedSnapshot) {
                attr.setValue(snapVal);
                continue;
            }

            var col = attr.column;
            if (attr.type === "ELEMENT") {
                if (!col) continue;  // no drawing column on the new node
            } else if (col && col.type === "EXPR") {
                continue;  // expression-driven, leave the template's expression alone
            }

            var keys = snapVal.keys;
            if (attr.type === "ELEMENT") {
                // Drawing exposure: explicitly fill every frame across the scene.
                var elementColName = col.uniqueName;

                // Drawing columns are often shared across several nodes.
                if (snapVal.columnDisplay !== undefined && snapVal.columnDisplay !== null) {
                    var newColumnDisplay = null;
                    try { newColumnDisplay = column.getDisplayName(elementColName); } catch (_dn) {}
                    if (newColumnDisplay !== snapVal.columnDisplay) {
                        continue;
                    }
                }

                var sceneLen = $.scene.length;
                var elementKeyIndex = 0;
                var setEntryFailed = false;

                // If the pasted frame-1 value differs from the snapshot, process
                // frames 2+ first so frame-1 is not overwritten while later
                // frames are still "held" from it.
                var frame1KeyIndex = 0;
                while (frame1KeyIndex + 1 < keys.length && keys[frame1KeyIndex + 1].f <= 1) frame1KeyIndex++;
                var frame1Desired = keys[frame1KeyIndex].v;
                var deferFrame1 = column.getEntry(elementColName, 1, 1) !== frame1Desired;
                var frameFillOrder = [];
                for (var fillFrame = (deferFrame1 ? 2 : 1); fillFrame <= sceneLen; fillFrame++) frameFillOrder.push(fillFrame);
                if (deferFrame1) frameFillOrder.push(1); // frame 1 processed last

                for (var fillIndex = 0; fillIndex < frameFillOrder.length; fillIndex++) {
                    var targetFrame = frameFillOrder[fillIndex];
                    while (elementKeyIndex + 1 < keys.length && keys[elementKeyIndex + 1].f <= targetFrame) elementKeyIndex++;
                    // When retrying frame 1 (processed last), reset to attempt
                    // column.setEntry again — the column is no longer freshly
                    // pasted at this point.
                    if (deferFrame1 && targetFrame === 1) setEntryFailed = false;
                    var desiredDrawing = keys[elementKeyIndex].v;
                    if (column.getEntry(elementColName, 1, targetFrame) === desiredDrawing) continue;
                    if (!setEntryFailed) {
                        try {
                            column.setEntry(elementColName, 1, targetFrame, desiredDrawing);
                            continue;
                        } catch (_setEntryError) {
                            setEntryFailed = true;
                        }
                    }
                    node.setTextAttr(oNode.path, "drawing.element", targetFrame, desiredDrawing);
                }
                continue;
            }

            // --- Animated non-drawing column.
            // Step 1: Delete every template keyframe that's not in our snapshot.
            // Step 2: Apply our snapshot values.
            // Step 3: Restore per-keyframe interpolation (handles, ease, continuity).
            var columnName = col ? col.uniqueName : null;
            var columnEaseType = col ? col.easeType : null;
            var snapshotFrameSet = {};
            for (var snapshotKeyIdx = 0; snapshotKeyIdx < keys.length; snapshotKeyIdx++) {
                snapshotFrameSet[keys[snapshotKeyIdx].f] = true;
            }
            // Enumerate template keyframes by raw point index — avoids allocating
            // an oFrame for every frame of the scene via `col.keyframes`.
            if (columnName) {
                var numTemplatePoints = 0;
                try { numTemplatePoints = func.numberOfPoints(columnName); } catch (_npe) {}
                for (var templatePointIdx = 0; templatePointIdx < numTemplatePoints; templatePointIdx++) {
                    var templateFrameNumber = func.pointX(columnName, templatePointIdx);
                    if (snapshotFrameSet[templateFrameNumber]) continue;
                    try { column.clearKeyFrame(columnName, templateFrameNumber); } catch (_clearError) {}
                }
            }
            for (var applyKeyIdx = 0; applyKeyIdx < keys.length; applyKeyIdx++) {
                var snapshotKey = keys[applyKeyIdx];
                attr.setValue(snapshotKey.v, snapshotKey.f);
            }

            if (!col) {
                col = attr.column;
                if (col) {
                    columnName = col.uniqueName;
                    columnEaseType = col.easeType;
                }
            }

            // Two ease passes: Harmony adjusts neighbour handles when a keyframe
            // is written, so the first pass can corrupt earlier writes; pass two
            // locks them in. Same pattern as oColumn.duplicate.
            for (var easePassIdx = 0; easePassIdx < keys.length; easePassIdx++) {
                applyEaseAt(columnName, columnEaseType, keys[easePassIdx].ease);
            }
            for (var easeRepeatIdx = 0; easeRepeatIdx < keys.length; easeRepeatIdx++) {
                applyEaseAt(columnName, columnEaseType, keys[easeRepeatIdx].ease);
            }
        } catch (err) {
            $.log(
                'AyonHarmony.applyAttributeSnapshot: skipped attribute "' + keyword +
                '" on ' + oNode.path + " — " + String(err)
            );
        }
    }

    return oNode;
};


/**
 * Switch a container backdrop.
 *
 * Captures the node tree, links and positions of the existing container,
 * reloads the new representation, then restores the captured tree: matching
 * nodes keep their attributes, position and name, user-added nodes are
 * recreated, and the wiring is reconciled with the captured topology.
 *
 * @function
 * @param {Array} args
 *   [0] {object}      backdrop          Backdrop object (from Backdrop.backdrops).
 *   [1] {string}      loaderName        Key in AyonHarmony.Loaders (e.g. "TemplateLoader").
 *   [2] {string}      templatePath      Ready-to-use .tpl path.
 *   [3] {string}      overrideName      Backdrop name override (or "").
 *   [4] {string|null} parentBackdropName
 * @return {string} New backdrop name.
 */
AyonHarmony.switchContainer = function(args) {
    var backdrop           = args[0];
    var loaderName         = args[1];
    var templatePath       = args[2];
    var overrideName       = args[3] || "";
    var parentBackdropName = args[4] || null;

    var oldPosition = backdrop.position;

    // Capture the full node tree and links before removing the old container.
    var oldTree = AyonHarmony.captureNodeTree(backdrop);
    var allLinks = AyonHarmony.captureBackdropLinks(backdrop);

    selection.clearSelection();

    // Batch the whole swap (remove + load + restore) into a single undo step.
    scene.beginUndoRedoAccum("AYON: Switch Container");
    var newBackdropName = "";
    try {
        AyonHarmony.removeBackdrop([backdrop, true]);
        newBackdropName = AyonHarmony.Loaders[loaderName].loadContainer(
            [templatePath, overrideName, parentBackdropName]
        );

        var newBackdrop = AyonHarmony.findParentBackdrop(newBackdropName);
        if (!newBackdrop) {
            throw new Error(
                "Backdrop '" + newBackdropName + "' not found after loading."
            );
        }

        // Capture the freshly loaded node paths while `newBackdrop` still
        // matches their position: the backdrop object is not refreshed when the
        // content is shifted below, so querying it afterwards would return
        // nothing and break matching.
        var newTopNodes = Backdrop.nodes(newBackdrop);
        var newTreePaths = AyonHarmony.collectNodePaths(newTopNodes, []);

        // Shift the newly loaded content to where the old backdrop was.
        var dx = oldPosition.x - newBackdrop.position.x;
        var dy = oldPosition.y - newBackdrop.position.y;
        if (dx !== 0 || dy !== 0) {
            newTopNodes.forEach(function(nodePath) {
                node.setCoord(
                    nodePath,
                    node.coordX(nodePath) + dx,
                    node.coordY(nodePath) + dy
                );
            });
            var subBackdrops = AyonHarmony.getSubBackdrops(newBackdrop);
            var allBackdrops = Backdrop.backdrops("Top");
            allBackdrops.forEach(function(b) {
                if (b.title.text === newBackdropName) {
                    b.position.x += dx;
                    b.position.y += dy;
                    return;
                }
                for (var i = 0; i < subBackdrops.length; i++) {
                    if (b.title.text === subBackdrops[i].title.text
                        && b.position.x === subBackdrops[i].position.x
                        && b.position.y === subBackdrops[i].position.y) {
                        b.position.x += dx;
                        b.position.y += dy;
                        break;
                    }
                }
            });
            Backdrop.setBackdrops("Top", allBackdrops);
        }

        // Re-apply user modifications and recreate user-added nodes.
        var pathMap = AyonHarmony.restoreNodeTree(oldTree, newTreePaths);

        // Make sure the new backdrop covers at least the old area
        // so recreated nodes stay inside it.
        var backdropsToFix = Backdrop.backdrops("Top");
        backdropsToFix.forEach(function(b) {
            if (b.title.text !== newBackdropName) {
                return;
            }
            var neededW = Math.max(b.position.w, oldPosition.w);
            var neededH = Math.max(b.position.h, oldPosition.h);
            if (neededW !== b.position.w || neededH !== b.position.h) {
                b.position.w = neededW;
                b.position.h = neededH;
            }
        });
        Backdrop.setBackdrops("Top", backdropsToFix);

        // Restore the wiring (internal + external).
        AyonHarmony.restoreNodeLinks(allLinks, pathMap);
    } finally {
        // Harmony's endUndoRedoAccum can throw while closing its UI on large
        // scenes; the scene data is committed regardless.
        try { scene.endUndoRedoAccum(); } catch (_endAccumErr) {}
    }
    return newBackdropName;
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
