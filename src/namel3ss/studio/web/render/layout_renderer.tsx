export type LayoutNode = {
  type: string;
  children?: LayoutNode[];
  sidebar?: LayoutNode[];
  main?: LayoutNode[];
  columns?: number;
  direction?: string;
  position?: "top" | "bottom" | string;
  title?: string;
  show_when?: { result?: boolean };
};

export type LayoutBranch = {
  container: "children" | "sidebar" | "main";
  nodes: LayoutNode[];
};

export function isLayoutNode(node: LayoutNode | null | undefined): node is LayoutNode {
  return Boolean(node && typeof node.type === "string" && node.type.startsWith("layout."));
}

export function layoutBranches(node: LayoutNode): LayoutBranch[] {
  if (node.type === "layout.sidebar") {
    return [
      { container: "sidebar", nodes: node.sidebar || [] },
      { container: "main", nodes: node.main || [] },
    ];
  }
  return [{ container: "children", nodes: node.children || [] }];
}

export function layoutDrawerOpen(node: LayoutNode): boolean {
  return node.type === "layout.drawer" && Boolean(node.show_when && node.show_when.result === true);
}

