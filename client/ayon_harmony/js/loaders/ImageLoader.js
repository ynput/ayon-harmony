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

// Transparency modes
AyonHarmony.TransparencyModes = {
    PNG: 0, // Premultiplied with Black
    TGA: 0, // Premultiplied with Black
    SGI: 0, // Premultiplied with Black
    LayeredPSD: 1, // Straight
    FlatPSD: 2 // Premultiplied with White
};

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

/**
 * @namespace
 * @classdesc Image loader JS code.
 */
var ImageLoader = function() {};


ImageLoader.getCurrentGroup = function () {
    var doc = $.scn;
    var nodeView = '';
    for (var i = 0; i < 200; i++) {
        nodeView = 'View' + (i);
        if (view.type(nodeView) == 'Node View') {
            break;
        }
    }

    if (!nodeView) {
        $.alert('You must have a Node View open!',
            'No Node View is currently open!\n' +
            'Open a Node View and Try Again.',
            'OK!');
        return;
    }

    var currentGroup;
    if (!nodeView) {
        currentGroup = doc.root;
    } else {
        currentGroup = doc.$node(view.group(nodeView));
    }

    return currentGroup.path;
};


/**
 * Get unique column name.
 * @function
 * @param  {string}  columnPrefix Column name.
 * @return {string}  Unique column name.
 */
ImageLoader.getUniqueColumnName = function(columnPrefix) {
    var suffix = 0;
    // finds if unique name for a column
    var columnName = columnPrefix;
    while (suffix < 2000) {
        if (!column.type(columnName)) {
            break;
        }

        suffix = suffix + 1;
        columnName = columnPrefix + '_' + suffix;
    }
    return columnName;
};


/**
 * Import single image file into Harmony.
 * @function
 * @param  {object}  args  Arguments for import, see Example.
 * @return {string}  Read node name
 *
 * @example
 * // Arguments are in following order:
 * var args = [
 *    filePath, // Single image file path.
 *    folderName, // Folder name.
 *    productName, // Product name.
 *    startFrame, // Frame to place the image, default to current frame.
 * ];
 */
ImageLoader.prototype.importImageFile = function(args) {
    MessageLog.trace("ImageLoader:: " + typeof AyonHarmony);
    MessageLog.trace("ImageLoader $:: " + typeof $);
    MessageLog.trace("ImageLoader OH:: " + typeof AyonHarmony.OpenHarmony);
    

    var doc = $.scn;
    var filePath = args[0];
    var folderName = args[1];
    var productName = args[2];
    var startFrame = args[3] || frame.current();
    var vectorFormat = null;
    var extension = null;
    var pos = filePath.lastIndexOf('.');
    if (pos < 0) {
        return null;
    }

    // Get the current group
    var currentGroup = doc.$node(ImageLoader.getCurrentGroup());

    // Get a unique iterative name for the container read node
    var num = 0;
    var name = '';
    do {
        name = folderName + '_' + productName;
    } while (currentGroup.getNodeByName(name) != null);

    extension = filePath.substr(pos+1).toLowerCase();

    if (extension == 'tvg') {
        vectorFormat = 'TVG';
        extension ='SCAN'; // element.add() will use this.
    }

    var elemId = element.add(
        name,
        'BW',
        scene.numberOfUnitsZ(),
        extension.toUpperCase(),
        vectorFormat
    );

    if (elemId == -1) {
        // hum, unknown file type most likely -- let's skip it.
        return null; // no read to add.
    }

    var uniqueColumnName = ImageLoader.getUniqueColumnName(name);
    column.add(uniqueColumnName, 'DRAWING');
    column.setElementIdOfDrawing(uniqueColumnName, elemId);
    var readNode = node.add(currentGroup, name, 'READ', 0, 0, 0);
    var transparencyAttr = node.getAttr(
        readNode, frame.current(), 'READ_TRANSPARENCY'
    );
    var opacityAttr = node.getAttr(readNode, frame.current(), 'OPACITY');
    transparencyAttr.setValue(true);
    opacityAttr.setValue(true);
    var alignmentAttr = node.getAttr(readNode, frame.current(), 'ALIGNMENT_RULE');
    alignmentAttr.setValue('ASIS');

    // Set transparency mode
    var transparencyModeAttr = node.getAttr(
        readNode, frame.current(), 'applyMatteToColor'
    );
    if (extension === 'png') {
        transparencyModeAttr.setValue(AyonHarmony.TransparencyModes.PNG);
    }
    if (extension === 'tga') {
        transparencyModeAttr.setValue(AyonHarmony.TransparencyModes.TGA);
    }
    if (extension === 'sgi') {
        transparencyModeAttr.setValue(AyonHarmony.TransparencyModes.SGI);
    }
    if (extension === 'psd') {
        transparencyModeAttr.setValue(AyonHarmony.TransparencyModes.FlatPSD);
    }
    if (extension === 'jpg' || extension === 'jpeg') {
        transparencyModeAttr.setValue(AyonHarmony.TransparencyModes.LayeredPSD);
    }

    node.linkAttr(readNode, 'DRAWING.ELEMENT', uniqueColumnName);
    
    // For single image, create drawing at the specified frame
    Drawing.create(elemId, startFrame, true); // 'true' indicate that the file exists.
    // Get the actual path, in tmp folder.
    var drawingFilePath = Drawing.filename(elemId, startFrame.toString());
    AyonHarmony.copyFile(filePath, drawingFilePath);
    // Set the drawing at the specified frame
    column.setEntry(uniqueColumnName, 1, startFrame, startFrame.toString());

    return readNode;
};


/**
 * Replace single image file in Harmony.
 * @function
 * @param  {object}  args  Arguments for replace, see Example.
 * @return {string}  Read node name
 *
 * @example
 * // Arguments are in following order:
 * var args = [
 *    node, // Node name
 *    filePath, // Single image file path
 *    folderName, // Folder name
 *    productName, // Product name
 * ];
 */
ImageLoader.prototype.replaceImageFile = function(args) {

    var imageNode = args[0];
    var filePath = args[1];
    var folderName = args[2];
    var productName = args[3];
    var col = node.linkedColumn(imageNode, 'DRAWING.ELEMENT');

    // Keep links to the node TODO use OpenHarmony?
    var links = AyonHarmony.getNodesLinks([[imageNode]]);

    // Keep exposure
    oNode = $.scn.getNodeByPath(imageNode);
    drawing = oNode.getAttributeByName("DRAWING.ELEMENT");
    var keyframes = drawing.getKeyframes();
    var exposure = [];
    for( var i=0; i < keyframes.length; i++ ){
        exposure.push({frame: keyframes[i].frameNumber, value: keyframes[i].value});
    }

    // Replace image node TODO make actual API
    // Delete old image node
    AyonHarmony.deleteNode(imageNode);
    var newImageNode = AyonHarmony.Loaders.ImageLoader.importImageFile([filePath, folderName, productName, exposure[0].frame]);

    // Update node name in links
    links.forEach(function(link) {
        if (link.srcNode == imageNode) {
            link.srcNode = newImageNode;
        }
        if (link.dstNode == imageNode) {
            link.dstNode = newImageNode;
        }
    });

    // Restore exposure
    oNode = $.scn.getNodeByPath(newImageNode);
    drawing = oNode.getAttributeByName("DRAWING.ELEMENT");
    for( var i=0; i < exposure.length; i++ ){
        drawing.setValue(exposure[i].value, exposure[i].frame);
    }

    // Restore links
    AyonHarmony.setNodesLinks(links);

    return newImageNode;
};

// add self to AYON Loaders
AyonHarmony.Loaders.PsdLoader = new PsdLoader();
AyonHarmony.Loaders.ImageLoader = new ImageLoader();
