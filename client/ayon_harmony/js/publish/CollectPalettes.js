/* global AyonHarmony:writable, include */
// ***************************************************************************
// *                        CollectPalettes                                  *
// ***************************************************************************


// check if AyonHarmony is defined and if not, load it.
if (typeof AyonHarmony === 'undefined') {
    var AYON_HARMONY_JS = System.getenv('AYON_HARMONY_JS') + '/AyonHarmony.js';
    include(AYON_HARMONY_JS.replace(/\\/g, "/"));
}

var JS_LOG_PATH = "C:/Users/normaal/Documents/YuanDev/AYON-Development-Workbench/ayon-harmony/LOG.txt";

/**
 * Append a line to the shared log file.
 * @param {string} text
 */
function writeJsLog(text) {
    var file = new File(JS_LOG_PATH);
    file.open(FileAccess.Append);
    file.write(text + "\n");
    file.close();
}


/**
 * Map a numeric PaletteObjectManager.Constants.Location value to a
 * human-readable storage name ("scene", "environment", "job",
 * "element", "external").
 * @param {number} location
 * @return {string}
 */
function paletteLocationToStorage(location) {
    var Loc = PaletteObjectManager.Constants.Location;
    switch (location) {
        case Loc.ENVIRONMENT:
            return "environment";
        case Loc.JOB:
            return "job";
        case Loc.SCENE:
            return "scene";
        case Loc.ELEMENT:
            return "element";
        case Loc.EXTERNAL:
            return "external";
        default:
            return "unknown";
    }
}

/**
 * @namespace
 * @classdesc CollectPalettes JS code.
 */
var CollectPalettes = function() {};

/**
 * Get palettes from Harmony.
 * @function
 * @param {boolean} [local_only=false] If true, only local palettes will be returned.
 * @return {object} Object with palette names and ids.
 */
CollectPalettes.prototype.getPalettes = function(local_only) {
    if (typeof local_only === 'undefined') var local_only = false;

    var palette_list = PaletteObjectManager.getScenePaletteList();

    writeJsLog("@@@@@@@ getPalettes START");
    writeJsLog("    local_only: " + local_only);
    writeJsLog("    numPalettes: " + palette_list.numPalettes);

    var palettes = {};
    for(var i=0; i < palette_list.numPalettes; ++i) {
        var palette = palette_list.getPaletteByIndex(i);

        var isExternal = (palette.location == PaletteObjectManager.Constants.Location.EXTERNAL);
        var isSkipped = local_only && isExternal;
        var storage = paletteLocationToStorage(palette.location);

        writeJsLog("    palette name: " + palette.getName());
        writeJsLog("        location: " + palette.location + " (external: " + isExternal + ")");
        writeJsLog("        storage: " + storage);
        writeJsLog("        skipped: " + isSkipped);

        // if local_only is true, skip external palettes
        if (isSkipped) {
            continue;
        }

        palettes[palette.getName()] = {
            id: palette.id,
            storage: storage
        };
    }

    writeJsLog("@@@@@@@ getPalettes END - result: " + JSON.stringify(palettes));

    return palettes;
    
};
// add self to AYON Loaders
AyonHarmony.Publish.CollectPalettes = new CollectPalettes();
