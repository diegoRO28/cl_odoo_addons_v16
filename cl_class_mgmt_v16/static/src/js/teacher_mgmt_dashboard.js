/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ChatterContainer } from "@mail/components/chatter_container/chatter_container";
import { computeLineChart, computeDonutSlices } from "@cl_class_mgmt_v16/js/cl_chart_utils";

const KPI_HISTORY_META = {
    asistencias: { title: "% carga de asistencias", color: "var(--tmd-lime-deep)" },
    evaluaciones: { title: "% carga de notas", color: "var(--tmd-lime-deep)" },
};

// Tamaño del ícono de estrella para el podio del ranking (1º más grande).
const PODIUM_STAR_SIZE = ["o_tmd_star_1", "o_tmd_star_2", "o_tmd_star_3"];

// Categorías con colores contrastantes (no monocromático): con 7 categorías
// de tamaños parecidos, la opacidad sola no alcanza para distinguirlas de un
// vistazo -- mismo criterio que secciones_por_campus/estudiantes_por_nivel
// en el dashboard académico. Iconos: Font Awesome, nunca emojis.
const DEMOGRAPHIC_CARDS = [
    { key: "kids", label: "Kids", icon: "fa-child" },
    { key: "teens", label: "Teens", icon: "fa-bicycle" },
    { key: "adults14", label: "Adults · Levels 1–4", icon: "fa-book" },
    { key: "adults56", label: "Adults · Levels 5–6", icon: "fa-graduation-cap" },
    { key: "adults78", label: "Adults · Levels 7–8", icon: "fa-trophy" },
    { key: "scholarship", label: "Scholarship", icon: "fa-star" },
    { key: "online", label: "Online", icon: "fa-laptop" },
];

const STATUS_FILTERS = [
    { key: "all", label: "Todos" },
    { key: "overdue", label: "Atrasados" },
    { key: "uptodate", label: "Al día" },
];

export class TeacherMgmtDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            error: null,
            data: null,
            activeTab: "overview",
            selectedTeacherId: null,
            navIds: null,
            search: "",
            statusFilter: "all",
            kpiModal: null,
            activitiesModal: null,
            profFilters: { curso: "", nivel: "", campus: "" },
        });
        this.demographicCards = DEMOGRAPHIC_CARDS;
        this.statusFilters = STATUS_FILTERS;
        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        this.state.error = null;
        try {
            this.state.data = await this.orm.call("teacher.mgmt.wizard", "get_dashboard_data", []);
        } catch (e) {
            this.state.error = "No se pudo cargar el tablero. Intente de nuevo.";
        } finally {
            this.state.loading = false;
        }
    }

    get selectedTeacher() {
        if (!this.state.data || !this.state.selectedTeacherId) {
            return null;
        }
        return this.state.data.profesores.find((p) => p.id === this.state.selectedTeacherId);
    }

    getFilteredTeachers(metricKey) {
        if (!this.state.data) return [];
        const query = this.state.search.trim().toLowerCase();
        const { curso, nivel, campus } = this.state.profFilters;
        return this.state.data.profesores.filter((p) => {
            if (query && !p.name.toLowerCase().includes(query)) return false;
            const value = p[metricKey];
            if (this.state.statusFilter === "overdue" && value >= 100) return false;
            if (this.state.statusFilter === "uptodate" && !(p.active_groups > 0 && value === 100)) return false;
            if (curso || nivel || campus) {
                const activas = p.secciones.filter((s) => !s.is_closed);
                const coincide = activas.some(
                    (s) =>
                        (!curso || s.course === curso) &&
                        (!nivel || s.age_band === nivel) &&
                        (!campus || s.campus === campus));
                if (!coincide) return false;
            }
            return true;
        });
    }

    get filteredTeachers() {
        return this.getFilteredTeachers("percent");
    }

    setProfFilter(key, value) {
        this.state.profFilters[key] = this.state.profFilters[key] === value ? "" : value;
    }

    onCursoSelect(ev) {
        this.state.profFilters.curso = ev.target.value;
    }

    clearProfFilters() {
        this.state.profFilters = { curso: "", nivel: "", campus: "" };
    }

    get demographicDonut() {
        if (!this.state.data) return { slices: [], total: 0 };
        const demo = this.state.data.demographics;
        const items = this.demographicCards.map((card) => ({ ...card, label: card.label, value: demo[card.key] || 0 }));
        const total = items.reduce((sum, it) => sum + it.value, 0);
        const slices = computeDonutSlices(items, { mode: "categorical" });
        return { slices, total };
    }

    setTab(tab) {
        this.state.activeTab = tab;
        this.state.selectedTeacherId = null;
    }

    async openKpiHistory(kind) {
        const meta = KPI_HISTORY_META[kind];
        this.state.kpiModal = { kind, title: meta.title, loading: true, points: [] };
        const points = await this.orm.call("cl.teacher.kpi.snapshot", "get_history", [kind]);
        if (this.state.kpiModal && this.state.kpiModal.kind === kind) {
            this.state.kpiModal.points = points;
            this.state.kpiModal.loading = false;
        }
    }

    closeKpiModal() {
        this.state.kpiModal = null;
    }

    // Clic en "Sección" de la ficha: abre el registro real de school.standard.
    openSectionForm(sectionId) {
        if (!sectionId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "school.standard",
            res_id: sectionId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    // Clic en "Estado evaluación" de la ficha: detalle de actividades
    // cargadas para la evaluación vigente de esa sección (bajo demanda, en
    // vez de mostrarlo todo siempre apilado).
    openActivitiesModal(seccion) {
        this.state.activitiesModal = seccion;
    }

    closeActivitiesModal() {
        this.state.activitiesModal = null;
    }

    get kpiModalChart() {
        if (!this.state.kpiModal) return null;
        return computeLineChart(this.state.kpiModal.points, { width: 100, height: 40 });
    }

    // Podio del ranking: estrella al top-3 (1º más grande, 3º más chica).
    podiumStarClass(index) {
        return PODIUM_STAR_SIZE[index] || "";
    }

    setStatusFilter(key) {
        this.state.statusFilter = key;
    }

    // `list` es el arreglo (Profesores filtrado o Ranking) desde el que se
    // hizo clic -- se recuerda como `navIds` para que Siguiente/Anterior
    // avancen dentro de ESE mismo orden, sin importar desde qué pestaña se
    // entró al detalle.
    selectTeacher(id, list) {
        this.state.selectedTeacherId = id;
        this.state.navIds = (list || this.state.data.profesores).map((p) => p.id);
    }

    backToGrid() {
        this.state.selectedTeacherId = null;
        this.state.navIds = null;
    }

    get navIndex() {
        if (!this.state.navIds) return -1;
        return this.state.navIds.indexOf(this.state.selectedTeacherId);
    }

    get hasPrevTeacher() {
        return this.navIndex > 0;
    }

    get hasNextTeacher() {
        const idx = this.navIndex;
        return idx !== -1 && idx < this.state.navIds.length - 1;
    }

    prevTeacher() {
        if (this.hasPrevTeacher) this.state.selectedTeacherId = this.state.navIds[this.navIndex - 1];
    }

    nextTeacher() {
        if (this.hasNextTeacher) this.state.selectedTeacherId = this.state.navIds[this.navIndex + 1];
    }

    percentClass(percent) {
        if (percent >= 80) return "is-good";
        if (percent >= 60) return "is-warn";
        return "is-bad";
    }

    progressWidth(percent) {
        return Math.max(4, percent);
    }

    initials(name) {
        if (!name) return "?";
        return name
            .trim()
            .split(/\s+/)
            .slice(0, 2)
            .map((w) => w[0])
            .join("")
            .toUpperCase();
    }
}

TeacherMgmtDashboard.template = "cl_class_mgmt_v16.TeacherMgmtDashboard";
TeacherMgmtDashboard.components = { ChatterContainer };

registry.category("actions").add("cl_teacher_mgmt_dashboard", TeacherMgmtDashboard);
