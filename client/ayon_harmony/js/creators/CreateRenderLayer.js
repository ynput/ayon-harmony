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
    $.beginUndo("createLayerNodes"); 

    var groupNodes = args[0];
    var productName = args[1];

    if (!groupNodes){
        MessageLog.trace("No nodes passed for 'createLayerNodes'")
        return;
    }

    var scn = $.scn;

    var compositeName = productName + "_comp";
    var groupCompositeNode = scn.getNodeByPath("Top/" + compositeName);
    var groupWriteNode = scn.getNodeByPath("Top/" + productName);

    var scnRoot = $.scn.root;
    var lastInPortNum = -1;
    var oNodes = [];
    var created = false;
    for (var i = 0; i< groupNodes.length; i++) {
        var groupNode = scn.getNodeByPath(groupNodes[i]);
	
        // create composition and
        if (!groupCompositeNode){
            groupCompositeNode = scnRoot.addNode("COMPOSITE", compositeName);
	     created = true;
        }
        if (!groupWriteNode){
            groupWriteNode = scnRoot.addNode("WRITE", productName);
            groupCompositeNode.linkOutNode(groupWriteNode);
            groupWriteNode.drawing_type = "PNG4"  // png + alpha
            created = true;
        }
        var connections = groupNode.linkedOutNodes || [];
        var compositePath = "Top/" + compositeName;
        var isConnectedToGroupCompositeAlready = false;
        for (var ci = 0; ci < connections.length; ci++) {
            var connPath = connections[ci].fullPath;
            if (connPath=== compositePath) {
                    isConnectedToGroupCompositeAlready = true;
                    break;
            }
        }
        if (isConnectedToGroupCompositeAlready){
            continue;
        }

        // connect to group composition
	    var outConnections = groupNode.getOutLinks();
        for (var j = 0; j< outConnections.length; j++) {
            var outConn = outConnections[j];
	        var linkedOutNode = outConn.inNode;
	        lastInPortNum = outConn.inPort;

            groupNode.unlinkOutNode(linkedOutNode);
        }
        groupNode.linkOutNode(groupCompositeNode);

    }
    groupCompositeNode.linkOutNode(linkedOutNode, undefined, lastInPortNum);

    $.endUndo();

    MessageLog.trace("group:: " + groupWriteNode);
    return groupWriteNode.fullPath;
};

/**
 * Tries to format nodes of a layer group and wrap them in Backdrop
 * 
 * Traverses up from layer group write node
 * 
 * TODO refactor
 * 
 * @function
 * @param {array} args Arguments for instance.
 */
CreateRenderLayer.prototype.formatNodes = function(args) {
    $.beginUndo("formatNodes");

    var layerGroupName = args[0];
    var groupLabel = args[1];
    var groupColor = args[2];

    var scn = $.scn;
    
    var groupNodes = [];
    var groupWriteNode = scn.getNodeByPath(layerGroupName);
    if (!groupWriteNode){
        MessageLog.trace("Couldnt find " + layerGroupName);
        return
    }
    groupNodes.push(groupWriteNode);
    var groupCompositeNode = groupWriteNode.getLinkedInNode(0);
    groupNodes.push(groupCompositeNode);

    var inNodes = groupCompositeNode.linkedInNodes;
    groupCompositeNode.placeAtCenter(inNodes ,0, 150);
    groupCompositeNode.orderAboveNodes();

    groupWriteNode.centerBelow(groupCompositeNode);
    groupWriteNode.x -= 150;

    for (var i = 0; i< inNodes.length; i++) {
        groupNodes.push(inNodes[i]);
    }

    var group = scn.root;
    var color = new $.oColorValue(groupColor);

    var backdrop = group.addBackdropToNodes(groupNodes, groupLabel, "", color);

    $.endUndo();

    return backdrop;
}

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
 *    - {string} name of read node (without Top/)
 *    - {string} product name
 *    - {bool} if read node should be renamed, in that
 *          case attached write contains original name with _render
 *          suffix 
 */
CreateRenderPass.prototype.createPassNode = function(args) {
    var readNode = args[0];
    var productName = args[1];
    var renameRead = args[2];

    if (!readNode){
        return;
    }
    var scene = $.scn;
    var readNode = scene.getNodeByPath("Top/" + readNode);
    var writeNode = scene.getNodeByPath("Top/" + productName);

    if (!writeNode){
        var sceneRoot = $.scn.root; 
        var writeNodeName = productName;
        if (renameRead){
            writeNodeName = readNode.name + "_render";
            readNode.name = productName;
        }
        writeNode = sceneRoot.addNode("WRITE", writeNodeName);
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