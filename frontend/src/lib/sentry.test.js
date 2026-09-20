import { resolveSentryEnvironment } from "./sentry";

jest.mock("@sentry/capacitor", () => ({ init: jest.fn() }));
jest.mock("@sentry/react", () => ({ init: jest.fn() }));

describe("resolveSentryEnvironment", () => {
  test.each(["localhost", "127.0.0.1", "127.0.1.1", "[::1]"])(
    "labels %s as development even when a production label is configured",
    (hostname) => {
      expect(resolveSentryEnvironment(hostname, "production")).toBe(
        "development",
      );
    },
  );

  test("preserves the configured environment for deployed hosts", () => {
    expect(resolveSentryEnvironment("www.ile-ubuntu.org", "preview")).toBe(
      "preview",
    );
  });

  test("defaults deployed hosts to production", () => {
    expect(resolveSentryEnvironment("www.ile-ubuntu.org", "")).toBe(
      "production",
    );
  });
});
