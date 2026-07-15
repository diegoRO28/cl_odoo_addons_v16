Módulo de Gestión Académica – 10-03-26

Items:

· Dashboard
· Metricas
· Reportes

Cambios necesarios a school (el modulo para contexto se encuentra en /opt/odoo16/odoo16/custom/school):

· Modificación a subject.asistencia y     standard.evaluacion
  · Añadir opción para programar encuentro o evaluacion.
  · El campo Date_start debe estar en modo solo lectura (readonly).

· Modificación a school.standard
  · Al abrir la sección (iniciar), se deben calcular las fechas de los encuentros y las evaluaciones a partir de la fecha de inicio (Start_date de school, standard).
  · Tomar en cuenta la fecha de finalización (mostrar diferencia en el nuevo encuentro) (end_date en school, standard).
  · Modal de reprogramar:
  ¿Que se va a reprogramar? Es encuentro o una evaluacion o ambas
    · Última asistencia cargada.
    · Ultima evaluacion cargada.
    · Fecha de la última asistencia.
    · Fecha del próximo encuentro.


---

Reporte de rendimiento – Dashboard de rendimiento docente: Tomar en cuenta el codigo localizado en: /opt/odoo16/odoo16/cl_addons_v16/cl_class_mgmt_v16/index.html

CONTEXTO: Un teacher creo un reporte utilizando IA que consulta un archivo Google Sheets. Este dashboard se encuentra alojado en: https://cleveland-attendance-teacher-report.netlify.app/ 

Y utiliza el siguiente archivo sheets: https://docs.google.com/spreadsheets/d/1hrg0fj0LD_qG1AONjZvmiyheacoRxauu/edit?usp=sharing&ouid=102165177968638459974&rtpof=true&sd=true

Este es el xlsx en el directorio por si no puedes acceder al google sheets: /opt/odoo16/odoo16/cl_addons_v16/cl_class_mgmt_v16/attendance_report_model.xlsx

Hay que buscar como adaptar ese dashboard a Odoo para que los directivos puedan revisarlo, ademas me gustaria buscar una manera de que se pueda alimentar el dashboard que creo el teacher, pero eso lo implementaremos en una fase futura. 

Reprogramar – Sección

Reporte de cumplimiento de asistencias

Campos:

· Teacher:
  · Course (Sección).
  · Status (Uptodate = Verde, Not uptodate = Rojo).
· Class days:
  · Start - End de este curso / Mes.
  · Grupos uptodate (por teacher).
  · Grupos (Secciones asignadas al teacher).
· Número de estudiantes de la sección.
· Edades.

IMPORTANTE: Todos los cambios se deben aplicar desde el modulo que estamos desarrollando
  por lo que todo debe heredar a school y editar en base a las herencias

---

DECISIÓN DE DISEÑO – Automatización de fechas de encuentros y evaluaciones (2026-07-14):

· Se debe crear (por herencia _inherit) un nuevo campo en school.standard que permita
  seleccionar los días de la semana en que se dicta el curso.
  Ej: (LUNES Y MARTES) / (MIÉRCOLES, JUEVES, SÁBADOS) / (SOLO SÁBADOS).

· Vista a heredar: school.standard.form
  ID externo: school.view_school_standard_form
  (ubicación real del campo start_date/end_date/code_moodle: school/views/standard_view.xml líneas 69-71)

· Con estos días de la semana marcados + start_date + end_date, se calculan las fechas
  de los encuentros (subject.asistencia.date_start) y de las evaluaciones
  (standard.evaluacion.date_start): se recorren los días desde start_date, y cada vez
  que el día de la semana coincide con uno de los marcados, se asigna esa fecha al
  siguiente encuentro/evaluación pendiente, hasta completar la cantidad requerida por
  el curso (subject.encuentro_ids / subject.libroevas_ids) o hasta llegar a end_date
  (mostrando la diferencia si no alcanza).

· Referencia de campos verificados en school (2026-07-14):
  - subject.asistencia.date_start (minúscula, no "Date_start")
  - standard.evaluacion.date_start (minúscula)
  - school.standard.start_date / end_date (orden invertido respecto al spec original)
  - school.standard.set_done() ya llama a generate_encuentros() y generate_registroEva()
    al iniciar la sección; ahí se debe enganchar el cálculo automático de fechas.

· IMPORTANTE - Conflicto detectado con otro módulo (2026-07-14):
  El módulo school_mod (instalado junto a school) sobrescribe
  generate_registroEva() en school.standard SIN llamar a super(), lo que rompe
  cualquier _inherit que intente engancharse ahí (las fechas de evaluaciones no se
  calculaban). Por eso el cálculo automático de fechas NO se hace sobreescribiendo
  generate_encuentros()/generate_registroEva(), sino en el create() de
  subject.asistencia y standard.evaluacion (cl_class_mgmt_v16/models/asistencia.py y
  registroeva.py) - así funciona sin importar qué módulo termine creando el registro.
  También existen instalados: school_optimize (crea standard.evaluaciones/actividades
  por estudiante, no toca date_start) y school_archive (solo agrega campo 'active').
  school_mod además tiene una @api.constrains en subject.asistencia que bloquea poner
  un encuentro en estado 'done' si date_start sigue igual a la fecha de creación
  (obligaba a corregir la fecha manualmente); con la automatización esto deja de
  ser un problema en el flujo normal.

· UI - Días de Clases (2026-07-14, ajuste pedido por el usuario tras ver la vista):
  En vez de 7 campos Boolean con checkboxes, se usa un Many2many
  (school.standard.dias_clase_ids -> nuevo modelo cl.dia.semana con 7 registros
  fijos LUNES..DOMINGO, campo weekday_index 0-6 y color) con widget
  "many2many_tags" para mostrarlo como badges compactos, ej:
  "Días de Clases: LUNES, MARTES, JUEVES". Ubicado justo ARRIBA del campo
  start_date ("Fecha de inicio") en el grupo "INFORMACIÒN DE LA CLASE"
  (xpath sobre field[@name='start_date'] position="before").

---

ESTADO ACTUAL DEL MÓDULO (2026-07-15) - resumen de lo implementado hasta ahora,
para que cualquier agente que retome el trabajo tenga contexto sin releer todo
el historial de chat.

· DEPLOY / ENTORNO (importante, evita perder tiempo):
  - Hay DOS bases de datos relevantes en esta máquina: `production_db` (la que
    el usuario realmente usa y donde está instalado cl_class_mgmt_v16) y
    `cleveland_development_db` (NO tiene este módulo instalado, no usar para
    probar salvo que se pida explícitamente instalarlo ahí).
  - Servicio: systemd `odoo16` (`/etc/odoo16.conf`), usuario `odoo16`,
    addons_path incluye /opt/odoo16/odoo16/{addons,custom,cl_addons_v16}.
  - Ciclo de actualización usado en toda la sesión: `sudo systemctl stop odoo16`
    → `sudo -u odoo16 /opt/odoo16/odoo16-venv/bin/python3 /opt/odoo16/odoo16/odoo-bin
    -c /etc/odoo16.conf -d production_db -u cl_class_mgmt_v16 --stop-after-init`
    (revisar log en /var/log/odoo/odoo16.log) → `sudo systemctl start odoo16`.
    Para probar lógica Python sin pasar por el navegador: `odoo-bin shell
    -c /etc/odoo16.conf -d production_db --no-http --shell-interface=python`.
  - Dependencias nuevas agregadas al manifest: `custom_libroeva_copy` (ya
    define el campo `sequence` con handle en subject.encuentros, lo
    reutilizamos en vez de duplicarlo) y `report_xlsx` (mixin OCA usado para
    el reporte Excel).
  - Referencia de catálogo completo del módulo school: ver
    `cl_class_mgmt_v16/school_module_overview.txt` (modelos, menús, estados,
    relaciones - generado el 2026-07-15).

· FECHAS DE EVALUACIONES LIGADAS AL PLAN DE ENCUENTROS (continuación de la
  automatización de fechas de arriba):
  - subject.encuentros (heredado en models/subject.py) ahora tiene
    `es_evaluacion` (Boolean) además del `sequence` de custom_libroeva_copy.
  - standard.evaluacion._asignar_fecha_automatica() ya NO calcula la fecha de
    una evaluación contando solo entre evaluaciones: usa
    `_posicion_encuentro_evaluacion()` para ubicar, dentro de
    subject_id.encuentro_ids (ordenado por sequence), qué encuentro marcado
    es_evaluacion le corresponde según su posición entre evaluaciones, y
    calcula la fecha según la posición REAL de ese encuentro en el plan
    completo. Si el curso no tiene encuentros marcados (todavía sin migrar),
    cae al comportamiento anterior (no rompe secciones ya en curso).
  - El botón provisional "GENERAR FECHAS DE CLASE" (action_recalcular_fechas_clase
    en school.standard) se actualizó para usar la misma lógica.

· REPROGRAMAR (implementado, cubre el punto "Modal de reprogramar" de arriba):
  - subject.asistencia y standard.evaluacion: campo `reprogramando` (Boolean,
    no expuesto) + botón "REPROGRAMAR" en el header que lo pone en True
    (date_start se vuelve editable); al guardar cualquier cambio con
    reprogramando=True, se vuelve a poner en False automáticamente
    (write() override). date_start es readonly salvo en ese momento.
  - school.standard: wizard `school.standard.reprogramar.wizard` (botón
    "REPROGRAMAR" en el form de la sección, solo admins). Campos: tipo
    (encuentro/evaluación/ambos), nueva_fecha (fecha ancla), más info de
    referencia (última asistencia/evaluación cargada con encuentro+nota
    concatenados, no un link genérico). Solo toca registros PENDIENTES
    (state=draft); lo ya dictado/evaluado no se mueve. Al reprogramar
    evaluaciones, sincroniza cada evaluación pendiente con la fecha REAL del
    subject.asistencia hermano (mismo encuentro_id) en vez de recalcular por
    fórmula independiente - así respeta reprogramaciones manuales previas de
    encuentros puntuales. Valida que la reprogramación no exceda end_date de
    la sección; si excede, corta con error y sugiere una fecha recomendada
    (_calcular_fecha_recomendada, retrocede desde end_date) en vez de ajustar
    solo. UI en 2 columnas (Encuentros/Evaluaciones), cada una se oculta si
    el tipo elegido no la incluye.

· REPORTE DE GESTIÓN DOCENTE (PDF/XLSX) - cubre el punto "Reporte de
  cumplimiento de asistencias" de arriba:
  - Menú nuevo (heredado, parent="school.menu_ems"): Class > Gestión >
    Reportes > Gestión Docente. Wizard `teacher.mgmt.wizard`
    (wizard/teacher_mgmt_wizard.py). Filtros opcionales: teacher_ids/
    subject_ids/standard_ids (Many2many), que se complementan entre sí vía
    onchange (elegir uno restringe las opciones de los otros dos a lo que
    comparten las secciones EN CURSO, state='done'). Formato pdf/xlsx.
  - Columnas: Teacher, Course, Section, Status (fecha + verde/rojo según haya
    o no un encuentro vencido sin registrar), Class days (dias_clase_ids si
    existe, si no el texto libre `note`), Start-End/Month, Groups Up to
    Date/Active Groups (agregado por profesor, solo secciones state=done),
    Student Cohort Size, Age Band (standard_id.name: ADULTS/KIDS/TEENS/ONLINE,
    ya poblado en producción).
  - report/teacher_mgmt_report_xlsx.py (mixin report.report_xlsx.abstract) y
    report/teacher_mgmt_report_views.xml (template qweb-pdf + 2 ir.actions.report).
  - `_compute_report_data()` en el wizard es la función que arma todo esto;
    es la MISMA lógica reutilizada por el dashboard (ver abajo) vía
    `get_dashboard_data()`.

· DASHBOARD OWL (cubre "Dashboard de rendimiento docente" / adaptación de
  index.html a Odoo):
  - Se evaluó OWL vs React; se eligió OWL (framework nativo de Odoo 16, sin
    dependencias externas ni build pipeline nuevo - React hubiera requerido
    webpack/npm que no existe en este repo, y convivir con OWL en la misma
    página). Nada de CDN externos (ni Tailwind ni Chart.js): CSS propio +
    SVG a mano para el donut.
  - Menú: Class > Gestión > Dashboard Docente (ir.actions.client, tag
    `cl_teacher_mgmt_dashboard`). Archivos:
    static/src/js/teacher_mgmt_dashboard.js (componente OWL),
    static/src/xml/teacher_mgmt_dashboard.xml (template),
    static/src/scss/teacher_mgmt_dashboard.scss (estilos), registrados en
    manifest 'assets': 'web.assets_backend'.
  - Backend: `teacher.mgmt.wizard.get_dashboard_data()` (@api.model, sin
    filtros - vive de datos en vivo). A diferencia del reporte PDF/XLSX
    (solo secciones done), acá se incluyen también las terminate para poder
    mostrar "grupos completados". Devuelve: logo/nombre de la compañía
    (company.logo_web / company.name, ya multi-company), % asistencias al
    día, % evaluaciones al día (mismo concepto que asistencias pero sobre
    registroeva_ids), total estudiantes, total retirados
    (total_students_cancel), demografía por categoría, top 5 cursos por nota
    promedio (standard.evaluacion.average), lista de profesores con foto
    (school.teacher.image_128), y ranking completo (score = promedio de %
    asistencia y % evaluación, solo profesores con active_groups>0).
  - Navegación: breadcrumbs (Panel / Profesores / [nombre]) + 4 pestañas:
    Panorama, Profesores, Evaluaciones, Ranking. Buscador + chips de filtro
    (Todos/Atrasados/Al día) en Profesores y Evaluaciones. Clic en cualquier
    profesor (desde Profesores, Evaluaciones o Ranking) lleva al mismo
    detalle: tabla con Estado asistencia + Estado evaluación por sección.
  - Diseño visual (iterado varias veces con feedback directo del usuario):
    tipografía SANS-SERIF en todo (no serif), paleta de marca de Cleveland
    English Institute (lima #BFD01F, lima oscuro #A3C62C, gris #585756,
    blanco - la paleta cambia según la compañía en teoría, pero por ahora
    está fija a estos valores; res.company ya tiene primary_color/
    secondary_color con valores ligeramente distintos, no se usó porque no
    coincidían exactamente con el kit de marca dado). Sellos de estado
    ("ATRASADO"/"AL DÍA"/fechas) SIN rotación (rectos). Gráfico de
    demografía: donut chart (pedido explícitamente por el usuario en vez de
    barras) con UN SOLO COLOR (opacidad decreciente por tamaño de porción,
    no arcoíris - pedido explícito del usuario). Ranking docente: barras
    (no torta, porque los % de cada profesor son independientes entre sí,
    no suman un todo - se mantiene la distinción de forma correcta).

· PENDIENTE / NO IMPLEMENTADO TODAVÍA (mencionado en la sesión pero no
  construido):
  - Historial con gráfico (Daily/Weekly/Monthly) del % de asistencia -
    requeriría un modelo nuevo tipo teacher.mgmt.snapshot + cron/botón
    "Recalcular y Guardar" para ir guardando un registro diario. Se
    descartó para esta iteración a pedido del usuario.
  - Observaciones por profesor (nota persistente editable desde el
    dashboard) - requeriría un campo/modelo nuevo. Descartado para esta
    iteración a pedido del usuario.
  - Posible: hacer la paleta de colores del dashboard dinámica por compañía
    (leer primary_color/secondary_color de res.company en vez de valores
    fijos) - quedó pendiente de confirmación con el usuario.

---

DASHBOARD ACADÉMICA — implementado (2026-07-15):

- Menú: Class > Gestión > Académica (ir.actions.client, tag
  `cl_academic_dashboard`), en `views/dashboard_views.xml`. También se
  renombró el menú "Dashboard Docente" → "Docente" para cumplir la regla de
  nomenclatura de la sección 3 (nunca usar la palabra "Dashboard" en un
  menuitem visible).
- Modelo `cl.academic.dashboard` (`models/dashboard/cl_academic_dashboard.py`),
  `_inherit = 'cl.dashboard.config'`. Es un Model persistido (no wizard): cada
  usuario tiene su propia configuración de filtros vía
  `_get_or_create_mine()` (busca por `user_id=self.env.uid`, crea si no
  existe). Protegido con un `ir.rule` (`security/dashboard_security.xml`)
  para que cada usuario solo vea su propia configuración.
- `get_dashboard_data(filters=None)` / `get_kpi_data(kpi_key, filters=None)`
  siguen el contrato de la sección 6 (kpis/rows/groups/alerts), con dos
  campos extra no documentados en el contrato original pero necesarios en la
  práctica: `campus_options` y `standard_options` (listas {id, name} para
  poblar los chips de filtro en el front).
- Ajuste sobre la sección 8.1: no todos los KPIs listados ahí tienen un
  desglose (`series`) real. `total_secciones_activas` y
  `total_estudiantes` son un solo número sin desglose que mostrar en
  barra/donut sin inventar datos, así que su `allow_viz` quedó en solo
  `['number']`. `pct_asistencias_al_dia`/`pct_evaluaciones_al_dia` sí
  soportan bar/donut, pero como **medidor** (el % lleno contra su propio
  límite de 100, no una serie categórica) -- ver `computeMeterSlice` en
  `cl_chart_utils.js`. `alertas_vencidas` quedó en solo `['number']` (la
  pestaña "Alertas" ya cubre el detalle completo; no vale la pena una tabla
  duplicada a medias dentro de la card).
- period_mode/date_from/date_to (heredados de cl.dashboard.config) están
  declarados pero **no se aplican todavía** al dominio de secciones: un
  preset "Este mes/trimestre/año" filtrando por `start_date` de la sección
  dejaría casi todas las secciones en curso fuera (empezaron antes),
  vaciando el panel -- justo lo contrario de "llenar los espacios en blanco"
  pedido por el usuario. Queda para cuando haya un KPI realmente sensible a
  fecha (ej. inscripciones del período, cuando se construya Administrativa).
- `static/src/js/cl_chart_utils.js` (nuevo): funciones puras reutilizables
  `computeDonutSlices`, `computeBarWidths`, `computeMeterSlice` -- extraídas
  del dashboard Docente para no repetir la geometría SVG en cada dashboard
  nuevo. El dashboard Docente NO se migró a usarlas todavía (sigue con su
  propia implementación inline); sería una limpieza futura de bajo riesgo.
- Colores de KPI (blue/teal/amber/coral/purple de la sección 8): son un tema
  por TARJETA (categorización de qué tipo de KPI es), no una codificación de
  datos dentro de un gráfico -- cada gráfico individual (barra/donut) sigue
  usando un solo tono con opacidad, cumpliendo la regla de "un solo color"
  que pidió el usuario para el dashboard Docente. Los 5 tonos están en
  `academic_dashboard.scss` como `--cad-kpi-*`.
- Todos los íconos son Font Awesome (`fa fa-xxx`), cero emojis, siguiendo la
  regla de la sección 0.
- Pestañas: Panel (KPI grid) / Secciones (tabla, con agrupación opcional por
  campus/nivel/curso) / Progreso (barras dictados vs. planeados) / Alertas
  (tabla de vencidos, o estado vacío "Todo al día" con ícono fa-check-circle
  si no hay ninguna).
- Filtros persistentes (header): Estado de sección (chips), Campus
  (chips, multi-toggle), Nivel (chips, multi-toggle), **Curso** (`<select>`
  nativo, NO chips -- hay ~85 cursos, un chip por curso sería inusable;
  selección de uno solo a la vez, `onSubjectSelect` en
  `academic_dashboard.js`), Agrupar por. Clic en una barra de "Secciones por
  campus" o "Estudiantes por nivel" aplica ese valor como filtro (mapea el
  label de vuelta al id vía campus_options/standard_options). El botón
  "Limpiar" solo resetea campus/nivel/curso, no el estado de sección ni el
  group_by (a propósito, para no perder de vista en qué "modo" está el
  usuario).
- KPI nuevo (2026-07-15, a pedido del usuario): **"Secciones con mejor
  promedio"** (`mejores_secciones_promedio`) -- promedio de notas POR
  SECCIÓN (no por curso, a diferencia del KPI equivalente del dashboard
  Docente), calculado siempre (curse o no en curso) sobre
  `standard.evaluacion.average > 0`. Viz `bar` únicamente (nunca `donut`:
  cada sección tiene su propio promedio, no suman un todo -- mismo criterio
  que el ranking docente).
- Ajuste 2026-07-15 (a pedido del usuario, "los colores de la rueda no
  permiten distinguir"): `secciones_por_campus` y `estudiantes_por_nivel`
  dejaron de usar el esquema mono-color-con-opacidad y ahora usan
  `computeDonutSlices(kpi, {mode: 'categorical'})` en
  `cl_chart_utils.js` -- paleta fija de 8 tonos contrastantes (misma
  paleta validada del dataviz skill), asignados por posición en el
  render (no hay un mapeo persistente campus→color entre refrescos). El
  donut demográfico del dashboard Docente NO cambió: ahí las categorías
  (Kids/Teens/Adults...) ya se distinguen por ícono + texto, así que el
  modo "mono" sigue siendo correcto ahí. `computeDonutSlices`/
  `computeBarWidths` ahora aceptan `{mode: 'mono'|'categorical'}`.
- Ajuste 2026-07-15 (a pedido del usuario, "coloca los gráficos de donut por
  defecto"): `viz` por defecto pasó de `bar`/`number` a `donut` en los 4 KPIs
  que lo soportan (`pct_asistencias_al_dia`, `pct_evaluaciones_al_dia`,
  `secciones_por_campus`, `estudiantes_por_nivel`). `progreso_encuentros` y
  `mejores_secciones_promedio` siguen en `bar` por defecto (no soportan
  donut, son rankings, no partes de un todo).

- Ajuste 2026-07-15 (a pedido del usuario, 3 cambios en la misma iteración):
  1. **Progreso** ahora tiene 2 sub-tabs (Encuentros / Evaluaciones, botones
     `.o_cad_subtab`, estado `progressTab` en el JS) -- antes solo mostraba
     encuentros. Backend: `progress_meetings` y `progress_evaluations`
     (reemplazan la clave única `progress`), más el KPI nuevo
     `progreso_evaluaciones` (terminadas vs. planeadas, mismo criterio que
     `progreso_encuentros` pero sobre `registroeva_ids`).
  2. **Panel**: nueva tabla "Últimas secciones creadas"
     (`_compute_recent_sections`, `school.standard` ordenado por
     `create_date desc`, límite 8). A propósito NO respeta el filtro de
     Estado de sección (si lo respetara, una sección recién creada en
     `draft` no aparecería con el filtro por defecto "En curso") -- sí
     respeta campus/nivel/curso.
  3. **Alertas se REEMPLAZÓ por completo** (antes: encuentros/evaluaciones
     vencidos sin registrar; eso ya no se muestra en ningún lado del
     dashboard). Ahora son 3 categorías fijas (`_compute_alertas`), cada una
     con su propia tabla en la pestaña, agrupadas client-side vía
     `alertsByType(tipo)`:
       - **Reprobados**: `student.inscripcion.state_eva == 'aplazado'`
         (dato real y ya poblado -- se comprobó por shell antes de
         implementar: 1021 aplazado / 2200 aprobado / 4194 borrador en
         producción; NO se usó `minimum_marks` de subject.subject porque
         está en 0 en todos los cursos). Umbral: > 25% de los inscritos
         `state='done'` de la sección.
       - **Inasistencia alta**: por (sección, estudiante), a partir de
         `subject.asistencias.is_attended`. Umbral: > 25% de los encuentros
         ya registrados para ese estudiante en esa sección.
       - **Inasistencia consecutiva**: mismo origen de datos, pero busca la
         racha más larga de `is_attended=False` ordenando por fecha; alerta
         si la racha > 3 (es decir, 4 o más seguidas).
     El KPI `alertas_vencidas` se renombró a `alertas_academicas` (mismo
     conteo total, ahora de las 3 categorías nuevas).
     Nota de rendimiento: `_compute_alertas` hace un `search_read` de
     `subject.asistencias` filtrado por las secciones ya filtradas (no la
     tabla completa, que tiene ~146k filas) -- con 145 secciones "en curso"
     son ~20k filas y toma ~2s; el cálculo completo del dashboard ronda
     ~3s. Si en el futuro esto se siente lento, la vía de optimización es
     mover el agrupado a SQL (`read_group` no sirve para la racha
     consecutiva porque necesita las filas ordenadas, no solo el conteo).

DASHBOARD ADMINISTRATIVA — implementado (2026-07-15):

- Modelo `cl.admin.dashboard` (`models/dashboard/cl_admin_dashboard.py`),
  `_inherit = 'cl.dashboard.config'`, mismo patrón de persistencia por
  usuario que `cl.academic.dashboard` (`_get_or_create_mine`, `ir.rule` propia
  en `security/dashboard_security.xml`). Campos propios:
  `inscripcion_state` (Activos/Retirados/Todos) y `show_financials`
  (Boolean, default False -- evita la consulta de facturación cuando no
  hace falta).
- Menú: Class > Gestión > Administrativa (`ir.actions.client`, tag
  `cl_admin_dashboard`), `views/dashboard_views.xml`, sequence=30 (después
  de Académica=10 y Docente=20).
- A diferencia de Académica, acá el **período SÍ se aplica** al dominio
  (`_resolver_periodo()`: mes/trimestre/año/personalizado → date_from/
  date_to). Justificación: inscripciones/retiros/facturas son eventos
  puntuales con fecha propia, a diferencia de una sección "en curso" que
  puede haber empezado antes del período -- filtrar por período acá no
  vacía el panel sin motivo (ver comentario en el código).
- Fuentes de datos: `student.inscripcion` (tab Inscripciones, KPI
  `total_estudiantes_activos`), `student.retiro` (tab Retiros, KPIs
  `retiros_periodo`/`retiros_por_motivo`), `school.standard` (tab Capacidad,
  KPI `capacidad_por_seccion` y `pct_ocupacion_promedio`), `account.move`
  (tab Facturación, KPIs `facturacion_pendiente`/`balance_pagos`).
- **Facturación**: la pestaña solo se muestra si
  `env.user.has_group('account.group_account_user')` (`has_billing_access`
  en el dict de datos) -- verificado con `with_user()` en shell, un usuario
  administrador SIN ese grupo no ve `billing_summary` (queda `None`). El
  cálculo pesado (`_compute_facturacion`) solo corre si además
  `show_financials=True` (toggle "Cargar cifras de facturación" en la UI).
- **Alertas de cupo**: `_compute_alertas_cupo()` (secciones activas con
  ocupación ≥90%, `capacity>0`) alimenta el campo `alerts` del contrato
  (sección 6) y se muestra como banner en el Panel + detalle en la pestaña
  Capacidad -- no es un tab dedicado (Administrativa no tiene pestaña
  "Alertas" en el diseño original, sección 9).
- **Semáforo de capacidad**: verde >70% ocupación, ámbar 40-70%, rojo <40%
  (rojo = riesgo de sección poco rentable, NO sobrecupo -- criterio inverso
  al que uno esperaría a primera vista, documentado explícitamente en
  claude.md sección 9 y replicado tal cual).
- **KPIs sin desglose real** (mismo criterio de ajuste que Académica):
  `total_estudiantes_activos` quedó en `allow_viz=['number']` (no hay
  histórico persistido todavía -- sección 12 sigue pendiente, así que no
  hay 'line' real de tendencia).
- Frontend: `static/src/js/admin_dashboard.js` + `static/src/xml/
  admin_dashboard.xml` + `static/src/scss/admin_dashboard.scss`, prefijo de
  clases `o_adb` (para no chocar con `o_tmd`/`o_cad` de los otros dos
  dashboards). El SCSS reutiliza el mismo sistema de diseño (variables
  `--adb-*` calcadas de `--cad-*`) generado a partir de
  `academic_dashboard.scss` con un `sed` de prefijo, no reescrito a mano.
  Reutiliza `cl_chart_utils.js` (`computeDonutSlices`/`computeBarWidths`/
  `computeMeterSlice`) sin cambios.
- **Diferencia de UX deliberada vs. Académica**: NO tiene el modal de
  detalle de sección (`o_cad_modal_*`) -- clic en una fila navega
  directamente al registro real de Odoo (`student.inscripcion`,
  `student.retiro` o `school.standard`) vía `action.doAction`. Se prefirió
  así para no duplicar otro patrón de modal genérico cuando cada tab ya
  apunta a un modelo distinto (a diferencia de Académica, donde todo gira
  alrededor de una sola entidad, `school.standard`).
- Registrado en `__manifest__.py` (`data`: `views/dashboard_views.xml` ya
  estaba; `assets`: 3 archivos nuevos agregados al final de
  `web.assets_backend`). ACL en `security/ir.model.access.csv`
  (`access_cl_admin_dashboard_admin`, solo `school.group_school_administration`,
  mismo criterio de seguridad que sección 11 -- probado con
  `with_user(teacher)` en shell: `AccessError` confirmado).
- **Verificado en shell** (2026-07-15, `production_db`): `get_dashboard_data()`
  corre sin error para un usuario admin real, `capacidad_por_seccion` calculó
  correctamente sobre datos reales (sección con 5/12 cupos → 42% → ámbar), y
  el bloqueo de seguridad para un usuario `teacher` devolvió `AccessError`
  como se esperaba. **No verificado en navegador** (sin herramienta de
  browser disponible en esta sesión) -- pendiente de que el usuario abra
  Class > Gestión > Administrativa y confirme visualmente antes de dar el
  feature por completamente cerrado.

---

MENÚ — "Gestión" movido al inicio de Class (2026-07-15, a pedido del
usuario): `menu_gestion` (wizard/teacher_mgmt_wizard_views.xml) pasó de
`sequence="120"` a `sequence="0"`, quedando antes que los menús propios de
`school` bajo `menu_ems` (el primero de ellos, `admission_register`, tiene
`sequence="1"`). De paso se corrigió `menu_gestion_reportes` de
`sequence="1"` a `sequence="40"` -- estaba apareciendo ANTES de Académica/
Docente/Administrativa dentro de Gestión, contradiciendo el orden
documentado en la sección 3 de este archivo (Académica, Docente,
Administrativa, Reportes).

---

DASHBOARD ADMINISTRATIVA — ampliación (2026-07-15, mismo día, a pedido del
usuario tras revisar la primera versión):

- **Bug de color corregido**: `cl_chart_utils.js` `computeBarWidths`/
  `computeDonutSlices` pisaban SIEMPRE el `color` que ya traía cada item de
  la serie (ej. el semáforo verde/ámbar/rojo de `capacidad_por_seccion`),
  reemplazándolo por `null` en modo 'mono'. Por eso las barras de
  "Capacidad por sección" se veían todas del mismo color en vez del
  semáforo -- visible en captura de pantalla que envió el usuario. Fix:
  `color: item.color || (...)` -- el color explícito del backend gana
  siempre; el color derivado del modo es solo fallback. Comparte archivo
  con el dashboard Académico, así que el fix aplica a ambos (no le afecta
  porque Académica no manda `color` por item en sus series).
- **Período**: `cl.dashboard.config.period_mode` ganó la opción
  `'semester'` ("Último semestre") y se relabeló todo el selector (Último
  mes/Último trimestre/Último semestre/Todo el año/Personalizado) a pedido
  explícito del usuario. Es un campo del modelo ABSTRACTO compartido por
  los 3 dashboards -- inofensivo para Académica (no aplica período) y
  Docente (no existe todavía).
- **KPI "Estudiantes activos" y facturación pendiente/vencido dejaron de
  depender del período** (bug real encontrado por el usuario: el panel
  mostraba 0 estudiantes activos con el filtro "Este mes" a pesar de haber
  secciones con inscritos reales, visible comparando con la pestaña
  Capacidad en la misma captura). Causa: esos KPIs son un SNAPSHOT del
  estado actual, no un evento con fecha propia -- un estudiante inscrito
  hace 3 meses en un curso vigente sigue "activo" hoy aunque su
  `inscription_date` caiga fuera del período. `_domain_estudiantes_activos()`
  y `_compute_morosidad()` quedaron sin filtro de fecha; solo
  Inscripciones/Retiros/Cambios/Facturado/Cobrado (que SÍ son eventos con
  fecha) siguen respetando el período.
- **Modelo `student.cambio`** (cambios de sección, `school/models/cambio.py`)
  incorporado: sección de ORIGEN = `standard_id` (related, vía `ri_id`),
  sección de DESTINO = `standard_des_id` (campo directo). Nueva pestaña
  **Cambios** (tabla: estudiante, sección origen, sección destino, campus
  destino, motivo `tipocambio_id`, fecha `cambio_date`) + KPI
  `cambios_por_seccion` en el Panel (ranking por sección de ORIGEN -- "de
  qué grupo salen más estudiantes por cambio"). ACL ya la daba `school`
  (`access_student_cambio_admin`, mismo grupo `group_school_administration`)
  -- no hizo falta tocar `ir.model.access.csv`.
- **Rankings "grupos con más X"** (a pedido explícito): `retiros_por_seccion`,
  `cambios_por_seccion`, `inscripciones_por_seccion` -- mismo helper
  `_top_secciones(records, section_field, limit=8)` reutilizado en los 3
  casos (cuenta ocurrencias agrupadas por `school.standard`, ordenado
  desc). Clic en cualquier barra de estos 3 KPIs (o en las de
  `capacidad_por_seccion`/`morosidad_por_seccion`) abre la sección real
  (`onRankingBarClick`, único handler genérico para los 5).
- **Pestaña Morosidad** (nueva, solo visible con `has_billing_access`):
  `_compute_morosidad()` -- snapshot (sin período) de todas las facturas
  `is_inscripcion=True` con `payment_state in (not_paid, partial)`,
  agrupadas por curso/sección/profesor (`school.standard.user_id`, mismo
  campo que ya usa el dashboard Docente para "profesor"). Responde
  literalmente al pedido "ver los grupos con mayor morosidad" -- ranking
  `por_seccion` top 8, clic abre la sección. Tabla de detalle con
  días de atraso (`hoy - invoice_date_due`, 0 si no está vencida).
- **Facturado / Cobrado / Pendiente, separados** (a pedido explícito del
  usuario -- "muchas veces se muestra la factura completa como si fuese
  dinero que ha entrado... realmente queremos saber lo que ha entrado"):
  - **Facturado** (`account.move.amount_total`, filtrado por `invoice_date`
    dentro del período) -- lo que se emitió, no necesariamente cobrado.
  - **Cobrado** (`account.payment`, filtrado por `date` -- fecha real del
    pago -- dentro del período) -- dinero que EFECTIVAMENTE entró.
    `account.payment.reconciled_invoice_ids` es un campo computado SIN
    `store`/`search` en Odoo 16 core (confirmado leyendo
    `addons/account/models/account_payment.py`) -- no se puede usar en un
    domain de búsqueda. Solución: se buscan los pagos de cliente
    (`payment_type=inbound`, `partner_type=customer`, `state=posted`) en el
    rango de fechas, y se filtra EN PYTHON cuáles reconcilian contra el
    conjunto de facturas de inscripción ya conocido (`_compute_cobrado`).
    Simplificación aceptada y documentada en el código: si un pago
    reconciliara parcialmente contra facturas fuera de ese conjunto además
    de una de adentro, se cuenta el monto completo del pago (caso de borde
    poco probable -- un pago de un representante normalmente cubre solo
    facturas de inscripción de su propio hijo).
  - **Pendiente/Vencido** (`account.move.amount_residual`) -- snapshot sin
    período, mismo dato que alimenta Morosidad (se calcula una sola vez y
    se reutiliza en ambas pestañas, `_compute_facturacion(morosidad=...)`
    recibe el dict ya calculado en vez de recalcular).
  - KPI `balance_pagos` (donut Pagado/Pendiente) se ELIMINÓ -- mezclaba
    conceptos de alcance temporal distinto (cobrado=período,
    pendiente=snapshot) en una sola dona de "partes de un todo", lo cual
    violaba el criterio de diseño del propio módulo (donut = desglose real
    de un total, no dos números inconexos). Reemplazado por 3 KPIs
    `number` separados: `facturacion_periodo`, `cobrado_periodo`,
    `facturacion_pendiente`.
- **Pestaña Facturación**: agregado control "Facturado por" (chips
  Ninguno/Curso/Sección/Mes, campo nuevo `billing_group_by`) que arma un
  bar chart de `total_facturado` desglosado por esa dimensión dentro del
  período seleccionado -- responde al pedido "por curso, por sección, por
  mes, ... y por rango personalizado" (el rango de fechas ya lo cubre el
  selector de período global, que ahora incluye 'custom').
- Todo lo anterior queda gated por `show_financials` (igual que antes) --
  Morosidad y Facturación comparten el mismo botón/estado "Cargar cifras",
  ya que ambas dependen de las mismas consultas de `account.move`.

---

DASHBOARD ADMINISTRATIVA — 2 bugs reales encontrados y corregidos
(2026-07-15, mismo día, tras reporte del usuario "sigue sin cargar los
datos en casi todos los items"):

1. **Crash total por introspección frágil de Selection.** `_compute_dashboard_data`
   armaba las etiquetas de `state_invoice`/`payment_state` con
   `dict(record._fields['x'].selection)`. Con el período por defecto
   ('Último mes' = solo 1-15 días) casi nunca había inscripciones que
   iterar, así que este código NUNCA se ejecutaba en la práctica -- el bug
   quedó invisible hasta que se probó con un período más amplio (había
   inscripciones reales) y explotó con `TypeError: 'function' object is
   not iterable` (el `.selection` de ese campo related no resuelve a una
   lista de tuplas en todos los casos). Como es una única excepción no
   capturada dentro de `get_dashboard_data()`, un solo campo roto tumbaba
   la respuesta COMPLETA del dashboard -- todos los tabs se veían vacíos,
   no solo Inscripciones. Fix: reemplazado por diccionarios estáticos
   `INVOICE_STATE_LABELS`/`PAYMENT_STATE_LABELS` (mismo criterio que
   `get_estado()`, que ya mapea a mano en vez de confiar en introspección
   del ORM).

2. **AccessError multi-compañía real, mismo síntoma (dashboard completo en
   blanco).** `student.retiro`/`student.cambio` NO tienen un `ir.rule`
   propio basado en `company_id` (a diferencia de `student.student`, que sí
   lo tiene y es estricto). Un usuario admin cuya compañía activa es solo
   una de varias (`self.env.companies`, ej. "TecnoCleveland" id=5) puede
   hacer `.search()` sobre `student.retiro` y recibir registros de OTRA
   compañía (id=1) sin error -- pero al acceder después a
   `retiro.student_id.name` en Python, esa lectura SÍ cruza a
   `student.student`, cuyo `ir.rule` rechaza la compañía ajena, y la
   excepción no capturada vuelve a tumbar el dashboard completo. Fix:
   `_domain_company()` (nuevo helper) agrega `('company_id', 'in',
   self.env.companies.ids)` a TODOS los domains de búsqueda del dashboard
   (inscripciones, retiros -- vía `company_id` propio --, cambios -- vía
   `ri_id.company_id`, no tiene uno propio --, secciones, facturas, pagos,
   campus_options). Filtrar en el domain de búsqueda resuelve por SQL/join
   y NO dispara el `ir.rule` del modelo relacionado, a diferencia de
   dereferenciar el campo en Python.
   **Decisión de diseño importante:** se evaluó usar `sudo()` en estas
   búsquedas (bypassear el problema en vez de resolverlo) y se descartó
   explícitamente -- el usuario nunca autorizó desactivar el control de
   acceso multi-compañía sobre datos de estudiantes/facturación, y hacerlo
   habría ocultado un problema real de aislamiento entre compañías en vez
   de respetarlo. La solución correcta es acotar el propio domain de
   búsqueda a `self.env.companies`, no elevar privilegios.
   **Nota:** esto significa que un admin con `company_ids` restringido a
   una sola compañía NUNCA verá en este dashboard datos de otra compañía,
   aunque tenga el grupo `school.group_school_administration` -- es el
   comportamiento esperado de un sistema multi-compañía, no una limitación
   a corregir.

- **Diagnóstico de por qué "no cargaban los datos" con el período por
  defecto:** NO era (solo) los 2 bugs de arriba -- con 'Último mes' (rango
  de solo medio mes, ej. 2026-07-01..2026-07-15) la base de producción
  real tiene muy pocos eventos puntuales (inscripciones/retiros/cambios)
  en una ventana tan angosta; con 'Todo el año' (2026-01-01..hoy) sí
  aparecen datos reales (64 inscripciones, 2 retiros, 2 cambios,
  $176,050 facturado en el primer semestre 2026, verificado en shell). El
  KPI `total_estudiantes_activos` (snapshot, no depende del período) sí
  mostraba datos correctos desde el principio. **Pendiente de decisión del
  usuario:** si vale la pena cambiar el `default` de `period_mode` de
  `'month'` a algo más amplio (`'quarter'` o `'year'`) para que el panel
  no se vea vacío la primera vez que se abre.

---

DASHBOARD ADMINISTRATIVA — 3er bug real: "Último trimestre"/"Último
semestre" colapsaban a la misma ventana que "Este mes" (2026-07-15,
reportado por el usuario tras el fix de los 2 bugs anteriores):

- `_resolver_periodo()` calculaba 'quarter'/'semester' como INICIO DEL
  PERÍODO CALENDARIO en curso (ej. quarter: `((mes-1)//3)*3+1` → 1 de
  julio para cualquier día de julio-septiembre). El 15 de julio de 2026
  (fecha en la que se probó) cae justo al INICIO tanto del Q3 (Jul-Sep)
  como del segundo semestre (Jul-Dic) -- así que 'Este mes' (1-15 jul),
  'Último trimestre' (1-15 jul) y 'Último semestre' (1-15 jul) daban
  EXACTAMENTE el mismo rango angosto, mientras 'Todo el año' (1 ene - hoy)
  sí mostraba datos. Confundía porque parecía que solo "año" funcionaba.
- Fix: 'month'/'quarter'/'semester' pasaron a ser VENTANAS MÓVILES
  (`hoy - relativedelta(months=1/3/6)` → hoy), no calendario-a-la-fecha.
  'year' se mantuvo como año-a-la-fecha (1 de enero → hoy) a propósito,
  distinto de un "últimos 12 meses" móvil -- es la lectura literal de
  "todo el año" que pidió el usuario, y ya funcionaba correctamente.
- Verificado en shell (producción): month=0 filas / quarter=12 /
  semester=63 / year=64 inscripciones -- creciente y consistente, ya no
  colapsan entre sí.

---

    # CLAUDE.md — cl_class_mgmt_v16
## Módulo de Gestión Académica · Odoo 16 · Cleveland English Institute

> Este archivo es el punto de entrada para cualquier agente que trabaje en este módulo.
> Léelo completo antes de tocar cualquier archivo. Contiene decisiones de diseño ya tomadas
> que NO deben revertirse sin justificación explícita del usuario.

---

## 0. REGLA DE ICONOGRAFÍA (2026-07-15) — NO usar emojis en las vistas

**Nunca usar emojis (🧸🎓👑🌟💻⟳ etc.) en ninguna vista de los dashboards ni en
ningún otro template/QWeb/OWL del módulo.** Para decorar o identificar
secciones, cards, leyendas, botones, etc., usar **Font Awesome** (ya incluido
en los assets del backend de Odoo — `/opt/odoo16/odoo16/addons/web/static/src/libs/fontawesome`,
sin necesidad de agregar ninguna dependencia ni CDN): `<i class="fa fa-xxx"/>`
(o `t-attf-class="fa {{variable}}"` si el ícono es dinámico).

Ejemplo aplicado (dashboard docente, 2026-07-15): los íconos de categorías
demográficas pasaron de emoji a Font Awesome:
`kids→fa-child, teens→fa-bicycle, adults14→fa-book, adults56→fa-graduation-cap,
adults78→fa-trophy, scholarship→fa-star, online→fa-laptop`; el botón
"Actualizar" pasó de `⟳ Actualizar` a `<i class="fa fa-refresh"/> Actualizar`.

Si se necesita un ícono que no esté seguro de que exista en la versión de
Font Awesome incluida, verificar antes con:
`grep -oE '\.fa-nombre-del-icono\b' /opt/odoo16/odoo16/addons/web/static/src/libs/fontawesome/css/font-awesome.css`

---

## 1. Entorno y despliegue

```
Servidor:      VPS con Ubuntu, usuario odoo16
Servicio:      systemd odoo16  (/etc/odoo16.conf)
Módulo:        /opt/odoo16/odoo16/cl_addons_v16/cl_class_mgmt_v16/
Base de datos: production_db          ← ÚNICA base relevante
               cleveland_development_db ← NO tiene este módulo instalado; no usar salvo
                                          que el usuario lo pida explícitamente
addons_path:   /opt/odoo16/odoo16/{addons,custom,cl_addons_v16}
Python venv:   /opt/odoo16/odoo16-venv/bin/python3
```

### Ciclo de actualización (copiar exacto cada vez)

```bash
sudo systemctl stop odoo16
sudo -u odoo16 /opt/odoo16/odoo16-venv/bin/python3 /opt/odoo16/odoo16/odoo-bin \
  -c /etc/odoo16.conf -d production_db -u cl_class_mgmt_v16 --stop-after-init
# revisar log:
tail -n 80 /var/log/odoo/odoo16.log | grep -E "(ERROR|WARNING|INFO.*cl_class)"
sudo systemctl start odoo16
```

### Shell para probar lógica Python sin navegador

```bash
sudo -u odoo16 /opt/odoo16/odoo16-venv/bin/python3 /opt/odoo16/odoo16/odoo-bin \
  shell -c /etc/odoo16.conf -d production_db --no-http --shell-interface=python
```

### Dependencias declaradas en `__manifest__.py`

```python
'depends': [
    'school',
    'school_mod',          # sobrescribe generate_registroEva() SIN super() — ver sección 4
    'school_optimize',     # crea standard.evaluaciones/actividades por estudiante
    'school_archive',      # solo agrega campo 'active'
    'custom_libroeva_copy', # define sequence + handle en subject.encuentros — reutilizar
    'report_xlsx',         # mixin OCA para reportes Excel
],
```

> **NUNCA editar los módulos `school`, `school_mod`, `school_optimize`, `school_archive` directamente.**
> Todo se hace por `_inherit` desde `cl_class_mgmt_v16`.

---

## 2. Arquitectura general del módulo

```
cl_class_mgmt_v16/
├── __manifest__.py
├── models/
│   ├── asistencia.py          # _inherit subject.asistencia
│   ├── registroeva.py         # _inherit standard.evaluacion
│   ├── subject.py             # _inherit subject.encuentros
│   ├── standard.py            # _inherit school.standard
│   ├── dashboard/             # ← NUEVO (ver sección 5)
│   │   ├── __init__.py
│   │   ├── cl_dashboard_config.py   # modelo abstracto base
│   │   ├── cl_kpi_definition.py     # catálogo de KPIs configurables
│   │   ├── academic_dashboard.py    # cl.academic.dashboard
│   │   ├── teacher_dashboard.py     # cl.teacher.dashboard
│   │   └── admin_dashboard.py       # cl.admin.dashboard
├── wizard/
│   ├── reprogramar_wizard.py
│   ├── teacher_mgmt_wizard.py       # wizard de reporte docente (ya existe)
│   ├── academic_report_wizard.py    # ← NUEVO
│   └── admin_report_wizard.py       # ← NUEVO
├── report/
│   ├── teacher_mgmt_report_xlsx.py
│   ├── teacher_mgmt_report_views.xml
│   ├── academic_report_xlsx.py      # ← NUEVO
│   └── admin_report_xlsx.py         # ← NUEVO
├── views/
│   ├── standard_view.xml
│   ├── menu_views.xml               # ← REORGANIZAR (ver sección 3)
│   └── dashboard_views.xml          # ← NUEVO (ir.actions.client de los 3 dashboards)
└── static/src/
    ├── js/
    │   ├── teacher_mgmt_dashboard.js   # ya existe
    │   ├── academic_dashboard.js       # ← NUEVO
    │   └── admin_dashboard.js          # ← NUEVO
    ├── xml/
    │   ├── teacher_mgmt_dashboard.xml
    │   ├── academic_dashboard.xml      # ← NUEVO
    │   └── admin_dashboard.xml         # ← NUEVO
    └── scss/
        ├── teacher_mgmt_dashboard.scss
        ├── academic_dashboard.scss     # ← NUEVO
        └── admin_dashboard.scss        # ← NUEVO
```

---

## 3. Estructura de menú (DECISIÓN TOMADA — no renombrar sin consultar)

### Jerarquía final

```
Class  (school.menu_ems — raíz existente, NO tocar)
└── Gestión  (cl.menu_gestion — nuevo padre)
    ├── Académica        (ir.actions.client → cl_academic_dashboard)
    ├── Docente          (ir.actions.client → cl_teacher_mgmt_dashboard — mover, ya existe)
    ├── Administrativa   (ir.actions.client → cl_admin_dashboard)
    └── Reportes         (submenú)
        ├── Gestión Docente      (wizard teacher_mgmt_wizard — ya existe, mover aquí)
        ├── Rendimiento Académico (wizard academic_report_wizard — nuevo)
        └── Administrativo       (wizard admin_report_wizard — nuevo)
```

### Reglas de nomenclatura de menú

- El padre se llama **Gestión** — los hijos NO repiten la palabra.
- Los hijos directos son sustantivos femeninos: **Académica**, **Docente**, **Administrativa**.
- Nunca usar la palabra "Dashboard" en ningún menuitem visible.
- Los xml_id siguen el patrón: `cl.menu_gestion_academica`, `cl.menu_gestion_docente`, etc.

### XML base (en `views/menu_views.xml`)

```xml
<!-- Padre Gestión -->
<menuitem id="cl.menu_gestion"
          name="Gestión"
          parent="school.menu_ems"
          sequence="20"/>

<!-- Hijos directos -->
<menuitem id="cl.menu_gestion_academica"
          name="Académica"
          parent="cl.menu_gestion"
          action="cl.action_academic_dashboard"
          sequence="10"/>

<menuitem id="cl.menu_gestion_docente"
          name="Docente"
          parent="cl.menu_gestion"
          action="cl.action_teacher_mgmt_dashboard"
          sequence="20"/>

<menuitem id="cl.menu_gestion_administrativa"
          name="Administrativa"
          parent="cl.menu_gestion"
          action="cl.action_admin_dashboard"
          sequence="30"/>

<!-- Submenú Reportes -->
<menuitem id="cl.menu_gestion_reportes"
          name="Reportes"
          parent="cl.menu_gestion"
          sequence="40"/>

<menuitem id="cl.menu_reportes_docente"
          name="Gestión Docente"
          parent="cl.menu_gestion_reportes"
          action="cl.action_teacher_mgmt_wizard"
          sequence="10"/>

<menuitem id="cl.menu_reportes_academico"
          name="Rendimiento Académico"
          parent="cl.menu_gestion_reportes"
          action="cl.action_academic_report_wizard"
          sequence="20"/>

<menuitem id="cl.menu_reportes_admin"
          name="Administrativo"
          parent="cl.menu_gestion_reportes"
          action="cl.action_admin_report_wizard"
          sequence="30"/>
```

---

## 4. Modelos existentes — conflictos y soluciones ya aplicadas

### Conflicto crítico: `school_mod` rompe `generate_registroEva()`

`school_mod` sobrescribe `generate_registroEva()` en `school.standard` **sin llamar a `super()`**.
Cualquier `_inherit` que intente engancharse ahí queda huérfano.

**Solución aplicada:** El cálculo automático de fechas NO se hace en `generate_encuentros()` /
`generate_registroEva()`. Se hace en el `create()` de `subject.asistencia` y `standard.evaluacion`
(archivos `models/asistencia.py` y `models/registroeva.py`). Esto funciona independientemente de
qué módulo cree el registro.

### Campos heredados ya existentes en este módulo

| Modelo base | Campo agregado | Archivo |
|---|---|---|
| `school.standard` | `dias_clase_ids` (M2m → `cl.dia.semana`) | `models/standard.py` |
| `school.standard` | `action_recalcular_fechas_clase` | `models/standard.py` |
| `subject.asistencia` | `dias_diferencia_fin`, `_asignar_fecha_automatica`, `reprogramando` | `models/asistencia.py` |
| `standard.evaluacion` | `dias_diferencia_fin`, `_asignar_fecha_automatica`, `_posicion_encuentro_evaluacion`, `reprogramando` | `models/registroeva.py` |
| `subject.encuentros` | `sequence`, `es_evaluacion` | `models/subject.py` |

### Modelo auxiliar ya existente

- `cl.dia.semana` — 7 registros fijos (LUNES..DOMINGO), campos: `name`, `weekday_index` (0-6), `color`.
  Widget `many2many_tags` en la vista de `school.standard`.

---

## 5. Nuevos modelos de dashboard (DECISIÓN DE DISEÑO — 2026-07-15)

### Motivación

Los datos de los dashboards NO deben vivir en los wizards de reporte. Los wizards son transaccionales
(generan PDF/XLSX y desaparecen). Los dashboards necesitan:
- Filtros persistentes por usuario (campus seleccionado, período, agrupación)
- Configuración de KPIs (cuáles mostrar, en qué orden, con qué visualización por defecto)
- Una capa de datos separada que permita agregar históricos en el futuro sin romper la UI

### 5.1 Modelo abstracto base: `cl.dashboard.config`

```python
# models/dashboard/cl_dashboard_config.py

class ClDashboardConfig(models.AbstractModel):
    _name = 'cl.dashboard.config'
    _description = 'Configuración base de dashboard'

    user_id = fields.Many2one('res.users', default=lambda self: self.env.user,
                              string='Usuario', required=True)
    campus_ids = fields.Many2many('school.campus', string='Campus')
    date_from = fields.Date(string='Desde')
    date_to = fields.Date(string='Hasta')
    # El período activo: 'month' | 'quarter' | 'year' | 'custom'
    period_mode = fields.Selection([
        ('month', 'Este mes'),
        ('quarter', 'Este trimestre'),
        ('year', 'Este año'),
        ('custom', 'Personalizado'),
    ], default='month', string='Período')
    kpi_ids = fields.One2many('cl.kpi.definition', 'dashboard_model',
                               string='KPIs configurados')
```

> **IMPORTANTE:** `cl.dashboard.config` es `AbstractModel` — no crea tabla propia.
> Los tres dashboards concretos heredan de él y SÍ crean tabla.

### 5.2 Catálogo de KPIs: `cl.kpi.definition`

```python
# models/dashboard/cl_kpi_definition.py

class ClKpiDefinition(models.Model):
    _name = 'cl.kpi.definition'
    _description = 'Definición de KPI configurable'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', required=True)
    technical_key = fields.Char(string='Clave técnica', required=True)
        # Clave que el componente OWL usa para buscar este KPI en el dict de datos.
        # Ej: 'pct_asistencias_al_dia', 'total_estudiantes', 'retiros_mes'
    dashboard_model = fields.Char(string='Modelo de dashboard')
        # Nombre técnico del modelo al que pertenece. Ej: 'cl.academic.dashboard'
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    default_viz = fields.Selection([
        ('number', 'Número grande'),
        ('bar', 'Barras'),
        ('donut', 'Donut'),
        ('line', 'Línea de tendencia'),
        ('table', 'Tabla'),
    ], default='number', string='Visualización por defecto')
    allow_viz = fields.Char(string='Visualizaciones permitidas')
        # CSV de opciones. Ej: 'number,bar,donut'
        # El componente OWL parsea esto para mostrar los botones de cambio de vista.
    color_theme = fields.Selection([
        ('blue', 'Azul'),
        ('teal', 'Verde'),
        ('amber', 'Ámbar'),
        ('coral', 'Coral'),
        ('purple', 'Morado'),
    ], default='blue', string='Color')
    description = fields.Text(string='Descripción para el usuario')
```

### 5.3 Dashboard Académico: `cl.academic.dashboard`

```python
# models/dashboard/academic_dashboard.py

class ClAcademicDashboard(models.Model):
    _name = 'cl.academic.dashboard'
    _description = 'Dashboard Académica'
    _inherit = 'cl.dashboard.config'

    # Filtros adicionales específicos de académica
    standard_ids = fields.Many2many('standard.standard', string='Niveles')
    subject_ids = fields.Many2many('subject.subject', string='Cursos')
    section_state = fields.Selection([
        ('all', 'Todas'),
        ('done', 'En curso'),
        ('terminate', 'Culminadas'),
    ], default='done', string='Estado de sección')

    # --- Métodos de datos (llamados por el componente OWL vía RPC) ---

    @api.model
    def get_dashboard_data(self, filters=None):
        """
        Devuelve dict completo para el componente OWL.
        `filters` es un dict opcional con:
          - campus_ids: list[int]
          - standard_ids: list[int]
          - subject_ids: list[int]
          - section_state: str
          - date_from: str ISO
          - date_to: str ISO
          - group_by: str  ('campus' | 'level' | 'course' | None)
        """
        # Implementar aquí. Ver sección 6 para el contrato del dict devuelto.
        pass

    @api.model
    def get_kpi_data(self, kpi_key, filters=None):
        """
        Devuelve solo los datos de un KPI específico.
        Permite que el componente OWL actualice un solo KPI sin recargar todo.
        """
        pass
```

### 5.4 Dashboard Docente: `cl.teacher.dashboard`

```python
# models/dashboard/teacher_dashboard.py

class ClTeacherDashboard(models.Model):
    _name = 'cl.teacher.dashboard'
    _description = 'Dashboard Docente'
    _inherit = 'cl.dashboard.config'

    teacher_ids = fields.Many2many('school.teacher', string='Profesores')
    status_filter = fields.Selection([
        ('all', 'Todos'),
        ('uptodate', 'Al día'),
        ('delayed', 'Atrasados'),
    ], default='all')

    @api.model
    def get_dashboard_data(self, filters=None):
        """
        Refactorizar la lógica actual de teacher.mgmt.wizard.get_dashboard_data()
        para que viva aquí. El wizard pasa a ser una capa delgada que llama a este método.
        """
        pass

    @api.model
    def get_kpi_data(self, kpi_key, filters=None):
        pass
```

> **Migración:** `teacher.mgmt.wizard.get_dashboard_data()` debe refactorizarse para
> delegar en `cl.teacher.dashboard.get_dashboard_data()`. El componente OWL
> `teacher_mgmt_dashboard.js` pasa a llamar al nuevo modelo. Hacer esto ANTES de
> construir los nuevos dashboards para no duplicar lógica.

### 5.5 Dashboard Administrativo: `cl.admin.dashboard`

```python
# models/dashboard/admin_dashboard.py

class ClAdminDashboard(models.Model):
    _name = 'cl.admin.dashboard'
    _description = 'Dashboard Administrativa'
    _inherit = 'cl.dashboard.config'

    show_financials = fields.Boolean(default=False,
        string='Mostrar facturación')
        # Se activa solo si el usuario tiene acceso a account.move

    @api.model
    def get_dashboard_data(self, filters=None):
        pass

    @api.model
    def get_kpi_data(self, kpi_key, filters=None):
        pass
```

---

## 6. Contrato de datos: lo que cada `get_dashboard_data()` debe devolver

El componente OWL espera SIEMPRE este formato de respuesta. No romper el contrato.

```python
{
    # Metadatos
    'company_name': str,
    'company_logo': str,          # base64 o False
    'generated_at': str,          # ISO datetime
    'filters_applied': dict,      # eco de los filtros usados (para mostrar en UI)

    # KPIs — lista ordenada por sequence
    'kpis': [
        {
            'key': str,           # technical_key del cl.kpi.definition
            'label': str,
            'value': float | int | str,
            'value_formatted': str,   # '85 %', '1,234', etc.
            'delta': float | None,    # variación respecto al período anterior (%)
            'delta_label': str,       # 'vs mes anterior'
            'viz': str,               # visualización activa ('number'|'bar'|'donut'|'line')
            'allow_viz': list[str],   # visualizaciones disponibles para este KPI
            'color': str,             # 'blue'|'teal'|'amber'|'coral'|'purple'
            'series': list | None,    # datos para bar/donut/line:
                                      # [{'label': str, 'value': float, 'color': str}]
        }
    ],

    # Datos de tabla principal (específico por dashboard)
    'rows': list[dict],

    # Datos agrupados (si group_by está activo)
    'groups': list[dict] | None,

    # Alertas (filas que requieren atención)
    'alerts': list[dict],
}
```

---

## 7. Diseño de KPIs interactivos en OWL (DECISIÓN TOMADA)

### Principio

Cada KPI card tiene tres niveles de interacción:
1. **Cambio de visualización** — botones icon-only en la card (número / barras / donut / línea).
   No hace RPC; solo cambia el modo de render local en el estado del componente.
2. **Filtro desde la card** — clic en una barra o segmento de donut aplica ese valor como filtro
   activo. Hace RPC con `get_dashboard_data()` pasando el filtro nuevo.
3. **Chips de filtro globales** — barra superior con chips seleccionables (campus, período,
   agrupación). Cada cambio hace RPC y recarga todos los KPIs.

### Estructura del componente OWL (patrón a seguir en los 3 dashboards)

```javascript
// Patrón base — adaptar por dashboard
class ClDashboard extends Component {
    setup() {
        this.state = useState({
            loading: true,
            data: null,
            filters: {
                campus_ids: [],
                period_mode: 'month',
                date_from: null,
                date_to: null,
                group_by: null,
                // ... filtros específicos del dashboard
            },
            kpi_viz: {},    // { [kpi_key]: 'number'|'bar'|'donut'|'line' }
                            // sobreescribe el default_viz del KPI
            active_tab: 'overview',
            breadcrumbs: ['Panel'],
            detail_id: null,
        });
    }

    async loadData() {
        this.state.loading = true;
        const result = await this.rpc('/web/dataset/call_kw', {
            model: 'cl.academic.dashboard',   // cambiar por modelo del dashboard
            method: 'get_dashboard_data',
            args: [],
            kwargs: { filters: this.state.filters },
        });
        this.state.data = result;
        this.state.loading = false;
    }

    setFilter(key, value) {
        this.state.filters[key] = value;
        this.loadData();
    }

    setKpiViz(kpi_key, viz) {
        // Sin RPC — solo cambia la visualización local
        this.state.kpi_viz[kpi_key] = viz;
    }

    onKpiSeriesClick(kpi_key, series_label) {
        // Clic en barra/segmento → aplica como filtro
        // Mapear kpi_key + series_label al filtro correspondiente
        // Ej: kpi_key='secciones_por_campus', series_label='Caracas' → setFilter('campus_ids', [id_caracas])
    }
}
```

### Reglas de visualización por tipo de KPI

| Tipo de KPI | `number` | `bar` | `donut` | `line` |
|---|---|---|---|---|
| Porcentaje global (ej: % al día) | ✓ default | ✓ (por grupo) | ✓ | ✓ (tendencia) |
| Conteo simple (ej: total estudiantes) | ✓ default | ✓ (por campus) | ✗ | ✓ |
| Distribución (ej: por categoría) | ✗ | ✓ default | ✓ | ✗ |
| Tendencia temporal | ✗ | ✓ | ✗ | ✓ default |
| Semáforo (ej: capacidad) | ✓ default | ✓ | ✗ | ✗ |

### SVG a mano — NO usar Chart.js ni librerías externas

Los gráficos se dibujan en SVG dentro del template OWL. Razón: no hay build pipeline (webpack/npm),
y Chart.js por CDN crea problemas de timing con OWL. El dashboard docente ya demostró que SVG
a mano es viable y suficiente para los casos de uso requeridos.

Componentes SVG reutilizables a implementar en `static/src/js/cl_chart_utils.js`:
- `renderBarChart(data, options)` → string SVG
- `renderDonutChart(data, options)` → string SVG
- `renderSparkline(data, options)` → string SVG (para tendencia en cards pequeñas)

---

## 8. KPIs por dashboard (catálogo completo)

### 8.1 Gestión Académica

| `technical_key` | Label | Viz permitidas | Color |
|---|---|---|---|
| `total_secciones_activas` | Secciones activas | number, bar | blue |
| `total_estudiantes` | Estudiantes matriculados | number, bar, donut | blue |
| `pct_asistencias_al_dia` | Asistencias al día | number, bar, donut | teal |
| `pct_evaluaciones_al_dia` | Evaluaciones al día | number, bar, donut | teal |
| `secciones_por_campus` | Secciones por campus | bar, donut | blue |
| `estudiantes_por_nivel` | Estudiantes por nivel | bar, donut | purple |
| `progreso_encuentros` | Progreso de encuentros | bar, table | amber |
| `alertas_vencidas` | Encuentros/evaluaciones vencidos | number, table | coral |

**`series` para KPIs agrupables:**
- `secciones_por_campus`: `[{'label': campus.name, 'value': count, 'color': ...}]`
- `estudiantes_por_nivel`: `[{'label': standard.name, 'value': count}]`
- `progreso_encuentros`: `[{'label': section.code, 'value': pct_completado, 'remaining': pct_restante}]`

### 8.2 Gestión Docente

| `technical_key` | Label | Viz permitidas | Color |
|---|---|---|---|
| `pct_asistencias_al_dia` | Asistencias al día | number, bar, donut | teal |
| `pct_evaluaciones_al_dia` | Evaluaciones al día | number, bar, donut | teal |
| `total_estudiantes` | Total estudiantes | number | blue |
| `total_retirados` | Retirados | number | coral |
| `distribucion_categoria` | Por categoría (ADULTS/KIDS) | donut, bar | purple |
| `top5_cursos_promedio` | Top 5 cursos por nota | bar, table | amber |
| `ranking_docentes` | Ranking docentes | bar, table | blue |

### 8.3 Gestión Administrativa

| `technical_key` | Label | Viz permitidas | Color |
|---|---|---|---|
| `total_estudiantes_activos` | Estudiantes activos | number, line | blue |
| `retiros_periodo` | Retiros del período | number, bar, line | coral |
| `pct_ocupacion_promedio` | Ocupación promedio | number, bar, donut | teal |
| `facturacion_pendiente` | Facturación pendiente | number | amber |
| `inscripciones_por_mes` | Inscripciones por mes | line, bar | blue |
| `retiros_por_motivo` | Retiros por motivo | donut, bar | coral |
| `capacidad_por_seccion` | Capacidad por sección | bar, table | purple |
| `balance_pagos` | Pagado vs pendiente | donut, number | amber |

---

## 9. Pestañas por sección de gestión

### Gestión Académica

```
Académica
├── Panel      — KPI cards globales + alertas rápidas
├── Secciones  — Tabla filtrable: sección / profesor / campus / estado asistencia / estado evaluación
├── Progreso   — Barras de progreso: encuentros dictados vs planeados, por sección
└── Alertas    — Solo secciones con encuentros o evaluaciones vencidos sin registrar
```

Filtros globales (chips superiores):
- Campus (multi-select)
- Nivel / `standard.standard` (multi-select)
- Estado de sección: Todas / En curso / Culminadas
- Período (Este mes / Este trimestre / Este año / Personalizado)
- Agrupar por: Campus / Nivel / Curso / Sin agrupación

### Gestión Docente (ya existe — extender, no reescribir)

```
Docente
├── Panorama     — KPIs globales + donut demográfico
├── Profesores   — Cards de profesor con estado + buscador + chips
├── Evaluaciones — Por profesor, estado de evaluaciones por sección
└── Ranking      — Barras de score por profesor
```

Agregar filtro por campus (ausente hoy). El resto ya está implementado.

Detalle de profesor (breadcrumb Panel / Profesores / [nombre]):
- Tabla: sección / estado asistencia / próximo encuentro / estado evaluación / próxima evaluación
- Agregar columnas "Próximo encuentro" y "Próxima evaluación" (date_start del primer draft)

### Gestión Administrativa

```
Administrativa
├── Panel          — KPI cards globales
├── Inscripciones  — Tabla: estudiante / sección / fecha / estado factura. Filtro por mes.
├── Retiros        — Lista + barra de retiros por mes
├── Capacidad      — Semáforo por sección (verde >70%, amarillo 40-70%, rojo <40%)
└── Facturación    — Resumen pagado/pendiente/vencido (solo si usuario tiene acceso a account.move)
```

Filtros globales:
- Campus (multi-select)
- Período: mes/año selector
- Estado de inscripción: Activos / Retirados / Todos

---

## 10. Fuentes de datos por dashboard (modelos a consultar)

### Gestión Académica

```python
# Secciones activas
env['school.standard'].search([('state', 'in', ['done', 'terminate'])])
# Campos: code, subject_id, user_id, school_id, total_students, capacity,
#         start_date, end_date, dias_clase_ids, asistencia_ids, registroeva_ids

# Encuentros vencidos sin registrar
env['subject.asistencia'].search([
    ('state', '=', 'draft'),
    ('date_start', '<', fields.Date.today()),
])
# Campos: standard_id, date_start, encuentro_id

# Evaluaciones vencidas sin registrar
env['standard.evaluacion'].search([
    ('state', '=', 'draft'),
    ('date_start', '<', fields.Date.today()),
])
```

### Gestión Docente

```python
# Ya implementado en teacher.mgmt.wizard._compute_report_data()
# Migrar a cl.teacher.dashboard.get_dashboard_data()
# Agregar: campus_ids como filtro adicional
```

### Gestión Administrativa

```python
# Inscripciones por período
env['student.inscripcion'].search([
    ('create_date', '>=', date_from),
    ('create_date', '<=', date_to),
])
# Campos: student_id, standard_id, state_aux, move_id, move_id.payment_state

# Retiros agrupados por mes
env['student.retiro'].search([...])
# Campos: create_date, tiporetiro_id, ri_id

# Capacidad
env['school.standard'].search([('state', '=', 'done')])
# Campos: total_students, capacity, remaining_seats, code, user_id, school_id

# Facturación (requiere acceso a account.move)
env['account.move'].search([('is_inscripcion', '=', True), ...])
# Campos: amount_total, amount_residual, payment_state
```

---

## 11. Grupos de acceso sugeridos

**DECISIÓN (2026-07-15, corrige lo que decía este doc antes): todos los
dashboards de Gestión son SOLO para administradores, nunca para profesores.**
El usuario pidió explícitamente que "estos dashboards no se le deben
mostrar a los usuarios teacher, solo a los administrators" — aplica a los 3
(Académica, Docente, Administrativa) y a los 3 wizards de Reportes. Ojo:
`school.group_school_manager` (mencionado en versiones anteriores de esta
tabla) **no existe** en este código; el grupo real siempre ha sido
`school.group_school_administration` (ver `school/security/school_security.xml`).

| Menú | Grupo requerido |
|---|---|
| Académica | `school.group_school_administration` (solo admin) |
| Docente | `school.group_school_administration` (solo admin) |
| Administrativa | `school.group_school_administration` (solo admin) |
| Reportes > Gestión Docente | `school.group_school_administration` (solo admin) |
| Reportes > Rendimiento Académico | `school.group_school_administration` (solo admin) |
| Reportes > Administrativo | `school.group_school_administration` + acceso a `account.move` |
| Facturación (pestaña interna) | Solo si `user.has_group('account.group_account_user')` |

**Importante para el ACL (`ir.model.access.csv`):** la restricción real no es
el `groups` del `<menuitem>` (eso solo oculta el menú de la navegación) sino
el `group_id` de la fila de `ir.model.access.csv` del modelo que sirve los
datos (`cl.academic.dashboard`, futuro `cl.teacher.dashboard`/
`cl.admin.dashboard`, `teacher.mgmt.wizard`). Si el ACL del modelo incluye
un grupo que el `<menuitem>` no muestra, un usuario de ese grupo igual
podría llamar al método por RPC si llega a la action de otra forma. Bug real
encontrado el 2026-07-15: `cl.academic.dashboard` tenía ACL para
`school.group_school_teacher` además de administración -- el usuario de
prueba (administrador, sin el grupo profesor) primero dio "No se pudo
cargar el tablero" por un ACL mal puesto (school.group_school_teacher en
vez de/además de administración), y luego, al pedir "solo administradores",
se quitó el acceso de profesor por completo. Antes de dar por buena la
seguridad de un dashboard nuevo, probar con
`env['modelo'].with_user(ese_usuario).get_dashboard_data()` en shell, no
asumir que el `groups` del menú alcanza.

---

## 12. Pendiente / no implementado (mencionado pero descartado para esta iteración)

- **Snapshots históricos** — modelo `cl.dashboard.snapshot` + cron diario para guardar KPIs en el
  tiempo y mostrar tendencias reales. La estructura de `cl.kpi.definition` ya lo soporta (campo
  `series` con `line`), pero requiere el modelo de snapshot y el cron. Descartado en esta fase.
- **Observaciones por profesor** — campo/modelo nuevo. Descartado.
- **Paleta dinámica por compañía** — usar `res.company.primary_color / secondary_color` en vez
  de los valores fijos de Cleveland. Pendiente de confirmación.
- **Alimentar el Google Sheets del teacher desde Odoo** — integración futura vía API Sheets.

---

## 13. Referencia de archivos clave

| Archivo | Qué contiene |
|---|---|
| `cl_class_mgmt_v16/school_module_overview.txt` | Catálogo completo del módulo `school` (modelos, menús, estados, relaciones) |
| `cl_addons_v16/cl_class_mgmt_v16/index.html` | Dashboard HTML del teacher (referencia visual para adaptar a Odoo) |
| `cl_addons_v16/cl_class_mgmt_v16/attendance_report_model.xlsx` | Modelo de reporte de asistencia del teacher (si no se puede acceder al Google Sheets) |
| `/var/log/odoo/odoo16.log` | Log del servidor — revisar siempre después de actualizar |

---

*Última actualización: 2026-07-15*
*Autor: cl_class_mgmt_v16 dev session*
