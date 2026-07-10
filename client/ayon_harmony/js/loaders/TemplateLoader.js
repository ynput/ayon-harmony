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
 *     overrideName, // Override name of backdrop container
 *     parentBackdropName // Optional parent backdrop name
 * ];
 */
TemplateLoader.prototype.loadContainer = function(args) {
    var templatePath = args[0];
    var overrideName = args[1] || "";
    var parentBackdropName = args[2] || null;
    var existingNames = args[3] || [];

    // Copy from template file
    MessageLog.trace("loadContainer:: ");

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
            return { baseName: name, count: 0 };
        }
        var base = name.substring(0, lastIndex);
        var suffix = name.substring(lastIndex + 1);
        var increment = parseInt(suffix, 10);
        var isNumericSuffix = !isNaN(increment) && String(increment) === suffix.trim() && increment >= 1;
        if (isNumericSuffix) {
            return { baseName: base, count: increment };
        }
        return { baseName: name, count: 0 };
    }

    var _copyOptions = copyPaste.getCurrentCreateOptions();
    var _tpl = copyPaste.copyFromTemplate(templatePath, 0, 999, _copyOptions);

    // Paste into scene
    var pasteOptions = copyPaste.getCurrentPasteOptions();
    pasteOptions.extendScene = true;
    $.beginUndo('AYON: Load Template');
    try {
        copyPaste.pasteNewNodes(_tpl, "Top", pasteOptions);

        var pastedBackdrops = selection.selectedBackdrops();
        var _allSelected = selection.selectedNodes();
        var topPastedNodes = _allSelected.filter(
            function(nodePath) { return node.parentNode(nodePath) === "Top"; }
        );
        var mainBackdropBeforeMove = AyonHarmony.findMainBackdrop(pastedBackdrops);
        var parentArea = null;
        if (parentBackdropName) {
            var pastedBounds = AyonHarmony.getContentBounds(
                pastedBackdrops, topPastedNodes
            );
            var parentBackdrop = AyonHarmony.ensureParentBackdrop(
                parentBackdropName, pastedBounds
            );
            parentArea = {
                x: parentBackdrop.position.x,
                y: parentBackdrop.position.y,
                w: parentBackdrop.position.w,
                h: parentBackdrop.position.h
            };
        }

        var overlapResult = AyonHarmony.preventOverlap(
            pastedBackdrops, topPastedNodes, parentArea, parentBackdropName
        );
        var allBackdrops = overlapResult.allBackdrops;

        if (parentBackdropName && overlapResult.area && parentArea &&
            (overlapResult.area.x !== parentArea.x ||
            overlapResult.area.y !== parentArea.y ||
            overlapResult.area.w !== parentArea.w ||
            overlapResult.area.h !== parentArea.h)) {
            allBackdrops = AyonHarmony.applyAreaToBackdrop(
                parentBackdropName, overlapResult.area
            );
        }

        var mainBackdrop = null;
        if (mainBackdropBeforeMove) {
            for (var backdropIndex = 0; backdropIndex < allBackdrops.length; backdropIndex++) {
                var backdrop = allBackdrops[backdropIndex];
                if (backdrop.title.text === mainBackdropBeforeMove.title.text &&
                    backdrop.position.w === mainBackdropBeforeMove.position.w &&
                    backdrop.position.h === mainBackdropBeforeMove.position.h) {
                    mainBackdrop = backdrop;
                    break;
                }
            }
        }
        if (!mainBackdrop && allBackdrops.length > 0) {
            mainBackdrop = allBackdrops[0];
        }
        if (!mainBackdrop) {
            $.cancelUndo();
            return "";
        }

        // Override name if provided
        if (overrideName) {
            mainBackdrop.title.text = overrideName;
        }

        var mainBackdropBaseName = parseBackdropName(mainBackdrop.title.text).baseName;

        // Collect used suffix slots for this baseName, based on the
        // Python-provided list of already-registered container names
        var usedNumbers = [];
        for (var n = 0; n < existingNames.length; n++) {
            var parsed = parseBackdropName(existingNames[n]);
            if (parsed.baseName !== mainBackdropBaseName) {
                continue;
            }
            usedNumbers.push(parsed.count);
        }

        var mainBackdropName;
        if (usedNumbers.indexOf(0) === -1) {
            mainBackdropName = mainBackdropBaseName;
        } else {
            var nextSuffix = 1;
            while (usedNumbers.indexOf(nextSuffix) !== -1) {
                nextSuffix++;
            }
            mainBackdropName = mainBackdropBaseName + "_" + nextSuffix;
        }

        // Set name of main backdrop (always at index 0)
        mainBackdrop.title.text = mainBackdropName;

        // Update backdrops in scene
        Backdrop.setBackdrops("Top", allBackdrops);
    } catch (_err) {
        $.cancelUndo();
        throw _err;
    }
    $.endUndo();

    return mainBackdropName;
};

// add self to AYON Loaders
AyonHarmony.Loaders.TemplateLoader = new TemplateLoader();
