import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

test("chat samples the existing interface selection on every text or audio turn", async () => {
  const bodies = [];
  const context = vm.createContext({
    document: { documentElement: {} },
    window: { localStorage: { setItem() {} }, dispatchEvent() {} },
    CustomEvent: class {},
    fetch: async (_url, request) => {
      bodies.push(JSON.parse(request.body));
      return { ok: true, status: 200, json: async () => ({ reply_text: "reply" }) };
    },
    setTimeout,
  });
  const i18n = readFileSync(new URL("../src/i18n.js", import.meta.url), "utf8").replaceAll("export function", "function");
  const chat = readFileSync(new URL("../src/api/chat.js", import.meta.url), "utf8")
    .replace('import { getLanguage } from "../i18n";', "")
    .replaceAll("import.meta.env", "({})")
    .replaceAll("export async function", "async function");
  vm.runInContext(i18n + "\n" + chat, context);
  for (const language of ["en", "es", "en"]) {
    vm.runInContext(`setLanguage("${language}")`, context);
    await vm.runInContext('sendChatRequest({user_text: "OK", ui_language: "wrong"})', context);
    await vm.runInContext('sendChatRequest({audio_base64: "YXVkaW8="})', context);
    assert.equal(bodies.at(-2).ui_language, language);
    assert.equal(bodies.at(-1).ui_language, language);
  }
});
