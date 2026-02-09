import { Namel3ssClient } from "@namel3ss/client";

const client = new Namel3ssClient("http://127.0.0.1:7340", {
  apiToken: "dev-token",
});

export async function runGoldenPath(uploadChecksum: string): Promise<void> {
  const ui = await client.getUi({ includeActions: true, includeState: true });
  const actionItems = Array.isArray(ui.actions?.actions) ? ui.actions?.actions : [];

  const uploadAction = actionItems.find((entry) => entry && (entry as { type?: string }).type === "upload_select");
  if (uploadAction && typeof (uploadAction as { id?: string }).id === "string") {
    await client.runAction((uploadAction as { id: string }).id, {
      upload: {
        checksum: uploadChecksum,
        name: "example.pdf",
        content_type: "application/pdf",
        bytes: 1024,
      },
    });
  }

  const ingestAction = actionItems.find((entry) => entry && (entry as { type?: string }).type === "ingestion_run");
  if (ingestAction && typeof (ingestAction as { id?: string }).id === "string") {
    await client.runAction((ingestAction as { id: string }).id, {
      upload_id: uploadChecksum,
      mode: "primary",
    });
  }

  const retrievalAction = actionItems.find((entry) => entry && (entry as { type?: string }).type === "retrieval_run");
  if (retrievalAction && typeof (retrievalAction as { id?: string }).id === "string") {
    const retrieval = await client.runAction((retrievalAction as { id: string }).id, {
      query: "Summarize policy changes.",
      limit: 4,
      tier: "auto",
    });
    const retrievalPayload =
      retrieval.result && typeof retrieval.result === "object"
        ? (retrieval.result as { retrieval?: Record<string, unknown> }).retrieval
        : null;
    if (!retrievalPayload) {
      throw new Error("Retrieval payload missing from retrieval_run action.");
    }
    const trace = Array.isArray(retrievalPayload.retrieval_trace) ? retrievalPayload.retrieval_trace : [];
    const trust = retrievalPayload.trust_score_details as { score?: number } | undefined;
    if (!trace.length) {
      throw new Error("Retrieval trace is required for citations and explainability.");
    }
    if (!trust || typeof trust.score !== "number") {
      throw new Error("Trust score details are missing from retrieval payload.");
    }
  }

  const chatAction = actionItems.find((entry) => entry && (entry as { type?: string }).type === "call_flow");
  if (chatAction && typeof (chatAction as { id?: string }).id === "string") {
    const result = await client.runAction((chatAction as { id: string }).id, {
      message: "Summarize the uploaded document.",
    });
    if (result.runtime_error) {
      throw new Error(`Runtime error: ${result.runtime_error.category} (${result.runtime_error.stable_code})`);
    }
  }
}
