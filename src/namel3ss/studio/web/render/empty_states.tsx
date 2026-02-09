export type ChatEmptyMode = "idle" | "no_sources" | "retrieving" | "error";

export type ChatEmptyState = {
  body: string;
  ctaLabel: string;
  mode: ChatEmptyMode;
  title: string;
};

const EMPTY_STATES: Record<ChatEmptyMode, ChatEmptyState> = {
  error: {
    body: "Something went wrong while preparing this answer. Try again.",
    ctaLabel: "Try again",
    mode: "error",
    title: "Unable to answer right now",
  },
  idle: {
    body: "Ask a question to start the conversation.",
    ctaLabel: "",
    mode: "idle",
    title: "Ready when you are",
  },
  no_sources: {
    body: "Upload a document to ground answers with citations.",
    ctaLabel: "Upload document",
    mode: "no_sources",
    title: "No sources available",
  },
  retrieving: {
    body: "Searching sources...",
    ctaLabel: "",
    mode: "retrieving",
    title: "Preparing answer",
  },
};

export function resolveChatEmptyState(params: {
  error?: string | null;
  hasMessages: boolean;
  hasSources: boolean;
  isRetrieving: boolean;
}): ChatEmptyState {
  if (typeof params.error === "string" && params.error.trim()) {
    return EMPTY_STATES.error;
  }
  if (params.isRetrieving) {
    return EMPTY_STATES.retrieving;
  }
  if (!params.hasMessages && !params.hasSources) {
    return EMPTY_STATES.no_sources;
  }
  return EMPTY_STATES.idle;
}

export function shouldRenderUploadAction(state: ChatEmptyState): boolean {
  return state.mode === "no_sources";
}

export function friendlyRuntimeErrorMessage(raw: unknown): string {
  if (typeof raw !== "string" || !raw.trim()) {
    return "Something went wrong while generating the response.";
  }
  const firstLine = raw.split("\n", 1)[0].trim();
  if (!firstLine) {
    return "Something went wrong while generating the response.";
  }
  return firstLine;
}
