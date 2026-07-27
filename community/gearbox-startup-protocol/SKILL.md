---
name: gearbox-startup-protocol
description: "Protocolo de arranque para agentes de mensajería continua (ej. Hermes): garantiza continuidad de flujo y entrega a canales, sin perder la regla de oro de Gearbox (clase más baja confiable) ni esconder degradaciones."
version: 1.0.1
author: Hermes + Gabriel Márquez (corregido por revisión de mantenedor antes de fusionar — ver notas)
---

# Protocolo de Arranque para Agentes de Mensajería (H0–H3)

Variante de `gearbox-startup-protocol` pensada para agentes que corren de forma
continua y entregan directo a canales de mensajería (Telegram, WhatsApp), donde
la fricción de "preguntar antes de cada paso" no es viable en el flujo normal.
**No reemplaza la regla de oro del Core — la aplica en ese contexto.**

## Directrices de Operación

1. **Clasificar SIEMPRE antes de ejecutar, con la clase más baja que sea
   confiable** — no una marcha fija por defecto. Rutina/recordatorios = H0;
   research accionable con datos verificables = H2; nunca escalar a H3 "por si
   acaso" (regla de oro del Core: escalar solo cuando el riesgo, dinero o
   exigencia de verificación lo justifique).
2. **Continuidad ante errores de payload/cuota (HTTP 413/429), con aviso
   obligatorio:** ante un error de tamaño o cupo, el agente puede limpiar
   contexto, reestructurar la tarea o cambiar de proveedor — pero **debe
   registrar el cambio de cerebro en su reporte** (qué proveedor/modelo se usó
   al final vs. el original). Cambiar de proveedor en silencio no es
   "continuidad", es degradación oculta — exactamente lo que este protocolo
   existe para evitar.
3. **Eficiencia de costo real, no solo "$0" como bandera:** preferir capas
   gratuitas cuando la clase de tarea lo permite (H0/H1), pero la clase de la
   tarea decide el modelo, nunca el costo decide la clase. Prompts acotados
   para no exceder límites de TPM.
4. **Flujo de información continuo:** mantener sincronizada la memoria
   persistente (`MEMORY.md`) y entregar reportes estructurados a los canales
   de destino — sin inventar ni omitir el aviso de degradación del punto 2.
5. **Acción proporcional al nivel de autorización, no "cero fricción":** este
   protocolo optimiza fricción operativa dentro de lo YA autorizado (rutina,
   canales de mensajería del propio agente) — no autoriza saltarse los niveles
   de autorización de la fábrica (Nivel C: dinero, legal, secretos,
   configuración compartida, publicar a terceros nuevos). Ahí la fricción de
   preguntar es la característica, no el defecto.

## Nota del mantenedor (por qué se corrigió antes de fusionar)

La versión original enviada proponía "Marcha Automática H3" por defecto y
"Cero Fricción: ejecución directa" — ambas contradicen la regla de oro del
Core (usar la clase MÁS BAJA confiable) y el principio de nunca saltarse
niveles de autorización. Se corrigió preservando el objetivo real del aporte
(que un agente de mensajería continua no se atore) sin heredar esos dos
riesgos. Ver PR de origen para el texto original.
