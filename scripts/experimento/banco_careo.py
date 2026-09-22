import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

# Patrones de extracción sobre la salida de texto de careo_ecp.py
RX_W1 = re.compile(r'W1 normalizado = ([0-9.]+)')
RX_RAZON = re.compile(r'razón ([0-9.]+)')
RX_AZAR = re.compile(r"al azar'\s+= ([0-9.]+)")
RX_NSNC = re.compile(r'no sabe / no informa\s+([0-9.]+)%\s+([0-9.]+)%')
RX_NOMBRE = re.compile(r'^rep_(.+?)_(.+)\.json$')


def localizar_runner():
    # El corredor vive en el árbol del proyecto; se busca en ubicaciones plausibles
    aqui = Path(__file__).resolve().parent
    candidatos = [
        Path('scripts/experimento/careo_ecp.py'),
        aqui / 'scripts/experimento/careo_ecp.py',
        aqui.parent / 'scripts/experimento/careo_ecp.py',
    ]
    for c in candidatos:
        if c.is_file():
            return c
    return None


def medir_celda(ruta, runner):
    # Nunca lanza: si algo falla, la celda se queda con None y el informe dirá '—'
    try:
        meta = json.loads(ruta.read_text(encoding='utf-8'))
    except Exception:
        return None
    celda = {
        'w1': None,
        'razon': None,
        'azar': None,
        'nsnc_humano': None,
        'nsnc_sintetico': None,
        'vacias': meta.get('vacias', 0) or 0,
    }
    if runner is not None:
        try:
            proc = subprocess.run(
                [sys.executable, str(runner), str(ruta)],
                capture_output=True, text=True, timeout=300,
            )
            texto = (proc.stdout or '') + '\n' + (proc.stderr or '')
        except Exception:
            texto = ''
        m = RX_W1.search(texto)
        if m:
            celda['w1'] = float(m.group(1))
        m = RX_RAZON.search(texto)
        if m:
            celda['razon'] = float(m.group(1))
        m = RX_AZAR.search(texto)
        if m:
            celda['azar'] = float(m.group(1))
        m = RX_NSNC.search(texto)
        if m:
            celda['nsnc_humano'] = float(m.group(1))
            celda['nsnc_sintetico'] = float(m.group(2))
    return celda


def fmt_celda(celda, negrita=False):
    if celda is None or celda['w1'] is None:
        return '—'
    s = f"{celda['w1']:.4f}"
    if negrita:
        s = f"**{s}**"
    # Fallo cualitativo: rendir peor que responder al azar no es "un número más alto"
    if celda['azar'] is not None and celda['w1'] > celda['azar']:
        s += ' ⚠ peor que el azar'
    return s


def p_binomial_dos_colas(victorias, decisivas):
    # p exacto de dos colas con math.comb: masa de la cola extrema, duplicada
    if decisivas == 0:
        return 1.0
    k = min(victorias, decisivas - victorias)
    masa = sum(math.comb(decisivas, i) for i in range(k + 1)) / (2 ** decisivas)
    return min(1.0, 2.0 * masa)


def main():
    ap = argparse.ArgumentParser(description='Banco de careo entre flotas simuladoras')
    ap.add_argument('--dir', required=True)
    ap.add_argument('--salida', required=True)
    args = ap.parse_args()

    runner = localizar_runner()
    datos = {}
    nombres_flotas = set()
    for ruta in sorted(Path(args.dir).glob('rep_*.json')):
        m = RX_NOMBRE.match(ruta.name)
        if not m:
            continue
        pregunta, flota = m.group(1), m.group(2)
        nombres_flotas.add(flota)
        datos.setdefault(pregunta, {})[flota] = medir_celda(ruta, runner)

    preguntas = sorted(datos)
    flotas = sorted(nombres_flotas)
    lineas = []

    lineas.append('# Banco de careo')
    if runner is None:
        lineas.append('')
        lineas.append('No se encontró scripts/experimento/careo_ecp.py: todas las celdas quedan sin valor (—).')

    # 1. Matriz W1: menor es mejor; negrita en el mínimo de cada fila
    lineas.append('')
    lineas.append('## 1. Matriz W1 (menor es mejor)')
    encabezado = '| Pregunta | ' + ' | '.join(flotas) + ' | gana |'
    lineas.append(encabezado)
    lineas.append('|' + ' --- |' * (len(flotas) + 2))

    # (pregunta, flota_a, flota_b) -> 'a' | 'b' | 'empate', para el test de signos
    ganadores = {}
    celdas_sin_valor = 0

    for p in preguntas:
        fila = datos[p]
        w1s = {}
        for f in flotas:
            c = fila.get(f)
            w1s[f] = c['w1'] if c is not None else None
        validos = {f: v for f, v in w1s.items() if v is not None}
        orden = sorted(validos.items(), key=lambda kv: kv[1])
        minimo = orden[0][1] if orden else None

        celdas_fila = []
        for f in flotas:
            c = fila.get(f)
            negrita = minimo is not None and w1s[f] is not None and w1s[f] == minimo
            celdas_fila.append(fmt_celda(c, negrita))
            if c is None or c['w1'] is None:
                celdas_sin_valor += 1

        # gana: empate si el segundo está a menos de 0.01 del primero
        if len(orden) == 0:
            g = '—'
        elif len(orden) == 1:
            g = orden[0][0]
        elif orden[1][1] - orden[0][1] < 0.01:
            g = 'empate'
        else:
            g = orden[0][0]
        ganadores[p] = g
        lineas.append(f'| {p} | ' + ' | '.join(celdas_fila) + f' | {g} |')

    # 2. Resumen de alarmas (las marcas ⚠ ya van dentro de la matriz)
    n_alarma = 0
    for p in preguntas:
        for f in flotas:
            c = datos[p].get(f)
            if c and c['w1'] is not None and c['azar'] is not None and c['w1'] > c['azar']:
                n_alarma += 1
    lineas.append('')
    lineas.append('## 2. Alarma por celda')
    lineas.append(f'{n_alarma} celda(s) con W1 sobre su propio baseline de azar (marcadas ⚠ en la matriz): '
                  'ahí el simulador no aporta nada.')
    if celdas_sin_valor:
        lineas.append(f'{celdas_sin_valor} celda(s) quedaron como —: careo_ecp.py falló o su salida no casó '
                      'con los patrones de extracción; ninguna se contó como 0.')

    # 3. Test de signos entre las dos flotas con más preguntas en común
    lineas.append('')
    lineas.append('## 3. Test de signos')
    mejor_par, mejor_comunes = None, -1
    for i in range(len(flotas)):
        for j in range(i + 1, len(flotas)):
            a, b = flotas[i], flotas[j]
            comunes = sum(
                1 for p in preguntas
                if datos[p].get(a) and datos[p].get(b)
                and datos[p][a]['w1'] is not None and datos[p][b]['w1'] is not None
            )
            if comunes > mejor_comunes:
                mejor_comunes, mejor_par = comunes, (a, b)

    if mejor_par is None or mejor_comunes == 0:
        lineas.append('No hay dos flotas con preguntas comparables: test de signos no aplicable.')
    else:
        a, b = mejor_par
        va = vb = empates = 0
        for p in preguntas:
            g = ganadores.get(p)
            if g == a:
                va += 1
            elif g == b:
                vb += 1
            elif g == 'empate':
                empates += 1
        # Los empates se descartan del test: solo cuentan decisiones
        decisivas = va + vb
        p_valor = p_binomial_dos_colas(va, decisivas)
        lineas.append(f'Comparación: {a} vs {b} ({mejor_comunes} preguntas en común; '
                      f'{empates} empate(s) descartados del test).')
        lineas.append(f'{va} victorias de {decisivas} decisivas, p = {p_valor:.4f}')
        if p_valor < 0.05:
            lineas.append('Lectura: la diferencia difícilmente es casualidad.')
        elif p_valor < 0.15:
            lineas.append('Lectura: dirección consistente, evidencia modesta.')
        else:
            lineas.append('Lectura: no se puede distinguir del azar.')

    # 4. Respuestas vacías por flota
    lineas.append('')
    lineas.append('## 4. Respuestas vacías')
    for f in flotas:
        total = sum(
            (datos[p].get(f) or {}).get('vacias', 0) or 0
            for p in preguntas
        )
        lineas.append(f'- {f}: {total}')

    # 5. Advertencia fija de dos líneas
    lineas.append('')
    lineas.append(f'> Advertencia: este informe usa {len(preguntas)} preguntas.')
    lineas.append('> Con pocos ítems un test de signos casi nunca alcanza p<0.05 aunque la dirección sea clara; '
                  'un p alto no demuestra que los modelos sean iguales.')

    texto = '\n'.join(lineas) + '\n'
    print(texto, end='')
    Path(args.salida).write_text(texto, encoding='utf-8')


if __name__ == '__main__':
    main()