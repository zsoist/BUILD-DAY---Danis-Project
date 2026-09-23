/* ¿La estimación de analista acierta más si se le dice el departamento?
   Banco con verdad conocida por departamento: a quién votaron en 2022 y 2026
   (Registraduría, simcolombia/data/presidenciales.json). Para cada pregunta y
   departamento: estimación nacional (como hoy) y con {donde}. Contra el proxy
   local (node scripts/dev.mjs), que respeta el tope de 40 por minuto.

     node scripts/experimento/estimar_dpto.mjs > /tmp/estimar_dpto.json
*/
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const PRES = JSON.parse(fs.readFileSync(path.join(ROOT, "simcolombia/data/presidenciales.json"), "utf8"));
const MARG = JSON.parse(fs.readFileSync(path.join(ROOT, "web/marginals.json"), "utf8")).departamentos;
const URL = process.env.PROXY || "http://localhost:8377/api/opina/";
const DPTOS = (process.env.DPTOS || "70,05,11,52,23,08,68,27,76,15").split(",");
const BANCO = [
  ["Si usted votó en la segunda vuelta presidencial de 2022, ¿votó por Gustavo Petro?", "2022_2v", "GUSTAVO PETRO"],
  ["Si usted votó en la segunda vuelta presidencial de 2026, ¿votó por Iván Cepeda?", "2026_2v", "IVÁN CEPEDA CASTRO"],
  ["Si usted votó en la primera vuelta presidencial de 2022, ¿votó por Federico Gutiérrez?", "2022_1v", "FEDERICO GUTIÉRREZ"],
  ["Si usted votó en la primera vuelta presidencial de 2026, ¿votó por Abelardo de la Espriella?", "2026_1v", "ABELARDO DE LA ESPRIELLA"],
  ["Si usted votó en la primera vuelta presidencial de 2022, ¿votó por Rodolfo Hernández?", "2022_1v", "RODOLFO HERNÁNDEZ"],
];
const espera = ms => new Promise(s => setTimeout(s, ms));
async function estimar(pregunta, donde) {
  for (let i = 0; i < 3; i++) {
    const r = await fetch(URL, { method: "POST", headers: { "Content-Type": "application/json", Origin: "http://localhost:8377" },
      body: JSON.stringify({ estimar: true, pregunta, ...(donde ? { donde } : {}) }) });
    if (r.ok) return (await r.json()).pct;
    await espera(5000);
  }
  return null;
}
const filas = [];
const nacional = {};
for (const [q, eleccion, cand] of BANCO) {
  nacional[q] = await estimar(q, null); await espera(1600);   // la de hoy: una por pregunta
  for (const d of DPTOS) {
    const donde = MARG[d].nombre;
    const conDonde = await estimar(q, donde); await espera(1600);
    filas.push({ q, dpto: d, donde, verdad: PRES[eleccion][d]?.[cand] ?? null, nacional: nacional[q], con_donde: conDonde });
    process.stderr.write(".");
  }
}
const mae = (f, k) => { const v = f.filter(x => x[k] != null && x.verdad != null).map(x => Math.abs(x[k] - x.verdad)); return +(v.reduce((a, b) => a + b, 0) / v.length).toFixed(2); };
const suc = filas.filter(x => x.dpto === "70");
console.log(JSON.stringify({ filas, mae: { nacional: mae(filas, "nacional"), con_donde: mae(filas, "con_donde"),
  sucre_nacional: mae(suc, "nacional"), sucre_con_donde: mae(suc, "con_donde") } }, null, 1));
