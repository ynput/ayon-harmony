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
 * @classdesc Image loader JS code.
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
    var parentBackdropName = args[2] || null;

    var psdNodes = PsdLoader.prototype.importPsd(psdPath);
    var sceneRoot = $.scn.root;
    psdNodes = psdNodes.filter(function(n) {
        return n.group == "Top";
    });
    var backdrop = sceneRoot.addBackdropToNodes(psdNodes, name);

    var newBackdrops = [backdrop.backdropObject];
    var newNodePaths = psdNodes.map(function(n) { return n.path; });
    var parentArea = null;
    if (parentBackdropName) {
        var newBounds = AyonHarmony.getContentBounds(newBackdrops, newNodePaths);
        var parentBackdrop = AyonHarmony.ensureParentBackdrop(
            parentBackdropName, newBounds
        );
        parentArea = {
            x: parentBackdrop.position.x,
            y: parentBackdrop.position.y,
            w: parentBackdrop.position.w,
            h: parentBackdrop.position.h
        };
    }

    var overlapResult = AyonHarmony.preventOverlap(
        newBackdrops, newNodePaths, parentArea, parentBackdropName
    );
    if (parentBackdropName && overlapResult.area && parentArea &&
        (overlapResult.area.x !== parentArea.x ||
        overlapResult.area.y !== parentArea.y ||
        overlapResult.area.w !== parentArea.w ||
        overlapResult.area.h !== parentArea.h)) {
        AyonHarmony.applyAreaToBackdrop(parentBackdropName, overlapResult.area);
    }

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
    if (sceneComp) {
        psdComp.linkOutNode(sceneComp);
        sceneRoot.orderNodeView();
        psdComp.unlinkOutNode(sceneComp);
    } else {
        sceneRoot.orderNodeView();
    }

    return psdNodes;
};

// add self to AYON Loaders
AyonHarmony.Loaders.PsdLoader = new PsdLoader();
