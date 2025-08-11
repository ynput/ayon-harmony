/* global AyonHarmony:writable, include */
// ***************************************************************************
// *                        ImageLoader                                   *
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
 * @classdesc PSD loader JS code.
 */
var PsdLoader = function() {};


/**
 * Load PSD file as container.
 * @function
 * @param {string} psdPath Path to psd file.
 * @param {string} name Name of the container.
 * @return {string} Name of backdrop container.
 */
PsdLoader.prototype.loadContainer = function(args) {
    var psdPath = args[0];
    var name = args[1];
    psdNodes = PsdLoader.prototype.importPsd(psdPath);
    var sceneRoot = $.scn.root;
    psdNodes = psdNodes.filter(function(node) {
        return node.group == "Top";
    });
    var backdrop = sceneRoot.addBackdropToNodes(psdNodes, name);
    return backdrop.title;
}


/**
 * Import PSD file.
 * @function
 * @param {string} psdPath Path to psd file.
 * @return {string} Nodes imported from PSD.
 */
PsdLoader.prototype.importPsd = function(psdPath) {
    var doc = $.scn;
    var sceneRoot = doc.root;
    var psdNodes = sceneRoot.importPSD(psdPath);

    // Gather nodes in view
    var psdComp = psdNodes[psdNodes.length - 1];
    var sceneComp = doc.$node("Top/Composite");
    psdComp.linkOutNode(sceneComp);
    sceneRoot.orderNodeView();
    psdComp.unlinkOutNode(sceneComp);

    return psdNodes;
};

// add self to AYON Loaders
AyonHarmony.Loaders.PsdLoader = new PsdLoader();
