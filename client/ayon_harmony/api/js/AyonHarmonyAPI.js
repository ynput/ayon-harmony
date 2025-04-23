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
 * @param {array} nodes Array containing node paths to add to selection.
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
AyonHarmonyAPI.isEnabled = function(nodeName) {
    var backdrop = AyonHarmony._getBackdropByName(nodeName);
    if (backdrop){
        var nodes = []
        nodes = Backdrop.nodes(backdrop);
        if (nodes){
            // check only first node, all should be same
            return node.getEnable(nodes[0]);
        }
    }else{
        return node.getEnable(nodeName);
    }
    return false;
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
        states.push(AyonHarmonyAPI.isEnabled(nodes[i]));
    }
    return states;
};


/**
 * Set state on nodes.
 *
 * If node is Backdrop it sets same state on all nodes inside
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
        var nodeName = nodes[i];
	    var backdrop = AyonHarmony._getBackdropByName(nodeName);
        if (backdrop){
        	var backdropNodes = Backdrop.nodes(backdrop);
        	for (var j=0; j < backdropNodes.length; j++){
			node.setEnable(backdropNodes[j], states[i]);
		}
	}else{
            node.setEnable(nodes[i], states[i]);
        }
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
        AyonHarmonyAPI.setState(nodes[i], false);
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
 * Create new Composite node in Harmony.
 * @function
 * @param {array} args Arguments, see example.
 * @return {string} Resulting node.
 *
 * @example
 * // arguments are in following order:
 * var args = [
 *  nodeName,
 *  nodeType,
 *  useSelection
 * ];
 */
AyonHarmonyAPI.createNodeContainer = function(args) {
    var nodeName = args[0];
    var nodeType = args[1];
    var useSelection = args[2];

    var resultNode = node.add('Top', nodeName, nodeType, 0, 0, 0);

    if (useSelection) {
        var selectedNodes = selection.selectedNodes();
        var compositeNodes = [];
        for (var i = 0; i < selectedNodes.length; i++) {
            var selectedNodeName = selectedNodes[i];
            var selectedNode = node.type(selectedNodeName);

            // Check if the node is a composite node
            if (node.type(selectedNodeName) === "COMPOSITE") { // Make sure to use the correct method to check type
                compositeNodes.push(selectedNodeName);
            }
        }

        if (compositeNodes.length > 0){
            var lastSelectedNode = compositeNodes[compositeNodes.length-1];
            node.link(lastSelectedNode, 0, resultNode, 0, false, true);
            node.setCoord(resultNode,
                node.coordX(lastSelectedNode),
                node.coordY(lastSelectedNode) + 70);
        }
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