/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { computeDonutSlices, computeBarWidths, computeMeterSlice } from "@cl_class_mgmt_v16/js/cl_chart_utils";

const KPI_ICONS = {
    total_secciones_activas: "fa-list-alt",
    total_estudiantes: "fa-users",
    pct_asistencias_al_dia: "fa-check-circle",
    pct_evaluaciones_al_dia: "fa-pencil-square-o",
    secciones_por_campus: "fa-university",
    estudiantes_por_nivel: "fa-signal",
    progreso_encuentros: "fa-tasks",
    progreso_evaluaciones: "fa-check-square-o",
    mejores_secciones_promedio: "fa-star",
    alertas_academicas: "fa-exclamation-triangle",
};

const ALERT_TYPES = [
    { key: "Reprobados", label: "Secciones con más de 25% de estudiantes reprobados", icon: "fa-graduation-cap" },
    { key: "Inasistencia alta", label: "Secciones con estudiantes con más de 25% de inasistencias", icon: "fa-user-times" },
    { key: "Inasistencia consecutiva", label: "Estudiantes con más de 3 inasistencias consecutivas", icon: "fa-calendar-times-o" },
];

const VIZ_ICONS = {
    number: "fa-hashtag",
    bar: "fa-bar-chart",
    donut: "fa-circle-o",
    table: "fa-table",
};

const CATEGORICAL_KPI_KEYS = ["secciones_por_campus", "estudiantes_por_nivel"];

// KPIs cuyo desglose es por SECCIÓN individual (cada barra es una sección
// real, con su propio school.standard detrás) -- estos abren el modal de
// detalle al hacer clic. Los categóricos (campus/nivel) en cambio alternan
// el filtro correspondiente (ver onSeriesClick).
const SECTION_LEVEL_KPI_KEYS = ["progreso_encuentros", "progreso_evaluaciones", "mejores_secciones_promedio"];

const SECTION_STATE_OPTIONS = [
    { key: "done", label: "En curso" },
    { key: "terminate", label: "Culminadas" },
    { key: "all", label: "Todas" },
];

const GROUP_BY_OPTIONS = [
    { key: "none", label: "Sin agrupación" },
    { key: "campus", label: "Campus" },
    { key: "standard", label: "Nivel" },
    { key: "subject", label: "Curso" },
];

export class ClAcademicDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            error: null,
            data: null,
            activeTab: "panel",
            progressTab: "encuentros",
            alertTab: ALERT_TYPES[0].key,
            kpiViz: {},
            search: "",
            modalSection: null,
            filtersCollapsed: true,
            // Orden por tabla: { [tableKey]: { field, dir: "asc"|"desc" } }.
            // Ausente = se respeta el orden que ya trae el backend.
            sort: {},
        });
        this.kpiIcons = KPI_ICONS;
        this.vizIcons = VIZ_ICONS;
        this.sectionStateOptions = SECTION_STATE_OPTIONS;
        this.groupByOptions = GROUP_BY_OPTIONS;
        this.alertTypes = ALERT_TYPES;
        onWillStart(() => this.loadData());
    }

    async loadData(filters) {
        this.state.loading = true;
        this.state.error = null;
        try {
            this.state.data = await this.orm.call(
                "cl.academic.dashboard", "get_dashboard_data", [], { filters: filters || null });
        } catch (e) {
            this.state.error = "No se pudo cargar el tablero académico. Intente de nuevo.";
        } finally {
            this.state.loading = false;
        }
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    toggleFilters() {
        this.state.filtersCollapsed = !this.state.filtersCollapsed;
    }

    setProgressTab(tab) {
        this.state.progressTab = tab;
    }

    alertsByType(tipo) {
        if (!this.state.data) return [];
        return this.state.data.alerts.filter((a) => a.tipo === tipo);
    }

    setAlertTab(key) {
        this.state.alertTab = key;
    }

    // sectionId: id real de school.standard. context: datos extra a fusionar
    // sin pisar los campos base de la fila (ej. { alertContext } o
    // { progressContext }), para que el modal pueda mostrar información
    // propia del gráfico/tabla desde el que se abrió.
    openSectionModal(sectionId, context) {
        if (!sectionId) return;
        const base =
            (this.state.data.rows || []).find((r) => r.id === sectionId) ||
            (this.state.data.recent_sections || []).find((r) => r.id === sectionId) ||
            { id: sectionId };
        this.state.modalSection = { ...base, ...(context || {}) };
    }

    closeModal() {
        this.state.modalSection = null;
    }

    // Hipervínculo del modal: abre el registro real de school.standard.
    openSectionForm() {
        if (!this.state.modalSection || !this.state.modalSection.id) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "school.standard",
            res_id: this.state.modalSection.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    isSectionLevelKpi(kpiKey) {
        return SECTION_LEVEL_KPI_KEYS.includes(kpiKey);
    }

    isClickableBar(kpiKey) {
        return CATEGORICAL_KPI_KEYS.includes(kpiKey) || SECTION_LEVEL_KPI_KEYS.includes(kpiKey);
    }

    onBarClick(kpi, bar) {
        if (CATEGORICAL_KPI_KEYS.includes(kpi.key)) {
            this.onSeriesClick(kpi.key, bar.label);
        } else if (SECTION_LEVEL_KPI_KEYS.includes(kpi.key) && bar.id) {
            this.openSectionModal(bar.id, { progressContext: bar });
        }
    }

    // ===== Orden de tablas (clic en encabezado, alterna asc/desc) =====
    toggleSort(tableKey, field) {
        const current = this.state.sort[tableKey];
        this.state.sort[tableKey] =
            current && current.field === field
                ? { field, dir: current.dir === "asc" ? "desc" : "asc" }
                : { field, dir: "asc" };
    }

    sortIcon(tableKey, field) {
        const s = this.state.sort[tableKey];
        if (!s || s.field !== field) return "fa-sort";
        return s.dir === "asc" ? "fa-sort-asc" : "fa-sort-desc";
    }

    applySort(list, tableKey) {
        const s = this.state.sort[tableKey];
        if (!s || !list || !list.length) return list || [];
        const sorted = [...list].sort((a, b) => {
            const va = a[s.field];
            const vb = b[s.field];
            if (typeof va === "number" && typeof vb === "number") return va - vb;
            return String(va ?? "").localeCompare(String(vb ?? ""), "es", { sensitivity: "base", numeric: true });
        });
        if (s.dir === "desc") sorted.reverse();
        return sorted;
    }

    get sortedRecentSections() {
        if (!this.state.data) return [];
        return this.applySort(this.state.data.recent_sections, "recent");
    }

    get sortedFilteredRows() {
        return this.applySort(this.filteredRows, "secciones");
    }

    sortedGroupRows(group) {
        return this.applySort(group.rows, "secciones");
    }

    sortedAlerts(atypeKey) {
        return this.applySort(this.alertsByType(atypeKey), "alert_" + atypeKey);
    }

    sortedKpiSeries(kpi) {
        return this.applySort(kpi.series || [], "kpi_" + kpi.key);
    }

    sortedProgress(kind) {
        if (!this.state.data) return [];
        const list = kind === "encuentros" ? this.state.data.progress_meetings : this.state.data.progress_evaluations;
        return this.applySort(list, "progress_" + kind);
    }

    setSectionState(key) {
        this.loadData({ section_state: key });
    }

    setGroupBy(key) {
        this.loadData({ group_by: key });
    }

    toggleCampus(id) {
        const current = this.state.data.filters_applied.campus_ids;
        const next = current.includes(id) ? current.filter((x) => x !== id) : [...current, id];
        this.loadData({ campus_ids: next });
    }

    toggleStandard(id) {
        const current = this.state.data.filters_applied.standard_ids;
        const next = current.includes(id) ? current.filter((x) => x !== id) : [...current, id];
        this.loadData({ standard_ids: next });
    }

    onSubjectSelect(ev) {
        // Selección de UN solo curso a la vez (con ~80 cursos, chips
        // multi-toggle no seria usable; un <select> nativo permite buscar
        // escribiendo). value vacío = "Todos los cursos".
        const id = ev.target.value ? parseInt(ev.target.value, 10) : null;
        this.loadData({ subject_ids: id ? [id] : [] });
    }

    clearFilters() {
        this.loadData({ campus_ids: [], standard_ids: [], subject_ids: [] });
    }

    kpiViz(kpi) {
        return this.state.kpiViz[kpi.key] || kpi.viz;
    }

    setKpiViz(kpiKey, viz) {
        this.state.kpiViz[kpiKey] = viz;
    }

    kpiColorClass(color) {
        return `o_cad_kpi_${color}`;
    }

    vizMode(kpiKey) {
        // "Secciones por campus" y "Estudiantes por nivel" son categorías
        // reales (campus/nivel distintos) sin ícono propio que las
        // distinga -- necesitan colores contrastantes, no solo opacidad.
        return CATEGORICAL_KPI_KEYS.includes(kpiKey) ? "categorical" : "mono";
    }

    donutSlices(kpi) {
        return computeDonutSlices(kpi.series || [], { mode: this.vizMode(kpi.key) });
    }

    barWidths(kpi) {
        return computeBarWidths(this.sortedKpiSeries(kpi), { mode: this.vizMode(kpi.key) });
    }

    meterSlice(value) {
        return computeMeterSlice(value);
    }

    onSeriesClick(kpiKey, label) {
        if (kpiKey === "secciones_por_campus") {
            const opt = this.state.data.campus_options.find((c) => c.name === label);
            if (opt) this.toggleCampus(opt.id);
        } else if (kpiKey === "estudiantes_por_nivel") {
            const opt = this.state.data.standard_options.find((s) => s.name === label);
            if (opt) this.toggleStandard(opt.id);
        }
    }

    get filteredRows() {
        if (!this.state.data) return [];
        const query = this.state.search.trim().toLowerCase();
        if (!query) return this.state.data.rows;
        return this.state.data.rows.filter(
            (r) =>
                r.section.toLowerCase().includes(query) ||
                r.course.toLowerCase().includes(query) ||
                r.teacher.toLowerCase().includes(query));
    }
}

ClAcademicDashboard.template = "cl_class_mgmt_v16.ClAcademicDashboard";

registry.category("actions").add("cl_academic_dashboard", ClAcademicDashboard);
