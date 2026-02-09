const DEFAULT_HEADERS = {
  "Accept": "application/json",
  "Content-Type": "application/json"
};

export class Namel3ssUiClient {
  constructor(baseUrl, options = {}) {
    if (typeof options === "function") {
      options = { fetchImpl: options };
    }
    const config = options && typeof options === "object" ? options : {};
    this.baseUrl = String(baseUrl || "").replace(/\/$/, "");
    this.fetch = typeof config.fetchImpl === "function" ? config.fetchImpl : fetch;
    this.apiVersion = String(config.apiVersion || "v1");
    this.apiToken = typeof config.apiToken === "string" ? config.apiToken.trim() : "";
  }

  async getManifest() {
    if (this.apiVersion === "v1") {
      try {
        const payload = await this._get("/api/v1/ui");
        if (payload && typeof payload === "object" && payload.manifest) {
          return payload.manifest;
        }
        return payload;
      } catch (error) {
        if (!this._shouldFallback(error)) {
          throw error;
        }
      }
    }
    return this._get("/api/ui/manifest");
  }

  async getState() {
    if (this.apiVersion === "v1") {
      try {
        const payload = await this._get("/api/v1/ui?include_state=1");
        if (payload && typeof payload === "object" && payload.state) {
          return payload.state;
        }
        return payload;
      } catch (error) {
        if (!this._shouldFallback(error)) {
          throw error;
        }
      }
    }
    return this._get("/api/ui/state");
  }

  async getActions() {
    if (this.apiVersion === "v1") {
      try {
        const payload = await this._get("/api/v1/ui?include_actions=1");
        if (payload && typeof payload === "object" && payload.actions) {
          return payload.actions;
        }
        return payload;
      } catch (error) {
        if (!this._shouldFallback(error)) {
          throw error;
        }
      }
    }
    return this._get("/api/ui/actions");
  }

  async runAction(id, payload = {}) {
    if (this.apiVersion === "v1") {
      try {
        return this._post(`/api/v1/actions/${encodeURIComponent(id)}`, { args: payload });
      } catch (error) {
        if (!this._shouldFallback(error)) {
          throw error;
        }
      }
    }
    return this._post("/api/ui/action", { id, payload });
  }

  async _get(path) {
    let response;
    try {
      response = await this.fetch(`${this.baseUrl}${path}`, {
        method: "GET",
        headers: this._headers()
      });
    } catch (error) {
      throw this._networkError(path, error);
    }
    return this._decode(response);
  }

  async _post(path, body) {
    let response;
    try {
      response = await this.fetch(`${this.baseUrl}${path}`, {
        method: "POST",
        headers: this._headers(),
        body: JSON.stringify(body || {})
      });
    } catch (error) {
      throw this._networkError(path, error);
    }
    return this._decode(response);
  }

  _headers() {
    const headers = { ...DEFAULT_HEADERS };
    if (this.apiToken) {
      headers["X-API-Token"] = this.apiToken;
    }
    return headers;
  }

  _shouldFallback(error) {
    return Boolean(error && typeof error === "object" && error.status === 404);
  }

  async _decode(response) {
    let payload = {};
    try {
      payload = await response.json();
    } catch (_error) {
      payload = {};
    }
    if (response.ok) {
      return payload;
    }
    const runtimeError = payload && payload.runtime_error && typeof payload.runtime_error === "object"
      ? payload.runtime_error
      : null;
    const message = runtimeError?.message || payload?.error?.message || payload?.message || "Request failed";
    const error = new Error(message);
    error.status = response.status;
    error.payload = payload;
    if (runtimeError) error.runtime_error = runtimeError;
    throw error;
  }

  _networkError(path, originalError) {
    const runtimeError = {
      category: "server_unavailable",
      message: "Runtime server is unavailable.",
      hint: `Start the runtime server and retry ${path}.`,
      origin: "network",
      stable_code: "runtime.server_unavailable"
    };
    const error = new Error(runtimeError.message);
    error.runtime_error = runtimeError;
    error.cause = originalError;
    return error;
  }
}

export default Namel3ssUiClient;
