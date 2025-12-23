/* global AyonHarmony:writable, include */
// ***************************************************************************
// *                        TemplateLoader                                   *
// ***************************************************************************


// check if AyonHarmony is defined and if not, load it.
if (typeof AyonHarmony === 'undefined') {
    var AYON_HARMONY_JS = System.getenv('AYON_HARMONY_JS') + '/AyonHarmony.js';
    include(AYON_HARMONY_JS.replace(/\\/g, "/"));
}

if (typeof $ === 'undefined'){
    $ = this.__proto__['$'];
}
/**
 * @namespace
 * @classdesc Image Sequence loader JS code.
 */
var TemplateLoader = function() {};


/**
 * Load template as container.
 * @function
 * @param {array} args Array of arguments.
 * @return {string} Name of backdrop container.
 * @example
 * // arguments are in this order:
 * var args = [
 *     templatePath, // Path to tpl file
 *     overrideName // Override name of backdrop container
 * ];
 */
TemplateLoader.prototype.loadContainer = function(args) {
    var templatePath = args[0];
    var overrideName = args[1] || "";

    // Copy from template file
    MessageLog.trace("loadContainer:: ");
    var hasOverrideName = overrideName !== undefined && overrideName !== null && overrideName !== "";

    /**
     * Parse a backdrop name into its base name and numeric suffix count.
     * If the name ends with _N (N = positive integer), returns the base and N.
     * Otherwise returns the full name as base with count 1.
     * @param {string} name - The backdrop name to parse.
     * @return {{baseName: string, count: number}}
     */
    function parseBackdropName(name) {
        var lastIndex = name.lastIndexOf('_');
        if (lastIndex === -1) {
            return { baseName: name, count: 1 };
        }
        var base = name.substring(0, lastIndex);
        var suffix = name.substring(lastIndex + 1);
        var increment = parseInt(suffix, 10);
        var isNumericSuffix = !isNaN(increment) && String(increment) === suffix.trim() && increment >= 1;
        if (isNumericSuffix) {
            return { baseName: base, count: increment };
        }
        return { baseName: name, count: 1 };
    }

    // Get existing content bounds
    var existingBackdrops = Backdrop.backdrops("Top");
    var existingNodes = node.subNodes("Top");
    var existingBounds = null;

    if (existingBackdrops.length > 0 || existingNodes.length > 0) {
        existingBounds = {
            top: Infinity,
            right: -Infinity,
            bottom: -Infinity
        };

        existingBackdrops.forEach(function(b) {
            var right = b.position.x + b.position.w;
            var top = b.position.y;
            var bottom = b.position.y + b.position.h;
            if (right > existingBounds.right) existingBounds.right = right;
            if (top < existingBounds.top) existingBounds.top = top;
            if (bottom > existingBounds.bottom) existingBounds.bottom = bottom;
        });

        existingNodes.forEach(function(nodePath) {
            var nodeRight = node.coordX(nodePath) + node.width(nodePath);
            var nodeTop = node.coordY(nodePath);
            var nodeBottom = node.coordY(nodePath) + node.height(nodePath);
            if (nodeRight > existingBounds.right) existingBounds.right = nodeRight;
            if (nodeTop < existingBounds.top) existingBounds.top = nodeTop;
            if (nodeBottom > existingBounds.bottom) existingBounds.bottom = nodeBottom;
        });

        if (existingBounds.right === -Infinity) existingBounds = null;
    }

    var _copyOptions = copyPaste.getCurrentCreateOptions();
    var _tpl = copyPaste.copyFromTemplate(templatePath, 0, 999, _copyOptions);

    // Paste into scene
    var pasteOptions = copyPaste.getCurrentPasteOptions();
    pasteOptions.extendScene = true; // TODO does this work?
    copyPaste.pasteNewNodes(_tpl, "Top", pasteOptions);

    // Get pasted content bounds and minimum offset
    var pastedBackdrops = selection.selectedBackdrops();
    var pastedNodes = selection.selectedNodes();
    var offsetX = 0;
    var offsetY = 0;

    if (existingBounds && (pastedBackdrops.length > 0 || pastedNodes.length > 0)) {
        // Bounding box of pasted backdrops and nodes
        var pastedLeft = Infinity;
        var pastedTop = Infinity;
        var pastedBottom = -Infinity;

        pastedBackdrops.forEach(function(b) {
            if (b.position.x < pastedLeft) pastedLeft = b.position.x;
            if (b.position.y < pastedTop) pastedTop = b.position.y;
            var bBottom = b.position.y + b.position.h;
            if (bBottom > pastedBottom) pastedBottom = bBottom;
        });

        pastedNodes.forEach(function(nodePath) {
            var nx = node.coordX(nodePath);
            if (nx < pastedLeft) pastedLeft = nx;
            var ny = node.coordY(nodePath);
            if (ny < pastedTop) pastedTop = ny;
            var nBottom = ny + node.height(nodePath);
            if (nBottom > pastedBottom) pastedBottom = nBottom;
        });

        // Offsets to clear existing: right (X) or below (Y), with 100px gap
        var potentialOffsetX = 0;
        var potentialOffsetY = 0;
        if (pastedLeft !== Infinity) {
            potentialOffsetX = Math.max(0, existingBounds.right - pastedLeft + 100);
        }
        if (pastedTop !== Infinity && pastedBottom > -Infinity &&
            pastedTop < existingBounds.bottom && pastedBottom > existingBounds.top) {
            potentialOffsetY = existingBounds.bottom - pastedTop + 100;
        }

        // Use only the smaller offset so pasted content stays as close as possible
        if (potentialOffsetX > 0 && potentialOffsetY > 0) {
            offsetX = potentialOffsetX <= potentialOffsetY ? potentialOffsetX : 0;
            offsetY = potentialOffsetY < potentialOffsetX ? potentialOffsetY : 0;
        } else if (potentialOffsetX > 0) {
            offsetX = potentialOffsetX;
        } else if (potentialOffsetY > 0) {
            offsetY = potentialOffsetY;
        }
    }

    if (offsetX !== 0 || offsetY !== 0) {
        // Apply offset to pasted content
        // Resolve pasted backdrop indices now (before move); order may change after node move
        var allBackdropsBeforeMove = Backdrop.backdrops("Top");
        var pastedBackdropIndices = [];
        pastedBackdrops.forEach(function(pastedBackdrop) {
            for (var i = 0; i < allBackdropsBeforeMove.length; i++) {
                var b = allBackdropsBeforeMove[i];
                if (b.title.text === pastedBackdrop.title.text &&
                    b.position.x === pastedBackdrop.position.x &&
                    b.position.y === pastedBackdrop.position.y) {
                    pastedBackdropIndices.push(i);
                    break;
                }
            }
        });

        // Move pasted nodes by offset
        pastedNodes.forEach(function(nodePath) {
            var newX = node.coordX(nodePath) + offsetX;
            var newY = node.coordY(nodePath) + offsetY;
            node.setCoord(nodePath, newX, newY);
        });

        // Move pasted backdrops by offset
        var allBackdrops = Backdrop.backdrops("Top");
        pastedBackdropIndices.forEach(function(idx) {
            allBackdrops[idx].position.x += offsetX;
            allBackdrops[idx].position.y += offsetY;
        });
        Backdrop.setBackdrops("Top", allBackdrops);
    }

     // Find main backdrop name
    // The main backdrop is the one with the smallest x + y value (top left corner)
    var selectedBackdrops = selection.selectedBackdrops();
    var mainBackdropName = selectedBackdrops[0].title.text;
    var mainAnchorValue = selectedBackdrops[0].position.x + selectedBackdrops[0].position.y;
    selectedBackdrops.slice(1).forEach(function(backdrop) {
        var anchor = backdrop.position.x + backdrop.position.y;
        if (mainAnchorValue > anchor) {
            mainBackdropName = backdrop.title.text;
            mainAnchorValue = anchor;
        }
    });

    var allBackdrops = Backdrop.backdrops("Top");
    var backdropCounts = {};
    for (var i = 0; i < allBackdrops.length; i++) {
        var parsed = parseBackdropName(allBackdrops[i].title.text);
        var baseName = parsed.baseName;
        var count = parsed.count;

        if (backdropCounts[baseName]) {
            backdropCounts[baseName]++;
        } else {
            backdropCounts[baseName] = count;
        }
    }

    var mainBackdropParsed = parseBackdropName(mainBackdropName);
    var count = backdropCounts[mainBackdropParsed.baseName] !== undefined ? backdropCounts[mainBackdropParsed.baseName] : 1;

    if (!hasOverrideName && count > 1){
        // count -1 to match imported nodes which start from _1
        mainBackdropName = mainBackdropName + "_" + (count - 1);

        // new backdrop always at 0
        allBackdrops[0].title.text = mainBackdropName;
        Backdrop.setBackdrops("Top", allBackdrops);
    }

    if (hasOverrideName) {
        mainBackdropName = overrideName;
        allBackdrops[0].title.text = mainBackdropName;
        Backdrop.setBackdrops("Top", allBackdrops);
    }

    return mainBackdropName;
};

// add self to AYON Loaders
AyonHarmony.Loaders.TemplateLoader = new TemplateLoader();
