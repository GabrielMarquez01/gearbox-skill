# Privacidad en Gearbox

> **Actualizado: 2026-07-26**
> Este documento describe **controles técnicos**, no una declaración de
> cumplimiento. Ver [Límite honesto](#límite-honesto).

## Principio

Gearbox observa cómo trabajas para recomendarte mejor. Eso sólo es aceptable si
la observación se queda contigo por defecto y si lo que eventualmente sale es
tan pobre en información que no te describe a ti, sino a un patrón.

## Qué pasa en tu equipo (modo local, por defecto)

Al enviar un prompt, el hook clasifica la tarea y guarda en SQLite:

| Se guarda | Ejemplo | Por qué |
|---|---|---|
| Longitud del prompt | `412` | señal de complejidad |
| `project_ref` | `21f5327cf57ce9d4` | agrupar por proyecto sin guardar la ruta |
| `session_ref` | `a91c…` | agrupar por sesión sin guardar el id real |
| Clasificación | `implementation`, `G2`, `sonnet`, `high` | el aprendizaje |
| Riesgo/complejidad/ambigüedad | `0.15`, `0.48`, `0.30` | explicar la recomendación |
| Resultado | `accepted` | cerrar el bucle |

**No se guarda** el prompt, ni un hash del prompt, ni la ruta, ni el id de
sesión, ni la respuesta del modelo.

`project_ref` es `HMAC-SHA256(sal_local, ruta)` truncado. La sal es aleatoria,
se genera por instalación, vive en `~/.claude/gearbox/.local_salt` con permisos
`0600` y **nunca se transmite**. Consecuencia: el mismo proyecto en dos equipos
produce refs distintos — no son correlacionables.

### Corrección respecto a versiones anteriores

El preview inicial de V3 guardaba `SHA-256(prompt)`, `cwd` y `session_id` en
claro. Un hash de prompt no es anónimo: para prompts cortos o repetidos se
revierte con un diccionario, y es correlacionable entre equipos. Se eliminó.

Para limpiar una instalación previa:

```bash
~/.claude/gearbox/gearbox.py privacy scrub-local
```

## Qué sale del equipo

**En modo local: nada.** Verificable:

```bash
python3 -m unittest tests.test_compat_transport.LocalModeIsOfflineTests -v
```

Esa prueba sustituye `socket.socket`, `socket.create_connection` y
`socket.getaddrinfo` por funciones que fallan, y luego ejecuta clasificación,
registro, feedback, historial y el hook completo. Si algo intentara abrir una
conexión, la prueba lo delataría.

En modo `community`/`self-hosted` sale exactamente lo descrito en
[TELEMETRY.md](TELEMETRY.md), y sólo tras tu consentimiento explícito.

## Las tres barreras antes de un envío

1. **Allowlist.** La cápsula se construye campo por campo desde un catálogo
   cerrado. Un campo desconocido no puede entrar por accidente porque no hay
   código que lo copie.
2. **Bandas.** Los números se generalizan a rangos: `0.7345` → `"0.7-0.8"`.
3. **Escáner.** Se inspecciona el JSON serializado buscando llaves AWS/GitHub/
   OpenAI/Anthropic/Google, JWT, cabeceras Bearer, llaves privadas, correos,
   teléfonos, URLs, rutas Unix y Windows, IPs, UUID no permitidos, números que
   pasan Luhn y cadenas largas de alta entropía. Un hallazgo bloqueante **detiene
   el envío**.

El escáner reporta *tipo, campo y posición aproximada*, nunca el valor. Hay una
prueba que verifica precisamente eso: que el hallazgo no contenga el secreto ni
un fragmento de doce caracteres de él.

## Permisos y almacenamiento

- Directorios sensibles: `0700`. Archivos sensibles: `0600`.
- Escrituras atómicas (`tmp` + `os.replace`) para que un corte de luz no deje
  archivos a medias.
- Consultas SQLite parametrizadas; nunca concatenación de cadenas.
- Los subprocesos de auditoría reciben un entorno filtrado: ninguna variable con
  `TOKEN` o `KEY` en el nombre se propaga a un CLI de terceros.

## Tus controles

| Quiero… | Comando |
|---|---|
| Ver qué se enviaría | `telemetry preview` |
| Guardarlo para revisarlo | `telemetry export --out archivo.json` |
| Entender el trato en llano | `telemetry explain` |
| Dejar de enviar | `telemetry disable` |
| Vaciar la cola | `telemetry purge` |
| Revocar todo | `telemetry revoke` |
| Cambiar de seudónimo | `telemetry rotate-id` |
| Borrar identificadores heredados | `privacy scrub-local` |
| Desinstalar conservando datos | `uninstall.sh` |
| Desinstalar borrando datos | `uninstall.sh --purge-data` |

## Menores y datos sensibles

La telemetría **no acepta** —ni siquiera con consentimiento— datos de menores,
salud, biometría, orientación sexual, religión, origen étnico, ubicación
precisa, información fiscal individual, expedientes legales, credenciales ni
información financiera personal.

Si tu tarea pertenece a uno de esos dominios, lo único que puede viajar es la
*forma* de la tarea, nunca su contenido:

```json
{ "task_type": "critical", "risk_band": "high", "outcome": "accepted" }
```

Los hechos del caso jamás. El colector rechaza cualquier campo fuera del
catálogo, así que un cliente modificado tampoco podría colarlos.

## Marco legal aplicable

Verificado contra fuentes oficiales el 2026-07-26.

### México

La **nueva Ley Federal de Protección de Datos Personales en Posesión de los
Particulares** se publicó en el DOF el **20 de marzo de 2025** y entró en vigor
el **21 de marzo de 2025**
([texto vigente](https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf) ·
[decreto original](https://www.diputados.gob.mx/LeyesBiblio/ref/lfpdppp/LFPDPPP_orig_20mar25.pdf)).

El mismo decreto **extinguió el INAI**. Las atribuciones en materia de
protección de datos personales pasaron a la **Secretaría Anticorrupción y Buen
Gobierno**
([acuerdo de extinción, DOF 01-04-2025](https://sidof.segob.gob.mx/notas/5753636)).

> ⚠️ Cualquier documento que todavía nombre al INAI como autoridad está
> desactualizado. Verificar también la vigencia del Reglamento de la ley
> anterior: es una pregunta para un abogado, no para este repositorio.

Obligaciones relevantes: aviso de privacidad, consentimiento, principios de
licitud y **minimización**, derechos **ARCO** (acceso, rectificación,
cancelación, oposición), reglas de transferencias, medidas de seguridad
administrativas/físicas/técnicas y respuesta a vulneraciones.

### Unión Europea / EEE

GDPR (Reglamento 2016/679): roles responsable/encargado, base de licitud
(art. 6), consentimiento (art. 7), minimización (art. 5.1.c), protección desde
el diseño (art. 25), evaluación de impacto (art. 35), transferencias
internacionales (cap. V), derechos de los titulares (cap. III), decisiones
automatizadas (art. 22) y notificación de brechas (arts. 33–34).

### California

CCPA reformada por la CPRA. Derechos a saber, eliminar, **corregir**, optar por
no participar en la venta/compartición y **limitar el uso de información
personal sensible**; aviso en el momento de la recolección; contratos con
*service providers*
([OAG](https://oag.ca.gov/privacy/ccpa) ·
[CPPA](https://cppa.ca.gov/faq.html)).

> ⚠️ La CPPA aprobó reglamentos adicionales con entrada en vigor escalonada en
> 2026. Verificar el texto vigente antes de operar un colector con residentes de
> California.

## Reparto de responsabilidades

| Actor | Rol |
|---|---|
| Usuario local | Responsable de su instalación y de sus datos locales |
| Contribuyente community | Aportante seudónimo |
| **Operador del colector** | Responsable/controlador del servicio que opere |
| Proveedor de hosting | Encargado / service provider |
| OpenGravity | Mantenedor del software. **Sólo si opera un colector**, responsable de ese servicio |
| Vendors de IA | Proveedores independientes bajo sus propios contratos |
| Especialista humano | Responsable profesional de la decisión |
| Desarrolladores | Mantenedores, **sin acceso automático a telemetría** |

Mantener el software abierto y operar un servicio de telemetría son **papeles
jurídicos distintos**. Este repositorio no los mezcla.

## Límite honesto

> El repositorio proporciona controles técnicos y plantillas. La entidad que
> despliegue el colector debe adaptar y validar su cumplimiento con asesoría
> jurídica según jurisdicción, operación y datos reales.

Ningún control técnico sustituye un análisis legal. Los documentos de
`docs/legal/` son **borradores**.

## Reportar un problema de privacidad

Abre un issue **sin incluir datos personales ni secretos** describiendo qué
observaste y cómo reproducirlo. Si el hallazgo implica exposición de datos,
sigue [INCIDENT-RESPONSE.md](INCIDENT-RESPONSE.md).
