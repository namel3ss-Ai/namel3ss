export type ChatStreamPhase = "thinking" | "streaming" | "complete";

export type ChatStreamState = {
  cursor: number;
  phase: ChatStreamPhase;
  text: string;
  tokens: string[];
};

const STREAM_PHASE_THINKING: ChatStreamPhase = "thinking";
const STREAM_PHASE_STREAMING: ChatStreamPhase = "streaming";
const STREAM_PHASE_COMPLETE: ChatStreamPhase = "complete";

function splitTokens(content: string): string[] {
  if (!content) {
    return [];
  }
  return content.split(/(\s+)/).filter((entry) => entry.length > 0);
}

export function createStreamState(content: string, tokens?: string[]): ChatStreamState {
  const tokenList = Array.isArray(tokens) && tokens.length > 0 ? [...tokens] : splitTokens(content);
  return {
    cursor: 0,
    phase: tokenList.length > 0 ? STREAM_PHASE_THINKING : STREAM_PHASE_COMPLETE,
    text: "",
    tokens: tokenList,
  };
}

export function advanceStreamState(current: ChatStreamState): ChatStreamState {
  if (!current.tokens.length) {
    return {
      ...current,
      phase: STREAM_PHASE_COMPLETE,
    };
  }
  if (current.cursor >= current.tokens.length) {
    return {
      ...current,
      phase: STREAM_PHASE_COMPLETE,
    };
  }
  const token = current.tokens[current.cursor] || "";
  const nextCursor = current.cursor + 1;
  const nextPhase = nextCursor >= current.tokens.length ? STREAM_PHASE_COMPLETE : STREAM_PHASE_STREAMING;
  return {
    ...current,
    cursor: nextCursor,
    phase: nextPhase,
    text: `${current.text}${token}`,
  };
}

export function shouldRenderCitationRow(state: ChatStreamState, citationCount: number): boolean {
  return citationCount > 0 && state.phase === STREAM_PHASE_COMPLETE;
}

export function thinkingTextForPhase(phase: ChatStreamPhase, retrievalInFlight: boolean): string {
  if (retrievalInFlight) {
    return "Searching sources...";
  }
  if (phase === STREAM_PHASE_THINKING || phase === STREAM_PHASE_STREAMING) {
    return "Assistant is typing...";
  }
  return "";
}

export const CHAT_STREAMING_PHASES = {
  COMPLETE: STREAM_PHASE_COMPLETE,
  STREAMING: STREAM_PHASE_STREAMING,
  THINKING: STREAM_PHASE_THINKING,
} as const;
