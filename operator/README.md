# Operación privada del servicio comunitario

Este directorio documenta la frontera operativa; no contiene secretos ni un
despliegue productivo.

Usa `collector/` como contrato y referencia local. La infraestructura real debe
vivir en un repositorio privado con:

- secretos administrados fuera de Git;
- base y respaldos cifrados;
- HTTPS y autenticación;
- rate limiting distribuido;
- monitoreo y alertas;
- retención y eliminación;
- firma de priors;
- runbooks de incidentes;
- revisión legal y de seguridad.

Copia `collector.env.example` al gestor de secretos de tu plataforma. Nunca
crees un `.env` productivo dentro de este repositorio.
