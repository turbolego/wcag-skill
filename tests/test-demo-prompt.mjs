import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const html = readFileSync(new URL("../docs/wcag-skill-demo.html", import.meta.url), "utf8");
const guide = readFileSync(new URL("../docs/wcag-skill-demo-prompt.md", import.meta.url), "utf8");
const defaultPrompt = html.match(/<textarea[^>]*>([\s\S]*?)<\/textarea>/)[1];
const prefix = "You are a frontend code generator. Return only a complete, standalone HTML document. Do not use external libraries or assets.";

function createDemo(fetch) {
  const nodes = new Map();
  const context = vm.createContext({
    fetch,
    DOMException,
    window: { addEventListener() {} },
    document: {
      querySelector(selector) {
        if (!nodes.has(selector)) {
          nodes.set(selector, {
            textContent: "",
            classList: { toggle() {} },
            addEventListener() {}
          });
        }
        return nodes.get(selector);
      }
    },
    setTimeout(callback) {
      queueMicrotask(callback);
      return 1;
    },
    clearTimeout() {}
  });
  const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
  const startup = /        loadModels\(\);\s*loadAxeVersions\(\);/;
  assert.match(script, startup);
  new vm.Script(script.replace(startup, "globalThis.demo = { fetchSkill, runSide };"), {
    filename: "wcag-skill-demo.html"
  }).runInContext(context);
  return context.demo;
}

test("both sides use identical settings and only Side A receives the complete demo guide", async () => {
  const requests = [];
  const signal = new AbortController().signal;
  const demo = createDemo(async (url, options) => {
    assert.equal(options.signal, signal);
    if (url === "./wcag-skill-demo-prompt.md") return new Response(guide);
    if (url.endsWith("/generate/text/async")) {
      requests.push(JSON.parse(options.body));
      return Response.json({ id: String(requests.length) });
    }
    assert.match(url, /\/generate\/text\/status\/\d+$/);
    return Response.json({ done: true, generations: [{ text: "<!doctype html><html lang='en'><title>Page</title><body>Page</body></html>" }] });
  });
  const fetchedGuide = await demo.fetchSkill(signal);
  assert.equal(fetchedGuide, guide);
  await Promise.all([
    demo.runSide("a", defaultPrompt, "community-model", fetchedGuide, 512, signal),
    demo.runSide("b", defaultPrompt, "community-model", "", 512, signal)
  ]);
  assert.equal(requests.length, 2);
  assert.equal(requests[0].prompt, `${prefix}\n\nApply the following wcag-skill instructions when creating the page:\n\n${guide}\n\nUser request:\n${defaultPrompt}`);
  assert.equal(requests[1].prompt, `${prefix}\n\nUser request:\n${defaultPrompt}`);
  assert.deepEqual(requests[0].models, requests[1].models);
  assert.deepEqual(requests[0].params, requests[1].params);
  assert.deepEqual(requests[0].params, {
    max_context_length: 2048,
    max_length: 512,
    temperature: 0.2,
    top_p: 0.9,
    rep_pen: 1.05
  });
  for (const request of requests) assert.equal(request.context_fit, "reject");
  assert.ok(Math.ceil(Array.from(requests[0].prompt).length / 3) + 512 <= 2048);
  assert.doesNotMatch(guide, /\[[^\]]+\]\([^)]+\)/);
});

test("an unavailable guide fails explicitly rather than using a partial skill", async () => {
  const demo = createDemo(async (url) => {
    assert.equal(url, "./wcag-skill-demo-prompt.md");
    return new Response("Not found", { status: 404 });
  });
  await assert.rejects(demo.fetchSkill(new AbortController().signal), /demo WCAG generation guide.*404/);
});

test("context rejection is reported without retrying with a truncated prompt", async () => {
  let submissions = 0;
  const demo = createDemo(async (url, options) => {
    assert.ok(url.endsWith("/generate/text/async"));
    const request = JSON.parse(options.body);
    assert.equal(request.context_fit, "reject");
    submissions += 1;
    return Response.json({ message: "Prompt does not fit the requested context", rc: "PromptExceedsContext" }, { status: 400 });
  });
  await assert.rejects(
    demo.runSide("a", "Long request", "community-model", guide, 512, new AbortController().signal),
    /AI Horde returned 400: Prompt does not fit/
  );
  assert.equal(submissions, 1);
});