// ***************************************************************************
// *                        AYON Harmony Host                                *
// ***************************************************************************


/**
 * @namespace
 * @classdesc AyonHarmonyAPI encapsulate all AYON related functions.
 */
var AyonHarmonyAPI = {};


/**
 * Get scene metadata from Harmony.
 * @function
 * @return {object} Scene metadata.
 */
AyonHarmonyAPI.getSceneData = function() {
    var metadata = scene.metadata('ayon');
    if (!metadata) {
        // Backwards compatibility
        metadata = scene.metadata('avalon');
    }

    if (metadata){
        return JSON.parse(metadata.value);
    }else {
        return {};
    }
};


/**
 * Set scene metadata to Harmony.
 * @function
 * @param {object} metadata Object containing metadata.
 */
AyonHarmonyAPI.setSceneData = function(metadata) {
    scene.setMetadata({
        'name'       : 'ayon',
        'type'       : 'string',
        'creator'    : 'AYON',
        'version'    : '1.0',
        'value'      : JSON.stringify(metadata)
    });
};


/**
 * Get selected nodes in Harmony.
 * @function
 * @return {array} Selected nodes paths.
 */
AyonHarmonyAPI.getSelectedNodes = function () {
    var selectionLength = selection.numberOfNodesSelected();
    var selectedNodes = [];
    for (var i = 0 ; i < selectionLength; i++) {
        selectedNodes.push(selection.selectedNode(i));
    }
    return selectedNodes;
};


/**
 * Set selection of nodes.
 * @function
 * @param {array} nodes Arrya containing node paths to add to selection.
 */
AyonHarmonyAPI.selectNodes = function(nodes) {
    selection.clearSelection();
    for (var i = 0 ; i < nodes.length; i++) {
        selection.addNodeToSelection(nodes[i]);
    }
};


/**
 * Is node enabled?
 * @function
 * @param {string} node Node path.
 * @return {boolean} state
 */
AyonHarmonyAPI.isEnabled = function(node) {
    return node.getEnable(node);
};


/**
 * Are nodes enabled?
 * @function
 * @param {array} nodes Array of node paths.
 * @return {array} array of boolean states.
 */
AyonHarmonyAPI.areEnabled = function(nodes) {
    var states = [];
    for (var i = 0 ; i < nodes.length; i++) {
        states.push(node.getEnable(nodes[i]));
    }
    return states;
};


/**
 * Set state on nodes.
 * @function
 * @param {array} args Array of nodes array and states array.
 */
AyonHarmonyAPI.setState = function(args) {
    var nodes = args[0];
    var states = args[1];
    // length of both arrays must be equal.
    if (nodes.length !== states.length) {
        return false;
    }
    for (var i = 0 ; i < nodes.length; i++) {
        node.setEnable(nodes[i], states[i]);
    }
    return true;
};


/**
 * Disable specified nodes.
 * @function
 * @param {array} nodes Array of nodes.
 */
AyonHarmonyAPI.disableNodes = function(nodes) {
    for (var i = 0 ; i < nodes.length; i++)
    {
        node.setEnable(nodes[i], false);
    }
};


/**
 * Save scene in Harmony.
 * @function
 * @return {string} Scene path.
 */
AyonHarmonyAPI.saveScene = function() {
    var app = QCoreApplication.instance();
    app.ayon_on_file_changed = false;
    scene.saveAll();
    return (
        scene.currentProjectPath() + '/' +
          scene.currentVersionName() + '.xstage'
    );
};


/**
 * Enable Harmony file-watcher.
 * @function
 */
AyonHarmonyAPI.enableFileWather = function() {
    var app = QCoreApplication.instance();
    app.ayon_on_file_changed = true;
};


/**
 * Add path to file-watcher.
 * @function
 * @param {string} path Path to watch.
 */
AyonHarmonyAPI.addPathToWatcher = function(path) {
    var app = QCoreApplication.instance();
    app.watcher.addPath(path);
};


/**
 * Setup node for Creator.
 * @function
 * @param {string} node Node path.
 */
AyonHarmonyAPI.setupNodeForCreator = function(node) {
    node.setTextAttr(node, 'COMPOSITE_MODE', 1, 'Pass Through');
};


/**
 * Get node names for specified node type.
 * @function
 * @param {string} nodeType Node type.
 * @return {array} Node names.
 */
AyonHarmonyAPI.getNodesNamesByType = function(nodeType) {
    var nodes = node.getNodes([nodeType]);
    var nodeNames = [];
    for (var i = 0; i < nodes.length; ++i) {
        nodeNames.push(node.getName(nodes[i]));
    }
    return nodeNames;
};


/**
 * Create container node in Harmony.
 * @function
 * @param {array} args Arguments, see example.
 * @return {string} Resulting node.
 *
 * @example
 * // arguments are in following order:
 * var args = [
 *  nodeName,
 *  nodeType,
 *  selection
 * ];
 */
AyonHarmonyAPI.createContainer = function(args) {
    var resultNode = node.add('Top', args[0], args[1], 0, 0, 0);
    if (args.length > 2) {
        node.link(args[2], 0, resultNode, 0, false, true);
        node.setCoord(resultNode,
            node.coordX(args[2]),
            node.coordY(args[2]) + 70);
    }
    return resultNode;
};


/**
 * Delete node.
 * @function
 * @param {string} node Node path.
 */
AyonHarmonyAPI.deleteNode = function(_node) {
    node.deleteNode(_node, true, true);
};