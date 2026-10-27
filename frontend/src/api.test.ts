import { describe, expect, it } from "vitest";
import { readError, UNREACHABLE_MESSAGE } from "./api";

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("readError", () => {
  it("backend 'detail' xabarini qaytaradi", async () => {
    expect(await readError(json(413, { detail: "Matn juda uzun: 51 belgi." }))).toBe("Matn juda uzun: 51 belgi.");
    expect(await readError(json(500, { detail: "Serverda ichki xato yuz berdi." }))).toBe("Serverda ichki xato yuz berdi.");
  });

  it("JSON bo'lmagan 5xx — backend o'chiq", async () => {
    expect(await readError(new Response("proxy error", { status: 500 }))).toBe(UNREACHABLE_MESSAGE);
    expect(await readError(new Response("", { status: 502 }))).toBe(UNREACHABLE_MESSAGE);
  });

  it("422 va boshqa holatlar uchun umumiy xabar", async () => {
    expect(await readError(json(422, { detail: [{ msg: "x" }] }))).toBe("So'rov noto'g'ri formatda.");
    expect(await readError(json(503, {}))).toBe("Serverda xato yuz berdi. Keyinroq urinib ko'ring.");
    expect(await readError(new Response("nope", { status: 404 }))).toBe("Server xatosi (404).");
  });
});
