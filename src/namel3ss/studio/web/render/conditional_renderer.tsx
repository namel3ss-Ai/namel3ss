import type { LayoutNode } from "./layout_renderer";

export type ConditionalNode = {
  condition?: { result?: boolean };
  then_children?: LayoutNode[];
  else_children?: LayoutNode[];
};

export function resolveConditionalChildren(node: ConditionalNode): LayoutNode[] {
  const result = Boolean(node.condition && node.condition.result === true);
  return result ? node.then_children || [] : node.else_children || [];
}

