# Matriz de promesas y evidencia

> **Actualizado: 2026-07-27** · 154 pruebas, todas pasando localmente en WSL.
> Verificado en CI en **6 combinaciones**: Ubuntu y macOS × Python 3.9, 3.11 y
> 3.12 ([run 30189667575](https://github.com/GabrielMarquez01/gearbox-skill/actions/runs/30189667575)).
> Localmente sólo se ejecutó 3.12 sobre Linux/WSL.

Regla de este documento: **nada se marca `verificado` por estar documentado.**
Sólo cuenta si existe una prueba que fallaría si la promesa dejara de cumplirse.

Estados: `verificado` (implementado + prueba) · `implementado` (código, sin
prueba automatizada) · `pendiente-infra` (requiere infraestructura que no
existe) · `pendiente-legal` (requiere abogado).

## Privacidad

| Promesa | Implementación | Prueba | Estado |
|---|---|---|---|
| No se envían prompts | allowlist cerrada + escáner | `test_capsule_contains_only_allowlisted_fields`, `test_forbidden_fields_are_rejected_one_by_one` | **verificado** |
| No se **almacena** el prompt ni su hash | `record_prediction` sin `prompt_hash` | `test_record_prediction_stores_no_path_no_session_no_prompt_hash` | **verificado** |
| El identificador de tarea no se deriva del prompt | UUID aleatorio independiente del contenido | `test_task_id_is_random_and_independent_of_prompt` | **verificado** |
| No se almacenan rutas locales | seudónimo HMAC con sal local | misma prueba (revisa los bytes crudos de la base) | **verificado** |
| Los seudónimos no son correlacionables entre equipos | sal aleatoria por instalación | `test_local_ref_is_not_correlatable_across_installs` | **verificado** |
| Las bases heredadas se pueden limpiar | `privacy scrub-local` | `test_scrub_local_clears_legacy_rows` | **verificado** |
| El contexto que ve el modelo no lleva el prompt | `prediction_context` | `test_hook_output_contains_no_prompt_text` | **verificado** |
| No sale ningún task_id ni ruta en la cápsula | `build()` devuelve ids aparte | `test_capsule_has_no_task_ids_or_paths` | **verificado** |
| Las marcas de tiempo se generalizan a semana | `iso_week` | `test_period_is_a_week_not_a_timestamp`, `test_exact_timestamp_period_is_rejected` | **verificado** |
| El motivo `other_local_only` nunca se transmite | degradación a `none` | `test_other_local_only_reason_never_leaves` | **verificado** |
| Las cifras exactas no salen (sólo bandas) | `probability_band`, `level_band` | `test_probability_band_never_leaks_exact_value`, `test_cohort_above_threshold_is_published_as_bands` | **verificado** |

## Escáner de secretos

| Promesa | Implementación | Prueba | Estado |
|---|---|---|---|
| Bloquea credenciales de AWS, GitHub, OpenAI, Anthropic, Google, Slack, JWT, llaves privadas | 22 patrones + entropía | `test_detects_every_fake_secret_as_blocking` (13 tipos) | **verificado** |
| Bloquea correos, teléfonos, URLs, rutas Unix/Windows, IPs | patrones PII | misma prueba | **verificado** |
| Detecta tarjetas por Luhn sin falsos positivos con dígitos aleatorios | `_luhn_ok` | `test_luhn_valid_number_blocks_but_random_digits_only_warn` | **verificado** |
| **Nunca imprime el secreto** — sólo tipo, campo y posición | `Finding` sin valor | `test_finding_never_contains_the_secret_value`, `test_reports_field_and_position_but_not_content` | **verificado** |
| Un secreto filtrado por bug detiene el envío | `assert_safe` en `enqueue` | `test_capsule_with_secret_never_reaches_the_queue` | **verificado** |
| No bloquea texto normal (sin falsos positivos ruidosos) | exenciones por campo | `test_ordinary_text_is_not_blocked` | **verificado** |

## Consentimiento

| Promesa | Implementación | Prueba | Estado |
|---|---|---|---|
| El modo por defecto es local | `default_record()` | `test_default_is_local_and_inactive`, `test_install_defaults_to_local_without_consent` | **verificado** |
| Nada premarcado | `bootstrap_from_env` exige acto explícito | `test_nothing_is_pre_checked` | **verificado** |
| Declarar el modo no equivale a consentir | dos variables obligatorias | `test_mode_env_alone_does_not_grant_consent`, `test_consent_env_alone_does_not_grant_consent`, `test_env_mode_alone_does_not_enable_telemetry_on_install` | **verificado** |
| No se envía sin consentimiento | `is_active()` antes de tocar la red | `test_send_without_consent_refuses_before_touching_the_network` | **verificado** |
| Revocar borra la cola pendiente | `purge_all` + `revoke` | `test_revoke_deletes_the_pending_queue` | **verificado** |
| Revocar deja comprobante y rota el seudónimo | `consent-receipts.jsonl` | `test_revoke_invalidates_and_leaves_receipt`, `test_contributor_id_is_random_and_not_derived` | **verificado** |
| El seudónimo es rotable | `rotate_id` | `test_rotate_id_changes_pseudonym_and_leaves_receipt` | **verificado** |
| La vista previa es exactamente lo que se enviaría | mismo objeto se imprime y se comprime | `test_preview_matches_exactly_what_would_be_sent` | **verificado** |

## Modo local sin red

| Promesa | Implementación | Prueba | Estado |
|---|---|---|---|
| **Cero conexiones** en clasificación, registro, feedback e historial | sin llamadas de red en esa ruta | `test_classify_record_and_feedback_make_zero_connections` | **verificado** |
| El hook no toca la red | `cmd_hook` local | `test_hook_makes_zero_connections` | **verificado** |

Ambas sustituyen `socket.socket`, `socket.create_connection` y
`socket.getaddrinfo` por funciones que fallan: cualquier intento se delata.

## Cola de salida

| Promesa | Implementación | Prueba | Estado |
|---|---|---|---|
| No duplica | `capsule_id` como PRIMARY KEY | `test_enqueue_then_duplicate_is_idempotent` | **verificado** |
| Reintentos con backoff creciente y jitter | `backoff_seconds` | `test_backoff_grows_and_has_deterministic_jitter` | **verificado** |
| No pierde en silencio | estados explícitos + `last_error_code` | `test_failure_schedules_backoff_and_keeps_entry`, `test_gives_up_after_max_attempts_without_losing_trace` | **verificado** |
| Un evento sólo queda entregado tras aceptación del colector | estados `reserved` → `delivered`; liberación al fallar | `test_reserved_events_are_confirmed_only_after_delivery` | **verificado** |
| Expira y purga | `purge_expired`, `purge_all` | `test_expired_entries_are_purged`, `test_purge_all_empties_queue_and_files` | **verificado** |
| Rechaza cápsulas demasiado grandes | tope por cantidad **y** por bytes | `test_oversized_capsule_is_rejected` | **verificado** |
| El payload es gzip del JSON canónico con su SHA-256 | `enqueue` | `test_stored_payload_is_valid_gzip_of_canonical_json` | **verificado** |

## Transporte

| Promesa | Implementación | Prueba | Estado |
|---|---|---|---|
| HTTPS obligatorio | `validate_endpoint` | `test_http_is_refused`, `test_https_is_accepted` | **verificado** |
| HTTP sólo en localhost y sólo en modo desarrollo | `allow_insecure_localhost` | `test_localhost_http_only_in_dev_mode` | **verificado** |
| El token sale del entorno y nunca se registra | `_token()`, `_redact()` | `test_token_comes_from_env_and_is_never_echoed` | **verificado** |
| User-Agent sin datos del equipo | constante | `test_user_agent_has_no_device_information` | **verificado** |
| Idempotency key y hash en cabeceras | `build_request` | `test_request_headers_carry_contract_metadata` | **verificado** |
| Certificados inválidos se rechazan | `ssl.CERT_REQUIRED`, `check_hostname` | — | **implementado** *(requiere un servidor TLS malo para probarlo end-to-end)* |

## Colector

| Promesa | Implementación | Prueba | Estado |
|---|---|---|---|
| Rechaza campos no permitidos | schema propio del servidor | `test_rejects_unknown_top_level_field` | **verificado** |
| Rechaza texto libre | límite de longitud + enums | `test_rejects_free_text_in_event` | **verificado** |
| Valida enums estrictamente | `ENUMS` | `test_rejects_value_outside_enum` | **verificado** |
| Resiste zip bombs | descompresión acotada + ratio | `test_rejects_zip_bomb` | **verificado** |
| Rechaza cuerpos grandes | `MAX_BODY_BYTES` | `test_rejects_oversized_body` | **verificado** |
| Idempotencia | `seen()` | `test_replay_of_same_capsule_is_deduplicated`, `test_rejects_idempotency_key_mismatch` | **verificado** |
| Anti-replay temporal | frescura del periodo | `test_rejects_stale_period` | **verificado** |
| Rate limiting | ventana deslizante | `test_rate_limit_kicks_in` | **verificado** |
| Autenticación configurable | comparación en tiempo constante | `test_auth_required_when_token_configured` | **verificado** |
| Los errores no devuelven el token | `redact_for_log` | `test_error_response_never_echoes_token` | **verificado** |
| Borra la cruda tras agregar | `drop_raw` | `test_raw_is_deleted_after_aggregation` | **verificado** |
| Retención con purga | `purge_expired_raw` | `test_expired_raw_is_purged` | **verificado** |
| Atiende solicitudes de borrado | `/v1/deletion-requests` | `test_deletion_request_removes_raw_capsules` | **verificado** |
| `/health` no expone PII | métricas filtradas | `test_health_exposes_no_pii` | **verificado** |
| Nunca publica cápsulas individuales | sólo agregados | `test_individual_capsule_is_never_exposed` | **verificado** |

## Aprendizaje comunitario

| Promesa | Implementación | Prueba | Estado |
|---|---|---|---|
| Cohortes < 20 no se publican | umbral | `test_small_cohort_is_never_published`, `test_cohort_violation_is_rejected` | **verificado** |
| Pocos contribuyentes distintos tampoco | umbral de 5 | `test_many_events_but_few_contributors_is_suppressed` | **verificado** |
| Documentos alterados se rechazan | `content_sha256` | `test_tampered_document_is_rejected`, `test_missing_hash_is_rejected` | **verificado** |
| Firma HMAC se verifica al guardar y en cada lectura cuando hay clave | `hmac.compare_digest` + clave configurada | `test_hmac_signature_is_verified_when_key_present`, `test_signature_is_revalidated_on_every_load` | **verificado** |
| Versión incompatible se rechaza | `SUPPORTED_SCHEMA` | `test_incompatible_schema_is_rejected` | **verificado** |
| Se conserva el último válido ante un rechazo | `store()` atómico | `test_last_valid_document_survives_a_rejection` | **verificado** |
| Un archivo tocado en disco no cuela | revalidación al leer | `test_corrupt_file_on_disk_is_ignored` | **verificado** |
| **Los priors nunca quitan un gate humano** | `human_gate` independiente | `test_priors_shift_prediction_but_never_the_human_gate` | **verificado** |
| La evidencia local pesa más con el tiempo | `blended_prior` | `test_blended_prior_gives_way_to_local_evidence` | **verificado** |
| Firma asimétrica de producción | — | — | **pendiente-infra** |
| Privacidad diferencial | — | — | **pendiente-infra** (documentada, no simulada) |

## Auditoría multi-vendor

| Promesa | Implementación | Prueba | Estado |
|---|---|---|---|
| El auditor no ve la respuesta del ejecutor | prompt derivado sólo de `AuditRequest` | `test_auditor_never_sees_the_executor_answer`, `test_blind_prompt_is_built_only_from_the_request` | **verificado** |
| El auditor sí recibe pregunta, hechos, jurisdicción, corte y criterios | `as_prompt()` | `test_auditor_receives_the_required_context` | **verificado** |
| Multi-vendor exige familias distintas | `_cross_vendor` | `test_two_families_count_as_cross_vendor`, `test_same_family_is_not_cross_vendor`, `test_undeclared_family_does_not_count` | **verificado** |
| Un solo vendor nunca cuenta como cruzado | — | `test_single_provider_is_never_cross_vendor` | **verificado** |
| Dominios críticos fuerzan L3 | `L3_DOMAINS` | `test_l3_domains_force_level_three` | **verificado** |
| **L3 no se aprueba solo** | `_status` | `test_l3_never_reaches_approved_on_its_own` | **verificado** |
| La aprobación exige persona identificada | `approve()` | `test_approval_requires_a_named_person` | **verificado** |
| «Coincidir» sin fuentes se marca como riesgo | `consensus_without_evidence` | `test_agreement_without_primary_sources_is_flagged_as_risk` | **verificado** |
| Conflicto material exige humano | `material_conflict` | `test_material_conflict_requires_human` | **verificado** |
| Hecho sin fuente primaria se degrada a inferencia | `normalize_claims` | `test_confirmed_fact_without_primary_source_is_downgraded` | **verificado** |
| Una fuente no accedida no cuenta como verificada | penalización | `test_unverified_source_does_not_count_as_verified`, `test_accessibility_is_never_assumed` | **verificado** |
| Una primaria pesa más que varias secundarias | saturación | `test_one_primary_outweighs_several_secondary` | **verificado** |
| Fuentes obsoletas pierden peso | `mark_stale` | `test_stale_source_loses_weight` | **verificado** |
| Tres confianzas separadas | `routing`/`factual`/`readiness` | `test_three_confidences_are_independent` | **verificado** |
| El brief tiene las 19 secciones | `SECTIONS` | `test_all_nineteen_sections_are_present` | **verificado** |
| El brief muestra hechos, supuestos, discrepancias y escenarios | `render` | `test_brief_separates_facts_assumptions_and_discrepancies` | **verificado** |
| Las respuestas no llegan a telemetría | `as_dict` sin `answer` | `test_audit_answers_never_reach_a_telemetry_capsule` | **verificado** |
| Sin `shell=True`, prompt por stdin | `providers/base.py` | `test_adapters_use_argument_lists_never_shell` | **verificado** |
| No se propagan credenciales a CLIs de terceros | `_env()` filtrado | `test_provider_env_excludes_credentials` | **verificado** |
| CLI ausente se reporta, no se supone | `capability()` | `test_unavailable_binary_is_reported_not_guessed` | **verificado** |
| Los adaptadores funcionan contra los CLIs reales | — | — | **pendiente-infra** (no verificado con proveedores autenticados) |

## Compatibilidad

| Promesa | Implementación | Prueba | Estado |
|---|---|---|---|
| `set.sh` sigue funcionando | wrapper | `test_set_sh_still_works` | **verificado** |
| `reset.sh` sigue funcionando | wrapper | `test_reset_sh_still_works` | **verificado** |
| `log.sh decision` sigue funcionando | wrapper | `test_log_sh_decision_still_appends` | **verificado** |
| Marchas inválidas se siguen rechazando | validación | `test_invalid_gear_is_still_rejected` | **verificado** |
| Statusline intacto (marcha, costo, cupo) | `cmd_statusline` | `test_statusline_renders_with_gears_and_usage`, `test_multiline_statusline_payload` | **verificado** |
| Tabla G0–G5 intacta | constantes | `test_gear_table_g0_to_g5_is_intact` | **verificado** |
| Modo `observe` sigue siendo el default | `default_policy` | `test_observe_mode_is_still_the_default` | **verificado** |
| Gates humanos preservados | `human_gate_categories` | `test_human_gate_categories_are_preserved` | **verificado** |
| La autonomía nunca alcanza G3+ | `allowed_gears` | `test_automation_never_allows_g3_or_above` | **verificado** |
| Instalación limpia y reinstalación idempotente | `install.sh` | `test_clean_install_then_reinstall_is_idempotent` | **verificado** |
| No se reemplaza un statusline ajeno | merge cuidadoso | `test_foreign_statusline_is_not_replaced` | **verificado** |
| Se conserva el backup inicial | `settings.pre-gearbox.json` | `test_backup_of_previous_settings_is_kept` | **verificado** |
| Desinstalar conserva configuración ajena y archiva datos | `uninstall.sh` | `test_uninstall_preserves_foreign_settings_and_archives_data` | **verificado** |
| Desinstalar limpia el bloque de CLAUDE.md | marcadores | `test_uninstall_removes_the_managed_claude_md_block` | **verificado** |

## Promesas que **no** se hacen

Se listan porque callarlas sería el problema:

| No se promete | Por qué |
|---|---|
| Cumplimiento legal automático | Los documentos de `docs/legal/` son borradores. **pendiente-legal** |
| Que dos modelos coincidiendo signifique verdad | Se detecta y se reporta como riesgo, explícitamente |
| Anonimato absoluto en el colector | El operador ve el seudónimo en cabecera durante la retención |
| Resistencia al envenenamiento de priors por un actor decidido | Sin autenticación fuerte, el umbral de cohorte es la única defensa. Ver `THREAT-MODEL.md` §3.3 |
| Que los CLIs de proveedores estén verificados | Los argumentos pueden envejecer; verificar contra la documentación oficial |
| Releases firmados o con checksum | **pendiente-infra** |
| Privacidad diferencial | **pendiente-infra**, documentada y no simulada |
| Windows nativo probado | Los scripts son bash; en CI sólo se comprueba que WSL esté documentado, no se ejecuta PowerShell |
