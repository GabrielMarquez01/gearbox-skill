# Frontera público/privado de Gearbox

## Decisión

Gearbox se distribuye como cliente open source y privado por defecto. El
servicio comunitario administrado se opera fuera del repositorio público.

## Parte pública

El repositorio contiene:

- clasificador y predictor local;
- base SQLite local;
- feedback normalizado;
- consentimiento y revocación;
- vista previa exacta;
- allowlist, bandas y escáner de secretos;
- outbox con reintentos;
- transporte HTTPS;
- cliente de priors agregados;
- colector de referencia para auditoría y autoalojamiento;
- pruebas y documentación.

No contiene:

- tokens de producción;
- dominio o endpoint privado no publicado;
- claves de firma;
- bases de datos de usuarios;
- cápsulas recibidas;
- logs productivos;
- respaldos;
- configuración del proveedor de hosting;
- información de incidentes no divulgados.

## Parte privada del operador

Debe vivir en un repositorio o plataforma de infraestructura con acceso
restringido:

- configuración de despliegue;
- secretos administrados;
- autenticación y rate limiting distribuido;
- base cifrada y respaldos;
- monitoreo, alertas y rotación;
- proceso de eliminación verificable;
- firma de priors;
- runbooks de incidentes;
- contratos, DPA y lista real de subencargados.

Publicar el cliente no autoriza a publicar datos operativos. Mantener privado el
backend tampoco autoriza a ocultar el contrato de datos: schema, campos,
retención y garantías permanecen documentados y comprobables en este repositorio.

## Flujo

```text
usuario
  → feedback local
  → cápsula minimizada
  → vista previa
  → consentimiento
  → HTTPS
servicio privado
  → validación estricta
  → agregación
  → borrado de crudas
  → priors firmados
cliente público
  → verificación
  → aprendizaje combinado con evidencia local
```

## Regla de lanzamiento

Community Learning no debe anunciarse como operativo hasta que existan:

1. endpoint productivo;
2. aviso de privacidad revisado;
3. responsable de incidentes;
4. eliminación autenticada;
5. firma verificable de priors;
6. monitoreo y respaldo;
7. prueba externa de seguridad.

Mientras falte alguno, se mantiene como beta cerrada o modo autoalojado.
