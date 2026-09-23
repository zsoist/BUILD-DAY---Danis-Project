/* TERTULIA: ¿debatir mueve algo? ¿acerca o aleja de la realidad?
   Para las mismas voces y la misma pregunta corre dos condiciones de 3 vueltas:
     tertulia  cada voz ve las últimas 10 intervenciones de la mesa (como el sitio)
     monologo  cada voz solo ve SUS propias intervenciones previas ("sellado")
   El system y el user son los de conversar() en web/index.html, copiados
   textualmente; persona() se extrae del index.html vivo (como careo_ecp.mjs).
   Diferencias con el sitio, a propósito: 3 vueltas fijas (sin corte por acuerdo,
   estancamiento de Jev ni reloj), sin contexto de noticias (como el sondeo base),
   y sin el marco del proxy (como careo_ecp.mjs). Si falta la etiqueta, Jev la
   lee (clasificarPostura del sitio); se guarda de dónde salió cada postura.

   uso: node scripts/experimento/tertulia.mjs <items.json> <salida_dir> [ITEM1,ITEM2,...]
   env: MESAS=3 N=8 RONDAS=3 TOPE=1.8 (USD, corta si el gasto medido lo pasa) */
import { fileURLToPath } from "node:url";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const html = fs.readFileSync(path.join(ROOT, "web/index.html"), "utf8");
const script = html.slice(html.indexOf("<script>") + 8, html.lastIndexOf("</script>"));

function extraer(nombre) {
  const pats = [new RegExp(`\\nfunction ${nombre}\\s*\\(`), new RegExp(`\\nconst ${nombre}\\s*=`)];
  for (const [k, re] of pats.entries()) {
    const m = script.match(re);
    if (!m) continue;
    const i = m.index + 1;
    const desde = k === 0 ? script.indexOf("{", script.indexOf("(", i)) : i;
    let prof = 0, abierto = false, q = null, esc = false;
    for (let j = desde; j < script.length; j++) {
      const c = script[j];
      if (esc) { esc = false; continue; }
      if (q) { if (c === "\\") esc = true; else if (c === q) q = null; continue; }
      if (c === '"' || c === "'" || c === "`") { q = c; continue; }
      if ("{[(".includes(c)) { prof++; abierto = true; }
      else if ("}])".includes(c)) { prof--; if (k === 0 && prof === 0) return script.slice(i, j + 1); }
      else if (k === 1 && c === ";" && prof === 0 && abierto) return script.slice(i, j + 1);
      else if (k === 1 && c === "\n" && prof === 0 && abierto) return script.slice(i, j);
    }
  }
  throw new Error(`no encontré ${nombre}`);
}
const NOMBRES = ["TEMPERAMENTOS", "LEAN", "FRANQUEZA", "ARRANQUES", "estiloDe",
  "FUNDAMENTOS", "marcoDe", "GUSTOS", "FASTIDIOS", "momentoDe", "COMPROMISO_TXT",
  "LEAN_TXT", "leanLinea", "vida", "DIALECTOS", "dialectoDe", "ESTILOS_RESP", "estiloRespuesta",
  "persona"];
const mod = new Function("OPC", "LIBRETO", "ORDEN_CACHE",
  NOMBRES.map(extraer).join("\n") + "\nreturn {persona};")(null, true, true);
/* postura() del sitio, copiada: extraer() no la saca porque su regex trae una
   comilla que el contador de llaves toma por string. Se verifica abajo que
   siga idéntica al index.html. */
function postura(txt){
  const m=txt.match(/\[POSTURA:?\s*(a_favor|en_contra|depende|ni_ni)/i);
  let limpio=txt.replace(/\[POSTURA[^\]]*\]?/gi,"").trim();
  // si el modelo quedó cortado a mitad de frase, recortar a la última completa
  if(limpio.length>60&&!/[.!?…"»)]$/.test(limpio)){
    const corte=Math.max(limpio.lastIndexOf(". "),limpio.lastIndexOf("! "),
      limpio.lastIndexOf("? "),limpio.lastIndexOf("… "),limpio.lastIndexOf(".\n"));
    if(corte>limpio.length*0.35)limpio=limpio.slice(0,corte+1);
    else limpio+="…";   // sin dónde cortar: al menos cerrar con elipsis honesta
  }
  return [m?m[1].toLowerCase():null,limpio];
}
mod.postura = postura;
{ const src = postura.toString(), i = script.indexOf("\nfunction postura(");
  if (i < 0 || script.slice(i + 1, i + 1 + src.length) !== src) throw new Error("postura() cambió en el sitio: recópiala"); }

const RES = JSON.parse(fs.readFileSync(path.join(ROOT, "web/residents_v2.json"), "utf8"));
const residentes = (RES.residentes || RES).filter(r => r.edad >= 18);
const DOS = JSON.parse(fs.readFileSync(path.join(ROOT, "web/dossiers.json"), "utf8"));
const MARG = JSON.parse(fs.readFileSync(path.join(ROOT, "web/marginals.json"), "utf8")).departamentos;

const [ITEMS_F, SALIDA, FILTRO] = process.argv.slice(2);
const MESAS = Number(process.env.MESAS || 3), N = Number(process.env.N || 8);
const RONDAS = Number(process.env.RONDAS || 3), TOPE = Number(process.env.TOPE || 1.8);
let items = JSON.parse(fs.readFileSync(ITEMS_F, "utf8"));
if (FILTRO) { const f = FILTRO.split(","); items = f.map(c => items.find(x => x.item === c)).filter(Boolean); }
fs.mkdirSync(SALIDA, { recursive: true });

let seed = 20260922;
const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
/* muestraDe() del sitio (todo el país, proporcional a población), con semilla */
function muestraDe(n) {
  const pesos = Object.keys(MARG).map(c => [c, MARG[c]?.poblacion || 1]);
  const tot = pesos.reduce((a, [, w]) => a + w, 0);
  const out = [], usados = new Set();
  let guardia = 0;
  while (out.length < n && guardia++ < n * 200) {
    let x = rnd() * tot, cod = pesos[0][0];
    for (const [c, w] of pesos) { x -= w; if (x <= 0) { cod = c; break; } }
    const pool = residentes.filter(r => r.dpto === cod && !usados.has(r.id));
    if (pool.length) { const r = pool[Math.floor(rnd() * pool.length)]; usados.add(r.id); out.push(r); }
  }
  return out;
}

const env = Object.fromEntries(fs.readFileSync(path.join(ROOT, ".env"), "utf8")
  .split("\n").filter(l => l.includes("=") && !l.trim().startsWith("#"))
  .map(l => [l.slice(0, l.indexOf("=")).trim(), l.slice(l.indexOf("=") + 1).trim().replace(/^["']|["']$/g, "")]));
const KEY = env.OPENROUTER_API_KEY;
if (!KEY) { console.error("⛔ falta OPENROUTER_API_KEY"); process.exit(1); }

let GASTO = 0, LLAMADAS = 0, VACIAS = 0, CORTADO = false;
async function flash(messages, max_tokens = 140) {
  if (GASTO >= TOPE) { CORTADO = true; throw new Error("tope de gasto"); }
  for (let i = 0; i < 3; i++) {
    try {
      const r = await fetch("https://openrouter.ai/api/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${KEY}` },
        body: JSON.stringify({ model: "deepseek/deepseek-v4.1-flash", messages, max_tokens,
          temperature: 0.95, reasoning: { enabled: false }, usage: { include: true },
          provider: { order: ["deepinfra", "streamlake", "alibaba"], allow_fallbacks: true,
            require_parameters: true, data_collection: "deny" } }),
      });
      if (r.ok) {
        const j = await r.json();
        LLAMADAS++; GASTO += Number(j.usage?.cost || 0);
        const txt = j.choices?.[0]?.message?.content || "";
        if (txt.trim()) return txt;
        VACIAS++;
      }
    } catch (e) { /* reintenta */ }
    await new Promise(s => setTimeout(s, 1200 * (i + 1)));
  }
  return "";
}

/* clasificarPostura() del sitio: si la voz no cerró la etiqueta, Jev la lee.
   Mismo endpoint, modelo, estado y criterios que api/opina.js + index.html. */
const CRIT_POSTURA={
  a_favor:"apoya o se inclina claramente a favor",
  en_contra:"rechaza o se inclina claramente en contra",
  depende:"genuinamente dividida o condicionada: pone una condición explícita (si X entonces Y), o depende del diseño, del caso o de quien lo proponga",
  ni_ni:"indiferencia genuina: ni me va ni me viene — no le interesa el tema, no lo tiene en el radar, no ve diferencia entre las opciones o esquiva sin evaluar; SIN condición y SIN balance"
};
let JEV = 0;
async function clasificarPostura(q, txt) {
  if (typeof txt !== "string" || !txt.trim()) return null;
  try {
    const r = await fetch("https://openrouter.ai/api/alpha/decisions", {
      method: "POST", headers: { Authorization: `Bearer ${KEY}`, "Content-Type": "application/json" },
      body: JSON.stringify({ model: "typesafe/jev-1.13", state: `Pregunta: ${q}\nRespuesta: ${txt}`.slice(0, 8000),
        questions: { postura: { type: "choice", instructions: "Postura que expresa ESTA respuesta sobre el tema de la pregunta",
          criteria: CRIT_POSTURA } } }) });
    const j = await r.json();
    JEV++; GASTO += Number(j.usage?.cost || 0);
    const v = j.answers?.postura?.choice;
    return ["a_favor", "en_contra", "depende", "ni_ni"].includes(v) ? v : null;
  } catch (e) { return null; }
}

/* ── system y user de la tertulia: copiados de conversar() ── */
const SIS_TERTULIA = `
Tertulia de vecinos de varias partes del país. Habla CORTO como colombiano de verdad: máximo 2 frases, a veces UNA basta. Reacciona a lo dicho (cita por nombre, apoya o contradice con picardía), puedes cambiar de opinión si te convencieron. Nada de discursos. PROHIBIDO adoptar la anécdota de otro como propia: si alguien ya contó lo de la camiseta/aguinaldo, tú traes una vivencia DISTINTA de tu oficio y tu edad, con tus propios detalles (plata, barrio, familia, edad) que nadie más pueda firmar. PROHIBIDO repetir una metáfora o frase-lema que ya sonó 2 veces en la mesa — cámbiale el ángulo (otro oficio, otro año, otra ciudad) o cede el punto y pasa a OTRA arista del tema. Si la mesa lleva 2 vueltas dando vueltas a lo mismo, tu intervención abre una arista nueva (plata/familia/barrio/historia/futuro) y no vuelve a citar el ejemplo ajeno como si fuera tuyo. Cierra con [POSTURA: a_favor|en_contra|depende|ni_ni] — ni_ni SOLO si a tu personaje genuinamente le da igual el tema; a_favor significa SÍ A LA PREGUNTA LITERAL del tema, no a lo que digan las noticias.`;
function charlaDe(visibles) {
  return visibles.length ?
    "La mesa va así:\n" + visibles.slice(-10).map(t => `${t.n}: ${String(t.t).replace(/\[POSTURA:[^\]]*\]?/g, "").trim()}`).join("\n") +
    "\nPROHIBIDO arrancar tu frase como arrancó cualquiera de los anteriores, PROHIBIDO reciclar su anécdota, su muletilla o su lema, y PROHIBIDO reusar un ejemplo que ya salió en la mesa; suena a TI y traes material NUEVO de tu propio oficio y tu edad. Si el tema ya se agotó, abre OTRA arista (plata/familia/barrio/historia/futuro)." : "abres tú";
}
function userDe(q, r, charla, ronda, postDe, ROCES) {
  return `Tema: ${q}\n${charla}\nVUELTA ${ronda + 1}. TU ÚLTIMA POSTURA REGISTRADA: ${postDe[r.id] ? postDe[r.id].replace("_", " ") + " — si cambias de lado, DILO explícito ('me convencieron', 'ya no estoy tan seguro')" : "ninguna aún"}.${r.compromiso === "indiferente" ? " Si de verdad no tienes nada nuevo, puedes pasar corto ('yo paso, eso ya está dicho')." : ""}${ROCES[r.id] ? `\n${ROCES[r.id].quien} te contradijo hace un rato; si viene al caso, cóbraselo con nombre propio — sin pelear, como se hace entre vecinos.` : ""}\nTe toca, ${r.nombre.split(" ")[0]}. Cierra tu idea COMPLETA antes de la etiqueta — nada de frases a medias.`;
}

/* una mesa, una condición. sellado=true: cada voz solo ve lo suyo */
async function mesa(q, sample, sellado) {
  const postDe = {}, ROCES = {}, transcript = [], hist = {}, fuentes = { etiqueta: 0, jev: 0 };
  sample.forEach(r => hist[r.id] = []);
  const turno = async (r, ronda) => {
    const visibles = sellado ? transcript.filter(t => t.id === r.id) : transcript;
    const raw = await flash([
      { role: "system", content: mod.persona(r, DOS[r.dpto] || {}) + "" + SIS_TERTULIA },
      { role: "user", content: userDe(q, r, charlaDe(visibles), ronda, postDe, sellado ? {} : ROCES) }], 140);
    let [pos, txt] = mod.postura(raw || "");
    const fuente = pos ? "etiqueta" : "jev";
    if (!pos) pos = await clasificarPostura(q, txt);
    hist[r.id].push(pos);                    // null = ni etiqueta ni Jev
    fuentes[fuente]++;
    if (pos) postDe[r.id] = pos;
    const mio = r.nombre.split(" ")[0];
    if (!sellado) for (const otro of transcript) {
      if (otro.id === r.id || !txt.includes(otro.n)) continue;
      const pa = postDe[r.id], pb = postDe[otro.id];
      if (pa && pb && pa !== pb) ROCES[otro.id] = { quien: mio, tema: txt.slice(0, 70) };
    }
    return { id: r.id, n: mio, d: r.dpto_nombre, t: txt, ronda: ronda + 1, pos, fuente };
  };
  for (let ronda = 0; ronda < RONDAS; ronda++) {
    if (sellado) {
      // nadie ve a nadie: las voces de la vuelta son independientes, van en paralelo
      const outs = await Promise.all(sample.map(r => turno(r, ronda)));
      transcript.push(...outs);
    } else for (const r of sample) transcript.push(await turno(r, ronda));
  }
  return { hist, final: postDe, fuentes, transcript };
}

const trabajos = [];
for (const it of items) for (let m = 0; m < MESAS; m++)
  trabajos.push({ it, m, sample: muestraDe(N) });

const resultados = [];
const cola = [...trabajos];
await Promise.all(Array.from({ length: 8 }, async () => {
  while (cola.length) {
    const t = cola.shift();
    try {
      const [ter, mon] = await Promise.all([mesa(t.it.pregunta, t.sample, false), mesa(t.it.pregunta, t.sample, true)]);
      resultados.push({ item: t.it.item, pregunta: t.it.pregunta, verdad: Number(t.it.verdad), mesa: t.m,
        voces: t.sample.map(r => ({ id: r.id, nombre: r.nombre, edad: r.edad, dpto: r.dpto_nombre, compromiso: r.compromiso })),
        tertulia: ter, monologo: mon });
      process.stderr.write(`✓ ${t.it.item} mesa ${t.m + 1} · $${GASTO.toFixed(4)} · ${LLAMADAS} llamadas\n`);
    } catch (e) { process.stderr.write(`✗ ${t.it.item} mesa ${t.m + 1}: ${e.message}\n`); }
  }
}));
const f = path.join(SALIDA, "tertulia.json");
fs.writeFileSync(f, JSON.stringify({ modelo: "deepseek/deepseek-v4.1-flash", temperatura: 0.95,
  max_tokens: 140, rondas: RONDAS, n: N, mesas: MESAS, gasto_usd: GASTO, llamadas: LLAMADAS, llamadas_jev: JEV,
  vacias: VACIAS, cortado_por_tope: CORTADO, fecha: new Date().toISOString(), resultados }, null, 1));
console.error(`OK → ${f} · gasto medido $${GASTO.toFixed(4)} · ${LLAMADAS} llamadas · ${VACIAS} vacías${CORTADO ? " · ⚠ CORTADO POR TOPE" : ""}`);
