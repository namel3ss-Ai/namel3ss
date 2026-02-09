import { describe, expect, it } from "vitest";
import { Namel3ssClient } from "../../packages/namel3ss-client/src/index";

describe("@namel3ss/client parsing", () => {
  it("constructs without hidden state", () => {
    const client = new Namel3ssClient("http://127.0.0.1:7340", { apiToken: "dev-token" });
    expect(client).toBeDefined();
  });
});
