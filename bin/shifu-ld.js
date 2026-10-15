#!/usr/bin/env node
"use strict";

// Lanzador de `shifu-ld`: envuelve el instalador en Python del paquete (scripts/iniciar_proyecto.py).
// Sin dependencias. Uso:  npx github:ElShifuDeveloper/shifu-ld <proyecto> [opciones]

const { spawnSync } = require("child_process");
const { join } = require("path");

const raiz = join(__dirname, "..");
const script = join(raiz, "scripts", "iniciar_proyecto.py");

function pythonValido(cmd) {
  if (!cmd) return false;
  const r = spawnSync(cmd, ["--version"], { stdio: "ignore" });
  return !r.error && r.status === 0;
}

const candidatos = [process.env.PYTHON, "python3", "python"].filter(Boolean);
const python = candidatos.find(pythonValido);

if (!python) {
  console.error(
    "shifu-ld: no encontré Python 3 en el PATH.\n" +
      "  Instálalo desde https://www.python.org/downloads/ y vuelve a ejecutar el comando."
  );
  process.exit(127);
}

const r = spawnSync(python, [script, ...process.argv.slice(2)], { stdio: "inherit" });
process.exit(r.status === null ? 1 : r.status);