/* global AyonHarmony:writable, include */
// ***************************************************************************
// *                        CollectCurrentFile                               *
// ***************************************************************************


// check if AyonHarmony is defined and if not, load it.
if (typeof AyonHarmony === 'undefined') {
    var AYON_HARMONY_JS = System.getenv('AYON_HARMONY_JS') + '/AyonHarmony.js';
    include(AYON_HARMONY_JS.replace(/\\/g, "/"));
}


/**
 * @namespace
 * @classdesc Collect Current file
 */
var CollectCurrentFile = function() {};

CollectCurrentFile.prototype.collect = function() {
    return (
        scene.currentProjectPath() + '/' +
            scene.currentVersionName() + '.xstage'
    );
};

// add self to AYON Loaders
AyonHarmony.Publish.CollectCurrentFile = new CollectCurrentFile();
