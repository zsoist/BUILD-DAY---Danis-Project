// node --test scripts/experimento/anclas.test.mjs
// La mezcla del sitio se validó con las anclas y la T de postura.py. Si el
// servidor usara otras, el sitio mostraría un método que nadie midió.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const py = readFileSync(new URL("./postura.py", import.meta.url), "utf8");
const js = readFileSync(new URL("../../api/opina.js", import.meta.url), "utf8");
const html = readFileSync(new URL("../../web/index.html", import.meta.url), "utf8");
const lista = (src, desde) => [...src.slice(src.indexOf(desde)).split("]")[0].matchAll(/"([^"]+)"/g)].map(m => m[1]);

test("anclas del servidor = anclas medidas", () => {
  assert.deepEqual(lista(js, "const ANCLAS_SSR = ["), lista(py, "GENERICAS = ["));
});
test("T del servidor = T medida (0.25)", () => {
  assert.match(js, /const T_SSR = 0\.25;/);
  assert.match(py, /SSR_TEMP", "0\.25"/);
});
test("α del sitio = α elegido en calibración (0.75)", () => {
  assert.match(html, /const ALFA_MEZCLA=0\.75;/);
});
test("instrucción de estimar del servidor = la medida en calibracion.py", () => {
  const cal = readFileSync(new URL("./calibracion.py", import.meta.url), "utf8");
  const deCal = [...cal.slice(cal.indexOf("INSTR_ESTIMAR = (")).split(")\n")[0].matchAll(/"((?:[^"\\]|\\.)*)"/g)]
    .map(m => m[1]).join("").replace(/\\"/g, '"');
  const deJs = JSON.parse('"' + js.match(/const INSTR_ESTIMAR = "((?:[^"\\]|\\.)*)";/)[1] + '"');
  assert.equal(deJs, deCal);
});
