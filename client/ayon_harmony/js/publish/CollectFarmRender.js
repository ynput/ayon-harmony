/* global AyonHarmony:writable, include */
// ***************************************************************************
// *                        CollectFarmRender                                *
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
var CollectFarmRender = function() {};


/**
 * Get information important for render output.
 * @function
 * @param node {String} node name.
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
CollectFarmRender.prototype.getRenderNodeSettings = function(n) {
    // this will return
    var output = [
        node.getTextAttr(
            n, frame.current(), 'DRAWING_NAME'),
        node.getTextAttr(
            n, frame.current(), 'DRAWING_TYPE'),
        node.getTextAttr(
            n, frame.current(), 'LEADING_ZEROS'),
        node.getTextAttr(n, frame.current(), 'START'),
        node.getEnable(n)
    ];

    return output;
};

// add self to AYON Loaders
AyonHarmony.Publish.CollectFarmRender = new CollectFarmRender();
