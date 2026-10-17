"use strict";

// Tiny dependency-free test runner: register with test(), clean up with after().
// Each *.test.js file runs in its own node process (see run.js).

const path = require("path");

const EXT = path.resolve(__dirname, "..");
const tests = [];
const cleanups = [];
let scheduled = false;

function test(name, fn, { skip } = {}) {
  tests.push({ name, fn, skip });
  if (!scheduled) {
    scheduled = true;
    setImmediate(runAll);
  }
}

function after(fn) {
  cleanups.push(fn);
}

async function runAll() {
  let pass = 0;
  let fail = 0;
  let skipped = 0;
  for (const t of tests) {
    if (t.skip) {
      skipped++;
      console.log("skip " + t.name + " (" + t.skip + ")");
      continue;
    }
    try {
      await t.fn();
      pass++;
      console.log("ok   " + t.name);
    } catch (e) {
      fail++;
      console.log("FAIL " + t.name + "\n     " + String((e && e.message) || e).replace(/\n/g, "\n     "));
    }
  }
  for (const fn of cleanups) {
    try {
      await fn();
    } catch {
      /* best effort */
    }
  }
  console.log(pass + " passed, " + fail + " failed" + (skipped ? ", " + skipped + " skipped" : ""));
  process.exit(fail ? 1 : 0);
}

module.exports = { test, after, EXT };
