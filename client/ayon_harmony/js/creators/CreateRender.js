/* global AyonHarmony:writable, include */
// ***************************************************************************
// *                             CreateRender                                *
// ***************************************************************************


// check if AyonHarmony is defined and if not, load it.
if (typeof AyonHarmony === 'undefined') {
    var AYON_HARMONY_JS = System.getenv('AYON_HARMONY_JS') + '/AyonHarmony.js';
    include(AYON_HARMONY_JS.replace(/\\/g, "/"));
}


/**
 * @namespace
 * @classdesc Code creating render containers in Harmony.
 */
var CreateRender = function() {};


/**
 * Create render instance.
 * @function
 * @param {array} args Arguments for instance.
 */
CreateRender.prototype.create = function(args) {
    node.setTextAttr(args[0], 'DRAWING_TYPE', 1, 'PNG4');
    node.setTextAttr(args[0], 'DRAWING_NAME', 1, args[1]);
    node.setTextAttr(args[0], 'MOVIE_PATH', 1, args[1]);
};

// add self to Pype Loaders
AyonHarmony.Creators.CreateRender = new CreateRender();
