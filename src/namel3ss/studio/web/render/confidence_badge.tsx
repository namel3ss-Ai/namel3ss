export type ConfidenceBadge = {
  ariaLabel: string;
  label: "Grounded" | "No sources" | "Partial";
  tone: "high" | "low" | "medium";
};

export function mapConfidenceBadge(value: unknown): ConfidenceBadge | null {
  if (value === true) {
    return {
      ariaLabel: "Grounded answer",
      label: "Grounded",
      tone: "high",
    };
  }
  if (value === false) {
    return {
      ariaLabel: "Answer without evidence",
      label: "No sources",
      tone: "low",
    };
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    if (value >= 0.75) {
      return {
        ariaLabel: "Grounded answer",
        label: "Grounded",
        tone: "high",
      };
    }
    if (value > 0) {
      return {
        ariaLabel: "Partially grounded answer",
        label: "Partial",
        tone: "medium",
      };
    }
    return {
      ariaLabel: "Answer without evidence",
      label: "No sources",
      tone: "low",
    };
  }
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (normalized === "grounded") {
      return {
        ariaLabel: "Grounded answer",
        label: "Grounded",
        tone: "high",
      };
    }
    if (normalized === "partial") {
      return {
        ariaLabel: "Partially grounded answer",
        label: "Partial",
        tone: "medium",
      };
    }
    if (normalized === "no_sources" || normalized === "no sources") {
      return {
        ariaLabel: "Answer without evidence",
        label: "No sources",
        tone: "low",
      };
    }
  }
  return null;
}
