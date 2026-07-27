# Aviso de privacidad (plantilla)

> ⚠️ **BORRADOR — REQUIERE REVISIÓN LEGAL.** Plantilla técnica redactada por el
> equipo del proyecto, no por abogados. Debe adaptarse y validarse con asesoría
> jurídica según jurisdicción, operación y datos reales antes de publicarse o
> firmarse. Los campos entre `[CORCHETES]` deben completarse.
>
> **Actualizado: 2026-07-26**

Estructura orientada a la **LFPDPPP vigente desde el 21 de marzo de 2025**
(DOF 20-03-2025). Recordatorio verificado: el INAI se extinguió y las
atribuciones pasaron a la **Secretaría Anticorrupción y Buen Gobierno**. No
copie avisos que aún nombren al INAI como autoridad.

## 1. Identidad y domicilio del responsable
[NOMBRE O RAZÓN SOCIAL] · [DOMICILIO] · [CORREO DE CONTACTO]

## 2. Datos que se tratan
Métricas técnicas agregadas de routing. **No** se tratan: prompts, respuestas,
código, archivos, rutas, nombres de proyecto, credenciales, correo, teléfono,
IP dentro del contenido, ni identificadores de sesión.

## 3. Datos sensibles
No se tratan datos personales sensibles. [SI APLICA OTRA COSA, DECLARARLO AQUÍ.]

## 4. Finalidades
**Primarias:** mejorar las recomendaciones de routing del software y publicar
estadísticas agregadas.
**Secundarias:** [NINGUNA / DECLARAR Y PERMITIR NEGATIVA.]

## 5. Fundamento y consentimiento
El tratamiento se basa en el **consentimiento expreso** de la persona titular,
otorgado mediante un acto afirmativo en la interfaz de línea de comandos y
registrado localmente con fecha y versión de política. Es **revocable en
cualquier momento** sin condición.

## 6. Transferencias
[DECLARAR TODA TRANSFERENCIA. Si el colector se aloja con un tercero, ese
proveedor es encargado y debe listarse en SUBPROCESSORS-TEMPLATE.md.]

## 7. Derechos ARCO
Acceso, rectificación, cancelación y oposición. Medio de ejercicio:
[CANAL]. Plazo de respuesta: [PLAZO CONFORME A LA LEY VIGENTE — VERIFICAR].
Procedimiento operativo: `docs/legal/DSAR-ARCO-PROCEDURE.md`.

## 8. Revocación del consentimiento
`gearbox.py telemetry revoke` (efecto inmediato en el equipo) y solicitud de
eliminación al colector con el `contributor_id` del comprobante.

## 9. Medidas de seguridad
Minimización previa al envío, escaneo de secretos, TLS validado, permisos
restrictivos, retención corta con borrado de crudas tras agregar. Detalle:
`SECURITY.md`.

## 10. Conservación
Crudas: máximo [N] días. Agregados: [PLAZO].

## 11. Vulneraciones
Procedimiento en `INCIDENT-RESPONSE.md`. Notificación conforme a la ley
aplicable.

## 12. Cambios al aviso
[MEDIO DE COMUNICACIÓN DE CAMBIOS.]

**Fecha de última actualización:** [FECHA]
