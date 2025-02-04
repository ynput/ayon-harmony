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
 * @param {array} args Arguments, see example.
 * @return {string} Name of backdrop container.
 *
 * @example
 * // arguments are in following order:
 * var args = [
 *  templatePath, // Path to tpl file.
 * ];
 */
TemplateLoader.prototype.loadContainer = function(args) {
    var templatePath = args[0];

    // Copy from template file
    var _copyOptions = copyPaste.getCurrentCreateOptions();
    var _tpl = copyPaste.copyFromTemplate(templatePath, 0, 999, _copyOptions);

    // Paste into scene
    var pasteOptions = copyPaste.getCurrentPasteOptions();
    pasteOptions.extendScene = true; // TODO does this work?
    copyPaste.pasteNewNodes(_tpl, "Top", pasteOptions);

    // Find backdrop name
    return selection.selectedBackdrops()[0]["title"]["text"];
};


/**
 * Replace existing node container.
 * @function
 * @param  {string}  dstNodePath Harmony path to destination Node.
 * @param  {string}  srcNodePath Harmony path to source Node.
 * @param  {string}  renameSrc   ...
 * @param  {boolean} cloneSrc    ...
 * @return {boolean}             Success
 * @todo   This is work in progress.
 */
TemplateLoader.prototype.replaceNode = function(
    dstNodePath, srcNodePath, renameSrc, cloneSrc) {
    var doc = $.scn;
    var srcNode = doc.$node(srcNodePath);
    var dstNode = doc.$node(dstNodePath);
    // var dstNodeName = dstNode.name;
    var replacementNode = srcNode;
    // var dstGroup = dstNode.group;
    $.beginUndo();
    if (cloneSrc) {
        replacementNode = doc.$node(
            $.nodeTools.copy_paste_node(
                srcNodePath, dstNode.name + '_CLONE', dstNode.group.path));
    } else {
        if (replacementNode.group.path != srcNode.group.path) {
            replacementNode.moveToGroup(dstNode);
        }
    }
    var inLinks = dstNode.getInLinks();
    var link, inNode, inPort, outPort, outNode, success;
    for (var l in inLinks) {
        if (Object.prototype.hasOwnProperty.call(inLinks, l)) {
            link = inLinks[l];
            inPort = Number(link.inPort);
            outPort = Number(link.outPort);
            outNode = link.outNode;
            success = replacementNode.linkInNode(outNode, inPort, outPort);
            if (success) {
                $.log('Successfully connected ' + outNode + ' : ' +
            outPort + ' -> ' + replacementNode + ' : ' + inPort);
            } else {
                $.alert('Failed to connect ' + outNode + ' : ' +
            outPort + ' -> ' + replacementNode + ' : ' + inPort);
            }
        }
    }

    var outLinks = dstNode.getOutLinks();
    for (l in outLinks) {
        if (Object.prototype.hasOwnProperty.call(outLinks, l)) {
            link = outLinks[l];
            inPort = Number(link.inPort);
            outPort = Number(link.outPort);
            inNode = link.inNode;
            // first we must disconnect the port from the node being
            // replaced to this links inNode port
            inNode.unlinkInPort(inPort);
            success = replacementNode.linkOutNode(inNode, outPort, inPort);
            if (success) {
                $.log('Successfully connected ' + inNode + ' : ' +
              inPort + ' <- ' + replacementNode + ' : ' + outPort);
            } else {
                if (inNode.type == 'MultiLayerWrite') {
                    $.log('Attempting standard api to connect the nodes...');
                    success = node.link(
                        replacementNode, outPort, inNode,
                        inPort, node.numberOfInputPorts(inNode) + 1);
                    if (success) {
                        $.log('Successfully connected ' + inNode + ' : ' +
                inPort + ' <- ' + replacementNode + ' : ' + outPort);
                    }
                }
            }
            if (!success) {
                $.alert('Failed to connect ' + inNode + ' : ' +
            inPort + ' <- ' + replacementNode + ' : ' + outPort);
                return false;
            }
        }
    }
};


TemplateLoader.prototype.askForColumnsUpdate = function() {
    // Ask user if they want to also update columns and
    // linked attributes here
    return ($.confirm(
        'Would you like to update in place and reconnect all \n' +
      'ins/outs, attributes, and columns?',
        'Update & Replace?\n' +
      'If you choose No, the version will only be loaded.',
        'Yes',
        'No'));
};

// add self to AYON Loaders
AyonHarmony.Loaders.TemplateLoader = new TemplateLoader();
