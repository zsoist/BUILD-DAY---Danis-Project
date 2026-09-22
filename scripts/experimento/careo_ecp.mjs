/* CAREO CONTRA HUMANOS REALES.
   Le hace a los residentes sintéticos la pregunta LITERAL de la Encuesta de
   Cultura Política del DANE y guarda sus respuestas en la misma escala 1-5.
   Después `careo_ecp.py` compara esa distribución contra la de los colombianos
   de verdad (ponderada con el factor de expansión oficial).

   Usa el prompt de producción extraído del index.html vivo. Solo DeepSeek. */
import { fileURLToPath } from "node:url";
import fs from "node:fs";
import path from "node:path";

// la raíz del repo, calculada: una ruta de disco quemada solo servía en una máquina
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
  "LEAN_TXT", "leanLinea", "vida", "DIALECTOS", "dialectoDe", "ESTILOS_RESP", "estiloRespuesta", "persona", "sondeoInstr", "INSTITUCIONES", "anclaDe", "anclaItemDe"];
/* LIBRETO=0: sin la postura asignada por hash. Es lo que decide si la
   dispersión es del método o fabricada por el prompt. Por defecto, la del sitio. */
const LIBRETO = (process.env.LIBRETO ?? "1") !== "0";
const mod = new Function("OPC", "LIBRETO", NOMBRES.map(extraer).join("\n") + "\nreturn {persona, sondeoInstr, anclaDe, anclaItemDe};")(null, LIBRETO);

const RES = JSON.parse(fs.readFileSync(path.join(ROOT, "web/residents_v2.json"), "utf8"));
const residentes = (RES.residentes || RES).filter(r => r.edad >= 18);   // universo ECP
const DOS = JSON.parse(fs.readFileSync(path.join(ROOT, "web/dossiers.json"), "utf8"));
const MARG = JSON.parse(fs.readFileSync(path.join(ROOT, "web/marginals.json"), "utf8")).departamentos;

let seed = 20260922;
const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
const N = Number(process.argv[2] || 200);
const CODIGO = process.argv[3] || "P5301";
const SALIDA = process.argv[4] || "/tmp/careo.json";

const cb = JSON.parse(fs.readFileSync(path.join(ROOT, "simcolombia/data/ecp2023_codebook.json"), "utf8"));
let pregunta = null;
(function buscar(o) {
  if (pregunta || !o || typeof o !== "object") return;
  if (Array.isArray(o)) return o.forEach(buscar);
  if (o.codigo === CODIGO) { pregunta = o; return; }
  Object.values(o).forEach(buscar);
})(cb);
// con PREGUNTA fijada, el código puede ser de otra fuente (LAPOP, Latinobarómetro)
if (!pregunta && process.env.PREGUNTA) pregunta = { texto_literal: process.env.PREGUNTA };
if (!pregunta) throw new Error(`no encontré ${CODIGO} en el codebook`);
const TEXTO = (pregunta.texto_literal || pregunta.etiqueta).trim();
console.error(`Pregunta ECP ${CODIGO}: ${TEXTO.slice(0, 120)}…`);
/* En modo libre la persona no debe ver opciones: el texto literal de la ECP
   trae la tarjeta pegada ("1 Si 2 No 99 No sabe"), y así "libre" no era libre.
   Se quita la numeración, el literal de la sub-pregunta y la cola de opciones. */
const TEXTO_LIBRE = process.env.PREGUNTA ? process.env.PREGUNTA : (() => {
  let s = TEXTO.replace(/^\d+\.\s*/, "")
               .replace(/:\s*[a-z]\.\s*Que\b/, " que")
               .replace(/:\s*[a-z]\.\s+/, ": ")
               .replace(/\s+1\s+S[ií]\s+2\s+No\b.*$/s, "");
  if (!s.startsWith("¿")) s = "¿" + s;
  if (!/\?\s*$/.test(s)) s += "?";
  return s.replace(/\?\?$/, "?");
})();

const muestra = [], usados = new Set();
const pesos = Object.keys(MARG).map(c => [c, MARG[c]?.poblacion || 1]);
const tot = pesos.reduce((a, [, w]) => a + w, 0);
let g = 0;
while (muestra.length < N && g++ < N * 400) {
  let x = rnd() * tot, cod = pesos[0][0];
  for (const [c, w] of pesos) { x -= w; if (x <= 0) { cod = c; break; } }
  const pool = residentes.filter(r => r.dpto === cod && !usados.has(r.id));
  if (pool.length) { const r = pool[Math.floor(rnd() * pool.length)]; usados.add(r.id); muestra.push(r); }
}

const env = Object.fromEntries(fs.readFileSync(path.join(ROOT, ".env"), "utf8")
  .split("\n").filter(l => l.includes("=") && !l.trim().startsWith("#"))
  .map(l => [l.slice(0, l.indexOf("=")).trim(), l.slice(l.indexOf("=") + 1).trim().replace(/^["']|["']$/g, "")]));
/* Dos flotas, un solo experimento. Para que la comparación signifique algo, lo
   ÚNICO que puede cambiar es el modelo: mismo prompt, misma muestra, misma
   semilla, mismo código de medición. Si escribiera un script aparte para GLM,
   cualquier diferencia podría venir del script y no del modelo.

     ENJAMBRE=deepseek  node careo_ecp.mjs ...   (por defecto)
     ENJAMBRE=glm       node careo_ecp.mjs ...

   GLM no deja apagar el razonamiento —devuelve 400 "Reasoning is mandatory"—
   pero con effort "low" no gasta un solo token de razonamiento. Medido. */
const FLOTA = (process.env.ENJAMBRE || "deepseek").toLowerCase();
/* "sitio": el mismo modelo y la misma ruta que usa producción (api/opina.js):
   DeepSeek por OpenRouter, razonamiento apagado. Es lo que hay que medir cuando
   la pregunta es "qué ve la gente en el sitio". */
const _MV = process.env.MODELO_VOZ || "deepseek/deepseek-v4.1-flash";
/* razonamiento por modelo (docs/OPENROUTER.md): DeepSeek se apaga, GLM no deja
   y va en "low"; al resto no se le manda, y entonces tampoco se exige que el
   proveedor lo soporte, o no habría a quién enrutar */
const _RZ = _MV.includes("glm") ? { effort: "low" } : _MV.includes("deepseek") ? { enabled: false } : null;
const MOTOR = FLOTA === "sitio"
  ? { modelo: _MV,
      url: "https://openrouter.ai/api/v1/chat/completions",
      key: env.OPENROUTER_API_KEY,
      extra: { ...(_RZ ? { reasoning: _RZ } : {}),
               provider: { require_parameters: !!_RZ, data_collection: "deny" } } }
  : FLOTA === "glm"
  ? { modelo: process.env.MODELO_VOZ || "z-ai/glm-5.3-flash",
      url: "https://openrouter.ai/api/v1/chat/completions",
      key: env.OPENROUTER_API_KEY,
      extra: { reasoning: { effort: "low" },
               /* sin esto el gateway puede enrutarte a un proveedor que
                  descarta en silencio los parámetros que pediste */
               provider: { require_parameters: true } } }
  : { modelo: process.env.MODELO_VOZ || "deepseek-flash",
      url: "https://api.deepseek.com/chat/completions",
      key: env.DEEPSEEK_API_KEY || env.DEEPSEEK_KEY,
      extra: { reasoning_effort: "none" } };
const TEMP = Number(process.env.TEMP_VOZ ?? 1.0);
if (!Number.isFinite(TEMP) || TEMP < 0 || TEMP > 2) {
  console.error(`⛔ TEMP_VOZ inválida: ${process.env.TEMP_VOZ}`); process.exit(1); }
const KEY = MOTOR.key;
if (!KEY) { console.error(`⛔ falta la llave para la flota "${FLOTA}"`); process.exit(1); }

let VACIAS = 0;
async function flash(messages, max_tokens = 120) {
  for (let i = 0; i < 3; i++) {
    try {
      const r = await fetch(MOTOR.url, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${KEY}` },
        body: JSON.stringify({ model: MOTOR.modelo, messages, max_tokens,
          /* TEMP_VOZ permite barrer temperaturas sin tocar el script: así el
             barrido usa EXACTAMENTE el mismo muestreo y las corridas se
             pueden comparar entre sí. */
          temperature: TEMP, ...MOTOR.extra }),
      });
      if (r.ok) {
        const txt = (await r.json()).choices?.[0]?.message?.content || "";
        if (txt.trim()) return txt;
        /* respuesta vacía: casi siempre el razonamiento se comió el presupuesto
           de salida. Se cuenta, porque es una diferencia real entre flotas. */
        VACIAS++;
      }
    } catch (e) { /* reintenta */ }
    await new Promise(s => setTimeout(s, 1200 * (i + 1)));
  }
  return "";
}

/* Dos modos.
   CATEGÓRICO: el encuestador lee la tarjeta y la persona escoge una de las cinco
   opciones. Es lo que hace todo el mundo — y arrastra los sesgos de formato
   (orden, etiqueta, atracción al punto medio) documentados en la literatura.
   CONTINUO: la persona NUNCA ve las cinco opciones. Da una intensidad de 0 a 100
   y la discretización la hace después el IRTree en Python, con umbrales propios
   de cada quien. Así el sesgo de formato desaparece por construcción. */
const MODO = (process.argv[5] || "categorico").toLowerCase();
const INSTR_CAT = "\nTe está encuestando el DANE en la puerta de tu casa. Contesta la pregunta "
  + "tal como te la leen, eligiendo UNA sola opción de la escala. Responde con el NÚMERO "
  + "y nada más (o 99 si de verdad no sabes). Sin explicaciones.";
const INSTR_CON = "\nTe está encuestando el DANE en la puerta de tu casa. IGNORA cualquier lista "
  + "de opciones numeradas que traiga la pregunta: aquí te lo preguntan con un termómetro. "
  + "Responde SOLO con un número entero de 0 a 100, donde 0 es lo más negativo que podrías "
  + "sentir sobre eso y 100 lo más positivo, y 50 es que te da exactamente igual. "
  + "Contesta con el número y nada más, sin explicaciones.";
/* MODO LIBRE — el insumo del método SSR (Semantic Similarity Rating).
   La persona no ve ninguna escala: habla como hablaría. La escala la reconstruye
   después Python, midiendo a qué punto de anclaje se parece semánticamente lo
   que dijo. La literatura de 2026 reporta que así la dispersión deja de
   colapsar, porque el modelo nunca tiene que elegir una casilla —y elegir
   casilla es justo donde se va a la más probable. */
const INSTR_LIB = "\nTe está encuestando el DANE en la puerta de tu casa. NO te dan opciones "
  + "ni números: te preguntan y tú contestas con tus propias palabras, en una o dos frases "
  + "cortas, como hablarías de verdad. Nada de listas, nada de cifras, nada de explicar que "
  + "eres un personaje. Solo lo que sientes al respecto.";
/* MODO SITIO — exactamente lo que ve la gente: la persona, la instrucción real
   del sondeo (extraída del sitio, no copiada) y la etiqueta [POSTURA: …] al
   final. Da a la vez el texto (para SSR) y la etiqueta (lo que cuenta hoy el
   sitio), de la MISMA voz: es lo que permite medir la mezcla de los dos. */
/* VARIANTE (solo modo sitio): para aislar de dónde sale un sesgo.
     sitio   la persona completa del sitio (por defecto)
     minima  solo datos demográficos, sin la maquinaria de personaje
     nula    "eres un colombiano adulto": lo que el modelo trae de fábrica
     podada  la persona del sitio con los reemplazos de PODA=<archivo.json>
             ([[texto, reemplazo], ...]) aplicados sobre el prompt final */
const VARIANTE = (process.env.VARIANTE || "sitio").toLowerCase();
const _ACTS = ["anclada", "anclada_min", "hermanas", "hermanas_min", "recuperada"].includes(VARIANTE)
  ? JSON.parse(fs.readFileSync(path.join(ROOT, "web/actitudes.json"), "utf8")) : { por_id: {}, hermanas: {} };
const ACT = _ACTS.por_id, HERM = _ACTS.hermanas || {};
/* recuperada: la voz del sitio + lo que su donante respondió a la pregunta de
   la ECP que encontró la búsqueda (ANCLA_ITEM). PREGUNTA reemplaza el texto que
   ve la voz: es lo que teclearía la persona en el sitio. */
const ANCLA_ITEM = process.env.ANCLA_ITEM || "";
/* RESP_FILE / BANCO_FILE: para LAPOP y Latinobarómetro, los archivos LOCALES de
   raw_v2/ (su licencia prohíbe publicarlos: nunca van a web/). */
const RESP = VARIANTE === "recuperada" && ANCLA_ITEM
  ? JSON.parse(fs.readFileSync(process.env.RESP_FILE || path.join(ROOT, "web/respuestas_ecp.json"), "utf8")) : null;
const BANCO_ECP = RESP ? JSON.parse(fs.readFileSync(process.env.BANCO_FILE || path.join(ROOT, "web/banco_ecp.json"), "utf8")) : [];
function anclaItemDe(r) {
  if (!RESP) return "";
  const k = RESP.items.indexOf(ANCLA_ITEM), b = BANCO_ECP.find(x => x.codigo === ANCLA_ITEM);
  if (k < 0 || !b) return "";
  return mod.anclaItemDe(b, (RESP.por_id[r.id] || [])[k]);   // la frase vive en el sitio
}
/* Las respuestas reales del donante a preguntas hermanas (mismas baterías de la
   ECP, disjuntas de las que se miden). Etiquetas fieles al cuestionario. */
const HERM_TXT = [
  ["en Colombia", "a todos los ciudadanos se les respeta el derecho a elegir y ser elegido"],
  ["en Colombia", "existe la libertad de expresar y difundir el pensamiento"],
  ["en Colombia", "se garantiza la libertad de conformar y pertenecer a partidos o movimientos políticos"],
  ["en Colombia", "se le facilita a los ciudadanos el acceso a la información pública"],
  ["en Colombia", "se protegen y garantizan los derechos a la recreación y la cultura"],
  ["en Colombia", "se protegen y garantizan los derechos de las minorías étnicas y sociales"],
  ["en Colombia", "se protegen y garantizan los derechos del campesinado"],
  ["para que un país sea democrático", "debe haber partidos o movimientos políticos"],
  ["para que un país sea democrático", "debe haber jueces, juzgados, tribunales y cortes"],
  ["para que un país sea democrático", "debe haber autoridades locales, municipales y departamentales"],
  ["para que un país sea democrático", "debe existir el derecho a elegir y ser elegido"],
];
function hermanasDe(v) {
  if (!Array.isArray(v)) return "";
  const si = [], no = [];
  v.forEach((x, i) => { if (x === 1) si.push(HERM_TXT[i]); else if (x === 2) no.push(HERM_TXT[i]); });
  const fr = l => l.map(([m, p]) => `${m}, ${p}`).join("; ");
  return "\nLO QUE LE RESPONDISTE AL DANE (es tuyo: una persona real como tú lo contestó así): " +
    (si.length ? "crees que SÍ: " + fr(si) + ". " : "") +
    (no.length ? "crees que NO: " + fr(no) + ". " : "") +
    "Tus demás respuestas salen de esa misma forma de ver el país.\n";
}
const CIERRE = "\nResponde la encuesta en 1-2 frases, como hablarías de verdad. Cierra SIEMPRE con " +
  "[POSTURA: a_favor|en_contra|depende|ni_ni]. a_favor significa SÍ a la pregunta literal.";
const PODA = process.env.PODA ? JSON.parse(fs.readFileSync(process.env.PODA, "utf8")) : [];
let PODA_APLICADA = 0;
function sistemaSitio(r) {
  if (VARIANTE === "nula") return "Eres un colombiano adulto." + CIERRE;
  if (VARIANTE.startsWith("minima") || VARIANTE.endsWith("_min")) {
    const zona = r.clase === "cabecera" ? "en la ciudad o el casco urbano" : "en zona rural";
    const ficha = `Eres ${r.nombre}, ${r.edad} años, ${r.sexo}, vives en ${r.dpto_nombre} ${zona}. ` +
      `Educación: ${r.educacion}. Oficio: ${r.ocupacion}.`;
    /* oraculo: SOLO diagnóstico, nunca para desplegar ni para evaluar métodos:
       le dice a la voz lo que su donante respondió a ESTA pregunta. Mide si el
       modelo es capaz siquiera de adoptar una postura dada. */
    if (VARIANTE === "oraculo_min") {
      const EV = JSON.parse(fs.readFileSync(path.join(ROOT, "scripts/experimento/donantes_eval.json"), "utf8"));
      const k = EV.items.indexOf(CODIGO), a = k >= 0 ? (EV.por_id[r.id] || [])[k] : null;
      const dijo = a === 1 ? "SÍ" : a === 2 ? "NO" : null;
      return ficha + (dijo ? `\nCuando el DANE te hizo exactamente esta pregunta, respondiste: ${dijo}. Esa es tu opinión.` : "") + CIERRE;
    }
    const extra = VARIANTE === "anclada_min" ? mod.anclaDe(ACT[r.id])
      : VARIANTE === "hermanas_min" ? mod.anclaDe(ACT[r.id]) + hermanasDe(HERM[r.id]) : "";
    return ficha + extra + CIERRE;
  }
  /* anclada: persona + la postura real de su donante de la ECP + instrucción */
  if (VARIANTE === "anclada")
    return mod.persona(r, DOS[r.dpto] || {}) + mod.anclaDe(ACT[r.id]) + mod.sondeoInstr(r);
  if (VARIANTE === "recuperada")
    return mod.persona(r, DOS[r.dpto] || {}) + anclaItemDe(r) + mod.sondeoInstr(r);
  if (VARIANTE === "hermanas")
    return mod.persona(r, DOS[r.dpto] || {}) + mod.anclaDe(ACT[r.id]) + hermanasDe(HERM[r.id]) + mod.sondeoInstr(r);
  let s = mod.persona(r, DOS[r.dpto] || {}) + mod.sondeoInstr(r);
  if (VARIANTE === "podada") for (const [de, a] of PODA) {
    if (s.includes(de)) { s = s.split(de).join(a); PODA_APLICADA++; }
  }
  return s;
}
const INSTR = MODO === "continuo" ? INSTR_CON : MODO === "libre" ? INSTR_LIB : MODO === "sitio" ? "" : INSTR_CAT;

const out = [];
const cola = [...muestra];
await Promise.all(Array.from({ length: 8 }, async () => {
  while (cola.length) {
    const r = cola.shift();
    const txt = await flash([
      { role: "system", content: MODO === "sitio" ? sistemaSitio(r) : mod.persona(r, DOS[r.dpto] || {}) + INSTR },
      { role: "user", content: MODO === "libre" ? TEXTO_LIBRE : MODO === "sitio"
          ? TEXTO_LIBRE + "\n\nRecuerda: cierra tu respuesta con la etiqueta [POSTURA: a_favor|en_contra|depende|ni_ni]."
          : TEXTO },
    ], MODO === "sitio" ? 170 : 120);   // 170: el presupuesto del sitio; con 120 la etiqueta final se corta
    let valor = null;
    if (MODO === "sitio") {
      /* la misma lectura que postura() en el sitio */
      const m = (txt || "").match(/\[POSTURA:?\s*(a_favor|en_contra|depende|ni_ni)/i);
      valor = m ? m[1].toLowerCase() : null;
    } else if (MODO === "libre") {
      /* sin número que extraer: el texto ES el dato */
      valor = null;
    } else if (MODO === "continuo") {
      const m = (txt || "").match(/\b(\d{1,3})\b/);
      const v = m ? Number(m[1]) : null;
      valor = v !== null && v >= 0 && v <= 100 ? v : null;
    } else {
      const m = (txt || "").match(/\b(99|[1-5])\b/);
      valor = m ? Number(m[1]) : null;
    }
    out.push({ id: r.id, edad: r.edad, sexo: r.sexo, dpto: r.dpto,
      educacion: r.educacion, clase: r.clase, modo: MODO,
      resp: valor,
      /* en modo libre el texto completo es el insumo, no un vistazo para depurar */
      crudo: (txt || "").replace(/\[POSTURA[^\]]*\]?/gi, "").trim().slice(0, ["libre", "sitio"].includes(MODO) ? 600 : 80) });
    process.stderr.write(".");
  }
}));
/* La flota queda grabada en el archivo: un resultado sin saber qué modelo lo
   produjo no se puede comparar con nada dentro de un mes. */
fs.writeFileSync(SALIDA, JSON.stringify({ codigo: CODIGO, pregunta: TEXTO, pregunta_libre: TEXTO_LIBRE, modo: MODO, n: out.length,
  flota: FLOTA, modelo: MOTOR.modelo, temperatura: TEMP, libreto: LIBRETO, variante: VARIANTE,
  poda_aplicada: PODA_APLICADA, vacias: VACIAS,
  fecha: new Date().toISOString(), respuestas: out }, null, 1));
console.error(`\nOK — ${out.length} respuestas de ${MOTOR.modelo} → ${SALIDA}`);
if (VACIAS) console.error(`   ⚠ ${VACIAS} respuesta(s) vacías reintentadas`);
