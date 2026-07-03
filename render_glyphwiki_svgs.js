#!/usr/bin/env node
/*
 * Render GlyphWiki KAGE data to SVG using an external kage-engine checkout.
 *
 * This file is project glue code. The kage-engine JavaScript files are loaded
 * from --engine-dir at build time and are not vendored in this repository.
 */

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ENGINE_FILES = [
  "2d.js",
  "buhin.js",
  "curve.js",
  "kage.js",
  "kagecd.js",
  "kagedf.js",
  "polygon.js",
  "polygons.js",
];

function parseArgs(argv) {
  const args = {
    force: false,
    checkExistingLimit: 0,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const item = argv[i];
    if (item === "--force") {
      args.force = true;
    } else if (item.startsWith("--")) {
      const key = item.slice(2).replace(/-([a-z])/g, (_match, char) => char.toUpperCase());
      if (i + 1 >= argv.length) {
        throw new Error(`Missing value for ${item}`);
      }
      args[key] = argv[i + 1];
      i += 1;
    } else {
      throw new Error(`Unknown argument: ${item}`);
    }
  }
  for (const key of ["engineDir", "data", "targets", "outDir"]) {
    if (!args[key]) {
      throw new Error(`Missing --${key.replace(/[A-Z]/g, (char) => `-${char.toLowerCase()}`)}`);
    }
  }
  args.checkExistingLimit = Number(args.checkExistingLimit || 0);
  return args;
}

function loadEngine(engineDir) {
  global.print = console.log;
  for (const file of ENGINE_FILES) {
    const scriptPath = path.join(engineDir, file);
    const code = fs.readFileSync(scriptPath, "utf8");
    vm.runInThisContext(code, { filename: scriptPath });
  }
}

function loadKageData(dataPath) {
  const kage = new Kage();
  const text = fs.readFileSync(dataPath, "utf8");
  for (const line of text.split(/\n/)) {
    if (!line) {
      continue;
    }
    const tab = line.indexOf("\t");
    if (tab <= 0) {
      continue;
    }
    kage.kBuhin.push(line.slice(0, tab), line.slice(tab + 1));
  }
  return kage;
}

function glyphPath(outDir, name) {
  const base = name.split("-", 1)[0];
  return path.join(outDir, base.slice(0, -3), base.slice(0, -2), `${name}.svg`);
}

function renderSvg(kage, name) {
  const polygons = new Polygons();
  kage.makeGlyph(polygons, name);
  return polygons.generateSVG(true);
}

function sha1(text) {
  return require("crypto").createHash("sha1").update(text).digest("hex");
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  loadEngine(args.engineDir);
  const kage = loadKageData(args.data);
  const targets = fs.readFileSync(args.targets, "utf8").split(/\n/).filter(Boolean);
  const checkRows = [];
  let checked = 0;
  let written = 0;
  let skipped = 0;
  let failures = 0;

  for (let i = 0; i < targets.length; i += 1) {
    const name = targets[i];
    const dest = glyphPath(args.outDir, name);
    const exists = fs.existsSync(dest);
    const shouldCheck = exists && args.checkExistingLimit !== 0
      && (args.checkExistingLimit < 0 || checked < args.checkExistingLimit);

    if (exists && !args.force && !shouldCheck) {
      skipped += 1;
      continue;
    }

    try {
      const svg = renderSvg(kage, name);
      if (shouldCheck) {
        const existing = fs.readFileSync(dest, "utf8");
        checkRows.push([
          name,
          svg === existing ? "byte_match" : "byte_different",
          sha1(svg),
          sha1(existing),
        ].join("\t"));
        checked += 1;
      }
      if (!exists || args.force) {
        fs.mkdirSync(path.dirname(dest), { recursive: true });
        fs.writeFileSync(dest, svg);
        written += 1;
      } else {
        skipped += 1;
      }
    } catch (error) {
      failures += 1;
      checkRows.push([name, "error", String(error && error.message ? error.message : error)].join("\t"));
    }

    const done = i + 1;
    if (done % 1000 === 0 || done === targets.length) {
      console.log(`  [${String(done).padStart(6)}/${targets.length}] written=${written} skipped=${skipped} checked=${checked} failures=${failures}`);
    }
  }

  if (args.checkReport) {
    fs.writeFileSync(args.checkReport, `name\tstatus\trendered_sha1\texisting_sha1\n${checkRows.join("\n")}${checkRows.length ? "\n" : ""}`);
  }
  if (failures) {
    process.exitCode = 1;
  }
}

main();
