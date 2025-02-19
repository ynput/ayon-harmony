/* global AyonHarmony:writable, include */
// ***************************************************************************
// *                        TemplateLoader                                   *
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
 * @classdesc Image Sequence loader JS code.
 */
var TemplateLoader = function() {};


/**
 * Load template as container.
 * @function
 * @param {string} templatePath Path to tpl file.
 * @return {string} Name of backdrop container.
 */
TemplateLoader.prototype.loadContainer = function(templatePath) {
    // Copy from template file
    var _copyOptions = copyPaste.getCurrentCreateOptions();
    var _tpl = copyPaste.copyFromTemplate(templatePath, 0, 999, _copyOptions);

    // Paste into scene
    var pasteOptions = copyPaste.getCurrentPasteOptions();
    pasteOptions.extendScene = true; // TODO does this work?
    copyPaste.pasteNewNodes(_tpl, "Top", pasteOptions);

    // Find main backdrop name
    // The main backdrop is the one with the smallest x + y value (top left corner)
    var selectedBackdrops = selection.selectedBackdrops();
    var mainBackdropName = selectedBackdrops[0].title.text;
    var mainAnchorValue = selectedBackdrops[0].position.x + selectedBackdrops[0].position.y;
    selectedBackdrops.slice(1).forEach(function(backdrop) {
        var anchor = backdrop.position.x + backdrop.position.y;
        if (mainAnchorValue > anchor) {
            mainBackdropName = backdrop.title.text;
            mainAnchorValue = anchor;
        }
    });
    return mainBackdropName;
};

// add self to AYON Loaders
AyonHarmony.Loaders.TemplateLoader = new TemplateLoader();
