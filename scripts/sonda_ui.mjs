// Sonda de UI: mide problemas reales del sitio en 3 tamaños y los deja en JSON,
// para que el enjambre busque causas sobre evidencia y no sobre suposiciones.
//   node scripts/sonda_ui.mjs [url] > sonda.json      (Playwright en el entorno)
// Mide: errores de consola, desborde horizontal, controles que se tapan entre sí,
// blancos táctiles < 32 px en teléfono, texto recortado, imágenes sin alt,
// botones sin nombre accesible, y cajones/modales que no caben en la pantalla.
import { chromium } from "playwright";

const URL = process.argv[2] || "http://localhost:8377/";
const TAM = { escritorio: [1440, 900, false], tableta: [768, 1024, true], telefono: [390, 844, true] };

function medir() {
  const vw = innerWidth, vh = innerHeight, out = [];
  const nombre = e => (e.id ? "#" + e.id : "") + (e.className && typeof e.className === "string" ? "." + e.className.trim().split(/\s+/).slice(0, 2).join(".") : "") || e.tagName.toLowerCase();
  const visible = e => { const s = getComputedStyle(e), r = e.getBoundingClientRect();
    return s.display !== "none" && s.visibility !== "hidden" && +s.opacity > .05 && r.width > 0 && r.height > 0; };
  const todos = [...document.querySelectorAll("body *")].filter(visible);
  for (const e of todos) {
    const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    if (s.position !== "fixed" && r.right > vw + 2 && !e.closest("#escena,#mundo,[style*=overflow]")) out.push({ tipo: "desborde_x", el: nombre(e), der: Math.round(r.right), vw });
    if ((s.overflow === "hidden" || s.textOverflow === "ellipsis") && e.scrollWidth > e.clientWidth + 2 && e.children.length === 0 && e.textContent.trim().length > 3)
      out.push({ tipo: "texto_recortado", el: nombre(e), texto: e.textContent.trim().slice(0, 50) });
  }
  const ctrls = todos.filter(e => e.matches("button,a[href],input,select,[role=button]"));
  for (const e of ctrls) {
    const r = e.getBoundingClientRect();
    if (matchMedia("(pointer:coarse)").matches && (r.width < 32 || r.height < 32) && r.width > 0) out.push({ tipo: "blanco_tactil_chico", el: nombre(e), w: Math.round(r.width), h: Math.round(r.height), texto: (e.textContent || e.getAttribute("aria-label") || "").trim().slice(0, 30) });
    const nom = (e.getAttribute("aria-label") || e.textContent || e.getAttribute("title") || e.getAttribute("placeholder") || "").trim();
    if (!nom && e.tagName !== "INPUT") out.push({ tipo: "sin_nombre_accesible", el: nombre(e) });
  }
  for (let i = 0; i < ctrls.length; i++) for (let j = i + 1; j < ctrls.length; j++) {
    const a = ctrls[i].getBoundingClientRect(), b = ctrls[j].getBoundingClientRect();
    if (ctrls[i].contains(ctrls[j]) || ctrls[j].contains(ctrls[i])) continue;
    const ix = Math.min(a.right, b.right) - Math.max(a.left, b.left), iy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
    if (ix > 4 && iy > 4) out.push({ tipo: "controles_encimados", a: nombre(ctrls[i]), b: nombre(ctrls[j]) });
  }
  for (const im of document.querySelectorAll("img")) if (!im.hasAttribute("alt")) out.push({ tipo: "img_sin_alt", el: nombre(im), src: im.getAttribute("src")?.slice(0, 40) });
  return out;
}
function cabe(sel) {
  const e = document.querySelector(sel); if (!e) return null;
  const r = e.getBoundingClientRect(), s = getComputedStyle(e);
  if (s.display === "none") return { sel, estado: "oculto" };
  return { sel, izq: Math.round(r.left), der: Math.round(r.right), arriba: Math.round(r.top), abajo: Math.round(r.bottom), vw: innerWidth, vh: innerHeight,
    cabe: r.left >= -1 && r.top >= -1 && r.right <= innerWidth + 1 && r.bottom <= innerHeight + 1 };
}

const navegador = await chromium.launch();
const res = {};
for (const [k, [w, h, movil]] of Object.entries(TAM)) {
  const ctx = await navegador.newContext({ viewport: { width: w, height: h }, isMobile: movil, hasTouch: movil, deviceScaleFactor: movil ? 2 : 1 });
  const p = await ctx.newPage(), consola = [];
  p.on("console", m => m.type() === "error" && consola.push(m.text().slice(0, 160)));
  p.on("pageerror", e => consola.push("pageerror: " + e.message.slice(0, 160)));
  await p.goto(URL); await p.waitForTimeout(5000);
  const r = { consola, inicio: await p.evaluate(medir), cajones: {} };
  // cada cajón y el modal de población, abiertos uno a uno
  for (const [nom, abrir, sel] of [["mapa", "[data-cajon=dr-mapa]", "#dr-mapa"], ["censo", "[data-cajon=dr-censo]", "#dr-censo"],
    ["tierra", "[data-cajon=ficha]", "#ficha"]]) {
    await p.click(abrir).catch(() => {}); await p.waitForTimeout(900);
    r.cajones[nom] = { caja: await p.evaluate(cabe, sel), problemas: (await p.evaluate(medir)).filter(x => x.tipo !== "controles_encimados").slice(0, 25) };
    await p.keyboard.press("Escape"); await p.evaluate(() => document.querySelectorAll(".cajon .cierra").forEach(b => b.offsetParent && b.click())); await p.waitForTimeout(500);
  }
  const pob = await p.$("text=Población");
  if (pob) { await pob.click().catch(() => {}); await p.waitForTimeout(900);
    r.cajones.poblacion = { caja: await p.evaluate(cabe, "#pobcard"), problemas: (await p.evaluate(medir)).filter(x => x.tipo !== "controles_encimados").slice(0, 25) };
    await p.keyboard.press("Escape"); await p.waitForTimeout(400); }
  for (const m of ["pais", "sondeo"]) {
    await p.click(`#modo [data-m=${m}]`).catch(() => {}); await p.waitForTimeout(1500);
    r["modo_" + m] = (await p.evaluate(medir)).slice(0, 25);
  }
  res[k] = r;
  await ctx.close();
}
await navegador.close();
console.log(JSON.stringify(res, null, 1));
