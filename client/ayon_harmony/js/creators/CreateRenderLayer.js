/* global AyonHarmony:writable, include */
// ***************************************************************************
// *                             CreateRenderLayer                           *
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
var CreateRenderLayer = function() {};


/**
 * Create render layer instance.
 * @function
 * @param {array} args Arguments for instance.
 */
CreateRenderLayer.prototype.create = function(args) {
    node.setTextAttr(args[0], 'DRAWING_TYPE', 1, 'PNG4');
    node.setTextAttr(args[0], 'DRAWING_NAME', 1, args[1]);
    node.setTextAttr(args[0], 'MOVIE_PATH', 1, args[1]);
};

/**
 * Get layers info
 * @function
 */
CreateRenderLayer.prototype.getLayerInfos = function() {
    var scene = $.scene;
    var readNodes = scene.getNodesByType("READ");
    var layerInfos = [];
    var info = {};

    for (var i = 0; i < readNodes.length; i++) {
        var readNode = readNodes[i];

        info = {
            "name": readNode.name,
            "color": readNode.nodeColor.toString(),
            "fullName": readNode.toString(),
            "selected": readNode.selected
        };

    layerInfos.push(info);
    }
    MessageLog.trace("layerInfox: " + JSON.stringify(layerInfos));
    return layerInfos;
};

/**
 * Create render layer nodes.
 * 
 * 
 * @function
 * @param {array} args Arguments for instance.
 */
CreateRenderLayer.prototype.createLayerNodes = function(args) {
    var groupNodes = args[0];
    var productName = args[1];

    var scene = $.scn;

    var compositeName = productName + "_comp";
    var groupCompositeNode = scene.getNodeByPath("Top/" + compositeName);
    var groupWriteNode = scene.getNodeByPath("Top/" + productName);

    for (var i = 0; i < groupNodes.length; i++) {
        var sceneRoot = $.scn.root; 
        var groupNode = scene.getNodeByPath(groupNodes[i]);
        // create composition and 
        if (!groupCompositeNode){  
            groupCompositeNode = sceneRoot.addNode("COMPOSITE", compositeName);
            groupCompositeNode.centerBelow(groupNode);
        }
        if (!groupWriteNode){
            groupWriteNode = sceneRoot.addNode("WRITE", productName);
            groupCompositeNode.linkOutNode(groupWriteNode);
            groupWriteNode.centerBelow(groupCompositeNode);
            groupWriteNode.x += 150;
        }
        var connections = groupNode.linkedOutNodes || [];
        var compositePath = "Top/" + compositeName;
        var isConnectedToGroup = false;
        for (var i = 0; i < connections.length; i++) {
                var connPath = connections[i].fullPath; 
                if (connPath=== compositePath) {
                        isConnectedToGroup = true;
                        break;
                }
        }
        if (isConnectedToGroup){
            continue;
        }

        // connect to group composition
        for (var j = 0; j< groupNode.linkedOutNodes.length; j++) {
            var linkedOutNode = groupNode.linkedOutNodes[j];
            groupCompositeNode.linkOutNode(linkedOutNode);
            groupNode.unlinkOutNode(linkedOutNode);
        }
        groupNode.linkOutNode(groupCompositeNode);
        
    }
    MessageLog.trace("group:: " + groupWriteNode);
    return groupWriteNode.fullPath;
};

// add self to AYON Loaders
AyonHarmony.Creators.CreateRenderLayer = new CreateRenderLayer();