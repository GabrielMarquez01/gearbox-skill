# Aviso en el momento de la recolección (notice at collection)

> ⚠️ **BORRADOR — REQUIERE REVISIÓN LEGAL.** Plantilla técnica redactada por el
> equipo del proyecto, no por abogados. Debe adaptarse y validarse con asesoría
> jurídica según jurisdicción, operación y datos reales antes de publicarse o
> firmarse. Los campos entre `[CORCHETES]` deben completarse.
>
> **Actualizado: 2026-07-26**

Modelo pensado para CCPA/CPRA (California). Debe mostrarse **en o antes** del
momento de recolectar. En Gearbox, ese momento es la pantalla de consentimiento
del instalador y `telemetry explain`.

## Texto modelo

**Qué recolectamos.** Métricas agregadas sobre cómo se rutean tareas de IA:
tipo de tarea, marcha, familia de modelo, esfuerzo, bandas de riesgo y
confianza, resultado y si hubo intervención humana.

**Para qué.** Únicamente para mejorar las recomendaciones de routing del
software y publicar estadísticas agregadas a la comunidad.

**Cuánto tiempo.** Las cápsulas crudas se conservan como máximo [N] días y se
eliminan al agregarse. Los agregados se conservan mientras opere el servicio.

**¿Vendemos o compartimos su información?** No. No se vende ni se comparte
información personal para publicidad conductual entre contextos.

**Información sensible.** No se recolecta información personal sensible. El
esquema técnico rechaza cualquier campo fuera de un catálogo cerrado.

**Sus derechos.** Saber, eliminar, corregir y limitar. Ejercicio:
[CANAL DE CONTACTO].

**Aviso completo:** [URL DEL AVISO DE PRIVACIDAD]

## Verificación técnica

Cualquier persona puede comprobar lo anterior antes de enviar nada:

```bash
gearbox.py telemetry preview
gearbox.py telemetry export --out capsula.json
```
