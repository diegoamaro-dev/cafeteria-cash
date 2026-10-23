<!--
========================= REXISTRO DA MEMORIA =========================
A memoria debe ser levadeira de ler e fácil de defender oralmente.
=======================================================================
-->

<!--
Capítulo redactado.

CRITERIO: os anexos ENLAZAN ou recollen material de apoio. Non se copia aquí
nada que xa exista noutro arquivo do repositorio.

NON se creou un anexo de glosario. Revisouse a memoria completa buscando
tecnicismos que precisasen definición e non aparece ningún: transacción,
snapshot, idempotente, determinista, RPO, RTO, commit, rollback, monolito,
ORM e API teñen CERO aparicións no texto. Os termos propios do negocio
—anulación, bruto, efectivo válido, IVE— explícanse onde se usan.
-->

# 14. Anexos

## Anexo A. Documentación técnica do repositorio

A memoria resume; estes documentos conservan o detalle completo.

| Documento | Contén |
|---|---|
| [ARQUITECTURA.md](../ARQUITECTURA.md) | Capas, módulos, grafo de dependencias e fluxos |
| [MODELO_DATOS.md](../MODELO_DATOS.md) | Dicionario de datos completo e diagrama ER |
| [DECISIONS_TECNICAS.md](../DECISIONS_TECNICAS.md) | As trece decisións, con alternativas descartadas |
| [PROBAS.md](../PROBAS.md) | A suite completa, arquivo por arquivo |
| [MANUAL_USUARIO.md](../MANUAL_USUARIO.md) | Manual detallado con capturas |
| [REQUIREMENTS.md](../../REQUIREMENTS.md) | Especificación de requisitos |
| [DISASTER_RECOVERY.md](../../DISASTER_RECOVERY.md) | Plan de recuperación |

---

## Anexo B. Modelo de datos

O diagrama entidade-relación e a descrición columna a columna das seis táboas
están en [MODELO_DATOS.md](../MODELO_DATOS.md).

Acompáñase o esquema real da base de datos, tal como o crea a aplicación.

---

## Anexo C. Probas

O desglose por arquivo e o que cobre cada grupo están en
[PROBAS.md](../PROBAS.md).

Acompáñase a saída completa da suite, coas 263 probas.

---

## Anexo D. Manual de usuario

O paso a paso completo, con todas as pantallas, mensaxes e casos particulares,
está en [MANUAL_USUARIO.md](../MANUAL_USUARIO.md).

O capítulo 10 desta memoria é unha versión reducida del.

---

## Anexo E. Índice de capturas

As dez capturas están en [`docs/capturas/`](../capturas/). **Todas están
feitas coa base de datos de demostración: ningún dato que aparece nelas é
real.**

| Arquivo | Que amosa | Onde aparece |
|---|---|---|
| `01-venda.png` | Pantalla de venda cunha venda en curso | Cap. 10 |
| `02-venda-rexistrada.png` | Confirmación tras cobrar | Cap. 10 |
| `03-historico.png` | Histórico con vendas válidas e anuladas | Cap. 10 |
| `04-resumo.png` | Resumo do día | Cap. 10 |
| `05-peche-previo.png` | Previsualización do peche | Cap. 10 |
| `06-peche-realizado.png` | Día xa pechado | Cap. 10 |
| `07-pdf-peche.png` | Documento A4 do peche | Cap. 10 e 11 |
| `08-backup.png` | Pantalla de copia de seguridade | Cap. 10 |
| `09-produtos.png` | Xestión de produtos | Cap. 10 |
| `10-establecemento.png` | Datos do establecemento | Cap. 10 |

---

## Anexo F. Plan de recuperación

O procedemento completo está en
[DISASTER_RECOVERY.md](../../DISASTER_RECOVERY.md), que documenta tanto o plan
de recuperación paso a paso como o estado real de cada parte do ciclo.

O [capítulo 9](09_SEGURIDADE_BACKUP_RECUPERACION.md) recolle ese estado e
explica por que a restauración segue pendente.

---

## Anexo G. O repositorio público

| | |
|---|---|
| **URL** | <https://github.com/diegoamaro-dev/cafeteria-cash> |
| **Licenza** | MIT |

Contén o código completo, as probas, a documentación técnica e as capturas.
Non contén ningunha base de datos, copia de seguridade nin documento xerado:
esa é unha regra do proxecto, e hai probas automatizadas que fallan se algún
deses arquivos chega a versionarse.

O [README](../../README.md) explica como instalalo, arrancalo, xerar datos de
demostración e executar as probas.
