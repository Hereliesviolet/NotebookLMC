"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type MouseEvent as ReactMouseEvent,
} from "react";
import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Edge,
  type Node,
  type NodeProps,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import type { StudioMindmapContent } from "@/lib/types";

interface MindmapNodeData extends Record<string, unknown> {
  label: string;
  branchId?: string;
  hasChildren?: boolean;
  collapsed?: boolean;
}

type MindmapNode = Node<MindmapNodeData>;

const HANDLE_SIDES = [Position.Top, Position.Bottom, Position.Left, Position.Right];

const OPPOSITE_SIDE: Record<Position, Position> = {
  [Position.Top]: Position.Bottom,
  [Position.Bottom]: Position.Top,
  [Position.Left]: Position.Right,
  [Position.Right]: Position.Left,
};

/** Invisible handles on all four sides so `smoothstep` edges can leave/enter
 * from whichever side actually faces the other node - needed because nodes
 * are arranged radially, not in a fixed top-down tree. */
function AllSideHandles() {
  return (
    <>
      {HANDLE_SIDES.map((side) => (
        <Handle
          key={`target-${side}`}
          type="target"
          position={side}
          id={`target-${side}`}
          className="!h-0 !w-0 !min-h-0 !min-w-0 !border-0 !bg-transparent !opacity-0"
        />
      ))}
      {HANDLE_SIDES.map((side) => (
        <Handle
          key={`source-${side}`}
          type="source"
          position={side}
          id={`source-${side}`}
          className="!h-0 !w-0 !min-h-0 !min-w-0 !border-0 !bg-transparent !opacity-0"
        />
      ))}
    </>
  );
}

function RootMindmapNode({ data }: NodeProps<MindmapNode>) {
  return (
    <div className="rounded-md bg-primary px-4 py-2 text-center text-sm font-semibold text-primary-foreground shadow-md">
      <AllSideHandles />
      {data.label}
    </div>
  );
}

function BranchMindmapNode({ data }: NodeProps<MindmapNode>) {
  return (
    <div
      className={cn(
        "flex max-w-[190px] items-center gap-1.5 rounded-md border border-border bg-card px-3 py-2 text-sm font-medium text-foreground shadow-sm transition-colors",
        data.hasChildren && "cursor-pointer hover:border-primary hover:bg-primary/5"
      )}
    >
      <AllSideHandles />
      {data.hasChildren ? (
        <ChevronDown
          className={cn(
            "h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform",
            !data.collapsed && "rotate-180"
          )}
        />
      ) : (
        <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-muted-foreground" />
      )}
      <span>{data.label}</span>
    </div>
  );
}

function LeafMindmapNode({ data }: NodeProps<MindmapNode>) {
  return (
    <div className="max-w-[170px] rounded-md bg-muted px-2.5 py-1.5 text-xs text-muted-foreground shadow-sm">
      <AllSideHandles />
      {data.label}
    </div>
  );
}

const nodeTypes: NodeTypes = {
  root: RootMindmapNode,
  branch: BranchMindmapNode,
  leaf: LeafMindmapNode,
};

function closestSide(dx: number, dy: number): Position {
  if (Math.abs(dx) > Math.abs(dy)) return dx >= 0 ? Position.Right : Position.Left;
  return dy >= 0 ? Position.Bottom : Position.Top;
}

function buildEdge(
  sourceId: string,
  targetId: string,
  sourcePos: { x: number; y: number },
  targetPos: { x: number; y: number },
  branchId?: string
): Edge {
  const sourceSide = closestSide(targetPos.x - sourcePos.x, targetPos.y - sourcePos.y);
  const targetSide = OPPOSITE_SIDE[sourceSide];
  return {
    id: `e-${sourceId}-${targetId}`,
    source: sourceId,
    target: targetId,
    sourceHandle: `source-${sourceSide}`,
    targetHandle: `target-${targetSide}`,
    type: "smoothstep",
    data: branchId ? { branchId } : undefined,
    style: { stroke: "hsl(var(--border))", strokeWidth: 1.5 },
  };
}

const BRANCH_BASE_RADIUS = 260;
const LEAF_BASE_RADIUS = 170;

/** Root at (0,0); branches spread evenly around it on a circle of radius
 * `branchRadius`; each branch's own children fan out around it (centered on
 * the branch's angle from the root) on a smaller circle of radius
 * `leafRadius`. Both radii grow with sibling count so nodes don't overlap. */
function buildMindmapGraph(content: StudioMindmapContent): { nodes: MindmapNode[]; edges: Edge[] } {
  const branches = content.root.children;
  const branchCount = Math.max(branches.length, 1);
  const branchRadius = Math.max(BRANCH_BASE_RADIUS, branchCount * 55);

  const nodes: MindmapNode[] = [
    {
      id: "root",
      type: "root",
      position: { x: 0, y: 0 },
      data: { label: content.root.label },
      draggable: true,
    },
  ];
  const edges: Edge[] = [];

  branches.forEach((branch, branchIndex) => {
    const branchAngle = (branchIndex / branchCount) * 2 * Math.PI - Math.PI / 2;
    const branchId = `branch-${branchIndex}`;
    const branchPos = {
      x: Math.cos(branchAngle) * branchRadius,
      y: Math.sin(branchAngle) * branchRadius,
    };

    nodes.push({
      id: branchId,
      type: "branch",
      position: branchPos,
      data: {
        label: branch.label,
        hasChildren: branch.children.length > 0,
        collapsed: false,
        branchId,
      },
      draggable: true,
    });
    edges.push(buildEdge("root", branchId, { x: 0, y: 0 }, branchPos));

    const leafCount = branch.children.length;
    if (leafCount === 0) return;

    const fanSpread = Math.min(Math.PI * 0.85, 0.5 + leafCount * 0.45);
    const leafRadius = Math.max(LEAF_BASE_RADIUS, leafCount * 26);

    branch.children.forEach((leaf, leafIndex) => {
      const leafAngle =
        leafCount === 1
          ? branchAngle
          : branchAngle - fanSpread / 2 + (fanSpread * leafIndex) / (leafCount - 1);
      const leafPos = {
        x: branchPos.x + Math.cos(leafAngle) * leafRadius,
        y: branchPos.y + Math.sin(leafAngle) * leafRadius,
      };
      const leafId = `${branchId}-leaf-${leafIndex}`;
      nodes.push({
        id: leafId,
        type: "leaf",
        position: leafPos,
        data: { label: leaf.label, branchId },
      });
      edges.push(buildEdge(branchId, leafId, branchPos, leafPos, branchId));
    });
  });

  return { nodes, edges };
}

function MindmapGraph({ content }: { content: StudioMindmapContent }) {
  const { fitView } = useReactFlow();
  const [collapsedBranchIds, setCollapsedBranchIds] = useState<Set<string>>(() => new Set());

  const { nodes: baseNodes, edges: baseEdges } = useMemo(
    () => buildMindmapGraph(content),
    [content]
  );

  const visibleNodes = useMemo(
    () =>
      baseNodes
        .filter((node) => node.type !== "leaf" || !collapsedBranchIds.has(node.data.branchId ?? ""))
        .map((node) =>
          node.type === "branch"
            ? { ...node, data: { ...node.data, collapsed: collapsedBranchIds.has(node.id) } }
            : node
        ),
    [baseNodes, collapsedBranchIds]
  );

  const visibleEdges = useMemo(
    () =>
      baseEdges.filter(
        (edge) =>
          !edge.data || !collapsedBranchIds.has((edge.data as { branchId?: string }).branchId ?? "")
      ),
    [baseEdges, collapsedBranchIds]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(visibleNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(visibleEdges);

  useEffect(() => {
    setNodes(visibleNodes);
    setEdges(visibleEdges);
    const frame = requestAnimationFrame(() => fitView({ padding: 0.2, duration: 250 }));
    return () => cancelAnimationFrame(frame);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibleNodes, visibleEdges]);

  const handleNodeClick = useCallback((_event: ReactMouseEvent, node: MindmapNode) => {
    if (node.type !== "branch" || !node.data.hasChildren) return;
    setCollapsedBranchIds((previous) => {
      const next = new Set(previous);
      if (next.has(node.id)) next.delete(node.id);
      else next.add(node.id);
      return next;
    });
  }, []);

  const totalNodeCount = baseNodes.length;

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeClick={handleNodeClick}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      minZoom={0.15}
      maxZoom={1.5}
      nodesConnectable={false}
    >
      <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
      <Controls showInteractive={false} />
      {totalNodeCount > 15 && (
        <MiniMap
          pannable
          zoomable
          nodeColor="hsl(var(--primary))"
          maskColor="hsl(var(--muted) / 0.6)"
        />
      )}
    </ReactFlow>
  );
}

export function StudioMindmapView({ content }: { content: StudioMindmapContent }) {
  return (
    <div className="h-[70vh] w-full overflow-hidden rounded-md border border-border">
      <ReactFlowProvider>
        <MindmapGraph content={content} />
      </ReactFlowProvider>
    </div>
  );
}
