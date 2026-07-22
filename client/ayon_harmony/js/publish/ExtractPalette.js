/* global AyonHarmony:writable, include */
// ***************************************************************************
// *                           ExtractPalette                                *
// ***************************************************************************


// check if AyonHarmony is defined and if not, load it.
if (typeof AyonHarmony === 'undefined') {
    var AYON_HARMONY_JS = System.getenv('AYON_HARMONY_JS') + '/AyonHarmony.js';
    include(AYON_HARMONY_JS.replace(/\\/g, "/"));
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
    var palette_list = PaletteObjectManager.getScenePaletteList();
    var palette = palette_list.getPaletteById(paletteId);
    var palette_name = palette.getName();
    return [
        palette_name,
        (palette.getPath() + '/' + palette.getName() + '.plt')
    ];  
};

// add self to AYON Loaders
AyonHarmony.Publish.ExtractPalette = new ExtractPalette();
