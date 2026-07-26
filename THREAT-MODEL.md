# Modelo de amenazas (STRIDE)

> **Actualizado: 2026-07-26** · Elaborado por el equipo del proyecto.
> **No ha habido auditoría de seguridad externa.**

Alcance: cliente Gearbox, almacenamiento local, cola, transporte, colector de
referencia, publicación de priors, adaptadores multi-vendor y cadena de
suministro.

Notación: **P** probabilidad, **I** impacto (B/M/A).

## 1. Cliente y almacenamiento local

| # | Amenaza (STRIDE) | Actor | Vector | I/P | Control preventivo | Control detectivo | Respuesta | Riesgo residual |
|---|---|---|---|---|---|---|---|---|
| 1.1 | **Information disclosure** — otro usuario del equipo lee `gearbox.db` | usuario local sin privilegios | permisos laxos | A/M | archivos `0600`, directorios `0700` | `doctor` | corregir permisos, rotar seudónimo | **Bajo**. Root o el propio usuario siempre pueden leer: es inevitable en un archivo local |
| 1.2 | **Information disclosure** — el prompt queda en disco | error de programación | log o campo nuevo | A/B | no se almacena prompt ni su hash; allowlist | pruebas `test_record_prediction_stores_no_path…` | `privacy scrub-local` | Bajo |
| 1.3 | **Information disclosure** — correlación por hash de prompt | quien obtenga la base | diccionario sobre SHA-256 | M/M | **eliminado**: ya no se guarda | — | `scrub-local` en bases heredadas | Muy bajo |
| 1.4 | **Tampering** — se edita `policy.json` para abrir autonomía | malware local | escritura directa | A/B | `allowed_gears` limitado a G0–G2; gates no dependen de la política | revisión manual | reinstalar | **Medio**: quien controla el equipo controla la configuración |
| 1.5 | **Denial of service** — la base crece sin límite | uso intensivo | acumulación | B/M | purga de cola, marcas de enviado | `telemetry status` | `purge` | Bajo |

## 2. Cola y transporte

| # | Amenaza | Actor | Vector | I/P | Preventivo | Detectivo | Respuesta | Residual |
|---|---|---|---|---|---|---|---|---|
| 2.1 | **Spoofing** — colector suplantado | atacante en red | DNS/proxy | A/B | HTTPS obligatorio, TLS validado, sin excepciones | error `tls_error` | no enviar; revisar endpoint | Bajo |
| 2.2 | **Tampering** — modificación en tránsito | MITM | red | A/B | TLS + SHA-256 del cuerpo en cabecera | rechazo del colector | reintento | Bajo |
| 2.3 | **Information disclosure** — token en logs | operador | volcado de errores | A/B | token sólo del entorno; `_redact()` | prueba `test_token_comes_from_env_and_is_never_echoed` | rotar token | Bajo |
| 2.4 | **Repudiation** — se pierde un envío en silencio | fallo de red | timeout | B/M | cola transaccional, backoff, estados explícitos | `telemetry status` | reintento automático | Bajo |
| 2.5 | **Elevation** — envío sin consentimiento | bug | ruta de código | A/B | `is_active()` se consulta antes de cualquier red | prueba `test_send_without_consent_refuses…` | revocar | Bajo |
| 2.6 | **DoS** — cápsula gigante | cliente modificado | eventos repetidos | M/M | tope por **cantidad** de eventos y por bytes | rechazo local y del colector | — | Bajo *(hallazgo real: el tope sólo por bytes era burlable con gzip)* |

## 3. Colector

| # | Amenaza | Actor | Vector | I/P | Preventivo | Detectivo | Respuesta | Residual |
|---|---|---|---|---|---|---|---|---|
| 3.1 | **DoS** — zip bomb | anónimo | gzip malicioso | A/M | descompresión acotada + ratio máximo | `rejected:decompression_bomb` | rate limit / bloqueo | Bajo |
| 3.2 | **DoS** — inundación de cápsulas | anónimo | volumen | M/A | rate limit por contribuyente | métricas | límite en el borde | **Medio**: el rate limit de referencia es en memoria; producción necesita almacén compartido |
| 3.3 | **Tampering** — envenenamiento de priors | actor con muchos seudónimos | cápsulas falsas | A/M | umbral de cohorte + de contribuyentes distintos | anomalías en `/health` | invalidar priors, publicar aviso | **Alto sin autenticación fuerte.** Es la amenaza abierta más seria |
| 3.4 | **Information disclosure** — celda con pocos usuarios | error de agregación | umbral mal aplicado | A/B | doble umbral; el cliente revalida y rechaza | pruebas de cohorte | retirar documento, rotar | Bajo |
| 3.5 | **Replay** — reenvío de cápsulas capturadas | MITM pasivo | repetición | M/M | idempotencia + frescura del periodo | `duplicates_ignored` | — | Bajo |
| 3.6 | **Spoofing** — token de ingesta filtrado | operador | fuga | A/B | token en entorno, comparación constante | uso anómalo | rotar token, invalidar | Medio |
| 3.7 | **Information disclosure** — retención excesiva | operador | mala configuración | A/B | tope duro de 30 días, borrado al agregar | `/health` reporta retención | purga y aviso | Bajo |
| 3.8 | **Elevation** — inyección SQL | anónimo | payload | A/B | consultas parametrizadas | — | — | Bajo |

## 4. Adaptadores multi-vendor

| # | Amenaza | Actor | Vector | I/P | Preventivo | Detectivo | Respuesta | Residual |
|---|---|---|---|---|---|---|---|---|
| 4.1 | **Elevation** — inyección de comandos vía prompt | contenido del prompt | `shell=True` | A/B | lista de argumentos; prompt por stdin | revisión de código | — | Bajo |
| 4.2 | **Information disclosure** — el prompt aparece en `ps` | usuario local | `argv` | M/B | prompt por stdin | — | — | Bajo |
| 4.3 | **Information disclosure** — un vendor registra datos sensibles | proveedor | su propia telemetría | A/M | ninguno técnico: es su servicio | contrato del proveedor | no enviar material sensible a CLIs | **Alto y estructural.** Lo que se manda a un tercero, lo tiene un tercero |
| 4.4 | **Spoofing** — falso consenso multi-vendor | configuración | mismo vendor en ambos roles | A/M | `cross_vendor` exige familias distintas | `cross_vendor_reason` en el brief | repetir con otro vendor | Bajo |
| 4.5 | **Tampering** — robo de credenciales de otro CLI | adaptador malicioso | leer archivos de sesión | A/B | prohibición explícita; entorno filtrado | revisión de código | — | Bajo |

## 5. Cadena de suministro y CI

| # | Amenaza | Actor | Vector | I/P | Preventivo | Detectivo | Respuesta | Residual |
|---|---|---|---|---|---|---|---|---|
| 5.1 | **Tampering** — dependencia comprometida | upstream | paquete | A/B | **cero dependencias externas** | — | — | Muy bajo |
| 5.2 | **Tampering** — action de GitHub comprometida | upstream | `uses:` | A/B | permisos mínimos (`contents: read`) | revisión | fijar SHA | **Medio**: aún no se fijan por SHA |
| 5.3 | **Tampering** — instalación por `curl \| bash` desde `master` | mantenedor o atacante con acceso | commit malicioso | A/B | aviso al instalar desde `master`; `GEARBOX_REF` fijable | revisión del script | fijar release | **Medio**: `curl \| bash` es cómodo y arriesgado; el README recomienda revisar antes |
| 5.4 | **Tampering** — release sin firmar | atacante | sustitución | A/B | — | — | — | **Medio**: no hay firma ni checksums publicados |
| 5.5 | **Social engineering** — PR que relaja un gate | contribuyente | cambio sutil | A/M | pruebas que fallan si el gate desaparece | CI | rechazar PR | Bajo |

## Riesgos residuales más altos

1. **Envenenamiento de priors (3.3)** — sin autenticación fuerte de
   contribuyentes, el umbral de cohorte es la única defensa real.
2. **Fuga hacia el vendor (4.3)** — estructural: no hay control técnico posible
   sobre lo que un proveedor registra de lo que le mandas.
3. **Releases y actions sin fijar/firmar (5.2, 5.4)** — mitigable con trabajo de
   infraestructura pendiente.
4. **Control del equipo local (1.4)** — quien controla la máquina controla la
   configuración. Ningún software local resuelve esto.

## Qué falta hacer

- Fijar actions por SHA y publicar checksums de releases.
- Rate limiting distribuido y autenticación de contribuyentes en el colector.
- Análisis estático (bandit/semgrep) y escaneo de dependencias en CI.
- Auditoría de seguridad externa antes de operar un colector público.
