/* global AyonHarmony:writable, include */
// ***************************************************************************
// *                        CollectPalettes                                  *
// ***************************************************************************


// check if AyonHarmony is defined and if not, load it.
if (typeof AyonHarmony === 'undefined') {
    var AYON_HARMONY_JS = System.getenv('AYON_HARMONY_JS') + '/AyonHarmony.js';
    include(AYON_HARMONY_JS.replace(/\\/g, "/"));
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

    var palettes = {};
    for(var i=0; i < palette_list.numPalettes; ++i) {
        var palette = palette_list.getPaletteByIndex(i);
        
        // if local_only is true, skip external palettes
        if (local_only && palette.location == PaletteObjectManager.Constants.Location.EXTERNAL) {
            continue;
        }
        
        palettes[palette.getName()] = palette.id;
    }

    return palettes;
};

// add self to AYON Loaders
AyonHarmony.Publish.CollectPalettes = new CollectPalettes();
