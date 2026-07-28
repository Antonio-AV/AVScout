import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("the initial page exposes the AVScout workspace", async () => {
  const page = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");

  assert.match(page, /AVScout/);
  assert.match(page, /Workspace initialized/);
});
