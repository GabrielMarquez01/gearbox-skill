# Community Learning

> **Actualizado: 2026-07-26** · Estado: implementado y probado. Sin
> infraestructura pública todavía.

## La idea en una frase

Si mil personas registran qué marcha funcionó para qué tipo de tarea, la
recomendación que recibe la persona mil uno en su **primer** día es mejor que la
que recibió la primera. Eso es todo lo que persigue este programa.

## Lo que la comunidad recibe

Nunca datos crudos. Sólo un documento agregado:

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-07-25",
  "minimum_cohort": 20,
  "routes": [
    {
      "task_type": "implementation",
      "gear": "G2",
      "model_family": "sonnet",
      "effort": "high",
      "sample_band": "100-249",
      "accepted_rate_band": "0.8-0.9",
      "rework_rate_band": "0.1-0.2"
    }
  ],
  "content_sha256": "…"
}
```

Ni un identificador. Ni una cifra exacta. Ni una cápsula individual.

## Protección estadística

Una celda **no se publica** si:

| Regla | Umbral | Por qué |
|---|---|---|
| Cohorte mínima | `n < 20` | una celda escasa puede señalar a una persona |
| Contribuyentes distintos | `< 5` | 20 eventos de una sola persona no son una cohorte, son un diario |

La segunda regla es un endurecimiento sobre el requisito original: el conteo de
eventos por sí solo no protege si todos vienen del mismo equipo.

Además: rangos en vez de cifras, redondeo, supresión de celdas escasas,
agrupación por categorías, **sin dimensión geográfica**, **sin ventana temporal
fina** y **sin identificadores**.

Prueba que lo demuestra: `test_many_events_but_few_contributors_is_suppressed`.

## Integridad

Cada documento lleva `content_sha256` sobre su contenido canónico (sin el bloque
de integridad). El cliente:

1. valida el schema y los enums;
2. recalcula el hash y lo compara;
3. verifica la firma HMAC-SHA256 si hay clave configurada;
4. **rechaza y conserva el último documento válido** si algo falla;
5. revalida al leer de disco, de modo que editar el archivo a mano no cuela.

Un documento con una celda por debajo del umbral se rechaza completo: publicar
una cohorte pequeña es un incidente, no un detalle.

## Cómo influyen los priors (y cómo no)

```
predicted_success = mezcla(prior_local, prior_comunitario, muestras_locales)
```

El peso comunitario es `4 / (4 + muestras_locales)`. Con cero evidencia propia,
la comunidad manda; con 200 tareas registradas, tu historia manda y la comunidad
apenas mueve la aguja.

**Lo que los priors NO pueden hacer, jamás:**

- quitar o suavizar un gate humano;
- cambiar la marcha asignada a un dominio crítico;
- sobreescribir tu `policy.json`;
- habilitar autonomía.

Prueba: `test_priors_shift_prediction_but_never_the_human_gate`.

## Comandos

```bash
gearbox.py community status      # ¿hay priors? ¿de cuándo? ¿firmados?
gearbox.py community update --url https://…/community-priors.json
gearbox.py community update --from priors.json      # archivo local
gearbox.py community inspect     # ver el documento y revalidarlo
gearbox.py community disable     # ignorar la comunidad, usar sólo tu evidencia
```

## Ciclo de vida del dato en el colector

```
cápsula recibida
  └─ validada contra el schema del SERVIDOR (no el del cliente)
      └─ guardada como cruda, temporalmente
          └─ agregada a contadores por ruta
              └─ CÁPSULA CRUDA ELIMINADA
                  └─ agregados → umbral de cohorte → community-priors.json
```

Retención por defecto: **7 días**, tope duro **30**. Una configuración más corta
siempre se acepta; una más larga se recorta. Las crudas se borran en cuanto se
agregan, sin esperar a que expiren.

## Privacidad diferencial

**No está implementada.** Es la mejora natural: añadir ruido calibrado a los
conteos para acotar formalmente lo que se puede inferir de una celda.

No se ha hecho porque hacerla mal es peor que no hacerla: un `epsilon` mal
elegido da una falsa sensación de garantía. Cuando exista, vendrá con su
presupuesto de privacidad documentado y pruebas. Mientras tanto, la protección
es la supresión por umbral, que es más burda pero honesta.

## Riesgos reconocidos

| Riesgo | Mitigación actual | Residual |
|---|---|---|
| Un actor envía datos falsos para sesgar priors | umbral de contribuyentes, rate limit, idempotencia | **Sí**: sin autenticación fuerte, un actor decidido con muchos seudónimos podría sesgar. Ver THREAT-MODEL.md |
| Celda con pocos usuarios se publica | doble umbral + validación en cliente | Bajo |
| Priors manipulados en tránsito | HTTPS + hash + HMAC opcional | Medio hasta que exista firma asimétrica |
| Correlación por seudónimo | rotación manual, seudónimo fuera del cuerpo | Medio: el operador del colector ve el seudónimo en cabecera |
