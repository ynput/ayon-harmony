/* global AyonHarmony:writable, include */
// ***************************************************************************
// *                           ExtractPalette                                *
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
 * @namespace
 * @classdesc Code for extracting palettes.
 */
var ExtractPalette = function() {};


/**
 * Get palette from Harmony.
 * @function
 * @param   {string} paletteId ID of palette to get.
 * @return  {array}  [paletteName, palettePath]
 */
ExtractPalette.prototype.getPalette = function(paletteId) {
    writeJsLog("@@@@@@@ extractpalette JS START");
    var palette_list = PaletteObjectManager.getScenePaletteList();
    var palette = palette_list.getPaletteById(paletteId);
    var palette_name = palette.getName();
    writeJsLog("        palette.getPath() + '/' + palette.getName() + '.plt'" + palette.getPath() + '/' + palette.getName() + '.plt');
    return [
        palette_name,
        (palette.getPath() + '/' + palette.getName() + '.plt')
    ];  
};

// add self to AYON Loaders
AyonHarmony.Publish.ExtractPalette = new ExtractPalette();
