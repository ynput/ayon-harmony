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
 * @classdesc Image Sequence loader JS code.
 */
var CollectPalettes = function() {};

CollectPalettes.prototype.getPalettes = function() {
    var palette_list = PaletteObjectManager.getScenePaletteList();

    var palettes = {};
    for(var i=0; i < palette_list.numPalettes; ++i) {
        var palette = palette_list.getPaletteByIndex(i);
        palettes[palette.getName()] = palette.id;
    }

    return palettes;
};

// add self to Pype Loaders
AyonHarmony.Publish.CollectPalettes = new CollectPalettes();
