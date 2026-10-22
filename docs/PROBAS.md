# Probas

**263 probas automatizadas** en 11 arquivos, escritas con **`unittest`**, da
biblioteca estándar de Python.

Convén distinguir dous grupos, porque non proban o mesmo:

| Grupo | Probas | Que proba |
|---:|---:|---|
| Aplicación | **250** | A lóxica de negocio: produtos, vendas, histórico, resumo, peche, IVE, PDF, establecemento e copias de seguridade |
| Ferramenta `seed_demo.py` | **13** | O script que xera os datos de demostración. **Non forma parte da aplicación** |
| **Suite completa** | **263** | |

Cando neste documento se fala de «probas da aplicación», refírese ás **250**.

Non hai ningún framework de probas engadido: `requirements.txt` só contén Flask
e as súas dependencias.

---

## Executar a suite

```bash
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Sen `-v` para a saída resumida:

```bash
.venv\Scripts\python.exe -m unittest discover -s tests
```

Un só arquivo:

```bash
.venv\Scripts\python.exe -m unittest discover -s tests -p test_cierre.py
```

Tarda arredor de **35 segundos**. A saída esperada remata en `OK`.

---

## Reparto por arquivo

| Arquivo | Probas | Área |
|---|---:|---|
| `test_cart.py` | 10 | Cálculo de subtotais e totais en céntimos |
| `test_sales.py` | 18 | Cobro: persistencia, numeración, snapshots, atomicidade |
| `test_historial.py` | 21 | Histórico, anulacións e ausencia de borrado |
| `test_resumen.py` | 16 | Resumo diario: totais, datas e snapshots |
| `test_cierre.py` | 48 | Peche: cifras, numeración, atomicidade, bloqueo e concorrencia |
| `test_iva.py` | 28 | Desglose de IVE conxelado no peche |
| `test_congelar_cierres.py` | 12 | Migración controlada de peches antigos |
| `test_pdf.py` | 31 | PDF: contido, A4, rexeneración e só lectura |
| `test_establecimiento.py` | 30 | Datos do establecemento |
| `test_backup.py` | 36 | Copia de seguridade: validación e illamento |
| **Subtotal da aplicación** | **250** | |
| `test_seed_demo.py` | 13 | Datos de demostración (ferramenta, non aplicación) |
| **Total da suite** | **263** | |

---

## Illamento: a base real nunca se toca

Esta é a regra máis importante da suite. **Cada proba crea a súa propia base
SQLite nun directorio temporal** e redirixe a aplicación a ela mediante a
variable de entorno `CAFETERIA_DB`. Ao rematar, o directorio bórrase.

O mesmo mecanismo aplícase ás outras dúas saídas:

| Variable | Redirixe |
|---|---|
| `CAFETERIA_DB` | A base de datos |
| `CAFETERIA_EXPORTS` | A carpeta dos PDF |
| `CAFETERIA_BACKUP_DIR` | A carpeta das copias de seguridade |

Seis dos once arquivos de proba usan directorios temporais. Ademais, hai probas
que **comproban explicitamente o illamento**: que a pegada da base real non
cambia, que non queda ningunha copia dentro do repositorio e que a carpeta real
de copias non aparece no código nin nas probas.

Consecuencia práctica: a suite pódese executar en calquera momento, incluso coa
aplicación en marcha, sen risco para os datos.

---

## Que se proba

### Corrección dos cálculos

Subtotais e totais en céntimos, incluídos **os casos onde `float` daría un
resultado incorrecto**. Por exemplo, que `6 × 1,40 € + 4 × 1,65 €` dá
exactamente `15,00 €`.

### Persistencia

Que o que se garda se recupera igual despois de **cerrar e abrir a conexión** e
despois de **volver crear a aplicación**, simulando un reinicio.

### Integridade do histórico

- Unha venda anulada conserva número, data, importe e todas as liñas; só cambian
  o estado e a hora de anulación.
- O número de filas **non cambia** ao anular.
- Cambiar o nome ou o prezo dun produto **non altera** as vendas nin os peches
  anteriores.
- Unha venda `VOID` non volve a `VALID`.

### Ausencia de borrado

Dúas probas complementarias:

1. **Rastrexo do SQL real**: captúranse todas as sentenzas que a anulación envía
   a SQLite e compróbase que a única escritura é un `UPDATE` condicionado.
2. **Salvagarda sobre o código**: unha proba percorre `app/` e **falla** se
   alguén engade un `DELETE FROM sale`, `DELETE FROM sale_item` ou un `UPDATE`
   ou `DELETE` sobre as táboas de peche.

A segunda protexe a regra fronte a cambios futuros, non só fronte ao estado
actual do código.

### Erros e casos límite

A suite non proba só o camiño feliz:

- cobrar cunha venda baleira;
- prezos inválidos: baleiros, con texto, negativos, con máis de dous decimais;
- anular unha venda que non existe, ou anulala dúas veces;
- pechar un día xa pechado, ou un día futuro;
- xerar o PDF dun día sen peche, ou dun peche sen os datos conxelados;
- facer unha copia de seguridade sen carpeta configurada, ou coa unidade non
  dispoñible;
- datos do establecemento incompletos ou con caracteres que o PDF non pode
  mostrar.

En cada un compróbase non só que se rexeita, senón **que non queda nada escrito
a medias**.

### Atomicidade

Provócase un fallo no medio dunha escritura de varias filas e compróbase que o
**rollback é completo**: non queda unha cabeceira sen liñas nin unha venda a
medias. Compróbase tamén que **a venda en curso non se baleira** cando o
gardado falla, para poder reintentar.

### Concorrencia

`test_cierre.py` contén unha clase dedicada (`TestCarrera`) con **tres probas
que usan fíos reais**:

| Proba | Comproba |
|---|---|
| Unha venda que chega durante un peche | **Espera** ao bloqueo e, cando o peche confirma, **rexéitase** |
| Unha anulación que chega durante un peche | O mesmo: espera e rexéitase, sen cambiar o estado da venda |
| Un peche que chega durante unha venda | Espera e **inclúe** esa venda no peche |

A técnica: ábrese unha transacción `BEGIN IMMEDIATE` que non fai `COMMIT`, e
lánzase a outra operación nun fío. Compróbase que o fío segue vivo (está
esperando) e despois que, ao confirmar, o resultado é o correcto.

**Estas probas verificáronse contra código deliberadamente roto.** Executáronse
contra dúas versións con fallos típicos — unha sen a comprobación do día pechado
e outra coa comprobación feita *antes* de tomar o bloqueo — e **fallaron nas
dúas**. É dicir: non son probas que pasen por casualidade.

### Reprodutibilidade do PDF

Compróbase que o PDF empeza por `%PDF`, que ten unha páxina A4 vertical, que a
estrutura interna é coherente e que contén os datos esperados. E, sobre todo,
que **rexenerar o mesmo peche produce bytes idénticos**, mesmo despois de
cambiar produtos ou a configuración do establecemento.

### Non escribir cando non toca

Varias probas capturan o SQL que se executa e comproban que o resumo, o PDF e a
consulta do peche **non executan ningunha sentenza de escritura**.

### Ausencia de datos reais

Unha proba percorre todos os arquivos versionados e **falla** se algún contén
algo coa forma dun NIF, NIE ou CIF. Outras comproban que non hai bases de datos,
PDF nin arquivos de configuración versionados.

---

## Como están escritas

- **Unha base temporal por proba**, montada en `setUp()` e borrada en
  `tearDown()`.
- **Clases base compartidas** entre arquivos para non repetir a preparación.
- **Nomes descritivos en lugar de comentarios**: por exemplo,
  `test_una_venta_que_llega_durante_el_cierre_espera_y_se_rechaza`.
- **Datos sempre ficticios.** Ningunha proba usa datos reais do establecemento.
- `subTest()` para comprobar varios casos na mesma proba sen perder información
  de cal falla.

---

## O que as probas **non** cobren

Por honestidade, o que queda fóra:

- **Non hai probas de interface no navegador.** As rutas próbanse co cliente de
  probas de Flask, que comproba o HTML devolto, non o comportamento real do
  navegador. O `confirm()` de JavaScript non está cuberto por probas
  automatizadas; comprobouse a man.
- **Non se proba a impresión física** do PDF. Compróbase que é un A4 válido e
  que abre correctamente; que saia ben na impresora verificouse a man.
- **Non se proba a subida á nube** da copia de seguridade. A aplicación escribe
  nunha carpeta local sincronizada; a subida faina o programa de sincronización
  e non hai integración para comprobala. Verificouse manualmente.
- **Non hai probas de carga nin de rendemento.** Non ten sentido para unha caixa
  cun só usuario.
- **Non se mide a cobertura.** Engadir `coverage` sería unha dependencia máis; o
  criterio seguido foi cubrir cada regra de negocio e cada camiño de erro.
