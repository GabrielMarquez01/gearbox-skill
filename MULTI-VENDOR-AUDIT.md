# Auditoría multi-vendor

> **Actualizado: 2026-07-26** · Implementado y probado con el adaptador manual.
> Los adaptadores de CLI existen pero **no se han verificado contra los CLIs
> reales autenticados** — ver [Límites](#límites).

## El error que esta capa existe para evitar

> «Dos modelos coincidieron, entonces es verdad.»

No lo es. Dos modelos pueden compartir sesgo, datos de entrenamiento y el mismo
error. Coincidir **sin evidencia primaria** no es validación: es un riesgo, y
Gearbox lo reporta como tal.

La fórmula que sí se sostiene:

```
independencia + evidencia primaria + contexto correcto + contradicción
+ aprobación responsable = decisión más defendible
```

## Roles separados

| Rol | Quién | Qué hace |
|---|---|---|
| **Executor** | un motor | produce el resultado |
| **Independent Auditor** | un motor de **otra familia** | responde el mismo problema a ciegas |
| **Evidence Verifier** | código + humano | comprueba que las fuentes existen y están vigentes |
| **Decision Synthesizer** | código | compara, mide y arma el brief |
| **Human Approver** | una persona con nombre | decide en dominios críticos |

Un mismo proveedor **no puede** ser Executor e Independent Auditor en una
auditoría que se declare multi-vendor. No es una recomendación: si las familias
coinciden, `cross_vendor` queda en `false` y el resultado pasa a `needs_human`.

## Revisión ciega

El auditor recibe: pregunta original, hechos, jurisdicción, fecha de corte,
criterios de aceptación y la obligación de citar fuentes.

El auditor **no** recibe: la respuesta del ejecutor, su conclusión, su
confianza, ni pistas sobre qué discrepancia se espera.

La ceguera es **estructural**, no disciplinaria: el prompt del auditor se
construye a partir de `AuditRequest`, un objeto que no contiene la respuesta del
ejecutor. Filtrarla exigiría modificar la clase, no olvidar un parámetro.

Pruebas: `test_auditor_never_sees_the_executor_answer`,
`test_blind_prompt_is_built_only_from_the_request`.

## Niveles

| Nivel | Cuándo | Qué exige |
|---|---|---|
| **L1** | tareas reversibles y de bajo riesgo | autoverificación |
| **L2** | trabajo normal con consecuencias | dos vendors independientes |
| **L3** | dominios críticos | dos vendors + fuentes oficiales + **especialista humano** |

L3 es obligatorio en: fiscal, legal, financiero, pagos, privacidad, datos
personales, salud, seguridad, producción y eliminación irreversible.

**Un L3 nunca queda `approved` sin aprobación humana explícita.** No hay
bandera, variable de entorno ni modo autónomo que lo evite, y la aprobación
exige identificar a la persona responsable — llamar `approve()` sin nombre lanza
un error.

## Jerarquía de fuentes

| Nivel | Qué es | Peso |
|---|---|---|
| **A** | leyes, reguladores, documentación oficial, contratos | 1.00 |
| **B** | tribunales, organismos técnicos, universidades | 0.60 |
| **C** | especialistas reconocidos | 0.35 |
| **D** | fuentes secundarias | 0.15 |

Reglas que el código aplica solo:

- una fuente **primaria vigente y accedida** pesa más que varias secundarias
  (la suma satura: cinco fuentes D nunca alcanzan a una A);
- una fuente **no accedida** pierde el 60 % de su peso: citarla no es
  verificarla;
- una fuente **desactualizada** pierde el 85 %;
- **la memoria del modelo no es fuente**: una afirmación marcada como «hecho
  confirmado» sin fuente primaria accedida se **degrada automáticamente** a
  inferencia;
- la accesibilidad **nunca se presume**: sin un verificador inyectado, ninguna
  fuente se marca como accedida.

## Las tres confianzas

Un solo número de confianza es una mentira cómoda. Se reportan tres, y son
independientes:

| Confianza | Responde | Ejemplo de trampa que evita |
|---|---|---|
| `routing_confidence` | ¿elegimos bien la marcha y el motor? | rutear perfecto una respuesta falsa |
| `factual_confidence` | ¿lo dicho está sostenido por evidencia verificable? | un modelo segurísimo sin fuentes |
| `decision_readiness` | ¿alcanza para **actuar**? | evidencia buena pero sin aprobación en un L3 |

`decision_readiness` es la más severa: se recorta si no hubo cross-vendor, si
hay discrepancias, si falta el auditor o si un L3 sigue sin aprobar.

## Decision Intelligence Brief

19 secciones obligatorias, siempre presentes. Si una no tiene contenido, se dice
explícitamente — un brief con huecos declarados es honesto; uno que omite
secciones, no.

1. Decisión que debe tomarse · 2. Respuesta ejecutiva · 3. Hechos confirmados ·
4. Información faltante · 5. Supuestos · 6. Posición del ejecutor ·
7. Posición del auditor independiente · 8. Coincidencias · 9. Discrepancias y
omisiones · 10. Evidencia y jerarquía de fuentes · 11. Escenarios posibles ·
12. Riesgo de cada escenario · 13. Recomendación razonada · 14. Confianza del
routing · 15. Confianza factual · 16. Confianza para actuar · 17. Qué podría
cambiar la conclusión · 18. Próxima acción · 19. Aprobación humana requerida

Debe ser legible por alguien no técnico y auditable por un especialista.

## Proveedores

```
audit/providers/
├── base.py         # subprocess con lista de args, prompt por stdin, timeout
├── claude_cli.py   # familia anthropic
├── codex_cli.py    # familia openai   (exec --sandbox read-only)
├── gemini_cli.py   # familia google
└── manual.py       # dos respuestas pegadas a mano, sin ejecutar nada
```

Reglas para cualquier adaptador:

- **nunca** leer, copiar ni inspeccionar archivos de autenticación de un
  proveedor. Cada persona autentica su propia cuenta;
- `subprocess` con **lista de argumentos**, nunca `shell=True`;
- el prompt viaja por **stdin**, no por `argv`: no aparece en `ps`;
- timeout obligatorio y salida acotada;
- entorno filtrado: ninguna variable con `TOKEN` o `KEY` llega al CLI.

Las capacidades se **detectan y reportan**, nunca se suponen: `available`,
`unavailable`, `unauthenticated`, `unsupported`.

### El adaptador manual

Existe porque la auditoría cruzada no puede depender de tener CLIs instalados y
autenticados. Pegas la respuesta que obtuviste de cada proveedor —de la web, de
otra máquina, de donde sea— y todo el pipeline funciona igual: comparación
ciega, jerarquía de fuentes, brief y gate humano.

## Uso

```python
from audit.contracts import AuditRequest
from audit.providers.manual import ManualProvider
from audit import orchestrator, decision_brief

peticion = AuditRequest(
    question="¿Podemos conservar estos datos 90 días?",
    facts=("El colector agrega y borra la cruda tras agregar.",),
    jurisdiction="MX",
    cutoff_date="2026-07-01",
    acceptance_criteria=("Citar la norma aplicable",),
    domains=("privacidad", "datos_personales"),     # ⇒ nivel L3
)

resultado = orchestrator.run_audit(
    peticion,
    ManualProvider(respuesta_a, vendor_family="anthropic", label="claude"),
    ManualProvider(respuesta_b, vendor_family="openai", label="codex"),
    routing_confidence=0.82,
)

print(decision_brief.render(resultado))
# resultado.status == "needs_human"  (L3)

orchestrator.approve(resultado, "Nombre del especialista responsable")
```

## Aislamiento respecto a la telemetría

Las respuestas de los proveedores **no son campos de cápsula**. `AuditResult.as_dict()`
expone `answer_chars` (la longitud), nunca el texto. Prueba:
`test_audit_answers_never_reach_a_telemetry_capsule`.

## Límites

- Los adaptadores de CLI están escritos pero **no verificados contra los CLIs
  reales autenticados**. Los argumentos (`claude -p`, `codex exec --sandbox
  read-only`, `gemini -p`) pueden envejecer: verifica la sintaxis vigente de cada
  proveedor antes de confiar en ellos.
- El emparejamiento de afirmaciones usa solapamiento léxico, no comprensión
  semántica: puede marcar como discrepancia dos formas de decir lo mismo. Es un
  sesgo **hacia la cautela** (más revisión humana), a propósito.
- La clasificación de fuentes por dominio es heurística y conservadora: ante la
  duda degrada el nivel.
- Nada de esto sustituye a un profesional. En dominios críticos, la
  responsabilidad es de la persona que aprueba.
