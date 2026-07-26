# Respuesta a incidentes

> **Actualizado: 2026-07-26** · Procedimiento para quien **opere** un colector y
> para el mantenimiento del proyecto. Sin infraestructura pública, varios pasos
> son todavía teóricos y se marcan como tales.

## Ciclo

```
detección → contención → preservación de evidencia → evaluación →
eliminación o rotación → notificación → recuperación → postmortem
```

Regla transversal: **preservar antes de borrar**. Un `rm -rf` apresurado
destruye la evidencia que después hace falta para saber a quién notificar.

Segunda regla: los plazos de notificación son legales, no técnicos. Un
responsable jurídico decide qué y a quién se notifica; la ingeniería aporta
hechos, no calificaciones.

## Comandos de contención

| Acción | Cómo |
|---|---|
| Detener ingestión | apagar el proceso del colector o retirar el token: sin token válido devuelve `401` |
| Rotar token de ingesta | cambiar `GEARBOX_COLLECTOR_TOKEN` y `GEARBOX_TELEMETRY_TOKEN`, reiniciar |
| Invalidar priors publicados | retirar el documento del origen; los clientes conservan el último válido y `community disable` los detiene |
| Purgar colas locales | `gearbox.py telemetry purge` |
| Detener envíos de un cliente | `gearbox.py telemetry disable` |
| Revocar por completo | `gearbox.py telemetry revoke` |
| Borrar aportaciones de un contribuyente | `POST /v1/deletion-requests` |
| Reducir retención | `GEARBOX_COLLECTOR_RETENTION_DAYS=1` y reiniciar |

## Escenarios

### 1. Una cápsula contenía un secreto

*No debería poder ocurrir:* el escáner bloquea antes de encolar. Si ocurre, es
un fallo del escáner.

1. **Contener:** `telemetry disable` en el cliente afectado.
2. **Preservar:** conservar la cápsula local; **no** pegarla en un issue.
3. **Evaluar:** ¿qué tipo de secreto, de quién, llegó al colector?
4. **Eliminar/rotar:** rotar la credencial expuesta *siempre*, aunque no se haya
   transmitido. En el colector, borrar la cruda.
5. **Notificar:** al titular de la credencial; evaluación legal si hay terceros.
6. **Recuperar:** añadir el patrón al escáner **con una prueba que falle antes
   del arreglo**.
7. **Postmortem:** por qué el patrón no estaba cubierto.

### 2. Colector comprometido

1. Sacarlo de servicio (no sólo detener ingestión).
2. Snapshot del disco y de logs antes de tocar nada.
3. Rotar tokens, credenciales de hosting y claves de firma.
4. Determinar qué crudas existían: son el peor caso de exposición.
5. Notificación a titulares y autoridad según jurisdicción — **decisión legal**.
6. Reconstruir desde imagen limpia; no reutilizar la comprometida.
7. Postmortem público si hubo datos de terceros.

### 3. Token de ingesta filtrado

Rotar de inmediato · revisar métricas por cápsulas anómalas · invalidar priors
generados en la ventana sospechosa · revisar cómo se filtró (logs, captura,
repositorio).

### 4. Datos crudos retenidos más tiempo del debido

Ejecutar purga · verificar por qué falló la retención automática · documentar la
ventana real · evaluar notificación si excedió lo declarado en el aviso.

### 5. Se publicó una celda con pocos usuarios

1. Retirar el documento del origen.
2. Publicar uno nuevo, corregido.
3. Asumir que el anterior puede estar cacheado en clientes.
4. Revisar por qué el doble umbral no lo detuvo.
5. Postmortem: es una fuga de privacidad, aunque parezca un error de conteo.

### 6. Priors comunitarios manipulados

Los clientes rechazan un documento con hash o firma inválidos y conservan el
último válido, así que el daño se limita a quien lo aceptara antes de detectarlo.
Retirar, publicar aviso de seguridad, rotar clave HMAC, revisar la cadena de
publicación.

### 7. Replay masivo

La idempotencia por `capsule_id` evita el doble conteo y la frescura del periodo
corta reenvíos viejos. Si aun así hay volumen: rate limit en el borde y bloqueo
temporal. Revisar si los agregados se inflaron.

### 8. Un vendor registró información sensible

No hay control técnico: lo enviado a un tercero lo tiene ese tercero.

1. Determinar qué se envió y a quién.
2. Revisar el contrato y la política de retención del proveedor.
3. Solicitar eliminación por sus canales.
4. Ajustar qué material se manda a CLIs externos.
5. Considerar el adaptador **manual** para material sensible.

### 9. El usuario revoca el consentimiento

Flujo normal, no incidente: `telemetry revoke` invalida, vacía la cola, rota el
seudónimo y deja comprobante. Si además pide borrado en el colector, ver
escenario 10.

### 10. Solicitud ARCO / DSAR

Ver [docs/legal/DSAR-ARCO-PROCEDURE.md](docs/legal/DSAR-ARCO-PROCEDURE.md).
Resumen: identificar por `contributor_id`, ejecutar el borrado de crudas,
entregar constancia y explicar con transparencia el límite sobre los agregados.

### 11. Dependencia comprometida

El proyecto **no tiene dependencias externas**: el riesgo se concentra en Python
y en las GitHub Actions. Si una action se ve comprometida: revisar workflows,
fijar por SHA, revisar si se publicó algún artefacto en la ventana afectada.

### 12. Falso consenso multi-vendor

Detección: `cross_vendor: false` con `cross_vendor_reason` explícito, o la nota
«Coincidir no es validar» en el brief. Respuesta: repetir con un proveedor de
otra familia y **revisar toda decisión tomada sobre ese brief**. Si se aprobó un
L3 con consenso falso, reabrir el caso con la persona responsable.

## Aviso de seguridad

Publicar en el README y en un issue fijado: qué pasó, qué versiones afectó, qué
datos pudieron verse, qué hacer como usuario, qué se corrigió. Sin exploits
completos mientras la mayoría no haya actualizado.

## Lo que no existe todavía

- No hay guardia ni SLA de respuesta.
- No hay canal cifrado dedicado para reportes.
- No hay avisos automáticos a clientes: la difusión es manual.
- No hay plantillas legales de notificación validadas por abogado.
