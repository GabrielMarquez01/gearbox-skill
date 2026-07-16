# Gearbox EV6 — Torre de Control para equipos de IA multi-motor

> Documentación comunitaria para replicar el sistema con cuentas propias, sesiones independientes y auditoría entre proveedores.

## Executive summary

Gearbox EV6 is an experimental multi-model orchestration system designed to reduce dependence on a single AI vendor.

A coordinator assigns work to different AI engines—currently Claude, Codex, and Antigravity—according to task type, effort level, availability, and measured performance. Autonomous workflows require two distinct roles: an executor and an auditor. Sensitive work involving money, legal interpretation, taxes, or personal data requires cross-vendor review and human approval.

The system does not merge credentials or share authenticated sessions. Every operator installs each CLI separately and performs every login personally. Engines are enrolled only after their invocation, operating modes, limits, and cost model have been verified.

During its first operational day, a Codex cross-audit identified a relevant Mexican tax-rule omission—Miscellaneous Tax Rule 3.13.7—that the primary review had missed. This did not prove that one model was universally better. It demonstrated the practical value of independent review by a model from another vendor.

Gearbox EV6 is early-stage infrastructure. Windows sandbox restrictions, headless authorization problems, quota visibility, and inconsistent CLI behavior remain real operational frictions. The goal of this document is to make those limitations reproducible and measurable, not to hide them.

---

## 1. ¿Qué problema intenta resolver?

Usar un único modelo de IA para coordinar, ejecutar y revisar una tarea crea varios puntos débiles:

- Si su cupo se agota, el flujo se detiene.
- Si interpreta mal una instrucción, puede revisar su propio error sin detectarlo.
- Si cambia el producto, sus precios o sus límites, toda la operación queda expuesta.
- Si el mismo motor ejecuta y aprueba, la auditoría puede convertirse en una confirmación de su primera respuesta.
- No existe evidencia comparable sobre qué motor funciona mejor para cada clase de trabajo.

Gearbox EV6 trata los motores de IA como una flota con puestos, suplencias y medición de desempeño.

No busca una “IA perfecta”. Busca una operación que pueda continuar cuando un motor falla, se queda sin cupo o necesita una segunda opinión verdaderamente independiente.

Sus objetivos son:

1. Reducir la dependencia de un solo proveedor.
2. Separar ejecución y auditoría.
3. Exigir revisión cruzada en decisiones sensibles.
4. Mantener continuidad cuando un motor no está disponible.
5. Medir resultados antes de reasignar responsabilidades.
6. Conservar al humano como autoridad final en acciones irreversibles.

### Lo que Gearbox EV6 no es

- No es un sistema que comparta cuentas o sesiones entre agentes.
- No elimina la responsabilidad humana.
- No garantiza que dos modelos produzcan una respuesta correcta.
- No permite que un auditor “autorice” por sí solo pagos, despliegues o decisiones legales.
- No asigna puestos de manera permanente por preferencia de marca.
- No es todavía una plataforma terminada: es un harness operativo en calibración.

Un **harness** es la capa que prepara instrucciones, invoca motores, registra resultados y aplica controles alrededor de ellos.

---

## 2. Arquitectura en cinco minutos

### 2.1 Los puestos

Gearbox separa los motores de los puestos.

Un motor es una implementación concreta, por ejemplo Claude, Codex o Antigravity. Un puesto es una responsabilidad operativa:

| Puesto | Responsabilidad |
|---|---|
| Coordinador | Clasifica la tarea, define el plan, asigna motores y mantiene el canal humano |
| Ejecutor | Produce el resultado solicitado dentro de un alcance definido |
| Auditor | Busca errores, omisiones, riesgos y violaciones de criterios |
| Suplente | Mantiene el flujo cuando el titular no está disponible |
| Guardia | Conserva operaciones limitadas si el coordinador principal se queda sin cupo |

El coordinador no debe asumirse como “el modelo más inteligente”. Su trabajo es conservar contexto, aplicar reglas y decidir quién atiende cada carril.

En la implementación inicial, Claude ocupa la coordinación. Codex y Antigravity pueden actuar como ejecutores, auditores o suplentes según la tarea y la evidencia disponible.

### 2.2 Sucesión meritocrática

Cada puesto puede tener:

- Un titular.
- Uno o más suplentes.
- Restricciones de autoridad.
- Evidencia histórica de desempeño.

La sucesión no significa que el suplente herede todos los poderes del titular.

Si el coordinador principal se queda sin cupo, el modo guardia puede pasar primero a Codex y después a Antigravity. La guardia queda limitada a:

- Continuar trabajos que ya tengan una especificación escrita.
- Mantener carriles previamente autorizados.
- Documentar avances y bloqueos.
- Informar al operador humano.

La guardia no puede, por defecto:

- Desplegar a producción.
- Autorizar gastos.
- Ejecutar pagos.
- Cerrar decisiones legales o fiscales.
- Modificar datos sensibles.
- Ampliar el alcance original.

La sucesión se vuelve meritocrática cuando los puestos se revisan usando resultados observados: aprobación inicial, retrabajo, rechazo, costo y desempeño por clase de tarea.

### 2.3 Pareja obligatoria: ejecutor + auditor

Todo flujo autónomo necesita dos funciones separadas:

```text
Especificación
     ↓
  Ejecutor
     ↓
  Auditor
     ↓
¿Cumple criterios?
  ├─ No → retrabajo
  └─ Sí → entrega o ventanilla humana
```

El auditor no debe limitarse a corregir estilo. Debe intentar refutar el resultado:

- ¿Falta un requisito?
- ¿Se inventó una fuente?
- ¿Hay una condición no contemplada?
- ¿Se modificó algo fuera del alcance?
- ¿La evidencia realmente sostiene la conclusión?
- ¿Existe un riesgo que el ejecutor minimizó?

Para tareas sensibles se exige un auditor de otro proveedor.

Ejemplos:

| Trabajo | Ejecutor | Auditor recomendado |
|---|---|---|
| Borrador técnico reversible | Cualquier motor habilitado | Otro rol o motor disponible |
| Cambio de código con pruebas | Motor constructor | Auditor técnico independiente |
| Análisis fiscal | Motor primario | Motor de otro proveedor + humano |
| Pago o despliegue | Motor preparador | Auditor cruzado + aprobación humana |
| Tratamiento de datos personales | Motor restringido | Auditor cruzado + revisión humana |

La diversidad de proveedor no garantiza independencia perfecta, pero reduce la posibilidad de repetir exactamente el mismo patrón de razonamiento.

### 2.4 Gearbox: dos ejes, no una sola escala

Cada tarea se clasifica en dos dimensiones:

```text
Tarea = marcha de esfuerzo × motor asignado
```

#### Eje 1: marcha G0–G5

La marcha representa el esfuerzo, riesgo o profundidad de razonamiento requerido.

| Marcha | Uso orientativo |
|---|---|
| G0 | Operación mecánica o consulta trivial |
| G1 | Redacción o transformación simple |
| G2 | Construcción con especificación clara |
| G3 | Trabajo ambiguo o con varias dependencias |
| G4 | Auditoría crítica, dinero, legal, fiscal o privacidad |
| G5 | Decisión arquitectónica o sistémica de alto impacto |

Las definiciones exactas deben adaptarse a cada proyecto. La marcha no debe confundirse con el motor: una tarea G2 puede ejecutarse con distintos motores.

#### Eje 2: motor

El motor se elige según:

1. Candados de riesgo.
2. Existencia de una especificación escrita.
3. Disponibilidad y cupo.
4. Capacidades verificadas.
5. Historial de desempeño.
6. Costo confirmado.

Ejemplos:

```text
Construir una función con criterios claros
= G2 × motor constructor disponible

Auditar una interpretación fiscal
= G4 × motor primario + G4 × auditor de otro proveedor
```

Para dinero, asuntos legales, fiscalidad o datos personales, la eficiencia nunca elimina la revisión cruzada ni la aprobación humana.

### 2.5 Telemetría y calibración

Cada ejecución debería registrar, como mínimo:

```json
{
  "fecha": "2026-07-16T10:30:00Z",
  "clase_tarea": "auditoria_fiscal",
  "marcha": "G4",
  "motor": "codex",
  "rol": "auditor",
  "resultado": "aprobado_primera",
  "costo_estimado": null,
  "duracion_segundos": 0,
  "retrabajo": false
}
```

Los valores concretos pueden variar, pero conviene conservar:

- Motor y versión, cuando sea visible.
- Rol desempeñado.
- Tipo de tarea.
- Marcha asignada.
- Resultado.
- Número de retrabajos.
- Duración.
- Costo estimado o estado “desconocido”.
- Motivo de rechazo.
- Incidentes de permisos, sandbox o autenticación.

La calibración no debería hacerse con impresiones aisladas. Una primera revisión puede realizarse tras reunir aproximadamente dos semanas de datos; después puede repetirse mensualmente.

Los cambios de titular deben proponerse con evidencia y ser aprobados por el operador humano.

---

## 3. Guía de replicación

### 3.1 Requisitos básicos

Necesitarás:

- Un repositorio de prueba, preferentemente sin información sensible.
- Git.
- Una terminal compatible con tu sistema operativo.
- Node.js o el entorno requerido por tus wrappers.
- Claude Code y una cuenta propia compatible.
- Codex CLI y una suscripción propia de ChatGPT que habilite su uso.
- Antigravity CLI y una cuenta propia de Google compatible.
- Un formato común de especificaciones y resultados.
- Una bitácora local para telemetría.
- Un operador humano responsable de autenticación y autorizaciones.

Los nombres de productos, comandos de instalación, planes y límites pueden cambiar. Verifica siempre la documentación oficial de cada proveedor antes de automatizar el flujo.

### 3.2 Estructura genérica sugerida

```text
~/proyecto/
├── AGENTS.md
├── specs/
│   └── tarea-001.md
├── wrappers/
│   ├── claude-runner.*
│   ├── codex-runner.*
│   └── antigravity-runner.*
├── gearbox/
│   ├── puestos.json
│   ├── motores.json
│   └── reglas.md
├── telemetry/
│   └── decisions.jsonl
└── runs/
    └── tarea-001/
        ├── entrada.md
        ├── ejecucion.md
        └── auditoria.md
```

No copies rutas locales, tokens, cookies ni archivos de sesión dentro del repositorio.

### 3.3 Autenticación: regla humana obligatoria

Cada CLI debe autenticarse por separado mediante el procedimiento oficial del proveedor.

El operador humano debe:

1. Instalar o revisar personalmente el CLI.
2. Iniciar el flujo oficial de autenticación.
3. Abrir el navegador cuando sea necesario.
4. Elegir su propia cuenta.
5. Revisar los permisos solicitados.
6. Completar el login.
7. Probar una invocación mínima.
8. Confirmar límites y costos antes de enrolar el motor.

Nunca se debe:

- Copiar una cookie del navegador para entregarla a un agente.
- Pegar tokens en prompts.
- Compartir archivos de sesión entre motores.
- Automatizar credenciales personales en el repositorio.
- Pedirle a un motor que complete el login como si fuera el humano.
- Dar por hecho que una sesión interactiva funcionará en modo headless.

**Headless** significa ejecutar una herramienta sin una interfaz gráfica o navegador interactivo disponible.

### 3.4 Claude Code

Proceso general:

1. Instala Claude Code desde la fuente oficial.
2. Inicia el comando oficial de autenticación.
3. Completa personalmente el login.
4. Abre un repositorio de prueba.
5. Ejecuta una consulta sin permisos de escritura.
6. Verifica qué modelo y modalidad están disponibles.
7. Registra sus límites conocidos y su comportamiento ante el agotamiento de cupo.

Antes de usarlo como coordinador, comprueba que pueda:

- Leer las reglas del proyecto.
- Clasificar tareas.
- Generar especificaciones autocontenidas.
- Invocar o preparar trabajo para otros motores.
- Detectar cuándo debe detenerse ante una ventanilla humana.

### 3.5 Codex CLI

Proceso general:

1. Instala Codex CLI desde la fuente oficial.
2. Inicia sesión con tu propia cuenta.
3. Completa personalmente cualquier autorización en el navegador.
4. Confirma que tu plan de ChatGPT habilite el acceso esperado.
5. Ejecuta una prueba de solo lectura.
6. Prueba explícitamente el modo de sandbox que utilizarás.
7. Registra el comando probado y sus restricciones.

En Windows, valida especialmente:

- Acceso al directorio de trabajo.
- Creación de procesos secundarios.
- Diferencias entre PowerShell y otros shells.
- Rutas con espacios.
- Sesiones de usuario no disponibles para procesos aislados.
- Restricciones de escritura impuestas por el sandbox.

Una invocación correcta en modo interactivo no demuestra que el mismo wrapper funcionará en un proceso automatizado.

### 3.6 Antigravity CLI

Proceso general:

1. Instala Antigravity CLI desde su canal oficial.
2. Inicia el flujo de autenticación.
3. Completa personalmente el login con tu cuenta de Google.
4. Revisa los permisos solicitados.
5. Prueba una tarea mínima en sesión interactiva.
6. Repite la prueba en el entorno headless previsto.
7. Registra las diferencias entre ambos modos.

La fricción más importante encontrada durante el enrolamiento inicial fue la autorización headless. Un motor puede estar correctamente instalado y funcionar en una terminal humana, pero fallar cuando:

- No existe navegador disponible.
- El proceso no puede abrir la URL de autorización.
- La sesión expira.
- El entorno aislado no puede leer la sesión local.
- El CLI requiere una confirmación interactiva.
- Los permisos de la cuenta no coinciden con los esperados.

No resuelvas estas diferencias copiando sesiones. Trátalas como una restricción operativa y conserva un procedimiento humano de renovación.

### 3.7 Contrato mínimo para enrolar un motor

Un motor no debe entrar en la flota solo porque está instalado.

Como mínimo, registra:

```yaml
nombre: codex
proveedor: openai

invocacion_probada:
  comando: "<comando verificado localmente>"
  fecha: "AAAA-MM-DD"
  entorno: "Windows | macOS | Linux"
  resultado: "correcto | parcial | fallido"

modos:
  interactivo: true
  headless: false
  solo_lectura: true
  escritura_controlada: false
  salida_estructurada: true

autenticacion:
  realizada_por_humano: true
  metodo: "<flujo oficial>"
  sesiones_compartidas: false

costo:
  modelo: "suscripcion | consumo | incluido | desconocido"
  confirmado: false
  fuente: "<documentacion oficial consultada>"

limites:
  cupo_visible: false
  comportamiento_al_agotarse: "desconocido"

roles_autorizados:
  - ejecutor
  - auditor

roles_restringidos:
  - aprobador_financiero
  - aprobador_legal
  - despliegue_produccion

sandbox:
  probado: true
  observaciones:
    - "<restriccion encontrada>"
```

Los cuatro campos indispensables son:

1. Nombre inequívoco del motor.
2. Invocación realmente probada.
3. Modos operativos confirmados.
4. Costo confirmado o marcado explícitamente como desconocido.

“Parece gratuito” no equivale a costo confirmado.

### 3.8 Especificación mínima de una tarea

Para que un suplente pueda continuar sin reinterpretar todo el proyecto, cada tarea debería incluir:

```markdown
# Tarea

## Objetivo
Resultado concreto que debe producirse.

## Alcance
Archivos, sistemas o información permitidos.

## Fuera de alcance
Acciones que no deben realizarse.

## Entradas
Documentos y datos necesarios.

## Criterios de aceptación
- Condición verificable 1
- Condición verificable 2

## Riesgo
G0–G5 y justificación.

## Autoridad
Qué puede ejecutar el motor y qué necesita aprobación humana.

## Auditoría
Quién revisará y si debe pertenecer a otro proveedor.
```

Sin una especificación suficiente, el modo guardia no debería improvisar trabajo sensible.

### 3.9 Flujo mínimo reproducible

1. El humano crea una tarea pequeña y reversible.
2. El coordinador asigna marcha y clase.
3. El selector elige ejecutor.
4. El ejecutor produce un artefacto.
5. Otro motor actúa como auditor.
6. El coordinador compara el resultado con los criterios.
7. La bitácora registra aprobación, retrabajo o rechazo.
8. El humano aprueba cualquier acción irreversible.
9. Tras varias ejecuciones, se comparan resultados por clase de tarea.

Empieza con documentación o código desechable. No utilices como primera prueba un pago, un despliegue de producción ni una interpretación legal real.

### 3.10 Apéndice: comandos verificados

Los siguientes comandos fueron probados entre el 15 y el 16 de julio de 2026:

#### Instalación de Antigravity CLI

Verificado el 2026-07-15/16 mediante el instalador oficial de Google:

```bash
curl -fsSL https://antigravity.google/cli/install.sh | bash
```

#### Invocación headless de Codex

Verificada el 2026-07-15/16 en modo de solo lectura:

```bash
codex exec --sandbox read-only
```

Cuando Codex se ejecuta desde WSL sobre Windows, la fricción del sandbox de Windows puede requerir un wrapper de PowerShell para realizar la invocación en el entorno adecuado.

#### Prueba headless de Antigravity

Probada el 2026-07-15/16:

```bash
agy --sandbox --print "prompt"
```

Esta invocación requiere reglas de autorización de permisos —*allow-rules*— para operar correctamente en modo headless. Su configuración completa es una limitación conocida todavía pendiente.

> Los comandos, instaladores y opciones de CLI envejecen. Verifica siempre la sintaxis y el procedimiento vigente contra la documentación oficial de cada proveedor.

---

## 4. Modo mono-motor (empezar solo con Claude Code)

Gearbox puede adoptarse por capas. No es necesario instalar tres sistemas ni construir desde el primer día una flota multi-motor.

La capa base funciona completa con un solo motor, por ejemplo Claude Code:

- Clasificación de tareas por esfuerzo y riesgo mediante las marchas G0–G5.
- Separación de los roles de ejecutor y auditor usando agentes distintos del mismo proveedor.
- Tablero de estados para registrar tareas, revisiones, retrabajos y bloqueos.
- Regla permanente de que toda acción sensible pasa por el operador humano.

Así operaba este harness antes de EV6. Aunque el ejecutor y el auditor pertenezcan al mismo proveedor, separar instrucciones, contexto y roles sigue aportando una revisión útil. No ofrece la misma diversidad de razonamiento que una auditoría entre proveedores, pero permite aplicar desde el inicio la disciplina operativa del sistema.

La calibración basada en datos también funciona en modo mono-motor. El ciclo “L5” consiste en acumular aproximadamente dos semanas de bitácora de decisiones y después ajustar los umbrales con evidencia: qué tareas fueron bien clasificadas, dónde apareció retrabajo, qué riesgos se subestimaron y cuándo hizo falta intervención humana.

El camino recomendado es:

```text
Empieza mono-motor
        ↓
Mide durante aproximadamente dos semanas
        ↓
Ajusta umbrales con evidencia
        ↓
Añade un segundo motor solo cuando exista un caso real
```

Los casos reales que justifican sumar un segundo motor incluyen:

- Auditoría cruzada de contenido sensible.
- Continuidad operativa cuando el motor principal se queda sin cupo.

Multi-motor es una evolución opcional, no un requisito de entrada.

---

## 5. El primer día: una omisión fiscal detectada por auditoría cruzada

Durante la primera jornada operativa, entre el 15 y el 16 de julio de 2026, el sistema fue probado con una revisión que incluía contenido fiscal mexicano.

El flujo utilizó:

- Un motor para el análisis primario.
- Codex como auditor cruzado.
- Separación entre la respuesta original y la revisión.
- Revisión humana posterior.

El auditor cruzado detectó que el análisis inicial no había considerado adecuadamente la Regla Miscelánea Fiscal 3.13.7. La omisión podía afectar la forma de interpretar el caso examinado.

No se incluyen aquí nombres, montos, declaraciones, clientes ni información del negocio. Lo relevante para la comunidad es el patrón técnico:

```text
Análisis primario
      ↓
Revisión del mismo marco mental
      ↓
Posible confirmación del error

frente a:

Análisis primario de un proveedor
      ↓
Auditoría adversarial de otro proveedor
      ↓
Detección de una regla omitida
      ↓
Validación humana contra la fuente normativa
```

Esta experiencia no demuestra que Codex sea siempre mejor en asuntos fiscales. Tampoco convierte a ningún modelo en asesor fiscal.

Demuestra algo más limitado y útil: un segundo motor, separado por rol y proveedor, puede descubrir una omisión material que pasó el primer filtro.

La regla fue verificada posteriormente ese mismo día contra más de cinco fuentes independientes —firmas fiscales y bases de reglas mexicanas— por el coordinador, confirmando que el hallazgo del auditor cruzado era real. El ciclo completo de hallazgo, verificación con fuentes y corrección del contenido tomó menos de una hora.

La conclusión operativa fue conservar como candado permanente:

> Toda tarea relacionada con dinero, fiscalidad, asuntos legales o datos personales necesita auditoría cruzada entre proveedores y decisión humana final.

---

## 6. Fricciones reales encontradas

### 6.1 Sandbox de Windows

La automatización en Windows presentó restricciones que no aparecían en pruebas manuales:

- Procesos secundarios que no podían iniciarse bajo la sesión aislada.
- Diferencias de permisos entre la terminal humana y el runner.
- Rutas y perfiles de usuario no disponibles dentro del sandbox.
- Comandos válidos interactivamente que fallaban en ejecución automatizada.
- Inconsistencias entre shells.

Lección: prueba cada wrapper en el mismo modo de sandbox, usuario y directorio que utilizará el flujo real.

### 6.2 Autorización headless

Antigravity mostró fricción al trasladar una sesión autenticada manualmente a un flujo sin interfaz.

Lección: “login correcto” y “automatización headless correcta” son dos criterios de aceptación distintos.

### 6.3 Costos y cupos imperfectamente visibles

No todos los motores exponen de la misma manera:

- Consumo actual.
- Cupo restante.
- Ventana de renovación.
- Costo marginal.
- Motivo exacto de una limitación.

Lección: usa `desconocido` como valor válido. No inventes precisión.

### 6.4 Comparaciones todavía inmaduras

Una sola auditoría exitosa no basta para reasignar todos los puestos. También deben medirse falsos positivos, retrabajo, costo, duración y desempeño por tipo de tarea.

Lección: la meritocracia necesita datos comparables, no anécdotas favorables.

### 6.5 Coordinación como posible punto único de fallo

Aunque existan varios motores, un único coordinador puede seguir concentrando contexto y autoridad.

Lección: documenta el modo guardia, limita sus poderes y conserva especificaciones que otro motor pueda retomar.

---

## 7. Este documento fue escrito en equipo multi-motor

Este documento también forma parte del experimento de transparencia de Gearbox EV6.

- **Redacción:** Codex, un motor GPT de OpenAI.
- **Coordinación y definición del encargo:** Claude.
- **Tercer motor enrolado en la flota:** Antigravity.
- **Autoridad final sobre publicación y cambios:** el operador humano.

Antigravity no se presenta como coautor de secciones que no redactó. Su participación declarada es la de tercer motor enrolado dentro de la arquitectura descrita.

Esta atribución importa porque una documentación multi-motor debería indicar:

- Qué motor produjo cada artefacto.
- Qué motor lo auditó.
- Qué fuente proporcionó el contexto.
- Qué decisiones tomó el humano.
- Qué partes no fueron verificadas de forma independiente.

La transparencia de procedencia no garantiza calidad, pero permite evaluar y reproducir el proceso.

---

## 8. Cómo evaluar tu propia réplica

Durante las primeras pruebas, registra al menos:

| Métrica | Pregunta que responde |
|---|---|
| Aprobación a la primera | ¿El resultado cumplió sin retrabajo? |
| Tasa de retrabajo | ¿Cuántas ejecuciones necesitaron correcciones? |
| Tasa de rechazo | ¿Cuántas salidas no pudieron aprovecharse? |
| Hallazgos del auditor | ¿Cuántos errores reales detectó? |
| Falsos positivos | ¿Cuántos “errores” señalados no eran errores? |
| Duración total | ¿La revisión cruzada compensa el tiempo adicional? |
| Costo estimado | ¿Cuánto cuesta cada clase de tarea? |
| Continuidad | ¿El suplente pudo continuar cuando faltó el titular? |
| Incidentes de permisos | ¿Cuántas ejecuciones fallaron por el entorno? |
| Intervenciones humanas | ¿Dónde fue necesario detener la autonomía? |

No compares motores mezclando tareas diferentes. Un motor puede rendir bien construyendo con especificaciones y mal resolviendo ambigüedad, o viceversa.

Una comparación útil agrupa resultados por:

```text
clase de tarea + marcha + rol + entorno
```

---

## 9. Controles recomendados

### Obligatorios

- Login realizado personalmente por el humano.
- Secretos fuera de prompts, logs y repositorios.
- Ejecutor y auditor como roles distintos.
- Auditor de otro proveedor para trabajo sensible.
- Aprobación humana para dinero, legal, fiscal, privacidad y producción.
- Especificación escrita antes de activar suplentes.
- Registro explícito de costos desconocidos.
- Pruebas reales de sandbox y modo headless.
- Trazabilidad de qué motor hizo qué.

### Convenientes

- Repositorio de prueba separado.
- Salidas estructuradas.
- Límites de tiempo por ejecución.
- Presupuesto máximo por tarea.
- Lista de archivos permitidos.
- Revisión mensual de puestos.
- Detección de telemetría desactualizada.
- Procedimiento documentado para agotamiento de cupo.
- Interruptor humano para detener todos los carriles.

---

## 10. Invitación a la comunidad

La forma más útil de mejorar Gearbox EV6 no es afirmar que un motor “gana”, sino publicar resultados reproducibles.

Puedes replicar el sistema con tus propias cuentas y abrir un issue en el repositorio del proyecto indicando:

- Sistema operativo y versión.
- Shell utilizado.
- Motores y versiones visibles.
- Método oficial de autenticación.
- Modo interactivo o headless.
- Configuración de sandbox.
- Clase y marcha de las tareas.
- Número de ejecuciones.
- Aprobaciones, retrabajos y rechazos.
- Hallazgos reales del auditor.
- Falsos positivos.
- Duración.
- Costo confirmado o desconocido.
- Comportamiento al agotarse el cupo.
- Problemas de permisos.
- Cómo funcionó la sucesión.
- Qué acciones necesitaron intervención humana.

### Plantilla sugerida para issues

```markdown
# Resultado de réplica de Gearbox EV6

## Entorno
- Sistema operativo:
- Shell:
- Entorno interactivo o headless:
- Tipo de sandbox:

## Motores
- Coordinador:
- Ejecutor:
- Auditor:
- Versiones visibles:

## Autenticación
- Flujos oficiales utilizados:
- Login realizado por humano: sí/no
- Problemas encontrados:

## Prueba
- Clase de tarea:
- Marcha:
- Criterios de aceptación:
- Número de ejecuciones:

## Resultados
- Aprobadas a la primera:
- Con retrabajo:
- Rechazadas:
- Hallazgos reales del auditor:
- Falsos positivos:
- Duración:
- Costo confirmado:

## Continuidad
- ¿Se agotó algún cupo?
- ¿Entró un suplente?
- ¿Pudo continuar con la especificación disponible?

## Fricciones
- Permisos:
- Sandbox:
- Headless:
- Límites o cupos:
- Otros:

## Aprendizajes
- Qué funcionó:
- Qué no funcionó:
- Cambio recomendado:
```

No publiques:

- Tokens.
- Cookies.
- Archivos de sesión.
- Prompts con información privada.
- Nombres de clientes.
- Datos financieros.
- Expedientes legales o fiscales.
- Rutas privadas del equipo.
- Capturas que revelen cuentas o credenciales.

---

## 11. Estado y alcance del proyecto

Gearbox EV6 es una arquitectura operativa temprana. Sus principios centrales son replicables, pero sus asignaciones iniciales todavía necesitan calibración:

- Dos ejes: marcha y motor.
- Puestos separados de los proveedores.
- Sucesión con poderes restringidos.
- Pareja ejecutor + auditor.
- Auditoría cruzada para lo sensible.
- Telemetría común.
- Calibración basada en resultados.
- Control humano sobre acciones irreversibles.

La promesa razonable no es que varios modelos siempre produzcan una respuesta mejor. La promesa comprobable es más modesta:

> Si se separan los roles, se conserva la trazabilidad y se mide el resultado, un equipo multi-motor puede detectar errores diferentes, resistir mejor el agotamiento de cupos y reducir la dependencia de un solo proveedor.

Esa hipótesis debe seguir siendo probada con datos de la comunidad.