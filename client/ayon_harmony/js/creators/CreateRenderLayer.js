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
 * Create render layer nodes.
 * 
 * Creates:
 * - composite node connected to all Harmony layers with same color
 * - write node connected to composite (for rendering)
 * @function
 * @param {array} args Arguments for instance.
 */
CreateRenderLayer.prototype.createLayerNodes = function(args) {
    var groupNodes = args[0];
    var productName = args[1];

    if (!groupNodes){
        return;
    }

    var scene = $.scn;

    var compositeName = productName + "_comp";
    var groupCompositeNode = scene.getNodeByPath("Top/" + compositeName);
    var groupWriteNode = scene.getNodeByPath("Top/" + productName);

    var sceneRoot = $.scn.root; 
    for (var i = groupNodes.length -1; i >= 0; i--) {
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
            groupWriteNode.drawing_type = "PNG4"  // png + alpha
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

/**
 * @namespace
 * @classdesc Code creating render containers in Harmony.
 */
var CreateRenderPass = function() {};

/**
 * Create render layer nodes.
 * 
 * Creates:
 * - write node connected to read (drawing) node
 * @function
 * @param {array} args Arguments for instance.
 */
CreateRenderPass.prototype.createPassNode = function(args) {
    var readNode = args[0];
    var productName = args[1];

    if (!readNode){
        return;
    }
    var scene = $.scn;
    var readNode = scene.getNodeByPath("Top/" + readNode);
    var writeNode = scene.getNodeByPath("Top/" + productName);

    if (!writeNode){
        var sceneRoot = $.scn.root; 
        writeNode = sceneRoot.addNode("WRITE", productName);
        readNode.linkOutNode(writeNode);
        writeNode.centerBelow(readNode);
        writeNode.x -= 150;
        writeNode.drawing_type = "PNG4"  // png + alpha
    }
    return writeNode.fullPath;
}

// add self to AYON
AyonHarmony.Creators.CreateRenderLayer = new CreateRenderLayer();
AyonHarmony.Creators.CreateRenderPass = new CreateRenderPass();