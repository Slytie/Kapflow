import { http, HttpResponse } from "msw";

import { ApiClientError, requestBinary } from "@/lib/api/httpClient";
import { server } from "@/test/api/server";

describe("requestBinary", () => {
  it("returns binary body plus parsed attachment headers", async () => {
    const binaryText = "template:binary-fixture";

    server.use(
      http.get("*/api/v1/test/download.bin", () =>
        new HttpResponse(binaryText, {
          status: 200,
          headers: {
            "content-type": "application/vnd.test.sheet",
            "content-length": String(binaryText.length),
            "content-disposition": 'attachment; filename="demo workbook.xlsx"',
            "x-request-id": "httpreq_test_download"
          }
        })
      )
    );

    const response = await requestBinary("/test/download.bin");

    expect(await response.body.text()).toBe(binaryText);
    expect(response.fileName).toBe("demo workbook.xlsx");
    expect(response.mediaType).toBe("application/vnd.test.sheet");
    expect(response.contentLength).toBe(binaryText.length);
    expect(response.requestId).toBe("httpreq_test_download");
  });

  it("surfaces JSON error envelopes from binary routes", async () => {
    server.use(
      http.get("*/api/v1/test/missing.bin", () =>
        HttpResponse.json(
          {
            status: "error",
            error: {
              code: "template_not_found",
              message: "template not found",
              details: { template_id: "missing" }
            }
          },
          { status: 404 }
        )
      )
    );

    let observed: unknown;
    try {
      await requestBinary("/test/missing.bin");
    } catch (error) {
      observed = error;
    }

    expect(observed).toBeInstanceOf(ApiClientError);
    expect(observed).toMatchObject({
      status: 404,
      code: "template_not_found",
      message: "template not found",
      details: { template_id: "missing" }
    });
  });
});
