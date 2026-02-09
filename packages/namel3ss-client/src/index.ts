import { CONTRACT_VERSION, HEADLESS_API_VERSION } from "./types";
import type {
  ClientOptions,
  ContractWarning,
  HeadlessActionResponse,
  HeadlessUiResponse,
  RuntimeError,
  UiManifest,
  UiState,
} from "./types";
import { validateHeadlessActionResponse, validateHeadlessUiResponse } from "./validate";

const DEFAULT_HEADERS = {
  Accept: "application/json",
  "Content-Type": "application/json",
};

export class Namel3ssClientError extends Error {
  status: number | null;
  payload: unknown;
  runtime_error: RuntimeError | null;
  contract_warnings: ContractWarning[];

  constructor(message: string, options: { status?: number | null; payload?: unknown; runtime_error?: RuntimeError | null; contract_warnings?: ContractWarning[] } = {}) {
    super(message);
    this.name = "Namel3ssClientError";
    this.status = typeof options.status === "number" ? options.status : null;
    this.payload = options.payload ?? null;
    this.runtime_error = options.runtime_error ?? null;
    this.contract_warnings = Array.isArray(options.contract_warnings) ? options.contract_warnings : [];
  }
}

export class Namel3ssClient {
  private baseUrl: string;
  private fetchImpl: typeof fetch;
  private apiToken: string;

  constructor(baseUrl: string, options: ClientOptions = {}) {
    this.baseUrl = String(baseUrl || "").replace(/\/$/, "");
    this.fetchImpl = typeof options.fetchImpl === "function" ? options.fetchImpl : fetch;
    this.apiToken = typeof options.apiToken === "string" ? options.apiToken.trim() : "";
  }

  async getUi(opts: { includeState?: boolean; includeActions?: boolean } = {}): Promise<HeadlessUiResponse> {
    const query = new URLSearchParams();
    if (opts.includeState) query.set("include_state", "1");
    if (opts.includeActions) query.set("include_actions", "1");
    const suffix = query.toString();
    const path = suffix ? `/api/${HEADLESS_API_VERSION}/ui?${suffix}` : `/api/${HEADLESS_API_VERSION}/ui`;
    return this.requestHeadlessUi(path);
  }

  async getManifest(): Promise<UiManifest | null> {
    const payload = await this.getUi();
    return payload.manifest ?? null;
  }

  async getState(): Promise<UiState | null> {
    const payload = await this.getUi({ includeState: true });
    return payload.state ?? null;
  }

  async getActions(): Promise<Record<string, unknown> | null> {
    const payload = await this.getUi({ includeActions: true });
    return payload.actions ?? null;
  }

  async runAction(actionId: string, args: Record<string, unknown> = {}): Promise<HeadlessActionResponse> {
    if (typeof actionId !== "string" || !actionId.trim()) {
      throw new Namel3ssClientError("Action id is required.");
    }
    const encoded = encodeURIComponent(actionId);
    return this.requestHeadlessAction(`/api/${HEADLESS_API_VERSION}/actions/${encoded}`, { args });
  }

  private async requestHeadlessUi(path: string): Promise<HeadlessUiResponse> {
    const payload = await this.requestJson(path, { method: "GET" });
    const warnings = validateHeadlessUiResponse(payload);
    return this.normalizeHeadlessUiPayload(payload, warnings);
  }

  private async requestHeadlessAction(path: string, body: Record<string, unknown>): Promise<HeadlessActionResponse> {
    const payload = await this.requestJson(path, {
      method: "POST",
      body: JSON.stringify(body || {}),
    });
    const warnings = validateHeadlessActionResponse(payload);
    return this.normalizeHeadlessActionPayload(payload, warnings);
  }

  private async requestJson(path: string, init: RequestInit): Promise<unknown> {
    let response: Response;
    try {
      response = await this.fetchImpl(`${this.baseUrl}${path}`, {
        ...init,
        headers: this.headers(init.headers),
      });
    } catch (error) {
      throw this.networkError(path, error);
    }
    let payload: unknown = {};
    try {
      payload = await response.json();
    } catch (_error) {
      payload = {};
    }
    if (response.ok) return payload;
    const runtimeError = this.readRuntimeError(payload);
    const message = runtimeError?.message || this.readErrorMessage(payload) || `Request failed with status ${response.status}.`;
    throw new Namel3ssClientError(message, {
      status: response.status,
      payload,
      runtime_error: runtimeError,
    });
  }

  private headers(existing: HeadersInit | undefined): HeadersInit {
    const merged: Record<string, string> = { ...DEFAULT_HEADERS };
    if (this.apiToken) {
      merged["X-API-Token"] = this.apiToken;
    }
    if (existing && typeof existing === "object") {
      for (const [key, value] of Object.entries(existing as Record<string, string>)) {
        merged[key] = value;
      }
    }
    return merged;
  }

  private normalizeHeadlessUiPayload(payload: unknown, warnings: ContractWarning[]): HeadlessUiResponse {
    if (!this.isObject(payload)) {
      throw new Namel3ssClientError("Invalid UI response payload.", { payload, contract_warnings: warnings });
    }
    const normalized: HeadlessUiResponse = {
      ...(payload as HeadlessUiResponse),
      contract_version: (payload as HeadlessUiResponse).contract_version || CONTRACT_VERSION,
      api_version: (payload as HeadlessUiResponse).api_version || HEADLESS_API_VERSION,
    };
    if (warnings.length > 0) {
      normalized.contract_warnings = warnings;
    }
    return normalized;
  }

  private normalizeHeadlessActionPayload(payload: unknown, warnings: ContractWarning[]): HeadlessActionResponse {
    if (!this.isObject(payload)) {
      throw new Namel3ssClientError("Invalid action response payload.", { payload, contract_warnings: warnings });
    }
    const normalized: HeadlessActionResponse = {
      ...(payload as HeadlessActionResponse),
      contract_version: (payload as HeadlessActionResponse).contract_version || CONTRACT_VERSION,
      api_version: (payload as HeadlessActionResponse).api_version || HEADLESS_API_VERSION,
      action_id: (payload as HeadlessActionResponse).action_id || "",
    };
    if (warnings.length > 0) {
      normalized.contract_warnings = warnings;
    }
    return normalized;
  }

  private readErrorMessage(payload: unknown): string {
    if (!this.isObject(payload)) return "";
    if (typeof payload.message === "string" && payload.message.trim()) return payload.message.trim();
    if (this.isObject(payload.error) && typeof payload.error.message === "string" && payload.error.message.trim()) {
      return payload.error.message.trim();
    }
    return "";
  }

  private readRuntimeError(payload: unknown): RuntimeError | null {
    if (!this.isObject(payload) || !this.isObject(payload.runtime_error)) return null;
    const candidate = payload.runtime_error as Record<string, unknown>;
    const category = typeof candidate.category === "string" ? candidate.category.trim() : "";
    const message = typeof candidate.message === "string" ? candidate.message.trim() : "";
    const hint = typeof candidate.hint === "string" ? candidate.hint.trim() : "";
    const origin = typeof candidate.origin === "string" ? candidate.origin.trim() : "";
    const stable = typeof candidate.stable_code === "string" ? candidate.stable_code.trim() : "";
    if (!(category && message && hint && origin && stable)) return null;
    return { category, message, hint, origin, stable_code: stable };
  }

  private networkError(path: string, cause: unknown): Namel3ssClientError {
    const runtimeError: RuntimeError = {
      category: "server_unavailable",
      message: "Runtime server is unavailable.",
      hint: `Start the runtime server and retry ${path}.`,
      origin: "network",
      stable_code: "runtime.server_unavailable",
    };
    const error = new Namel3ssClientError(runtimeError.message, {
      runtime_error: runtimeError,
      payload: null,
    });
    (error as { cause?: unknown }).cause = cause;
    return error;
  }

  private isObject(value: unknown): value is Record<string, unknown> {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }
}
