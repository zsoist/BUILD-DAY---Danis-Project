/* ESCENA — el escenario HD-2D de ColombIA ¡Que Piensa!
   Fondo: un diorama pixel de un lugar real (web/escenas/*.webp), en capas CSS
   con fundido. Encima, Three.js con la gente: sprites pixel (web/gente/*.webp)
   de pie en un piso 3D, siempre de frente a la cámara, con sombra.
   El sitio le habla con window.ESC(metodo, ...args); si este módulo aún no
   cargó, las llamadas esperan en ESC_Q. Nada de aquí decide qué dice nadie:
   solo muestra lo que la lógica del sitio (medida) ya produjo. */
import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js";

const $ = s => document.querySelector(s);
const QUIETO = matchMedia("(prefers-reduced-motion: reduce)").matches;
const LUGARES = {
  nacional: ["Plaza de Bolívar", "Bogotá", "#fff4e4"], bogota: ["La Candelaria", "Bogotá", "#fff1dc"],
  caribe: ["Ciudad amurallada", "Cartagena", "#ffe4c8"], sanandres: ["San Andrés", "Mar de siete colores", "#fffbe8"],
  guajira: ["Alta Guajira", "La Guajira", "#fff0cf"], medellin: ["Comuna 13", "Medellín", "#fff4e6"],
  cafetero: ["Salento", "Eje cafetero", "#fffaf0"], cali: ["Bulevar del río", "Cali", "#ffe6c4"],
  choco: ["Río Atrato", "Quibdó", "#f2f2e4"], narino: ["Las Lajas", "Nariño", "#eef0f2"],
  popayan: ["La ciudad blanca", "Popayán", "#fff8ee"], boyaca: ["Villa de Leyva", "Boyacá", "#fff6e8"],
  santander: ["Barichara", "Santander", "#ffeed8"], llanos: ["Los Llanos", "Meta y Casanare", "#ffdcb8"],
  amazonia: ["Leticia", "Amazonas", "#fff1d6"], tatacoa: ["Desierto de la Tatacoa", "Huila", "#d9d8ff"],
  estudio: ["¿Qué dicen los colombianos?", "estudio de televisión", "#ffffff"],
};
/* dónde está el piso pintado de cada fondo (fracción desde arriba) y qué tan
   grande se ve la gente ahí: medido a ojo sobre cada imagen */
const PISO = { nacional: [.80, 1.0], bogota: [.87, .9], caribe: [.85, .95], sanandres: [.86, .95], guajira: [.84, 1.0],
  medellin: [.88, .9], cafetero: [.89, .92], cali: [.86, .95], choco: [.89, .95], narino: [.86, .9], popayan: [.87, .92],
  boyaca: [.85, .95], santander: [.87, .9], llanos: [.86, 1.0], amazonia: [.87, .95], tatacoa: [.87, .95], estudio: [.79, .88] };
const DPTO_LUGAR = { "11": "bogota", "05": "medellin", "13": "caribe", "08": "caribe", "47": "caribe", "20": "caribe",
  "23": "caribe", "70": "caribe", "88": "sanandres", "44": "guajira", "17": "cafetero", "63": "cafetero", "66": "cafetero",
  "76": "cali", "27": "choco", "52": "narino", "19": "popayan", "15": "boyaca", "25": "boyaca", "68": "santander",
  "54": "santander", "50": "llanos", "85": "llanos", "81": "llanos", "99": "llanos", "91": "amazonia", "97": "amazonia",
  "95": "amazonia", "86": "amazonia", "18": "amazonia", "94": "amazonia", "41": "tatacoa", "73": "tatacoa" };
const COLOR = { a_favor: "#2fd08a", en_contra: "#ff5a5f", depende: "#fcd116", ni_ni: "#9aa3b8", sin_postura: "#9aa3b8" };
const ICONO = { a_favor: "▲", en_contra: "▼", depende: "◆", ni_ni: "○", sin_postura: "…" };

/* ── montaje ─────────────────────────────────────────────────────────── */
const host = $("#escena");
const capaFondo = [host.querySelector(".fondo.a"), host.querySelector(".fondo.b")];
const over = host.querySelector("#esc-capa");
const canvas = host.querySelector("#esc3d");
const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: false, powerPreference: "high-performance", preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
const scene = new THREE.Scene();
const camara = new THREE.PerspectiveCamera(27, 16 / 9, 0.1, 100);
const CAM_BASE = new THREE.Vector3(0, 3.1, 12.5), MIRA_BASE = new THREE.Vector3(0, 1.15, 0);
camara.position.copy(CAM_BASE);
const mira = MIRA_BASE.clone(), camObj = CAM_BASE.clone(), miraObj = MIRA_BASE.clone();
let tinte = new THREE.Color("#ffffff");

const cargador = new THREE.TextureLoader();
const TEX = new Map();
function textura(url) {
  if (!TEX.has(url)) TEX.set(url, new Promise(res => cargador.load(url, t => {
    t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.generateMipmaps = false;
    t.colorSpace = THREE.SRGBColorSpace; res(t);
  }, undefined, () => res(null))));
  return TEX.get(url);
}
/* sombra: elipse suave pintada una vez */
const sombraTex = (() => {
  const c = document.createElement("canvas"); c.width = 64; c.height = 32;
  const g = c.getContext("2d"), gr = g.createRadialGradient(32, 16, 2, 32, 16, 30);
  gr.addColorStop(0, "rgba(8,6,16,.85)"); gr.addColorStop(.45, "rgba(8,6,16,.45)"); gr.addColorStop(1, "rgba(8,6,16,0)");
  g.fillStyle = gr; g.fillRect(0, 0, 64, 32);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
})();

/* motas de polvo en la luz: lo que hace que un diorama se sienta con aire */
const polvo = (() => {
  const n = 90, pos = new Float32Array(n * 3), fase = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    pos[i * 3] = (Math.random() - .5) * 16; pos[i * 3 + 1] = Math.random() * 5; pos[i * 3 + 2] = (Math.random() - .5) * 8;
    fase[i] = Math.random() * 6.28;
  }
  const geo = new THREE.BufferGeometry(); geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  const m = new THREE.PointsMaterial({ color: 0xfff1c4, size: 0.035, transparent: true, opacity: .55, depthWrite: false });
  const p = new THREE.Points(geo, m); p.userData.fase = fase; scene.add(p); return p;
})();

const charco = (() => {
  const c = document.createElement("canvas"); c.width = c.height = 128;
  const g = c.getContext("2d"), gr = g.createRadialGradient(64, 64, 4, 64, 64, 64);
  gr.addColorStop(0, "rgba(255,226,170,.55)"); gr.addColorStop(1, "rgba(255,226,170,0)");
  g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
  const t = new THREE.CanvasTexture(c);
  const m = new THREE.Mesh(new THREE.PlaneGeometry(11, 4.5),
    new THREE.MeshBasicMaterial({ map: t, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: .5 }));
  m.rotation.x = -Math.PI / 2; m.position.set(0, .005, -.2); scene.add(m); return m;
})();
/* ── gente ───────────────────────────────────────────────────────────── */
const GENTE = new Map();          // id → actor
let JUEZ = null, MESA = null;
let ALTO = 1.45;                 // metros de escena por persona (lo ajusta cada lugar)

/* cuadros=4: tira de poses (quieto, paso izq, paso der, mano arriba) */
async function actor(id, url, alto = ALTO, cuadros = 1, estatico = false) {
  let tex = await textura(url);
  if (tex && cuadros > 1) { tex = tex.clone(); tex.repeat.set(1 / cuadros, 1); tex.needsUpdate = true; }
  const g = new THREE.Group();
  const asp = tex ? tex.image.width / cuadros / tex.image.height : 0.4;
  const mat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, alphaTest: 0.5, color: tinte.clone() });
  const cuerpo = new THREE.Mesh(new THREE.PlaneGeometry(alto * asp, alto), mat);
  cuerpo.position.y = alto / 2;
  const som = new THREE.Mesh(new THREE.PlaneGeometry(Math.max(alto * asp * 1.1, alto * .42), alto * 0.2),
    new THREE.MeshBasicMaterial({ map: sombraTex, transparent: true, depthWrite: false }));
  som.rotation.x = -Math.PI / 2; som.position.y = 0.01;
  g.add(som, cuerpo);
  g.userData = { id, cuerpo, alto, fase: Math.random() * 6.28, meta: null, vel: 2.6, habla: 0, llega: null,
    cuadros, estatico, mano: 0, cuadro: 0 };
  scene.add(g);
  return g;
}
function quitarTodos() {
  for (const a of GENTE.values()) scene.remove(a);
  GENTE.clear();
  if (JUEZ) { scene.remove(JUEZ); JUEZ = null; }
  if (MESA) { scene.remove(MESA); MESA = null; }
  over.querySelectorAll(".globo,.marca,.cartel,.tablero,.juezdice").forEach(e => e.remove());
}

/* la mesa y las cosas de cada región (web/gente/catalogo.json, "utileria") */
const UTIL_DE = { nacional: "bogota", bogota: "bogota", medellin: "antioquia", caribe: "caribe", sanandres: "insular_guajira",
  guajira: "insular_guajira", cafetero: "cafetero", tatacoa: "cafetero", cali: "pacifico", choco: "pacifico", narino: "sur_andino",
  popayan: "sur_andino", boyaca: "boyaca", santander: "santander", llanos: "llanos", amazonia: "amazonia" };
function utileriaDe(k) { return window.CATALOGO?.utileria?.[UTIL_DE[k]] || null; }
const COSAS = [[-4.7, -1.7], [4.9, -2.0], [-5.8, 0.7], [5.9, 0.5]];
/* acomodos: dónde se para cada quien */
function puestos(n, modo) {
  const P = [];
  if (modo === "mesa") {
    // media luna detrás de la mesa, de frente a la cámara; si son muchos, segunda fila
    const f1 = Math.min(n, 8);
    for (let i = 0; i < f1; i++) {
      const t = f1 === 1 ? .5 : i / (f1 - 1), a = Math.PI * (1.08 - 1.16 * t);
      P.push([Math.cos(a) * 3.1, -0.2 - Math.sin(a) * 1.05]);
    }
    for (let i = 0; i < n - f1; i++) {
      const m = n - f1, t = m === 1 ? .5 : i / (m - 1);
      P.push([-4.6 + 9.2 * t, -2.6 - (i % 2) * .35]);
    }
  } else if (modo === "publico") {
    // el show: hasta 5 concursantes detrás de su podio; el resto, de pie al
    // fondo de la tarima; el presentador adelante a la izquierda
    const k = Math.min(5, n);
    for (let i = 0; i < k; i++) P.push([(i - (k - 1) / 2) * 1.35 + .5, .15, true]);
    const resto = n - k, porFila = 8;
    for (let i = 0; i < resto; i++) {
      const fila = Math.floor(i / porFila), col = i % porFila, enFila = Math.min(porFila, resto - fila * porFila);
      P.push([(col - (enFila - 1) / 2) * 1.0 + .5 + (fila % 2) * .45, -1.9 - fila * 1.0]);
    }
  } else {
    // de pie, en fila suelta (modo país)
    for (let i = 0; i < n; i++) P.push([(i - (n - 1) / 2) * 1.55, 0.4 + (i % 2) * .25]);
  }
  return P;
}

/* ── globos y marcas en HTML, anclados a la cabeza ─────────────────────── */
function aPantalla(v) {
  const p = v.clone().project(camara), r = canvas.getBoundingClientRect();
  return { x: (p.x * .5 + .5) * r.width, y: (-p.y * .5 + .5) * r.height, z: p.z };
}
function cabeza(a) { return new THREE.Vector3(a.position.x, a.userData.alto * 1.02, a.position.z); }
function pegar(el, a, dy = 0) {
  el.userData = a;
  el.dataset.dy = dy;
  over.append(el);
}
function seguir() {
  const W = canvas.clientWidth;
  for (const el of over.querySelectorAll("[data-dy]")) {
    const a = el.userData; if (!a || !a.parent) { el.remove(); continue; }
    const p = aPantalla(cabeza(a));
    el.style.transform = `translate(${Math.round(p.x)}px,${Math.round(p.y - (+el.dataset.dy || 0))}px)`;
    const gv = el.firstElementChild;
    if (gv && el.classList.contains("globo")) {
      const w = gv.offsetWidth, m = 12;
      const dx = Math.max(m - (p.x - w / 2), Math.min(0, W - m - (p.x + w / 2)));
      gv.style.setProperty("--dx", Math.round(dx) + "px");
    }
  }
}

function globo(a, nombre, txt, pos) {
  over.querySelectorAll(".globo").forEach(g => g.classList.add("sale"));
  setTimeout(() => over.querySelectorAll(".globo.sale").forEach(g => g.remove()), 260);
  const el = document.createElement("div");
  el.className = "globo";
  el.style.setProperty("--pc", COLOR[pos] || "#f4ecd8");
  el.innerHTML = `<div class="gv"><b></b><p></p></div>`;
  el.querySelector("b").textContent = nombre;
  pegar(el, a, 14);
  const p = el.querySelector("p"), corto = txt.length > 170 ? txt.slice(0, 167).replace(/\s+\S*$/, "") + "…" : txt;
  if (QUIETO) { p.textContent = corto; return; }
  let i = 0; const paso = Math.max(1, Math.round(corto.length / 55));
  const iv = setInterval(() => { i += paso; p.textContent = corto.slice(0, i); if (i >= corto.length) clearInterval(iv); }, 26);
}
function marca(a, pos) {
  a.userData.marca?.remove();
  const el = document.createElement("div");
  el.className = "marca"; el.textContent = ICONO[pos] || "…";
  el.style.setProperty("--pc", COLOR[pos] || "#9aa3b8");
  el.title = { a_favor: "a favor", en_contra: "en contra", depende: "depende", ni_ni: "ni fu ni fa" }[pos] || "";
  pegar(el, a, -4);
  a.userData.marca = el;
}
function piensa(a) {
  a.userData.marca?.remove();
  const el = document.createElement("div");
  el.className = "marca piensa"; el.textContent = "···";
  pegar(el, a, -4);
  a.userData.marca = el;
}

let pisoY = .82;
function encuadrar() {
  /* el fondo va "cover" y pegado abajo: el piso pintado a fracción f de la
     imagen cae en pantalla donde lo dice el recorte real de este visor */
  const r = host.getBoundingClientRect(), W = r.width || 16, H = r.height || 9;
  const imgH = Math.max(H, W * 768 / 1376), yPx = H - (1 - pisoY) * imgH;
  const objetivo = 1 - 2 * Math.min(.94, Math.max(.45, yPx / H)), p = new THREE.Vector3(0, 0, -.3);
  let lo = -6, hi = 8;
  for (let i = 0; i < 28; i++) {
    const m = (lo + hi) / 2;
    camara.position.copy(CAM_BASE); camara.lookAt(0, m, 0); camara.updateMatrixWorld();
    const y = p.clone().project(camara).y;
    if (y > objetivo) lo = m; else hi = m;          // mirar más arriba baja el piso en pantalla
  }
  MIRA_BASE.y = (lo + hi) / 2;
  miraObj.copy(MIRA_BASE); mira.copy(MIRA_BASE);
}
/* un punto de la imagen de fondo (fracciones) → píxeles del visor, con el mismo
   recorte "cover" pegado abajo que hace el CSS */
function imgAPantalla(fx, fy) {
  const r = host.getBoundingClientRect(), W = r.width, H = r.height;
  const k = Math.max(W / 1376, H / 768), iw = 1376 * k, ih = 768 * k;
  return { x: (W - iw) / 2 + fx * iw, y: H - ih + fy * ih };
}
const CARA_TABLERO = [.196, .228, .496, .497];     // la cara del tablero pintado en estudio.webp
function ubicarTablero() {
  const t = over.querySelector(".tablero"); if (!t) return;
  const a = imgAPantalla(CARA_TABLERO[0], CARA_TABLERO[1]), b = imgAPantalla(CARA_TABLERO[2], CARA_TABLERO[3]);
  const w = b.x - a.x, h = b.y - a.y;
  const cabe = lugarActual === "estudio" && w >= 300 && a.x > 0;
  t.classList.toggle("empotrado", cabe);
  if (cabe) Object.assign(t.style, { left: a.x + "px", top: a.y + "px", width: w + "px", height: h + "px", fontSize: Math.max(10, Math.min(16, h / 12)) + "px" });
  else Object.assign(t.style, { left: "", top: "", width: "", height: "", fontSize: "" });
}
/* ── lugar ───────────────────────────────────────────────────────────── */
let lugarActual = null, capa = 0;
function lugar(k) {
  if (!LUGARES[k]) k = "nacional";
  if (k === lugarActual) return;
  lugarActual = k;
  const siguiente = capaFondo[1 - capa];
  const img = new Image();
  img.onload = () => {
    siguiente.style.backgroundImage = `url(escenas/${k}.webp)`;
    siguiente.classList.add("on"); capaFondo[capa].classList.remove("on"); capa = 1 - capa;
  };
  img.src = `escenas/${k}.webp`;
  const [nom, sub, t] = LUGARES[k];
  const [fy, esc] = PISO[k] || [.84, 1]; pisoY = fy; ALTO = 1.45 * esc; encuadrar();
  tinte = new THREE.Color(t);
  for (const a of [...GENTE.values(), JUEZ, MESA]) a?.userData.cuerpo?.material.color.copy(tinte);
  const pl = $("#lugar");
  if (pl) { pl.querySelector("b").textContent = nom; pl.querySelector("span").textContent = sub;
    pl.classList.remove("entra"); void pl.offsetWidth; pl.classList.add("entra"); }
}

/* ── API que usa el sitio ────────────────────────────────────────────── */
const API = {
  lugarDe(sel) {
    const c = [...(sel || [])];
    return c.length === 1 ? (DPTO_LUGAR[c[0]] || "nacional") : "nacional";
  },
  lugar,
  async escena({ modo, lugar: k, sel, gente }) {
    quitarTodos();
    lugar(k || (modo === "sondeo" ? "estudio" : API.lugarDe(sel)));
    camObj.copy(CAM_BASE); miraObj.copy(MIRA_BASE);
    const acomodo = modo === "sondeo" ? "publico" : modo === "pais" ? "pie" : "mesa";
    const U = utileriaDe(lugarActual);
    if (acomodo === "mesa") {
      MESA = await actor("mesa", "escenas/" + (U?.mesa || "mesa.webp"), ALTO * .72, 1, true);
      MESA.position.set(0, 0, 0.55);
    }
    if (U && acomodo !== "publico") {           // ambiente: hasta 3 cosas del lugar, a los lados
      const cosas = U.cosas.slice(0, 3);
      await Promise.all(cosas.map(async (c, i) => {
        const a = await actor("cosa" + i, "escenas/" + c, ALTO * (i === 2 ? .7 : .85), 1, true);
        a.position.set(COSAS[i][0], 0, COSAS[i][1]);
        GENTE.set("__cosa" + i, a);
      }));
    }
    const P = puestos(gente.length, acomodo);
    if (acomodo === "publico") {
      JUEZ = await actor("juez", "gente/urbano_7_poses.webp", ALTO * 1.1, 4);
      JUEZ.position.set(-3.35, 0, 1.15);
      // un podio delante de cada concursante: tapa de verdad (profundidad)
      await Promise.all(P.filter(p => p[2]).map(async ([x, z], i) => {
        const podio = await actor("podio" + i, "escenas/podio.webp", ALTO * .6, 1, true);
        podio.position.set(x, 0, z + .42);
        podio.children[0].visible = false;          // el podio no lleva sombra de persona
        GENTE.set("__podio" + i, podio);
      }));
    }
    await Promise.all(gente.map(async (r, i) => {
      const a = await actor(r.id, "gente/" + (r._spr || window.spriteDe?.(r) || "andino_0") + "_poses.webp",
        ALTO * (.97 + (r.edad > 64 ? -.04 : 0) + (r.sexo === "mujer" ? -.03 : 0)), 4);
      const [x, z] = P[i];
      a.userData.meta = new THREE.Vector3(x, 0, z);
      const lado = x < 0 ? -1 : 1;
      if (QUIETO) a.position.set(x, 0, z);
      else { a.position.set(lado * (8.5 + Math.random() * 2), 0, z + .6); a.userData.llega = performance.now() + i * 170; }
      GENTE.set(r.id, a);
    }));
  },
  piensa(r) { const a = GENTE.get(r.id); if (a) piensa(a); },
  habla(r, txt, pos) {
    const a = GENTE.get(r.id); if (!a) return;
    a.userData.habla = performance.now() + Math.min(4200, 900 + txt.length * 22);
    a.userData.mano = performance.now() + 1500;          // pide la palabra
    globo(a, `${r.nombre.split(" ")[0]} · ${r.edad}`, txt, pos);
    marca(a, pos);
    if (!QUIETO) {                // la cámara se acerca un poco a quien habla
      camObj.set(CAM_BASE.x + a.position.x * .32, CAM_BASE.y - .15, CAM_BASE.z - 1.6);
      miraObj.set(a.position.x * .55, MIRA_BASE.y, a.position.z * .4);
    }
  },
  calma() { camObj.copy(CAM_BASE); miraObj.copy(MIRA_BASE); },
  cartel(html, pos) {
    over.querySelectorAll(".cartel,.globo").forEach(e => e.remove());
    const el = document.createElement("div");
    el.className = "cartel"; el.style.setProperty("--pc", COLOR[pos] || "#fcd116");
    const m = html.match(/^(<b>[\s\S]*?<\/b>)([\s\S]*)$/);
    el.innerHTML = m ? `${m[1]}<p>${m[2]}</p><small>completo en la conversación · clic para recoger</small>` : html;
    el.onclick = () => el.classList.toggle("chico");
    over.append(el);
    setTimeout(() => el.classList.add("chico"), 9000);
    API.calma();
  },
  /* el show: el juez revela el tablero fila por fila */
  async tablero({ titulo, n, filas, nota }) {
    over.querySelectorAll(".tablero,.juezdice").forEach(e => e.remove());
    const t = document.createElement("div");
    t.className = "tablero";
    t.innerHTML = `<h4></h4><ol></ol><small></small>`;
    t.querySelector("h4").textContent = titulo;
    t.querySelector("small").textContent = nota || "";
    const ol = t.querySelector("ol");
    filas.slice(0, 6).forEach((f, i) => {
      const li = document.createElement("li");
      li.innerHTML = `<span class="n">${i + 1}</span><span class="e"></span><span class="c"></span>`;
      li.querySelector(".e").textContent = f.e; li.querySelector(".c").textContent = f.n;
      li.style.setProperty("--pc", COLOR[f.pos] || "#fcd116");
      ol.append(li);
    });
    over.append(t);
    ubicarTablero();
    const dice = document.createElement("div");
    dice.className = "juezdice";
    if (JUEZ) pegar(dice, JUEZ, 18); else over.append(dice);
    const decir = s => { dice.textContent = s; if (JUEZ) { JUEZ.userData.habla = performance.now() + 1100; JUEZ.userData.mano = performance.now() + 900; } };
    decir(`¡Le preguntamos a ${n} colombianos sintéticos! Veamos qué dijeron…`);
    const lis = [...ol.children];
    for (let i = lis.length - 1; i >= 0; i--) {
      await new Promise(s => setTimeout(s, QUIETO ? 60 : 1100));
      lis[i].classList.add("ve");
      decir(i === 0 ? `Y la respuesta número uno… ¡${filas[0].e}!` : `En el puesto ${i + 1}: ${filas[i].e}.`);
    }
  },
  limpiar: quitarTodos,
  /* cambio de modo: escenario vacío del lugar que toca */
  vista(modo, sel) { quitarTodos(); API.calma(); lugar(modo === "sondeo" ? "estudio" : API.lugarDe(sel)); },
  vistaLugar(modo, sel) { if (modo !== "sondeo") lugar(API.lugarDe(sel)); },
};
window.ESCENA = API;
API._pinta = () => { for (let i = 0; i < 3; i++) cuadroForzado(); };
API._diag = () => ({ gente: GENTE.size, juez: !!JUEZ, pos: [...GENTE.values()].map(a => a.position.toArray().map(v => +v.toFixed(2))), cam: camara.position.toArray().map(v => +v.toFixed(2)) });
for (const [m, a] of (window.ESC_Q || []).splice(0)) API[m]?.(...a);

/* ── bucle ───────────────────────────────────────────────────────────── */
function medir() {
  const r = host.getBoundingClientRect();
  if (!r.width) return;
  renderer.setSize(r.width, r.height, false);
  camara.aspect = r.width / r.height;
  // en pantallas angostas, la cámara se aleja para que quepa la gente
  CAM_BASE.z = camara.aspect < 1 ? 17.5 : camara.aspect < 1.4 ? 14.5 : 12.5;
  camara.updateProjectionMatrix();
  encuadrar(); ubicarTablero();
}
new ResizeObserver(medir).observe(host);
medir();
let visible = true;
new IntersectionObserver(e => { visible = e[0].isIntersecting; }).observe(host);
const reloj = new THREE.Clock();
const tmp = new THREE.Vector3();
function cuadro() {
  requestAnimationFrame(cuadro);
  if (!visible || document.hidden) return;
  cuadroForzado();
}
function cuadroForzado() {
  const dt = Math.min(reloj.getDelta(), .25), t = reloj.elapsedTime, ahora = performance.now();
  camara.position.lerp(camObj, QUIETO ? 1 : dt * 1.6);
  mira.lerp(miraObj, QUIETO ? 1 : dt * 1.6);
  if (!QUIETO) camara.position.x += Math.sin(t * .23) * .004;        // la cámara respira
  camara.lookAt(mira);
  for (const a of [...GENTE.values(), JUEZ, MESA]) {
    if (!a) continue;
    const u = a.userData, c = u.cuerpo;
    a.quaternion.copy(camara.quaternion); a.rotation.x = 0; a.rotation.z = 0;   // siempre de frente
    let brinco = 0, anda = false;
    if (u.estatico) { c.position.y = u.alto / 2; continue; }
    if (u.meta && (!u.llega || ahora > u.llega)) {
      tmp.subVectors(u.meta, a.position);
      const d = tmp.length();
      if (d > .03) {
        a.position.addScaledVector(tmp.normalize(), Math.min(d, u.vel * dt));
        brinco = Math.abs(Math.sin(t * 9 + u.fase)) * .035;              // pasos
        anda = true;
        c.scale.x = (tmp.x < 0 ? -1 : 1);                                // mira hacia donde camina
      } else { u.meta = null; c.scale.x = 1; }
    }
    if (u.habla > ahora && u.cuadros < 4) brinco = Math.max(brinco, Math.abs(Math.sin(t * 16)) * .06);
    if (u.cuadros === 4) {
      const f = anda ? [1, 0, 2, 0][Math.floor(t * 7.5 + u.fase) % 4] : u.mano > ahora ? 3 : 0;
      if (f !== u.cuadro) { u.cuadro = f; c.material.map.offset.x = f / 4; }
    }
    const resp = QUIETO ? 1 : 1 + Math.sin(t * 2.1 + u.fase) * .012;   // respira
    c.scale.y = resp;
    c.position.y = u.alto / 2 * resp + brinco;
  }
  const pos = polvo.geometry.attributes.position, f = polvo.userData.fase;
  if (!QUIETO) for (let i = 0; i < f.length; i++) {
    pos.array[i * 3 + 1] += Math.sin(t * .6 + f[i]) * .0015 + .0009;
    if (pos.array[i * 3 + 1] > 5) pos.array[i * 3 + 1] = 0;
  }
  pos.needsUpdate = true;
  renderer.render(scene, camara);
  seguir();
  if (over.querySelector(".tablero.empotrado") && (t * 4 | 0) % 2 === 0) ubicarTablero();
}
cuadro();
lugar("nacional");
