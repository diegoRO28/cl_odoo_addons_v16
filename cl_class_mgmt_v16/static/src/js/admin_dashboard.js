/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { computeDonutSlices, computeBarWidths, computeMeterSlice } from "@cl_class_mgmt_v16/js/cl_chart_utils";

const KPI_ICONS = {
    total_estudiantes_activos: "fa-users",
    retiros_periodo: "fa-sign-out",
    pct_ocupacion_promedio: "fa-pie-chart",
    inscripciones_por_mes: "fa-line-chart",
    retiros_por_motivo: "fa-list-alt",
    capacidad_por_seccion: "fa-th-large",
    retiros_por_seccion: "fa-arrow-circle-o-down",
    cambios_por_seccion: "fa-exchange",
    inscripciones_por_seccion: "fa-arrow-circle-o-up",
    facturacion_periodo: "fa-file-text-o",
    cobrado_periodo: "fa-money",
    facturacion_pendiente: "fa-exclamation-circle",
    morosidad_por_seccion: "fa-warning",
};

const VIZ_ICONS = {
    number: "fa-hashtag",
    bar: "fa-bar-chart",
    donut: "fa-circle-o",
    table: "fa-table",
};

// KPIs cuyas porciones son categorías reales sin identidad propia en la UI
// (a diferencia de, por ejemplo, un semáforo de capacidad, donde el color ya
// viene del backend) -- necesitan paleta contrastante, no mono+opacidad.
const CATEGORICAL_KPI_KEYS = ["retiros_periodo", "retiros_por_motivo", "inscripciones_por_mes"];

const PERIOD_OPTIONS = [
    { key: "month", label: "Último mes" },
    { key: "quarter", label: "Último trimestre" },
    { key: "semester", label: "Último semestre" },
    { key: "year", label: "Todo el año" },
];

const INSCRIPCION_STATE_OPTIONS = [
    { key: "active", label: "Activos" },
    { key: "retirado", label: "Retirados" },
    { key: "all", label: "Todos" },
];

const BILLING_GROUP_BY_OPTIONS = [
    { key: "none", label: "Sin agrupación" },
    { key: "curso", label: "Curso" },
    { key: "seccion", label: "Sección" },
    { key: "mes", label: "Mes" },
];

export class ClAdminDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            error: null,
            data: null,
            activeTab: "panel",
            kpiViz: {},
            search: "",
            filtersCollapsed: true,
            sort: {},
        });
        this.kpiIcons = KPI_ICONS;
        this.vizIcons = VIZ_ICONS;
        this.periodOptions = PERIOD_OPTIONS;
        this.inscripcionStateOptions = INSCRIPCION_STATE_OPTIONS;
        this.billingGroupByOptions = BILLING_GROUP_BY_OPTIONS;
        onWillStart(() => this.loadData());
    }

    async loadData(filters) {
        this.state.loading = true;
        this.state.error = null;
        try {
            this.state.data = await this.orm.call(
                "cl.admin.dashboard", "get_dashboard_data", [], { filters: filters || null });
        } catch (e) {
            this.state.error = "No se pudo cargar el tablero administrativo. Intente de nuevo.";
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

    setPeriod(key) {
        this.loadData({ period_mode: key });
    }

    setInscripcionState(key) {
        this.loadData({ inscripcion_state: key });
    }

    toggleCampus(id) {
        const current = this.state.data.filters_applied.campus_ids;
        const next = current.includes(id) ? current.filter((x) => x !== id) : [...current, id];
        this.loadData({ campus_ids: next });
    }

    clearFilters() {
        this.loadData({ campus_ids: [] });
    }

    toggleFinancials() {
        this.loadData({ show_financials: !this.state.data.filters_applied.show_financials });
    }

    setBillingGroupBy(key) {
        this.loadData({ billing_group_by: key });
    }

    kpiViz(kpi) {
        return this.state.kpiViz[kpi.key] || kpi.viz;
    }

    setKpiViz(kpiKey, viz) {
        this.state.kpiViz[kpiKey] = viz;
    }

    kpiColorClass(color) {
        return `o_adb_kpi_${color}`;
    }

    vizMode(kpiKey) {
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

    // ===== Orden de tablas =====
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

    sortedKpiSeries(kpi) {
        return this.applySort(kpi.series || [], "kpi_" + kpi.key);
    }

    get filteredInscripciones() {
        if (!this.state.data) return [];
        const query = this.state.search.trim().toLowerCase();
        const rows = this.state.data.rows;
        if (!query) return rows;
        return rows.filter(
            (r) =>
                r.student.toLowerCase().includes(query) ||
                r.section.toLowerCase().includes(query) ||
                r.course.toLowerCase().includes(query));
    }

    get sortedInscripciones() {
        return this.applySort(this.filteredInscripciones, "inscripciones");
    }

    get sortedRetiros() {
        if (!this.state.data) return [];
        return this.applySort(this.state.data.retiros_rows, "retiros");
    }

    get sortedCapacidad() {
        if (!this.state.data) return [];
        return this.applySort(this.state.data.capacity_rows, "capacidad");
    }

    get retirosByMonthBars() {
        if (!this.state.data) return [];
        return computeBarWidths(this.state.data.retiros_by_month, { mode: "mono" });
    }

    get sortedCambios() {
        if (!this.state.data) return [];
        return this.applySort(this.state.data.cambios_rows, "cambios");
    }

    get sortedMorosidad() {
        if (!this.state.data || !this.state.data.morosidad) return [];
        return this.applySort(this.state.data.morosidad.rows, "morosidad");
    }

    morosidadBars(dimension) {
        // dimension: 'por_curso' | 'por_seccion' | 'por_profesor'
        if (!this.state.data || !this.state.data.morosidad) return [];
        return computeBarWidths(this.state.data.morosidad[dimension] || [], { mode: "categorical" });
    }

    get billingBreakdownBars() {
        if (!this.state.data || !this.state.data.billing_summary) return [];
        return computeBarWidths(this.state.data.billing_summary.breakdown || [], { mode: "categorical" });
    }

    // ===== Navegación a los registros reales de Odoo =====
    openRecord(model, id) {
        if (!id) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openInscripcion(id) {
        this.openRecord("student.inscripcion", id);
    }

    openRetiro(id) {
        this.openRecord("student.retiro", id);
    }

    openCambio(id) {
        this.openRecord("student.cambio", id);
    }

    openSeccion(id) {
        this.openRecord("school.standard", id);
    }

    onRankingBarClick(bar) {
        // Los rankings 'por sección' en el Panel (retiros/cambios/
        // inscripciones/capacidad/morosidad) siempre llevan el id de
        // school.standard.
        if (bar.id) this.openSeccion(bar.id);
    }
}

ClAdminDashboard.template = "cl_class_mgmt_v16.ClAdminDashboard";

registry.category("actions").add("cl_admin_dashboard", ClAdminDashboard);
