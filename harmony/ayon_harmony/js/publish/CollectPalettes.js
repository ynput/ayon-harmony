/* global PypeHarmony:writable, include */
// ***************************************************************************
// *                        CollectPalettes                                  *
// ***************************************************************************


// check if PypeHarmony is defined and if not, load it.
if (typeof PypeHarmony === 'undefined') {
    var AYON_HARMONY_JS = System.getenv('AYON_HARMONY_JS') + '/PypeHarmony.js';
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
PypeHarmony.Publish.CollectPalettes = new CollectPalettes();
