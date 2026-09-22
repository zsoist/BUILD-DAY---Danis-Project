// Filtro de salida del proxy: lo último que ve una respuesta antes de salir.
//
// Una instrucción de sistema reduce la inyección pero no la elimina (medido:
// 5 de 18 ataques pasaban con el marco del servidor puesto). Lo que se cuela
// tiene forma reconocible —código, eco de nuestras instrucciones, HTML,
// enlaces— y una voz colombiana opinando nunca la tiene. Se bloquea por forma,
// con expresiones regulares y no con otro modelo: un juez LLM también se
// puede inyectar.
//
// Sesgo deliberado hacia dejar pasar: un filtro que calla voces reales es
// peor que uno que deja pasar algo raro. Por eso cada patrón exige una señal
// fuerte, no un carácter suelto.

const ECO = [
  /INSTRUCCI[ÓO]N DEL SERVIDOR/i,
  /tiene prioridad sobre todo lo anterior/i,
  /simulador de opini[óo]n p[úu]blica colombiana[.,]?\s*Responde/i,
  /\[FICHA DE LA PERSONA/i,
];

// "<" suelto es "menor que" en una opinión; solo cuenta si va pegado a una
// etiqueta que ejecuta o carga algo.
const HTML = /<\s*\/?\s*(script|img|iframe|svg|object|embed|style|link|meta|form|input|a\s+href)\b/i;

const MARKDOWN = /!\[[^\]]*\]\([^)]*\)|\[[^\]]+\]\(\s*https?:/i;
const URL = /\bhttps?:\/\/\S+/i;

const CODIGO = [
  /```/,
  /\bfunction\s*\w*\s*\([^)]*\)\s*\{/,
  /=>\s*\{/,
  /\bconsole\.log\s*\(/,
  // sin exigir inicio de línea: el ataque lo mete en mitad de una opinión.
  // "def" no es palabra del castellano, así que no roba voces.
  /\bdef\s+(\w+\s+)?\w+\s*\([^)]*\)\s*:/,
  /^\s*(import|from)\s+[\w.]+(\s+import\b|\s*;|\s*$)/m,
  /\b(SELECT|INSERT|UPDATE|DELETE)\b[\s\S]{1,80}\b(FROM|INTO|SET|WHERE)\b/,
  /#include\s*</,
];

// Varias líneas que terminan como código. Un ";" al final de una frase es
// raro pero posible; tres líneas seguidas así ya no es alguien hablando.
function pareceBloque(texto) {
  const lineas = texto.split("\n").map(l => l.trimEnd()).filter(Boolean);
  const cod = lineas.filter(l => /[;{}]$/.test(l) && !/^\{[^{}]{1,20}\}$/.test(l));
  return cod.length >= 3;
}

/**
 * @param {string} texto  lo que respondió el modelo
 * @param {{urls?: boolean}} opciones  urls:false bloquea enlaces (las voces no
 *   citan URLs; las noticias traen el medio entre paréntesis, tampoco URLs)
 * @returns {{ok: boolean, motivo: string|null}}
 */
export function revisarSalida(texto, opciones = {}) {
  const t = String(texto || "");
  if (ECO.some(r => r.test(t))) return { ok: false, motivo: "eco de instrucciones" };
  if (HTML.test(t)) return { ok: false, motivo: "html" };
  if (MARKDOWN.test(t)) return { ok: false, motivo: "enlace markdown" };
  if (opciones.urls === false && URL.test(t)) return { ok: false, motivo: "url" };
  if (CODIGO.some(r => r.test(t)) || pareceBloque(t)) return { ok: false, motivo: "código" };
  return { ok: true, motivo: null };
}

// Para la rama de noticias: los modelos con búsqueda web citan con enlaces
// markdown por costumbre. Ahí el enlace no es un ataque, es ruido; se deja el
// texto y se quita la URL, en vez de tirar la noticia entera.
export function limpiarEnlaces(texto) {
  return String(texto || "")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
    .replace(/\[([^\]]+)\]\(\s*https?:[^)]*\)/g, "$1")
    .replace(/\(?\bhttps?:\/\/\S+\)?/g, "")
    .replace(/[ \t]{2,}/g, " ");
}
