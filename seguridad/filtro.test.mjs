// node --test seguridad/filtro.test.mjs
// Los casos los escribió otro agente sin ver el filtro, a propósito: así
// prueban lo que el filtro DEBE hacer, no lo que el código ya hace.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { revisarSalida } from "../lib/filtro.mjs";

const { casos } = JSON.parse(readFileSync(new URL("./filtro_casos.json", import.meta.url)));

for (const c of casos) {
  test(`${c.id} ${c.bloquear ? "bloquea" : "deja pasar"}: ${c.por_que}`, () => {
    const r = revisarSalida(c.texto, { urls: false });
    assert.equal(!r.ok, c.bloquear, `motivo=${r.motivo} · texto=${c.texto.slice(0, 90)}`);
  });
}

test("la copia en api/opina.js coincide con lib/filtro.mjs", () => {
  const lib = readFileSync(new URL("../lib/filtro.mjs", import.meta.url), "utf8")
    .replace(/export function/g, "function").trim();
  const api = readFileSync(new URL("../api/opina.js", import.meta.url), "utf8");
  const m = api.match(/\/\/ ── filtro:inicio ──\n([\s\S]*?)\n\/\/ ── filtro:fin/);
  assert.ok(m, "no encuentro los marcadores filtro:inicio / filtro:fin en api/opina.js");
  assert.equal(m[1].trim(), lib, "api/opina.js tiene una copia vieja del filtro: vuelve a copiarla");
});
