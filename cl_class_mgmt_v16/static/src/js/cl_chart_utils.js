/** @odoo-module **/

// Utilidades puras y reutilizables para dibujar gráficos en SVG a mano
// (sin librerías externas, ver claude.md sección 7). Cada dashboard las usa
// para no repetir la geometría de barras/donut en cada componente.

const TAU = 2 * Math.PI;
const DEFAULT_OPACITY_STEPS = [1, 0.82, 0.66, 0.52, 0.4, 0.3, 0.22, 0.16];

// Paleta categórica fija (8 matices, orden validado para separación bajo
// daltonismo -- ver dataviz skill references/palette.md). Se usa cuando las
// porciones son entidades DISTINTAS que hay que poder diferenciar de un
// vistazo (ej. campus, nivel) y no alcanza con un solo tono + opacidad
// (varias porciones de tamaño parecido se ven casi iguales). Para series de
// 2-3 categorías fijas y ya identificadas por ícono/texto (ej. el donut de
// demografía del dashboard docente), seguir usando el modo "mono".
export const CATEGORICAL_PALETTE = [
    "#2a78d6", "#1baf7a", "#eda100", "#008300",
    "#4a3aa7", "#e34948", "#e87ba4", "#eb6834",
];

/**
 * Convierte una lista de {label, value} en porciones de donut, ordenadas de
 * mayor a menor valor. Dos modos:
 *  - "mono" (default): un solo color, opacidad decreciente según el tamaño
 *    relativo (identidad ya dada por ícono/texto, no hace falta más).
 *  - "categorical": un color distinto de CATEGORICAL_PALETTE por porción,
 *    para cuando las categorías en sí necesitan distinguirse por color
 *    (ej. "secciones por campus"). El color se asigna por posición en ESTE
 *    render (orden de mayor a menor valor), no por identidad persistente
 *    de la entidad -- aceptable para conjuntos abiertos (nombres de campus/
 *    nivel que varían por instalación), a costa de que el color de una
 *    misma entidad puede cambiar si el orden cambia entre refrescos.
 */
export function computeDonutSlices(items, options = {}) {
    const radius = options.radius ?? 40;
    const gap = options.gap ?? 1.4;
    const circumference = TAU * radius;
    const total = items.reduce((sum, it) => sum + (it.value || 0), 0);
    const mode = options.mode ?? "mono";
    const opacitySteps = options.opacitySteps ?? DEFAULT_OPACITY_STEPS;
    const palette = options.palette ?? CATEGORICAL_PALETTE;

    let cumulative = 0;
    return items
        .slice()
        .sort((a, b) => b.value - a.value)
        .map((item, index) => {
            const share = total ? item.value / total : 0;
            const rawLength = share * circumference;
            const length = Math.max(0, rawLength - gap);
            const dasharray = `${length} ${circumference - length}`;
            const dashoffset = -cumulative;
            cumulative += rawLength;
            const isCategorical = mode === "categorical";
            const opacity = isCategorical ? 1 : (opacitySteps[index] ?? opacitySteps[opacitySteps.length - 1]);
            // item.color gana siempre que el backend ya trae un color propio
            // (ej. semáforo de capacidad: verde/ámbar/rojo por sección) --
            // el color derivado del modo (mono/categorical) es solo un
            // fallback para series sin color explícito.
            const color = item.color || (isCategorical ? palette[index % palette.length] : (options.color || null));
            return { ...item, pct: total ? Math.round(share * 100) : 0, dasharray, dashoffset, opacity, color, radius };
        });
}

/**
 * Porción única de "medidor" (gauge): un valor 0-100 lleno sobre el track
 * completo (ya dibujado como círculo de fondo). Para KPIs porcentuales sin
 * un desglose real detrás -- NO es una serie categórica, es un solo valor
 * contra su propio límite (100%).
 */
export function computeMeterSlice(value, options = {}) {
    const total = options.total ?? 100;
    const radius = options.radius ?? 40;
    const circumference = TAU * radius;
    const share = total ? Math.min(1, Math.max(0, value / total)) : 0;
    const length = share * circumference;
    return {
        value,
        pct: Math.round(share * 100),
        dasharray: `${length} ${circumference - length}`,
        dashoffset: 0,
        radius,
    };
}

/**
 * Convierte una lista de {label, value} en anchos de barra (%) relativos
 * al valor máximo del conjunto. No ordena la lista (se respeta el orden
 * de entrada, ej. ya ordenado por el backend).
 */
export function computeBarWidths(items, options = {}) {
    const minWidth = options.minWidth ?? 4;
    const max = Math.max(1, ...items.map((it) => it.value || 0));
    const mode = options.mode ?? "mono";
    const palette = options.palette ?? CATEGORICAL_PALETTE;
    return items.map((item, index) => ({
        ...item,
        width: item.value ? Math.max(minWidth, (item.value / max) * 100) : 0,
        // item.color gana siempre que el backend ya trae un color propio
        // (ver mismo criterio en computeDonutSlices).
        color: item.color || (mode === "categorical" ? palette[index % palette.length] : (options.color || null)),
    }));
}

/**
 * Serie temporal simple ({date, value}[], value 0-100) convertida a un path
 * SVG (línea + área) dentro de un viewBox "0 0 width height". A mano, sin
 * librerías -- usado para el histórico de KPIs (ver cl.teacher.kpi.snapshot).
 */
export function computeLineChart(points, options = {}) {
    const width = options.width ?? 100;
    const height = options.height ?? 40;
    const padding = options.padding ?? 4;
    if (!points.length) return { path: "", area: "", points: [], width, height };
    const min = options.min ?? 0;
    const max = options.max ?? 100;
    const range = Math.max(1, max - min);
    const stepX = points.length > 1 ? (width - 2 * padding) / (points.length - 1) : 0;
    const coords = points.map((p, index) => ({
        x: padding + index * stepX,
        y: height - padding - ((p.value - min) / range) * (height - 2 * padding),
        value: p.value,
        date: p.date,
    }));
    const path = coords.map((c, index) => `${index === 0 ? "M" : "L"}${c.x.toFixed(2)},${c.y.toFixed(2)}`).join(" ");
    const baseline = height - padding;
    const area = `${path} L${coords[coords.length - 1].x.toFixed(2)},${baseline} L${coords[0].x.toFixed(2)},${baseline} Z`;
    return { path, area, points: coords, width, height };
}
