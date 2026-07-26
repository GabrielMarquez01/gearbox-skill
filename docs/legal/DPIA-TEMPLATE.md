# Evaluación de impacto (DPIA / EIPD) — plantilla

> ⚠️ **BORRADOR — REQUIERE REVISIÓN LEGAL.** Plantilla técnica redactada por el
> equipo del proyecto, no por abogados. Debe adaptarse y validarse con asesoría
> jurídica según jurisdicción, operación y datos reales antes de publicarse o
> firmarse. Los campos entre `[CORCHETES]` deben completarse.
>
> **Actualizado: 2026-07-26**

## 1. Descripción del tratamiento
Recolección voluntaria de métricas agregadas de routing de IA, con
minimización previa al envío y publicación únicamente agregada.

## 2. Necesidad y proporcionalidad
**Finalidad:** mejorar recomendaciones con evidencia real.
**¿Se puede lograr con menos datos?** Se eliminó todo identificador y se
generalizaron las cifras a bandas. El modo local demuestra que el producto
funciona **sin** ningún envío: la telemetría es genuinamente opcional.

## 3. Datos tratados
Sólo enums y bandas del catálogo cerrado. Sin texto libre, sin identificadores,
sin marcas de tiempo finas, sin geografía.

## 4. Titulares
Personas usuarias que consintieron expresamente. **No dirigido a menores.**

## 5. Riesgos identificados

| Riesgo | Probabilidad | Impacto | Medida | Residual |
|---|---|---|---|---|
| Reidentificación por combinación de bandas | Baja | Alto | doble umbral de cohorte, bandas, sin geografía ni tiempo fino | Bajo |
| Fuga de secretos en la cápsula | Muy baja | Alto | allowlist + escáner bloqueante + pruebas negativas | Bajo |
| Correlación por seudónimo en el colector | Media | Medio | seudónimo fuera del cuerpo, rotación, retención corta | Medio |
| Retención excesiva | Baja | Alto | borrado al agregar, tope duro de 30 días | Bajo |
| Envenenamiento de agregados | Media | Medio | umbrales, rate limit, idempotencia | **Medio-alto** |

## 6. Decisiones automatizadas
Gearbox **recomienda**; no decide por la persona. En dominios críticos el gate
humano es obligatorio y no puede desactivarse. No hay elaboración de perfiles
con efectos jurídicos sobre las personas.

## 7. Consulta previa
[EVALUAR SI PROCEDE ANTE LA AUTORIDAD COMPETENTE.]

## 8. Conclusión
[A COMPLETAR POR EL RESPONSABLE CON ASESORÍA LEGAL.]

**Responsable de la evaluación:** [NOMBRE Y CARGO] · **Fecha:** [FECHA]
