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
  caribe: ["Ciudad amurallada", "Cartagena", "#ffe4c8"], barranquilla: ["Gran Malecón del Río", "Barranquilla", "#fff1d6"], sanandres: ["San Andrés", "Mar de siete colores", "#fffbe8"],
  guajira: ["Alta Guajira", "La Guajira", "#fff0cf"], medellin: ["Comuna 13", "Medellín", "#fff4e6"],
  cafetero: ["Salento", "Eje cafetero", "#fffaf0"], cali: ["Bulevar del río", "Cali", "#ffe6c4"],
  choco: ["Río Atrato", "Quibdó", "#f2f2e4"], narino: ["Las Lajas", "Nariño", "#eef0f2"],
  popayan: ["La ciudad blanca", "Popayán", "#fff8ee"], boyaca: ["Villa de Leyva", "Boyacá", "#fff6e8"],
  santander: ["Barichara", "Santander", "#ffeed8"], llanos: ["Los Llanos", "Meta y Casanare", "#ffdcb8"],
  amazonia: ["Leticia", "Amazonas", "#fff1d6"], tatacoa: ["Desierto de la Tatacoa", "Huila", "#d9d8ff"],
  sucre: ["Plaza de Sincelejo", "Sucre", "#fff0dc"],
  estudio: ["¿Qué dicen los colombianos?", "estudio de televisión", "#ffffff"],
};
/* dónde está el piso pintado de cada fondo (fracción desde arriba) y qué tan
   grande se ve la gente ahí: medido a ojo sobre cada imagen */
const PISO = { nacional: [.80, 1.0], bogota: [.87, .9], caribe: [.85, .95], barranquilla: [.86, .95], sanandres: [.86, .95], guajira: [.84, 1.0],
  medellin: [.88, .9], cafetero: [.89, .92], cali: [.86, .95], choco: [.89, .95], narino: [.86, .9], popayan: [.87, .92],
  boyaca: [.85, .95], santander: [.87, .9], llanos: [.86, 1.0], amazonia: [.87, .95], tatacoa: [.87, .95], estudio: [.79, .88],
  sucre: [.85, 1.0] };
const DPTO_LUGAR = { "11": "bogota", "05": "medellin", "13": "caribe", "08": "barranquilla", "47": "caribe", "20": "caribe",
  "23": "caribe", "70": "sucre", "88": "sanandres", "44": "guajira", "17": "cafetero", "63": "cafetero", "66": "cafetero",
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
/* el MUNDO es lo que se pinta (fondo, cielo, 3D); la ventana es lo que se ve. Con
   un fondo normal son iguales; con uno panorámico (más de 9 personas) el mundo es
   más ancho y la cámara 2D lo recorre */
const PANOS = new Set(["nacional", "bogota", "medellin", "caribe", "barranquilla", "cafetero", "llanos", "amazonia", "choco", "santander",
  "narino", "popayan", "cali", "guajira", "sanandres", "boyaca", "tatacoa", "sucre"]);
const PISO_PANO = { sanandres: [.88, 1.0], llanos: [.85, 1.0], guajira: [.86, 1.0] };
let IMG = { w: 1376, h: 768 }, PANO = false;
const MUNDO = { w: 16, h: 9 };
function mundoTam() {
  const W = host.clientWidth || 16, H = host.clientHeight || 9;
  MUNDO.h = H; MUNDO.w = PANO ? Math.max(W, Math.round(H * IMG.w / IMG.h)) : W;
}
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
  }, undefined, () => { TEX.delete(url); res(null); })));
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
/* aire: lo lejano se funde con el color del horizonte pintado (perspectiva atmosférica) */
function niebla(base, t) {
  const c = CIELOS[base], col = new THREE.Color(c ? c.abajo : t || "#cfd6e0");
  const d = Math.hypot(CAM_BASE.y, CAM_BASE.z);
  scene.fog = QUIETO ? null : new THREE.Fog(col, d + 4, d + 160);     // sutil: a 20 m de más, ~12 %
}
/* ── gente ───────────────────────────────────────────────────────────── */
const GENTE = new Map();          // id → actor
let JUEZ = null, MESA = null;
let ALTO = 1.45;                 // metros de escena por persona (lo ajusta cada lugar)

/* cuadros=4: tira de poses (quieto, paso izq, paso der, mano arriba) */
async function actor(id, url, alto = ALTO, cuadros = 1, estatico = false) {
  let tex = await textura(url);
  // tiras de poses: 4 cuadros (de frente) u 8 (más lado y espalda); se cuenta por la proporción de la imagen
  if (tex && cuadros >= 4) cuadros = tex.image.width / tex.image.height > 3.6 ? 8 : 4;
  if (tex && cuadros > 1) { tex = tex.clone(); tex.repeat.set(1 / cuadros, 1); tex.needsUpdate = true; }
  const g = new THREE.Group();
  const asp = tex ? tex.image.width / cuadros / tex.image.height : 0.4;
  const mat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, alphaTest: 0.5, color: tinte.clone() });
  const cuerpo = new THREE.Mesh(new THREE.PlaneGeometry(alto * asp, alto), mat);
  cuerpo.position.y = alto / 2;
  const som = new THREE.Mesh(new THREE.PlaneGeometry(Math.max(alto * asp * 1.1, alto * .42), alto * 0.2),
    new THREE.MeshBasicMaterial({ map: sombraTex, transparent: true, depthWrite: false }));
  som.rotation.x = -Math.PI / 2; som.position.y = 0.01;
  if (!tex) { cuerpo.visible = false; som.visible = false; }   // imagen rota: nada, no un bloque de color
  g.add(som, cuerpo);
  g.userData = { id, cuerpo, alto, fase: Math.random() * 6.28, meta: null, vel: 1.9, habla: 0, llega: null,
    cuadros, estatico, mano: 0, cuadro: 0 };
  scene.add(g);
  return g;
}
function quitarTodos() {
  for (const a of GENTE.values()) scene.remove(a);
  GENTE.clear();
  if (JUEZ) { scene.remove(JUEZ); JUEZ = null; }
  if (MESA) { scene.remove(MESA); MESA = null; }
  over.querySelectorAll(".globo,.marca,.cartel,.tablero,.juezdice,.placa,.rotulo").forEach(e => e.remove());
  COLA.length = 0; enTurno = false;
}

/* la mesa y las cosas de cada región (web/gente/catalogo.json, "utileria") */
const UTIL_DE = { nacional: "bogota", bogota: "bogota", medellin: "antioquia", caribe: "caribe", barranquilla: "caribe", sanandres: "insular_guajira",
  guajira: "insular_guajira", cafetero: "cafetero", tatacoa: "cafetero", cali: "pacifico", choco: "pacifico", narino: "sur_andino",
  popayan: "sur_andino", boyaca: "boyaca", santander: "santander", llanos: "llanos", amazonia: "amazonia", sucre: "caribe_rural" };
function utileriaDe(k) { return window.CATALOGO?.utileria?.[UTIL_DE[k]] || null; }
const COSAS = [[-4.7, -1.7], [4.9, -2.0], [-5.8, 0.7], [5.9, 0.5]];
/* cuánto cabe: el medio ancho visible del escenario (en z = -0,3) contra el de
   referencia (4,6). En una playa vista desde arriba cabe menos que en una plaza */
function escalaEscenario() {
  const c = aPantalla(new THREE.Vector3(0, 0, -.3)), d = aPantalla(new THREE.Vector3(1, 0, -.3));
  const medio = MUNDO.w / 2 / Math.max(1e-3, d.x - c.x);
  return Math.min(1.1, Math.max(.5, medio / 4.6));
}
/* acomodos: dónde se para cada quien */
function repartir(r) { const k = Math.ceil(r / 7), base = Math.floor(r / k); return Array.from({ length: k }, (_, i) => base + (i < r % k ? 1 : 0)); }
function puestos(n, modo) {
  const P = [], e = escalaEscenario();
  if (modo === "mesa") {
    // hasta 9: herradura detrás de la mesa, repartida PAREJO EN X (así nadie queda
    // detrás de otro en pantalla). Más de 9: la mesa con 7 y el resto en corrillos
    // junto a las cosas del lugar y al fondo, como en una plaza de verdad.
    const grupos = n <= 9 ? [n] : [7, ...repartir(n - 7)];
    const g0 = grupos[0], ancho = Math.min(3.7, .45 + g0 * .42);
    for (let i = 0; i < g0; i++) {
      const x = g0 === 1 ? 0 : -ancho + 2 * ancho * i / (g0 - 1), k = x / (ancho + .7);
      P.push([x * e, -0.25 - 1.05 * e * Math.sqrt(1 - k * k)]);
    }
    const CENTROS = [[-2.9, -3.7], [3.1, -3.9], [0.2, -6.2], [-3.6, -7.0], [3.9, -7.2]];
    grupos.slice(1).forEach((m, j) => {
      const [cx0, cz0] = CENTROS[j % CENTROS.length], cx = cx0 * (PANO ? 1.6 : 1) * e, cz = cz0 * e, w = Math.min(1.7, .25 + m * .3) * e;
      for (let i = 0; i < m; i++) {
        const x = m === 1 ? 0 : -w + 2 * w * i / (m - 1), k = x / (w + .5);
        P.push([cx + x, cz - .6 * Math.sqrt(1 - k * k) + (i % 2) * .14, false, j + 1]);
      }
    });
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
/* coordenadas LÓGICAS del visor (sin el zoom de la cámara 2D): para decidir dónde se camina */
function aPantalla(v) {
  const p = v.clone().project(camara), W = canvas.clientWidth, H = canvas.clientHeight;
  return { x: (p.x * .5 + .5) * W, y: (-p.y * .5 + .5) * H, z: p.z };
}
function cabeza(a) { return new THREE.Vector3(a.position.x, a.userData.alto * 1.02, a.position.z); }
function pies(a) { return new THREE.Vector3(a.position.x, 0, a.position.z); }
function pegar(el, a, dy = 0, ancla = "cabeza") {
  el.userData = a;
  el.dataset.dy = dy; el.dataset.ancla = ancla;
  over.append(el);
}
function seguir() {
  const W = host.clientWidth;
  for (const el of over.querySelectorAll("[data-dy]")) {
    const a = el.userData; if (!a || !a.parent) { el.remove(); continue; }
    const q = aPantalla(el.dataset.ancla === "pies" ? pies(a) : cabeza(a)), p = vistaA(q);
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
  const p = el.querySelector("p"), corto = idea(txt);
  if (QUIETO) { p.textContent = corto; return; }
  let i = 0; const paso = Math.max(1, Math.round(corto.length / 55));
  const iv = setInterval(() => { if (!p.isConnected) { clearInterval(iv); return; } i += paso; p.textContent = corto.slice(0, i); if (i >= corto.length) clearInterval(iv); }, 26);
}
/* la idea: primera frase, hasta ~110 caracteres. Leer un párrafo en un globo
   no es un intercambio ágil; el completo queda en la conversación */
function idea(t) {
  t = String(t || "").trim();
  const m = t.match(/^.{25,}?[.!?…](?=\s|$)/);
  let c = m ? m[0] : t;
  if (c.length > 115) c = c.slice(0, 112).replace(/\s+\S*$/, "") + "…";
  return c;
}
function placa(a, nombre) {
  a.userData.placa?.remove();
  const el = document.createElement("div");
  el.className = "placa"; el.textContent = nombre;
  pegar(el, a, -6, "pies");
  a.userData.placa = el;
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
/* ── la cámara de la pintura ───────────────────────────────────────────
   Regla del pintor: una persona de pie mide (su altura / altura de la cámara) ×
   (distancia de sus pies a la línea del horizonte). Si la cámara 3D no tiene el
   horizonte donde lo tiene el cuadro, la gente no achica al alejarse (o achica de
   más) y no cuadra con las puertas. Por fondo: [horizonte (fy), altura de la
   cámara en metros]. La altura sale de una puerta medida (Salento, Barichara,
   Popayán, La Candelaria); sin puerta, la que deja a una persona en el ~17 % del
   alto del cuadro en el escenario (en la playa o el desierto el cuadro se ve desde
   arriba: la cámara sale de 6 a 8 m). */
const HORIZ = {
  nacional: [.59], bogota: [.52, 2.5], medellin: [.55], caribe: [.69], barranquilla: [.34], cafetero: [.50, 2.47],
  llanos: [.47], amazonia: [.32], choco: [.30], santander: [.50, 1.62], narino: [.63],
  popayan: [.55, 1.8], cali: [.55], guajira: [.15], sanandres: [.12], boyaca: [.52], tatacoa: [.45],
  nacional_pano: [.59], bogota_pano: [.56], medellin_pano: [.60], caribe_pano: [.69], barranquilla_pano: [.34],
  cafetero_pano: [.55], llanos_pano: [.40], amazonia_pano: [.30], choco_pano: [.30],
  santander_pano: [.55], narino_pano: [.63], popayan_pano: [.60], cali_pano: [.58],
  guajira_pano: [.20], sanandres_pano: [.20], boyaca_pano: [.55], tatacoa_pano: [.50],
  sucre: [.58, 1.66], sucre_pano: [.57, 1.6],   // Sincelejo: puerta del portal medida (2,4 m)
};
function encuadrar() {
  const W = MUNDO.w, H = MUNDO.h, hz = HORIZ[sueloK];
  if (hz) {
    // cabeceo: el horizonte de la cámara cae en el horizonte pintado; altura: la de la puerta;
    // distancia: el centro de la tertulia (z = -0,3) cae en el piso del cuadro (pisoY)
    ALTO = 1.45;
    const t = Math.tan(THREE.MathUtils.degToRad(camara.fov / 2)), pf = Math.max(pisoY, hz[0] + .08);
    const hc = (hz[1] || 1.65 * (pf - hz[0]) / .17) / 1.65 * ALTO;
    const Yh = imgAPantalla(.5, hz[0]).y, Yp = imgAPantalla(.5, pf).y;
    const th = Math.atan((1 - 2 * Yh / H) * t), al = Math.atan((2 * Yp / H - 1) * t);
    const D = hc / Math.tan(Math.max(.02, al + th)) - .3;
    CAM_BASE.set(0, hc, D); MIRA_BASE.set(0, hc - Math.tan(th) * D, 0);
    camara.position.copy(CAM_BASE); camObj.copy(CAM_BASE);
    miraObj.copy(MIRA_BASE); mira.copy(MIRA_BASE);
    camara.lookAt(MIRA_BASE); camara.updateMatrixWorld();
    return;
  }
  /* sin horizonte medido (el estudio): el piso pintado a fracción pisoY cae donde toca */
  CAM_BASE.set(0, 3.1, CAM_BASE.z > 5 ? CAM_BASE.z : 12.5);
  const imgH = Math.max(H, W * IMG.h / IMG.w), yPx = H - (1 - pisoY) * imgH;
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
  const W = MUNDO.w, H = MUNDO.h;
  const k = Math.max(W / IMG.w, H / IMG.h), iw = IMG.w * k, ih = IMG.h * k;
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

/* ── el piso pintado ─────────────────────────────────────────────────────
   Por fondo, dónde EMPIEZA el suelo caminable: [fx, fy] en fracción de la imagen,
   de izquierda a derecha (medido sobre cada imagen con una rejilla del 10 %). Por
   encima de esa línea hay casas, muros, árboles, río o cielo: nadie camina ahí.
   FRENTE: donde el piso se acaba por delante (el muelle del Atrato tiene agua). */
const SUELO = {
  nacional: [[0, 0.674], [0.1, 0.666], [0.2, 0.655], [0.3, 0.649], [0.4, 0.647], [0.5, 0.645], [0.6, 0.647], [0.7, 0.649], [0.8, 0.659], [0.9, 0.672], [1, 0.678]],   // Plaza de Bolívar HD: Justicia al norte, Capitolio al sur, Bolívar de pie
  bogota: [[0, .93], [.1, .9], [.18, .78], [.3, .7], [.4, .64], [.5, .6], [.6, .64], [.7, .72], [.8, .8], [.9, .86], [1, .9]],
  medellin: [[0, .9], [.08, .78], [.15, .72], [.6, .72], [.8, .74], [.87, .85], [1, .95]],
  caribe: [[0, 0.761], [0.1, 0.755], [0.2, 0.741], [0.3, 0.714], [0.4, 0.704], [0.5, 0.7], [0.6, 0.7], [0.7, 0.705], [0.8, 0.747], [0.9, 0.763], [1, 0.776]],   // Cartagena HD: Plaza de los Coches, Torre del Reloj, Portal de los Dulces
  barranquilla: [[0, 0.752], [0.1, 0.746], [0.2, 0.73], [0.3, 0.73], [0.4, 0.73], [0.5, 0.73], [0.6, 0.73], [0.7, 0.73], [0.8, 0.73], [0.9, 0.752], [1, 0.755]],   // Gran Malecón: detrás de la baranda está el río
  cafetero: [[0, .8], [.05, .76], [.75, .74], [.78, .8], [1, .8]],
  llanos: [[0, .52], [.4, .55], [.5, .6], [.95, .6], [1, .55]],
  amazonia: [[0, .72], [.1, .64], [.2, .61], [.85, .61], [.9, .7], [1, .8]],
  choco: [[0, .7], [1, .7]],
  santander: [[0, .9], [.12, .85], [.2, .66], [.4, .62], [.7, .62], [.88, .66], [.92, .85], [1, .92]],
  narino: [[0, 0.836], [0.1, 0.827], [0.2, 0.808], [0.3, 0.777], [0.4, 0.771], [0.5, 0.77], [0.6, 0.771], [0.7, 0.777], [0.8, 0.808], [0.9, 0.827], [1, 0.836]],   // Las Lajas HD: el santuario sobre el puente
  popayan: [[0, .75], [.1, .7], [.3, .66], [.5, .65], [.75, .68], [1, .74]],
  cali: [[0, .64], [.3, .62], [.7, .62], [1, .63]],
  guajira: [[0, .65], [.1, .57], [.2, .55], [.7, .56], [.75, .65], [.85, .78], [1, .8]],
  sanandres: [[0, .72], [.12, .68], [.2, .62], [.7, .62], [.78, .7], [1, .75]],
  boyaca: [[0, .72], [.12, .66], [.2, .57], [.6, .56], [.72, .62], [.85, .72], [1, .8]],
  tatacoa: [[0, .72], [.15, .64], [.3, .62], [.85, .63], [.92, .72], [1, .8]],
  nacional_pano: [[0, 0.685], [0.2, 0.665], [0.3, 0.65], [0.5, 0.645], [0.7, 0.65], [0.78, 0.67], [1, 0.685]],
  bogota_pano: [[0, .74], [.3, .72], [.4, .64], [.5, .58], [.6, .64], [.7, .72], [1, .74]],
  medellin_pano: [[0, .75], [.05, .68], [.95, .68], [1, .75]],
  caribe_pano: [[0, 0.77], [0.25, 0.75], [0.3, 0.72], [0.45, 0.7], [0.65, 0.7], [0.7, 0.74], [0.85, 0.77], [1, 0.79]],
  barranquilla_pano: [[0, 0.76], [0.2, 0.745], [0.22, 0.73], [0.75, 0.73], [0.78, 0.75], [1, 0.76]],
  cafetero_pano: [[0, .74], [.1, .72], [.3, .68], [.8, .68], [1, .72]],
  llanos_pano: [[0, .52], [.4, .54], [.45, .56], [.75, .56], [1, .52]],
  amazonia_pano: [[0, .66], [.2, .63], [.85, .63], [1, .66]],
  choco_pano: [[0, .7], [1, .7]],
  santander_pano: [[0, .64], [.3, .6], [.5, .58], [.9, .66], [1, .72]],
  narino_pano: [[0, 0.87], [0.07, 0.84], [0.25, 0.82], [0.3, 0.78], [0.44, 0.77], [0.56, 0.77], [0.7, 0.78], [0.75, 0.82], [0.93, 0.84], [1, 0.87]],
  popayan_pano: [[0, .62], [.45, .62], [.6, .64], [.9, .72], [1, .74]],
  cali_pano: [[0, .64], [.5, .61], [1, .63]],
  guajira_pano: [[0, .54], [.3, .5], [.6, .52], [.65, .6], [.85, .6], [.9, .54], [1, .54]],
  sanandres_pano: [[0, .6], [.2, .55], [.8, .55], [1, .6]],
  boyaca_pano: [[0, .66], [.15, .6], [.4, .56], [.6, .56], [.85, .62], [1, .68]],
  tatacoa_pano: [[0, .62], [.3, .58], [.7, .58], [1, .62]],
  sucre: [[0, .71], [.1, .69], [.12, .66], [.85, .68], [.88, .71], [1, .71]],
  sucre_pano: [[0, .66], [.2, .66], [.5, .63], [.8, .66], [1, .66]],
};
const FRENTE = { choco_pano: .8 };
let sueloK = null;                                  // la clave del fondo puesto (k o k_pano)
function sueloEn(fx) {
  const L = SUELO[sueloK]; if (!L) return null;
  for (let i = 1; i < L.length; i++) if (fx <= L[i][0]) {
    const [a, b] = [L[i - 1], L[i]], t = (fx - a[0]) / Math.max(1e-6, b[0] - a[0]);
    return a[1] + (b[1] - a[1]) * Math.min(1, Math.max(0, t));
  }
  return L[L.length - 1][1];
}
/* píxel del mundo → fracción de la imagen (lo inverso de imgAPantalla) */
function aImagen(px, py) {
  const W = MUNDO.w, H = MUNDO.h, k = Math.max(W / IMG.w, H / IMG.h), iw = IMG.w * k, ih = IMG.h * k;
  return [(px - (W - iw) / 2) / iw, (py - (H - ih)) / ih];
}
/* fracción de la imagen → punto del piso 3D (rayo desde la cámara base) */
const _rayo = new THREE.Raycaster(), _plano = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0), _cam = new THREE.PerspectiveCamera();
function imgAPiso(fx, fy) {
  _cam.copy(camara); _cam.position.copy(CAM_BASE); _cam.lookAt(MIRA_BASE); _cam.updateMatrixWorld(); _cam.updateProjectionMatrix();
  const p = imgAPantalla(fx, fy), v = new THREE.Vector2(p.x / MUNDO.w * 2 - 1, -(p.y / MUNDO.h) * 2 + 1);
  _rayo.setFromCamera(v, _cam);
  const q = new THREE.Vector3();
  return _rayo.ray.intersectPlane(_plano, q) ? q : null;
}
/* por dónde se entra a la escena: el fondo de la calle (el punto más lejano del
   piso) y las orillas del piso a los lados. Nunca desde una pared o el cielo. */
function entradas() {
  const L = SUELO[sueloK]; if (!L) return null;
  let mejor = [.5, 1];
  for (let fx = .05; fx <= .95; fx += .01) { const fy = sueloEn(fx); if (fy < mejor[1]) mejor = [fx, fy]; }
  const fondo = imgAPiso(mejor[0], mejor[1] + .02);
  const izq = imgAPiso(.02, Math.min(.96, sueloEn(.02) + .06)), der = imgAPiso(.98, Math.min(.96, sueloEn(.98) + .06));
  return { fondo, izq, der };
}
/* ¿el punto (x,z) del piso cae dentro del cuadro, sobre el piso, con la persona
   entera a la vista? Así nadie se sale de la imagen ni camina por las paredes */
function caminable(x, z, alto = ALTO) {
  const H = MUNDO.h || 1;
  const f = aPantalla(new THREE.Vector3(x, 0, z)), c = aPantalla(new THREE.Vector3(x, alto, z));
  const fx = f.x / (MUNDO.w || 1), fy = f.y / H;
  if (!(fx > .03 && fx < .97 && fy < .97 && c.y / H > .06)) return false;
  const [ix, iy] = aImagen(f.x, f.y), s0 = sueloEn(ix);
  if (s0 === null) return fy < .95 && fy > Math.max(.5, pisoY - .3);            // estudio: la regla de antes
  return iy > s0 + .012 && iy < (FRENTE[sueloK] || .985);
}
function puntoLibre(cx, cz, radio, alto) {
  for (let i = 0; i < 24; i++) {
    const x = cx + (Math.random() * 2 - 1) * radio, z = cz + (Math.random() * 2 - 1) * radio * .7;
    if (caminable(x, z, alto)) return new THREE.Vector3(x, 0, z);
  }
  return null;
}

/* ── cielo vivo ──────────────────────────────────────────────────────────
   Los fondos con cielo recortado (escenas/<k>_tierra.webp, ver scripts/escena/cielo.py)
   dejan ver este lienzo: degradado con tramado Bayer, nubes pixel que pasan y
   pájaros del lugar. Resolución baja escalada sin suavizado: píxel de verdad. */
const CIELOS = {};
const cielo = (() => {
  const cv = document.createElement("canvas"); cv.id = "cielo"; host.prepend(cv);
  const g = cv.getContext("2d");
  const PX = 3, BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];
  let W = 0, H = 0, k = null, pal = null, degr = null, nubes = [], aves = [], proxAves = 0, sol = null;
  const rgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
  const mez = (a, b, t) => a.map((v, i) => Math.round(v + (b[i] - v) * t));
  const css = c => `rgb(${c[0]},${c[1]},${c[2]})`;
  /* pájaros por lugar: [forma, color, color2, velocidad px/s, tamaño bandada] */
  const AVES = {
    nacional: [["paloma", "#8b8f9c", "#c9ccd6", 16, 5], ["golondrina", "#24222e", "#24222e", 26, 3]],
    bogota: [["paloma", "#8b8f9c", "#c9ccd6", 16, 4], ["golondrina", "#24222e", "#24222e", 26, 3]],
    medellin: [["golondrina", "#24222e", "#24222e", 26, 4], ["gallinazo", "#1c1a20", "#3a3640", 9, 2]],
    caribe: [["gaviota", "#f7f7f2", "#9aa2ad", 18, 4], ["alcatraz", "#6e6258", "#b9aea0", 11, 3]],
    barranquilla: [["gaviota", "#f7f7f2", "#9aa2ad", 18, 4], ["alcatraz", "#6e6258", "#b9aea0", 11, 3]],
    sanandres: [["gaviota", "#f7f7f2", "#9aa2ad", 18, 5], ["alcatraz", "#6e6258", "#b9aea0", 11, 3]],
    guajira: [["flamenco", "#f08aa0", "#20181c", 13, 6], ["gaviota", "#f7f7f2", "#9aa2ad", 18, 3]],
    cafetero: [["loro", "#3fbf4a", "#f2d640", 22, 5], ["golondrina", "#24222e", "#24222e", 26, 3]],
    cali: [["garza", "#f4f4ee", "#e3b23c", 12, 3], ["golondrina", "#24222e", "#24222e", 26, 4]],
    choco: [["garza", "#f4f4ee", "#e3b23c", 12, 3], ["loro", "#3fbf4a", "#f2d640", 22, 4]],
    amazonia: [["guacamaya", "#e0302a", "#2f6fe0", 17, 3], ["loro", "#3fbf4a", "#f2d640", 22, 6]],
    llanos: [["corocora", "#e8412c", "#e8412c", 14, 7], ["garza", "#f4f4ee", "#e3b23c", 12, 4]],
    santander: [["gallinazo", "#1c1a20", "#3a3640", 9, 3], ["golondrina", "#24222e", "#24222e", 26, 3]],
    popayan: [["gallinazo", "#1c1a20", "#3a3640", 9, 2], ["golondrina", "#24222e", "#24222e", 26, 3]],
    narino: [["gallinazo", "#1c1a20", "#3a3640", 9, 2]],
  };
  /* cuadros de aleteo (a = color, b = color2); arriba y abajo */
  const FORMA = {
    golondrina: [["a...a", ".a.a.", "..a.."], [".....", "aaaaa", "..a.."]],
    paloma: [["a...a", ".abaa", "..a.."], [".....", "aabaa", ".a.a."]],
    gaviota: [["b.....b", ".a...a.", "..aaa.."], [".......", "baaaaab", "...a..."]],
    alcatraz: [["a.......a", ".a.....a.", "..aabaa..", "....b...."], [".........", "aaaabaaaa", "....b...."]],
    flamenco: [["a.....a", ".a...a.", "bbaaaab", "......."], [".......", "aaaaaaa", "bb....b", "......."]],
    loro: [["a...a", ".aba.", "..a.."], [".....", "aabaa", "..a.."]],
    guacamaya: [["b.....b", ".a...a.", "..aaa..", "...bb.."], [".......", "baaaaab", "...a...", "...bb.."]],
    corocora: [["a...a", ".aaa.", "..a.."], [".....", "aaaaa", ".a.a."]],
    garza: [["a.......a", ".a.....a.", "..aaaaa..", "......b.."], [".........", "aaaaaaaaa", "......b.."]],
    gallinazo: [["b.........b", ".baaaaaaab.", "....aaa...."], ["b.........b", ".baaaaaaab.", "....aaa...."]],
  };
  function paleta(c) {
    const a = rgb(c.arriba), b = rgb(c.abajo), h = c.hora;
    if (h === "tarde") return { top: mez(a, [66, 56, 128], .55), bot: mez(b, [255, 176, 104], .45), nube: [255, 222, 188], sombra: [186, 124, 146], sol: true };
    if (h === "bruma") return { top: mez(a, [132, 182, 200], .6), bot: mez(b, [232, 222, 196], .3), nube: [246, 242, 230], sombra: [196, 190, 172] };
    if (h === "niebla") return { top: mez(a, [168, 186, 202], .55), bot: mez(b, [228, 226, 218], .35), nube: [246, 246, 242], sombra: [196, 202, 210] };
    return { top: mez(a, [70, 146, 222], .68), bot: mez(b, [214, 236, 246], .4), nube: [255, 255, 255], sombra: mez(mez(a, [70, 146, 222], .68), [255, 255, 255], .5) };
  }
  function nubeSprite(w) {
    const h = Math.max(6, Math.round(w * .38)), c = document.createElement("canvas"); c.width = w; c.height = h;
    const x = c.getContext("2d"); x.fillStyle = "#fff";
    x.beginPath(); x.ellipse(w / 2, h * .72, w / 2, h * .28, 0, 0, 7); x.fill();
    const n = 3 + (Math.random() * 3 | 0);
    for (let i = 0; i < n; i++) { const r = h * (.28 + Math.random() * .22), cx = r + (w - 2 * r) * (i + .5) / n;
      x.beginPath(); x.arc(cx, h * .72 - r * .55, r, 0, 7); x.fill(); }
    // píxel duro: nada de antialias
    const d = x.getImageData(0, 0, w, h), P = d.data;
    for (let i = 0; i < P.length; i += 4) {
      const y = (i / 4 / w) | 0, on = P[i + 3] > 110;
      const col = y > h * .62 ? pal.sombra : pal.nube;
      P[i] = col[0]; P[i + 1] = col[1]; P[i + 2] = col[2]; P[i + 3] = on ? 255 : 0;
    }
    x.putImageData(d, 0, 0);
    return c;
  }
  function horizonte() {
    const c = CIELOS[k]; if (!c || !IMG.w || !IMG.h) return H;   // fondo aún sin cargar: sin esto, NaN en las nubes
    const kk = Math.max(MUNDO.w / IMG.w, MUNDO.h / IMG.h), ih = IMG.h * kk;
    return Math.min(H, Math.ceil((MUNDO.h - ih + c.horizonte * ih) / PX) + 2);
  }
  function pintarDegradado() {
    if (!pal || !W) return;
    degr = document.createElement("canvas"); degr.width = W; degr.height = H;
    const x = degr.getContext("2d"), d = x.createImageData(W, H), P = d.data, hz = Math.max(8, horizonte()), BANDAS = 7;
    for (let y = 0; y < H; y++) {
      const t = Math.min(1, y / hz) * BANDAS, b0 = Math.floor(t), fr = t - b0;
      for (let xx = 0; xx < W; xx++) {
        const b = fr * 16 > BAYER[(y & 3) * 4 + (xx & 3)] ? b0 + 1 : b0;
        const col = mez(pal.top, pal.bot, Math.min(1, b / BANDAS)), i = (y * W + xx) * 4;
        P[i] = col[0]; P[i + 1] = col[1]; P[i + 2] = col[2]; P[i + 3] = 255;
      }
    }
    x.putImageData(d, 0, 0);
    if (pal.sol) {        // sol bajo de la tarde, con halo tramado
      const sx = W * .7, sy = hz - 6, R = 11;
      for (let y = -R * 3; y <= R * 3; y++) for (let xx = -R * 3; xx <= R * 3; xx++) {
        const dd = Math.hypot(xx, y), X = Math.round(sx + xx), Y = Math.round(sy + y);
        if (X < 0 || Y < 0 || X >= W || Y >= H) continue;
        if (dd <= R) { x.fillStyle = dd > R - 2 ? "#ffd88a" : "#fff3c8"; x.fillRect(X, Y, 1, 1); }
        else if (dd < R * 3 && (R * 3 - dd) / (R * 2) * 16 > BAYER[(Y & 3) * 4 + (X & 3)] + 6) { x.fillStyle = "rgba(255,214,150,.55)"; x.fillRect(X, Y, 1, 1); }
      }
    }
  }
  function sembrar() {
    const hz = horizonte();
    nubes = Array.from({ length: Math.max(4, Math.round(W / 70)) }, () => {
      const y = hz * (.06 + Math.random() * .62), lejos = y / hz;          // más abajo = más lejos: chica y lenta
      const w = Math.round((58 - lejos * 30) * (.6 + Math.random() * .6));
      return { x: Math.random() * (W + 80) - 40, y: Math.round(y), v: (3.2 - lejos * 2.2) * (.7 + Math.random() * .5), spr: nubeSprite(w) };
    }).sort((a, b) => b.y - a.y);                                         // las lejanas se pintan primero
    aves = []; proxAves = performance.now() + 2500 + Math.random() * 4000;
  }
  function bandada(ahora) {
    const tipos = AVES[k.replace("_pano", "")]; if (!tipos || QUIETO) return;
    const [forma, a, b, v, n] = tipos[Math.random() < .7 ? 0 : tipos.length - 1];
    const hz = horizonte(), dir = Math.random() < .5 ? 1 : -1, y0 = hz * (.12 + Math.random() * .5);
    const cuantos = Math.max(1, Math.round(n * (.6 + Math.random() * .6)));
    for (let i = 0; i < cuantos; i++)
      aves.push({ forma, a, b, v: v * (.9 + Math.random() * .2) * dir, x: dir > 0 ? -12 - i * (6 + Math.random() * 5) : W + 12 + i * (6 + Math.random() * 5),
        y: y0 + (i % 2 ? 1 : -1) * Math.ceil(i / 2) * (3 + Math.random() * 2), fase: Math.random() * 6, planea: forma === "gallinazo" || forma === "garza" });
    proxAves = ahora + 9000 + Math.random() * 14000;
  }
  return {
    poner(clave) {
      k = clave; const c = CIELOS[k];
      cv.style.display = c ? "block" : "none";
      if (!c) return;
      pal = paleta(c); this.medir();
    },
    medir() {
      if (!MUNDO.w) return;
      W = cv.width = Math.ceil(MUNDO.w / PX); H = cv.height = Math.ceil(MUNDO.h / PX);
      if (pal) { pintarDegradado(); sembrar(); if (degr) g.drawImage(degr, 0, 0); }   // primer cuadro ya, sin esperar al bucle
    },
    cuadro(dt, t, ahora) {
      if (!pal || !degr || cv.style.display === "none") return;
      g.drawImage(degr, 0, 0);
      for (const n of nubes) {
        if (!QUIETO) n.x += n.v * dt;
        if (n.x > W + 10) n.x = -n.spr.width - 10;
        g.drawImage(n.spr, Math.round(n.x), n.y);
      }
      if (ahora > proxAves) bandada(ahora);
      aves = aves.filter(p => p.x > -140 && p.x < W + 140);
      for (const p of aves) {
        p.x += p.v * dt; const F = FORMA[p.forma], fr = p.planea ? F[0] : F[(t * 5 + p.fase | 0) % 2];
        const y = Math.round(p.y + Math.sin(t * 2 + p.fase) * 1.5), x0 = Math.round(p.x);
        for (let j = 0; j < fr.length; j++) for (let i = 0; i < fr[j].length; i++) {
          const ch = fr[j][p.v < 0 ? i : fr[j].length - 1 - i]; if (ch === ".") continue;
          g.fillStyle = ch === "a" ? p.a : p.b; g.fillRect(x0 + i, y + j, 1, 1);
        }
      }
    },
  };
})();
// si el primer lugar se pintó antes de saber qué cielos hay, se vuelve a poner (ya con su cielo)
fetch("escenas/cielos.json").then(r => r.json()).then(d => { Object.assign(CIELOS, d); const k = lugarActual; if (k) { lugarActual = null; lugar(k, PANO); } }).catch(() => {});

/* ── ambiente: la vida del lugar que no tiene nada que ver con la tertulia ──
   Animales, vehículos y transeúntes coherentes con cada sitio (escenas/amb/*.webp,
   hechos con GPT Image; ver scripts/escena/ambiente.py). Cada carril se define en
   fracción de la IMAGEN (dónde está la calle, el río, la sabana pintados) y se
   convierte a profundidad del piso 3D: la perspectiva escala sola.
   [sprite, alto en metros, comportamiento, fy de la imagen (o [min,max]), cuántos, velocidad m/s] */
const AMB = {
  nacional: [["paloma", .26, "deambula", [.72, .9], 5, .35], ["llama", 1.55, "cruza", .72, 1, .45], ["turista", 1.7, "cruza", .76, 1, .9], ["vendedor", 1.75, "cruza", .82, 1, .7]],
  bogota: [["perro", .55, "deambula", [.66, .8], 1, .8], ["turista", 1.7, "cruza", .58, 1, .9], ["gato", .32, "deambula", [.62, .72], 1, .5], ["paloma", .26, "deambula", [.6, .74], 2, .35]],
  medellin: [["turista", 1.7, "cruza", .74, 2, .8], ["perro", .55, "deambula", [.76, .86], 1, .8], ["vendedor", 1.75, "cruza", .78, 1, .6]],
  caribe: [["coche", 1.9, "cruza", .8, 1, 1.4], ["palenquera", 1.72, "cruza", .84, 1, .6], ["gato", .32, "deambula", [.8, .92], 1, .5], ["turista", 1.7, "cruza", .88, 1, .9]],
  barranquilla: [["turista", 1.7, "cruza", .8, 1, .9], ["bici", 1.6, "cruza", .835, 1, 2.2], ["vendedor", 1.75, "cruza", .9, 1, .7], ["perro", .55, "deambula", [.8, .92], 1, .8]],
  cafetero: [["willys", 1.8, "cruza", .74, 1, 2.6], ["mula", 1.5, "cruza", .76, 1, .7], ["gallina", .4, "deambula", [.8, .9], 2, .45], ["perro", .55, "deambula", [.78, .9], 1, .8]],
  llanos: [["vaca", 1.4, "deambula", [.47, .53], 4, .25], ["llanero", 2.2, "cruza", .56, 1, 1.3], ["garza", .8, "deambula", [.58, .66], 2, .3], ["perro", .55, "deambula", [.65, .8], 1, .8]],
  amazonia: [["canoa", 1.1, "cruza", .55, 1, 1.6], ["garza", .8, "deambula", [.72, .8], 1, .3], ["perro", .55, "deambula", [.78, .88], 1, .8]],
  choco: [["canoa", 1.1, "cruza", .6, 1, 1.5], ["garza", .8, "deambula", [.74, .82], 1, .3], ["gallina", .4, "deambula", [.8, .9], 1, .45]],
  santander: [["burro", 1.2, "cruza", .67, 1, .6], ["gallina", .4, "deambula", [.72, .9], 2, .45], ["perro", .55, "deambula", [.72, .88], 1, .8]],
  narino: [["turista", 1.7, "cruza", .84, 1, .8], ["gallinazo", .6, "deambula", [.8, .9], 1, .2], ["perro", .55, "deambula", [.82, .92], 1, .8]],
  popayan: [["bici", 1.6, "cruza", .7, 1, 2.2], ["perro", .55, "deambula", [.72, .88], 1, .8], ["turista", 1.7, "cruza", .72, 1, .9]],
  cali: [["vendedor", 1.75, "cruza", .7, 1, .6], ["bici", 1.6, "cruza", .72, 1, 2.2], ["paloma", .26, "deambula", [.72, .86], 3, .35], ["perro", .55, "deambula", [.74, .88], 1, .8]],
  guajira: [["chivo", .8, "deambula", [.58, .72], 3, .4], ["wayuu", 1.62, "cruza", .6, 1, .6], ["burro", 1.2, "cruza", .56, 1, .5]],
  sanandres: [["carrito_golf", 1.7, "cruza", .63, 1, 2.2], ["turista", 1.7, "cruza", .66, 1, .8], ["perro", .55, "deambula", [.7, .86], 1, .8]],
  boyaca: [["burro", 1.2, "cruza", .66, 1, .5], ["gallina", .4, "deambula", [.72, .88], 2, .45], ["bici", 1.6, "cruza", .7, 1, 2.2], ["perro", .55, "deambula", [.72, .88], 1, .8]],
  tatacoa: [["chivo", .8, "deambula", [.7, .82], 3, .4], ["gallinazo", .6, "deambula", [.74, .84], 1, .2]],
  // Plaza de Sincelejo (lo propuso el enjambre: mototaxi, perro a la sombra del portal, palomas, vendedor, bicicleta)
  sucre: [["moto", 1.5, "cruza", .67, 1, 2.4], ["perro", .55, "deambula", [.72, .9], 1, .8], ["paloma", .26, "deambula", [.7, .86], 3, .35],
          ["vendedor", 1.75, "cruza", .69, 1, .6], ["bici", 1.6, "cruza", .68, 1, 2.2]],
};
const M = .88;                                     // unidades de escena por metro (la gente: 1,45 ≈ 1,65 m)
const ambiente = (() => {
  let lista = [], clave = null, gen = 0;
  const ref = new THREE.PerspectiveCamera();
  function camRef() {
    ref.copy(camara); ref.position.copy(CAM_BASE); ref.lookAt(MIRA_BASE); ref.updateMatrixWorld(); ref.updateProjectionMatrix();
    return ref;
  }
  const pant = (c, x, z) => { const p = new THREE.Vector3(x, 0, z).project(c); return [(p.x * .5 + .5), (-p.y * .5 + .5)]; };
  /* fracción de la imagen → profundidad del piso donde cae ese punto (bisección) */
  function zDe(fy) {
    const c = camRef(), r = host.getBoundingClientRect(), obj = imgAPantalla(.5, fy).y / (MUNDO.h || 1);
    let lo = -60, hi = 5;                          // más lejos = más arriba en pantalla
    for (let i = 0; i < 30; i++) { const m = (lo + hi) / 2; if (pant(c, 0, m)[1] < obj) lo = m; else hi = m; }
    return (lo + hi) / 2;
  }
  /* a esa profundidad, qué x queda en el borde izquierdo y derecho de la pantalla (lineal en x) */
  function bordes(z) {
    const c = camRef(), a = pant(c, 0, z)[0], b = pant(c, 1, z)[0], k = b - a;
    return [(0 - a) / k, (1 - a) / k];
  }
  async function uno(def, i, g) {
    const [spr, alto, modo, fy, , vel] = def;
    const a = await actor("amb", `escenas/amb/${spr}.webp`, alto * M, 1);
    if (g !== gen) { scene.remove(a); return; }
    a.children[0].scale.set(1.25, 1, 1);           // la sombra de un animal es más larga que alta
    const u = a.userData;
    Object.assign(u, { amb: modo, vel: vel * M, fy, spr, espera: 0, meta: null });
    if (modo === "cruza") {
      u.espera = performance.now() + (i === 0 ? 1500 + Math.random() * 5000 : 6000 + Math.random() * 16000);
      a.visible = false;
    } else colocar(a, true);
    lista.push(a);
  }
  function colocar(a, inicio) {
    const u = a.userData;
    if (u.amb === "cruza") {
      const fy = u.fy + (Math.random() - .5) * .015, z = zDe(fy), [x0, x1] = bordes(z), dir = Math.random() < .5 ? 1 : -1;
      // el tramo del carril que es piso (en una calle angosta, solo el fondo de la calle): se entra y se sale por ahí
      let a0 = 0, a1 = 1;
      if (SUELO[sueloK]) { let d = null, h = null; for (let fx = 0; fx <= 1.0001; fx += .01) if (sueloEn(fx) < fy - .01) { if (d === null) d = fx; h = fx; }
        if (d === null) { u.espera = performance.now() + 20000; return; } a0 = d; a1 = h; }
      const xa = imgAPiso(a0, fy)?.x ?? x0, xb = imgAPiso(a1, fy)?.x ?? x1, m = a0 < .02 && a1 > .98 ? (x1 - x0) * .08 + 1.5 : 0;
      a.position.set(dir > 0 ? Math.max(x0, xa) - m : Math.min(x1, xb) + m, 0, z);
      u.meta = new THREE.Vector3(dir > 0 ? Math.min(x1, xb) + m : Math.max(x0, xa) - m, 0, z);
      u.aparece = performance.now(); a.visible = true;
    } else {
      const [f0, f1] = u.fy;
      for (let i = 0; i < 14; i++) {                 // un sitio del piso, no encima de un techo
        const z = zDe(f0 + Math.random() * (f1 - f0)), [x0, x1] = bordes(z), w = x1 - x0;
        a.position.set(x0 + w * (.12 + Math.random() * .76), 0, z);
        if (caminable(a.position.x, a.position.z, u.alto)) break;
      }
      u.casa = a.position.clone(); u.espera = performance.now() + (inicio ? Math.random() * 4000 : 2500 + Math.random() * 7000);
    }
  }
  return {
    async poner(k) {
      if (k === clave) return;
      clave = k; gen++;
      for (const a of lista) scene.remove(a);
      lista = [];
      const defs = AMB[k] || [], g = gen;
      await Promise.all(defs.flatMap(d => Array.from({ length: d[4] }, (_, i) => uno(d, i, g))));
    },
    recolocar() { const k = clave; clave = null; if (k) this.poner(k); },
    cuadro(dt, t, ahora) {
      for (const a of lista) {
        const u = a.userData, c = u.cuerpo;
        a.quaternion.copy(camara.quaternion); a.rotation.x = 0; a.rotation.z = 0;
        if (u.amb === "cruza" && !a.visible) { if (ahora > u.espera) colocar(a); else continue; }
        if (!u.meta && u.amb === "deambula" && ahora > u.espera && !QUIETO) {
          // un paso corto cerca de su casa: picotear, olfatear, cambiar de lado
          const q = u.casa.clone().add(new THREE.Vector3((Math.random() - .5) * 2.4, 0, (Math.random() - .5) * .8));
          if (caminable(q.x, q.z, u.alto)) u.meta = q; else u.espera = ahora + 1500;   // no se sube a un techo
        }
        let anda = false;
        if (u.meta && !QUIETO) {
          tmp.subVectors(u.meta, a.position); const d = tmp.length();
          if (d > .04) { a.position.addScaledVector(tmp.normalize(), Math.min(d, u.vel * dt)); anda = true;
            if (Math.abs(tmp.x) > .05) c.scale.x = tmp.x < 0 ? -1 : 1; }
          else {
            u.meta = null;
            if (u.amb === "cruza") { a.visible = false; u.espera = ahora + 9000 + Math.random() * 22000; }
            else u.espera = ahora + 2000 + Math.random() * 7000;
          }
        }
        // paso: un píxel de rebote al ritmo de las patas (o el motor)
        const rueda = /taxi|willys|moto|bici|chiva|coche|carrito|canoa/.test(u.spr);
        const b = anda ? (rueda ? Math.abs(Math.sin(t * 18 + u.fase)) * .012 : Math.abs(Math.sin(t * 8 + u.fase)) * .03 * u.alto) : 0;
        c.position.y = u.alto / 2 + b;
        if (u.spr === "canoa") { c.position.y = u.alto / 2 - .06 + Math.sin(t * 1.7 + u.fase) * .02; a.children[0].visible = false; }
      }
    },
  };
})();

/* ── cámara 2D ─────────────────────────────────────────────────────────
   Cielo, fondo pintado y lienzo 3D viven juntos en #mundo y se acercan como una
   sola pieza (zoom sobre el cuadro): así el piso pintado y la gente nunca se
   desalinean. Globos y nombres quedan afuera, a tamaño legible.
   Sola: se acerca a quien habla (más si hay mucha gente) y vuelve al plano general.
   A mano: rueda = zoom hacia el cursor, arrastrar = mover, doble clic = todo. */
const mundo = document.createElement("div"); mundo.id = "mundo";
host.prepend(mundo);
const VISTA = { z: 1, fx: 0, fy: 0, zo: 1, fxo: 0, fyo: 0, hasta: 0, mano: 0, sigue: null, tx: 0, ty: 0 };
function vistaA(p) { return { x: VISTA.tx + p.x * VISTA.z, y: VISTA.ty + p.y * VISTA.z }; }
function enfocar(a, z, ms) {
  if (QUIETO || performance.now() < VISTA.mano) return;
  VISTA.sigue = a; VISTA.zo = z; VISTA.hasta = performance.now() + ms;
}
function general() { VISTA.sigue = null; VISTA.zo = 1; }
function camara2d(dt, ahora) {
  const W = host.clientWidth, H = host.clientHeight, MW = MUNDO.w;
  if (VISTA.sigue && VISTA.sigue.parent && ahora < Math.max(VISTA.hasta, VISTA.mano)) {
    const u = VISTA.sigue.userData, p = aPantalla(new THREE.Vector3(VISTA.sigue.position.x, u.alto * .62, VISTA.sigue.position.z));
    VISTA.fxo = p.x; VISTA.fyo = p.y;
  } else if (ahora > VISTA.mano) { general(); VISTA.fxo = MW / 2; VISTA.fyo = H / 2; }
  const k = QUIETO ? 1 : Math.min(1, dt * 2.2);          // se desliza, no salta
  VISTA.z += (VISTA.zo - VISTA.z) * k; VISTA.fx += (VISTA.fxo - VISTA.fx) * k; VISTA.fy += (VISTA.fyo - VISTA.fy) * k;
  const z = VISTA.z;
  VISTA.tx = Math.min(0, Math.max(W - MW * z, W / 2 - VISTA.fx * z));
  VISTA.ty = Math.min(0, Math.max(H - H * z, H * .55 - VISTA.fy * z));
  mundo.style.transform = `translate3d(${VISTA.tx.toFixed(1)}px,${VISTA.ty.toFixed(1)}px,0) scale(${z.toFixed(4)})`;
}
(() => {
  host.addEventListener("wheel", e => {
    if (e.target.closest(".cartel,.tablero,.globo")) return;
    e.preventDefault();
    const r = host.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
    if (e.ctrlKey) return; const zn = Math.min(2.4, Math.max(1, VISTA.zo * (e.deltaY < 0 ? 1.18 : .85)));
    // el punto bajo el cursor se queda quieto
    const lx = (mx - VISTA.tx) / VISTA.z, ly = (my - VISTA.ty) / VISTA.z;
    VISTA.sigue = null; VISTA.zo = zn; VISTA.fxo = lx + (r.width / 2 - mx) / zn; VISTA.fyo = ly + (r.height * .55 - my) / zn;
    VISTA.mano = performance.now() + 15000;
  }, { passive: false });
  let ini = null;
  host.addEventListener("pointerdown", e => {
    if (e.button !== 0 || !e.isPrimary || ini || e.target.closest("button,a,.cartel,.tablero")) return;   // un dedo manda; el segundo no reinicia
    ini = { x: e.clientX, y: e.clientY, fx: VISTA.fxo, fy: VISTA.fyo };
    if (e.pointerType === "mouse") try { host.setPointerCapture(e.pointerId); } catch (_) {}   // soltar fuera de la ventana también suelta
  });
  addEventListener("pointermove", e => {
    if (!ini || (VISTA.zo <= 1.01 && MUNDO.w <= host.clientWidth + 2)) return;
    VISTA.sigue = null; VISTA.mano = performance.now() + 15000;
    VISTA.fxo = ini.fx - (e.clientX - ini.x) / VISTA.z; VISTA.fyo = ini.fy - (e.clientY - ini.y) / VISTA.z;
  });
  addEventListener("pointerup", () => { ini = null; });
  addEventListener("pointercancel", () => { ini = null; });   // gesto cancelado (scroll, long-press): no queda enganchado
  host.addEventListener("dblclick", e => { if (e.target.closest("button,a,.cartel,.tablero,.globo")) return; VISTA.mano = 0; general(); });
  const bt = document.createElement("div"); bt.id = "zoomesc";
  bt.innerHTML = `<button type="button" data-z="1.25" aria-label="Acercar">+</button><button type="button" data-z=".8" aria-label="Alejar">−</button><button type="button" data-z="0" aria-label="Ver todo">⤢</button>`;
  bt.onclick = e => { const b = e.target.closest("button"); if (!b) return; const f = +b.dataset.z;
    if (!f) { VISTA.mano = 0; general(); return; }
    VISTA.sigue = null; VISTA.zo = Math.min(2.4, Math.max(1, VISTA.zo * f)); if (VISTA.zo === 1) { VISTA.mano = 0; return; }
    VISTA.mano = performance.now() + 15000; };
  host.append(bt);
})();
/* ── lugar ───────────────────────────────────────────────────────────── */
let lugarActual = null, capa = 0;
function lugar(k, pano = false) {
  if (!LUGARES[k]) k = "nacional";
  pano = !!pano && PANOS.has(k);
  if (k === lugarActual && pano === PANO) return;
  lugarActual = k; PANO = pano; IMG = pano ? { w: 2048, h: 896 } : { w: 1376, h: 768 };
  const base = pano ? k + "_pano" : k; sueloK = base; const arch = `escenas/${CIELOS[base] ? base + "_tierra" : base}.webp`;
  const siguiente = capaFondo[1 - capa];
  const img = new Image();
  const turno = lugar.turno = (lugar.turno || 0) + 1;
  img.onload = () => {
    if (turno !== lugar.turno) return;             // llegó tarde: ya se pidió otro fondo
    siguiente.style.backgroundImage = `url(${arch})`;
    siguiente.classList.add("on"); capaFondo[capa].classList.remove("on"); capa = 1 - capa;
  };
  img.src = arch;
  cielo.poner(base);
  ambiente.poner(k);
  const [nom, sub, t] = LUGARES[k];
  const [fy, esc] = (pano ? PISO_PANO[k] || [.86, 1.0] : PISO[k]) || [.84, 1]; pisoY = fy; ALTO = HORIZ[base] ? 1.45 : 1.45 * esc; medir(); niebla(base, t);
  tinte = new THREE.Color(t);
  for (const a of [...GENTE.values(), JUEZ, MESA]) a?.userData.cuerpo?.material.color.copy(tinte);
  const pl = $("#lugar");
  if (pl) { pl.querySelector("b").textContent = nom; pl.querySelector("span").textContent = sub;
    pl.classList.remove("entra"); void pl.offsetWidth; pl.classList.add("entra"); }
}

/* hablar de verdad: se detiene, levanta la mano, dice la idea, muestra su voto */
function hablaYa(r, txt, pos) {
  const a = GENTE.get(r.id); if (!a) return;
  if (a.userData.fuera || !a.userData.casa) a.userData.meta = null;   // quien habla no pasea (pero si viene llegando, sigue hasta su puesto)
  a.userData.habla = performance.now() + Math.min(3600, 900 + idea(txt).length * 25);
  a.userData.mano = performance.now() + 1400;             // pide la palabra
  a.userData.paseo = performance.now() + 9000;
  const muchos = [...GENTE.keys()].filter(k => !k.startsWith("__")).length;
  const angosto = host.clientWidth < 640;
  enfocar(a, muchos > 9 ? 1.55 : angosto ? 1.4 : muchos > 5 ? 1.18 : 1.08, Math.min(5200, 2200 + idea(txt).length * 30));
  a.userData.placa?.classList.add("ve");
  const h = a.userData._hablaN = (a.userData._hablaN || 0) + 1;
setTimeout(() => { if (a.userData._hablaN === h) a.userData.placa?.classList.remove("ve"); }, 6000);
  globo(a, `${r.nombre.split(" ")[0]} · ${r.edad}`, txt, pos);
  marca(a, pos);
}
let turnos = false, enTurno = false, modoActual = "tertulia";
const COLA = [];
function siguienteTurno() {
  const id = siguienteTurno.id = (siguienteTurno.id || 0) + 1;
  const t = COLA.shift();
  if (!t) { enTurno = false; return; }
  enTurno = true;
  hablaYa(...t);
  setTimeout(() => { if (id === siguienteTurno.id) siguienteTurno(); }, QUIETO ? 400 : Math.min(3800, 1600 + idea(t[1]).length * 18));
}
/* ── API que usa el sitio ────────────────────────────────────────────── */
const API = {
  lugarDe(sel) {
    const c = [...(sel || [])];
    return c.length === 1 ? (DPTO_LUGAR[c[0]] || "nacional") : "nacional";
  },
  lugar,
  async escena({ modo, lugar: k, sel, gente, pregunta }) {
    const gen = API.escena.gen = (API.escena.gen || 0) + 1;   // si llega otra escena, esta se retira
    const vieja = () => gen !== API.escena.gen;
    quitarTodos();
    modoActual = modo;
    API.turnos(modo === "sondeo");
    if (pregunta) API.titulo(pregunta, modo);
    lugar(k || (modo === "sondeo" ? "estudio" : API.lugarDe(sel)), modo !== "sondeo" && gente.length > 9);
    if (PANO && !QUIETO) { VISTA.fx = host.clientWidth / 2; VISTA.mano = 0; general(); }   // entra desde la izquierda
    camObj.copy(CAM_BASE); miraObj.copy(MIRA_BASE);
    const acomodo = modo === "sondeo" ? "publico" : modo === "pais" ? "pie" : "mesa";
    const U = utileriaDe(lugarActual);
    if (acomodo === "mesa") {
      const m = await actor("mesa", "escenas/" + (U?.mesa || "mesa.webp"), ALTO * .72, 1, true);
      if (vieja()) { scene.remove(m); return; }
      MESA = m;
      MESA.position.set(0, 0, 0.55 * escalaEscenario());
    }
    if (U && acomodo !== "publico") {           // ambiente: hasta 3 cosas del lugar, a los lados
      const cosas = U.cosas.slice(0, 3);
      await Promise.all(cosas.map(async (c, i) => {
        const a = await actor("cosa" + i, "escenas/" + c, ALTO * (i === 2 ? .7 : .85), 1, true);
        if (vieja()) { scene.remove(a); return; }
        const e = escalaEscenario(); a.position.set(COSAS[i][0] * e, 0, COSAS[i][1] * e);
        GENTE.set("__cosa" + i, a);
      }));
    }
    const P = puestos(gente.length, acomodo), ENT = acomodo === "publico" ? null : entradas();
    if (acomodo === "publico") {
      const j = await actor("juez", "gente/urbano_7_poses.webp", ALTO * 1.1, 4);
      if (vieja()) { scene.remove(j); return; }
      JUEZ = j;
      JUEZ.position.set(-3.35, 0, 1.15);
      // un podio delante de cada concursante: tapa de verdad (profundidad)
      await Promise.all(P.filter(p => p[2]).map(async ([x, z], i) => {
        const podio = await actor("podio" + i, "escenas/podio.webp", ALTO * .6, 1, true);
        if (vieja()) { scene.remove(podio); return; }
        podio.position.set(x, 0, z + .42);
        podio.children[0].visible = false;          // el podio no lleva sombra de persona
        GENTE.set("__podio" + i, podio);
      }));
    }
    await Promise.all(gente.map(async (r, i) => {
      const spr = r._spr || window.spriteDe?.(r) || "andino_0";
      const nc = (window.CATALOGO?.gente || []).find(g => g.id === spr)?.d || 4;
      const a = await actor(r.id, "gente/" + spr + "_poses.webp",
        ALTO * (.97 + (r.edad > 64 ? -.04 : 0) + (r.sexo === "mujer" ? -.03 : 0)), nc);
      if (vieja()) { scene.remove(a); return; }
      let [x, z] = P[i];
      if (!caminable(x, z)) {                             // el puesto cae en una pared: al piso más cercano
        let q = null;
        for (const rad of [.8, 1.5, 2.5, 4]) { q = puntoLibre(x, z, rad); if (q) break; }
        if (q) { x = q.x; z = q.z; }
      }
      a.userData.meta = new THREE.Vector3(x, 0, z);
      a.userData.casa = a.userData.meta.clone();
      a.userData.llegando = true;
      a.userData.paseo = performance.now() + 14000 + Math.random() * 30000;
      a.userData.quieto = acomodo === "publico";          // concursantes y público no pasean
      a.userData.edad = r.edad;
      a.userData.vel = 1.9 * (r.edad > 64 ? .68 : r.edad < 30 ? 1.12 : 1);   // los mayores caminan más despacio
      const fondo = i % 2 === 0;                          // unos llegan del fondo, otros por los lados
      if (QUIETO) a.position.set(x, 0, z);
      else {
        // llegan por donde se puede llegar: del fondo de la calle o por las orillas del piso
        const E = ENT || {};
        const o = fondo ? E.fondo : (x < 0 ? E.izq : E.der);
        if (o) {
          // en una plaza enorme el fondo queda a 30 m: se entra desde máximo 7 unidades de su puesto
          const v = new THREE.Vector3(o.x - x, 0, o.z - z), L = v.length();
          if (L > 7) { v.multiplyScalar(7 / L); if (!caminable(x + v.x, z + v.z)) v.multiplyScalar(.6); }
          a.position.set(x + v.x + (Math.random() - .5) * .8, 0, z + v.z + (Math.random() - .5) * .4);
        }
        else if (fondo) a.position.set(x * .6 + (Math.random() - .5) * 2, 0, -6.5);
        else a.position.set((x < 0 ? -1 : 1) * 9, 0, z - 1);
        a.userData.llega = performance.now() + i * (acomodo === "publico" ? 420 : 200);
      }
      placa(a, r.nombre.split(" ")[0]);
      if (gente.length > 9 || host.clientWidth < 640) a.userData.placa.classList.add("tenue");   // en teléfono no caben 8 nombres en fila
      GENTE.set(r.id, a);
    }));
  },
  piensa(r) { const a = GENTE.get(r.id); if (a) piensa(a); },
  habla(r, txt, pos) {
    if (turnos) { COLA.push([r, txt, pos]); if (!enTurno) siguienteTurno(); return; }
    hablaYa(r, txt, pos);
  },
  turnos(on) { turnos = !!on; COLA.length = 0; enTurno = false; },
  calma() { camObj.copy(CAM_BASE); miraObj.copy(MIRA_BASE); general(); },
  titulo(q, modo) {
    over.querySelectorAll(".rotulo").forEach(e => e.remove());
    const el = document.createElement("div");
    el.className = "rotulo";
    el.innerHTML = `<small></small><b></b>`;
    el.querySelector("small").textContent = { sondeo: "la pregunta del show", tertulia: "el tema de la mesa", pais: "el país responde" }[modo] || "la pregunta";
    el.querySelector("b").textContent = q;
    over.append(el);
  },
  cartel(html, pos) {
    over.querySelectorAll(".cartel,.globo").forEach(e => e.remove());
    const el = document.createElement("div");
    el.className = "cartel"; el.style.setProperty("--pc", COLOR[pos] || "#fcd116");
    const m = html.match(/^(<b>[\s\S]*?<\/b>)([\s\S]*)$/);
    el.innerHTML = m ? `${m[1]}<p>${m[2]}</p><small>completo en la conversación · clic para recoger</small>` : html;
    el.tabIndex = 0; el.setAttribute("role", "button"); el.setAttribute("aria-expanded", "true");
el.onclick = () => { clearTimeout(el._t); const ch = el.classList.toggle("chico"); el.setAttribute("aria-expanded", String(!ch)); };
el.onkeydown = e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); el.onclick(); } };
    over.append(el);
    el._t = setTimeout(() => el.classList.add("chico"), 9000);
    API.calma();
  },
  /* el show: el juez revela el tablero fila por fila */
  async tablero({ titulo, n, filas, nota }) {
    // espera a que termine la ronda de turnos: el show no se pisa a sí mismo
    const gen = API.escena.gen;
    while (enTurno) { await new Promise(s => setTimeout(s, 300)); if (gen !== API.escena.gen) return; }
    if (gen !== API.escena.gen) return;
    VISTA.mano = 0; general();
    over.querySelectorAll(".tablero,.juezdice,.globo").forEach(e => e.remove());
    const t = document.createElement("div");
    t.className = "tablero grande";
    t.innerHTML = `<h4></h4><ol></ol><small></small>`;
    t.querySelector("h4").textContent = titulo;
    t.querySelector("small").textContent = nota || "";
    const ol = t.querySelector("ol");
    filas.slice(0, 5).forEach((f, i) => {
      const li = document.createElement("li");
      li.innerHTML = `<span class="n">${i + 1}</span><span class="e"></span><span class="caras"></span><span class="c"></span>`;
      li.querySelector(".e").textContent = f.e; li.querySelector(".c").textContent = f.n;
      li.style.setProperty("--pc", COLOR[f.pos] || "#fcd116");
      li.style.setProperty("--pct-n", (f.n / Math.max(1, n)).toFixed(3));
      for (const spr of (f.caras || []).slice(0, 6)) {
        const im = document.createElement("img"); im.src = "gente/" + spr + ".webp"; im.alt = "";
        li.querySelector(".caras").append(im);
      }
      ol.append(li);
    });
    over.append(t);
    const dice = document.createElement("div");
    dice.className = "juezdice";
    over.append(dice);
    const decir = s => { dice.innerHTML = `<b>EL PRESENTADOR</b>`; dice.append(s); if (JUEZ) { JUEZ.userData.habla = performance.now() + 1100; JUEZ.userData.mano = performance.now() + 900; } };
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
mundo.append(host.querySelector("#cielo"), ...capaFondo, canvas);
window.ESCENA = API;
API._pinta = () => { for (let i = 0; i < 3; i++) cuadroForzado(); };
/* depuración: qué tan alta (fracción de la imagen) se ve una persona parada en (fx, fy) del fondo */
API._alto = (fx, fy) => {
  const p = imgAPiso(fx, fy); if (!p) return null;
  const k = Math.max(MUNDO.w / IMG.w, MUNDO.h / IMG.h), ih = IMG.h * k;
  const b = aPantalla(new THREE.Vector3(p.x, 0, p.z)), c = aPantalla(new THREE.Vector3(p.x, ALTO, p.z));
  return +((b.y - c.y) / ih).toFixed(4);
};
API._cam = () => {           // depuración: cámara y ancho visible del escenario (z = -0,3)
  const c = aPantalla(new THREE.Vector3(0, 0, -.3)), d = aPantalla(new THREE.Vector3(1, 0, -.3));
  return { cam: CAM_BASE.toArray().map(v => +v.toFixed(2)), mira: +MIRA_BASE.y.toFixed(2), medioAncho: +(MUNDO.w / 2 / (d.x - c.x)).toFixed(2), piso: +(c.y / MUNDO.h).toFixed(3) };
};
API._camina = (i, fx, fy) => {   // depuración: manda a la persona i a un punto del cuadro
  const a = [...GENTE.entries()].filter(([k]) => !k.startsWith("__"))[i]?.[1], q = imgAPiso(fx, fy);
  if (a && q) { a.userData.meta = q; a.userData.fuera = true; a.userData.salio = performance.now(); a.userData.llega = 0; }
  return !!(a && q && caminable(q.x, q.z));
};
API._diag = () => ({ gente: GENTE.size, juez: !!JUEZ, pos: [...GENTE.values()].map(a => a.position.toArray().map(v => +v.toFixed(2))), cam: camara.position.toArray().map(v => +v.toFixed(2)) });
for (const [m, a] of (window.ESC_Q || []).splice(0)) API[m]?.(...a);

/* empuje para no atravesar a los demás: personas (radio 0,3), mesa (0,9), cosas y podios (0,5) */
function esquive(a) {
  let x = 0, z = 0;
  for (const b of [...GENTE.values(), MESA]) {
    if (!b || b === a || !b.visible) continue;
    const r = (b === MESA ? .9 : b.userData.estatico ? .5 : .3) + .32;
    const dx = a.position.x - b.position.x, dz = a.position.z - b.position.z, d = Math.hypot(dx, dz);
    if (d < r && d > 1e-4) { const k = (r - d) / r; x += dx / d * k; z += dz / d * k; }
  }
  return x || z ? { x, z } : null;
}
/* ── bucle ───────────────────────────────────────────────────────────── */
function medir() {
  const r = host.getBoundingClientRect();
  if (!r.width) return;
  mundoTam();
  mundo.style.width = MUNDO.w + "px"; mundo.style.right = "auto";
  renderer.setSize(MUNDO.w, MUNDO.h, false);
  camara.aspect = MUNDO.w / MUNDO.h;
  // en pantallas angostas, la cámara se aleja para que quepa la gente
  const va = r.width / r.height;
  if (!HORIZ[sueloK]) CAM_BASE.z = va < 1 ? 17.5 : va < 1.4 ? 14.5 : 12.5;
  camara.updateProjectionMatrix();
  encuadrar(); ubicarTablero(); cielo.medir();
  clearTimeout(medir.t); medir.t = setTimeout(() => ambiente.recolocar(), 400);
}
new ResizeObserver(medir).observe(host);
medir();
let visible = true;
new IntersectionObserver(e => { visible = e[0].isIntersecting; }).observe(host);
const reloj = new THREE.Clock();
const tmp = new THREE.Vector3();
/* vida entre turnos: de a uno o dos, alguien va a la mesa (se sirve un tinto),
   se acerca a una cosa del lugar o da unos pasos, y vuelve a su puesto */
function pasear(ahora) {
  let andando = 0;
  for (const a of GENTE.values()) if (a.userData.meta && !a.userData.estatico) andando++;
  for (const a of GENTE.values()) {
    const u = a.userData;
    if (u.estatico || u.quieto || !u.casa || u.meta || u.habla > ahora || ahora < u.paseo || andando >= 2 || modoActual === "sondeo") continue;
    if (u.fuera) {                                         // de vuelta a su puesto
      u.meta = u.casa.clone(); u.fuera = false; u.salio = ahora; u.paseo = ahora + 20000 + Math.random() * 25000; andando++; continue;
    }
    const r = Math.random();
    if (r < .3) {                                          // se va a charlar con otro, de lado a lado
      const otros = [...GENTE.values()].filter(b => b !== a && !b.userData.estatico && !b.userData.meta && b.userData.habla < ahora && b.userData.casa);
      const o = otros[Math.floor(Math.random() * otros.length)];
      if (o) {
        const lado = a.position.x < o.position.x ? -.75 : .75, q = new THREE.Vector3(o.position.x + lado, 0, o.position.z + .05);
        if (caminable(q.x, q.z, u.alto)) {
          u.meta = q; u.fuera = true; u.salio = ahora; u.charla = ahora + 9000;
          o.userData.paseo = Math.max(o.userData.paseo, ahora + 12000);          // el otro lo espera
          setTimeout(() => { if (o.parent) o.userData.mano = performance.now() + 900; }, 1800);
          u.paseo = ahora + 7000 + Math.random() * 5000; andando++; continue;
        }
      }
    } else if (r < .55) {                                  // cruza la plaza o sube la calle, y vuelve
      const L = SUELO[sueloK];
      for (let i = 0; L && i < 16; i++) {
        const fx = .08 + Math.random() * .84, s0 = sueloEn(fx), fy = s0 + .02 + Math.random() * Math.max(.02, .93 - s0 - .02);
        const q = imgAPiso(fx, fy);
        if (q && caminable(q.x, q.z, u.alto)) { u.meta = q; u.fuera = true; u.salio = ahora; u.paseo = ahora + 3500 + Math.random() * 4000; andando++; break; }
      }
      if (u.meta) continue;
    }
    const dianas = [MESA, ...[...GENTE.values()].filter(g => g.userData.id?.startsWith?.("cosa"))].filter(Boolean);
    let q = null;
    if (dianas.length && Math.random() < .6) {
      const d = dianas[Math.floor(Math.random() * dianas.length)];
      q = puntoLibre(d.position.x + (a.position.x < d.position.x ? -.8 : .8), d.position.z + .15, .35, u.alto);
      if (q && d === MESA) u.sirve = true;
    }
    q = q || puntoLibre(u.casa.x, u.casa.z, 1.6, u.alto);
    if (!q) { u.paseo = ahora + 6000; continue; }
    u.meta = q; u.fuera = true; u.salio = ahora; u.paseo = ahora + 2500 + Math.random() * 3000; andando++;
  }
}
function cuadro() {
  requestAnimationFrame(cuadro);
  if (!visible || document.hidden) return;
  cuadroForzado();
}
function cuadroForzado() {
  const dt = Math.min(reloj.getDelta(), .25), t = reloj.elapsedTime, ahora = performance.now();
  camara.position.lerp(camObj, QUIETO ? 1 : dt * 1.6);
  mira.lerp(miraObj, QUIETO ? 1 : dt * 1.6);
  if (!QUIETO) camara.position.x += Math.sin(t * .23) * .002;        // la cámara respira, no se pasea
  if (!QUIETO) pasear(ahora);
  camara.lookAt(mira);
  camara2d(dt, ahora);
  cielo.cuadro(dt, t, ahora);
  ambiente.cuadro(dt, t, ahora);
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
        tmp.normalize();
        // esquiva: nadie atraviesa a nadie ni a la mesa; el empuje es lateral y suave
        const ex = esquive(a);
        if (ex) { tmp.x += ex.x * 1.6; tmp.z += ex.z * 1.6; tmp.normalize(); }
        const paso = Math.min(d, u.vel * dt), nx = a.position.x + tmp.x * paso, nz = a.position.z + tmp.z * paso;
        // y no se sale del piso pintado: si el paso cae en una pared, resbala por el borde
        if (!u.llegando && !caminable(nx, nz, u.alto) && caminable(a.position.x, a.position.z, u.alto)) {
          if (caminable(nx, a.position.z, u.alto)) a.position.x = nx;
          else if (caminable(a.position.x, nz, u.alto)) a.position.z = nz;
          else u.meta = null;
        } else a.position.set(nx, 0, nz);
        if (u.meta && ahora - (u.salio || ahora) > 16000) u.meta = null;     // atascado: se queda donde está
        if (u.llegando && caminable(a.position.x, a.position.z, u.alto)) u.llegando = false;
        brinco = Math.abs(Math.sin(t * 9 + u.fase)) * .035;              // pasos
        anda = true;
        // hacia dónde mira: de lado (se refleja a la izquierda), de espaldas si se aleja, de frente si viene
        u.dir = Math.abs(tmp.x) > Math.abs(tmp.z) * 1.1 ? "lado" : tmp.z < 0 ? "espalda" : "frente";
        c.scale.x = u.dir === "lado" && tmp.x < 0 ? -1 : (u.cuadros === 8 || u.dir === "lado") ? 1 : c.scale.x;
        if (u.cuadros < 8 && Math.abs(tmp.x) > Math.abs(tmp.z) * .5) c.scale.x = (tmp.x < 0 ? -1 : 1);
      } else {
        u.meta = null; c.scale.x = 1; u.dir = null; u.salio = 0;
        if (u.charla && ahora < u.charla) { u.mano = ahora + 900; const e = document.createElement("div");
          e.className = "marca taza"; e.textContent = "💬"; pegar(e, a, -4); setTimeout(() => e.remove(), 2200); }
        if (u.sirve) { u.sirve = false; u.mano = ahora + 900; const e = document.createElement("div");
          e.className = "marca taza"; e.textContent = "☕"; pegar(e, a, -4); setTimeout(() => e.remove(), 1600); }
      }
    }
    if (u.habla > ahora && u.cuadros < 4) brinco = Math.max(brinco, Math.abs(Math.sin(t * 16)) * .06);
    if (u.cuadros >= 4) {
      const k = Math.floor(t * 6 + u.fase);
      const f = !anda ? (u.mano > ahora ? 3 : 0)
        : u.cuadros === 8 && u.dir === "lado" ? 4 + k % 2
        : u.cuadros === 8 && u.dir === "espalda" ? 6 + k % 2
        : [1, 0, 2, 0][k % 4];
      if (f !== u.cuadro) { u.cuadro = f; c.material.map.offset.x = f / u.cuadros; }
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
