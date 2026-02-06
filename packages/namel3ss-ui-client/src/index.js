const DEFAULT_HEADERS = {
  "Accept": "application/json",
  "Content-Type": "application/json"
};

export class Namel3ssUiClient {
  constructor(baseUrl, fetchImpl = fetch) {
    this.baseUrl = String(baseUrl || "").replace(/\/$/, "");
    this.fetch = fetchImpl;
  }

  async getManifest() {
    return this._get("/api/ui/manifest");
  }

  async getState() {
    return this._get("/api/ui/state");
  }

  async getActions() {
    return this._get("/api/ui/actions");
  }

  async runAction(id, payload = {}) {
    return this._post("/api/ui/action", { id, payload });
  }

  async _get(path) {
    const response = await this.fetch(`${this.baseUrl}${path}`, {
      method: "GET",
      headers: DEFAULT_HEADERS
    });
    return this._decode(response);
  }

  async _post(path, body) {
    const response = await this.fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: DEFAULT_HEADERS,
      body: JSON.stringify(body || {})
    });
    return this._decode(response);
  }

  async _decode(response) {
    const payload = await response.json();
    if (response.ok) {
      return payload;
    }
    const message = payload?.error?.message || payload?.message || "Request failed";
    throw new Error(message);
  }
}

export default Namel3ssUiClient;
