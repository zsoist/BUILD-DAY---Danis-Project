import { spawn } from 'node:child_process';
import { access, constants } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Ruta al generador de voces. Este barrido vive en una carpeta hermana de experimento/.
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RUTA_CAREO = path.resolve(__dirname, '../experimento/careo_ecp.mjs');

// DOCUMENTACIÓN DEL CONTRATO: careo_ecp.mjs DEBE leer la variable de entorno TEMP_VOZ
// (número flotante, ej. 1.2) y usarla como temperatura de muestreo de todas las voces.
// Si TEMP_VOZ no está definida, careo_ecp.mjs cae a su valor por defecto interno (se asume 0.8).
// Toda la temperatura viaja por entorno: así el proceso hijo es exactamente el mismo script
// que produce el banco, y las corridas entre temperaturas siguen siendo comparables.

async function existe(p) {
  try { await access(p, constants.F_OK); return true; } catch { return false; }
}

// Corre una temperatura lanzando careo_ecp.mjs como hijo (opción preferida: nada de
// duplicar lógica de muestreo, que rompería la comparabilidad entre corridas).
function correrTemp(temp, n, codigo, carpeta, flota) {
  return new Promise((resolve, rechazar) => {
    const hijo = spawn(process.execPath, [RUTA_CAREO, String(n), codigo, carpeta], {
      env: { ...process.env, TEMP_VOZ: temp, ENJAMBRE: flota },
      stdio: 'inherit',
    });
    hijo.on('error', rechazar);
    hijo.on('close', (codigoSalida) => {
      if (codigoSalida === 0) resolve();
      else rechazar(new Error(`careo_ecp.mjs salió con código ${codigoSalida} en T=${temp}`));
    });
  });
}

async function main() {
  const [nArg, codigo, carpeta, tempsArg] = process.argv.slice(2);
  if (!nArg || !codigo || !carpeta) {
    console.error('uso: node barrido_temp.mjs <N> <CODIGO_PREGUNTA> <carpeta_salida> <temps>');
    process.exit(1);
  }
  const n = Number(nArg);
  // Temperaturas por defecto: la grilla mínima para distinguir corrección por muestreo
  // de colapso estructural del modelo (por debajo de 0.8 ya es la zona de colapso).
  const temps = (tempsArg ? tempsArg.split(',').map(s => s.trim()).filter(Boolean) : ['0.8', '1.0', '1.2', '1.4']);

  // Si el generador exporta algo utilizable lo importamos; si no, spawn por temperatura.
  let exportaFn = null;
  try {
    const mod = await import(urlDe(RUTA_CAREO));
    const clave = Object.keys(mod).find(k => typeof mod[k] === 'function' && k !== 'default');
    if (typeof mod.default === 'function') exportaFn = mod.default;
    else if (clave) exportaFn = mod[clave];
  } catch { /* no exporta nada o no se puede importar: usamos spawn */ }

  const flota = process.env.ENJAMBRE || 'glm';

  // Concurrencia máxima 2: más de dos en paralelo contra el mismo proveedor dispara
  // 429, los reintentos contaminan la comparación entre temperaturas.
  const COLA = temps.slice();
  const MAX_EN_VUELO = 2;
  const errores = [];

  async function trabajador() {
    while (COLA.length) {
      const temp = COLA.shift();
      const t0 = Date.now();
      try {
        if (exportaFn) {
          const previa = process.env.TEMP_VOZ;
          process.env.TEMP_VOZ = temp;
          try { await exportaFn(String(n), codigo, carpeta); }
          finally { process.env.TEMP_VOZ = previa; }
        } else {
          await correrTemp(temp, n, codigo, carpeta, flota);
        }
        const archivo = path.join(carpeta, `rep_${codigo}_${flota}T${temp}.json`);
        if (!(await existe(archivo))) {
          errores.push(`T=${temp}: careo_ecp.mjs terminó pero no escribió ${archivo}`);
        }
        console.log(`T=${temp}: ${(Date.now() - t0) / 1000}s`);
      } catch (e) {
        errores.push(`T=${temp}: ${e.message}`);
        console.error(`T=${temp} FALLÓ tras ${(Date.now() - t0) / 1000}s: ${e.message}`);
      }
    }
  }

  await Promise.all(Array.from({ length: Math.min(MAX_EN_VUELO, temps.length) }, trabajador));

  if (errores.length) {
    console.error('Barrido con errores:');
    for (const e of errores) console.error(`  - ${e}`);
    process.exit(1);
  }

  // Comando del banco de careo para medir lo generado, sin cambios.
  console.log(`\nMedir con:\n  node scripts/experimento/banco_careo.mjs ${carpeta}`);
}

function urlDe(p) {
  return 'file://' + p.split(path.sep).map(encodeURIComponent).join('/');
}

main().catch((e) => { console.error(e); process.exit(1); });