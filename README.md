# Cafetería Cash

**Aplicación web local para a xestión de vendas en efectivo dunha cafetería.**

Rexistra vendas en efectivo cunha botoeira de produtos, garda o histórico sen
borrar nada, pecha a caixa do día, xera o peche en PDF A4 e fai unha copia de
seguridade validada fóra do equipo.

## Capturas

![Pantalla de venda: botoeira de produtos á esquerda e venda en curso á dereita](docs/capturas/01-venda.png)

*Pantalla de venda. Cada pulsación engade unha unidade; o total calcúlase en céntimos enteiros.*

![Histórico con vendas válidas, unha anulada e os días xa pechados](docs/capturas/03-historico.png)

*Histórico. Unha venda anulada consérvase íntegra; as dun día pechado xa non se poden tocar.*

![PDF A4 do peche coa cabeceira do establecemento, os totais e o desglose de IVE](docs/capturas/07-pdf-peche.png)

*PDF A4 do peche diario, xerado coa biblioteca estándar e reproducible byte a byte.*

> Todas as capturas están feitas coa base de demostración
> ([`scripts/seed_demo.py`](scripts/seed_demo.py)): **os datos son ficticios**.
> O resto están en [`docs/capturas/`](docs/capturas/) e explícanse no
> [manual de usuario](docs/MANUAL_USUARIO.md).

---

## Contexto académico

| | |
|---|---|
| **Traballo** | Proxecto Final de Ciclo |
| **Ciclo** | Desenvolvemento de Aplicacións Web (DAW) |
| **Centro** | CIFP A Carballeira |
| **Curso** | 2026–2027 |

A aplicación naceu dunha necesidade real: unha cafetería que precisa rexistrar
as súas vendas en efectivo de xeito rápido e fiable. Os pagamentos con tarxeta
xestiónanse por separado cun TPV externo e quedan **fóra do alcance** deste
proxecto.

---

## Funcionalidades

Fluxo principal:

```
Seleccionar produtos → cobrar en efectivo → gardar venda
   → histórico → peche diario → PDF → copia de seguridade
```

- [x] **Produtos**: alta, edición de nome e prezo, activar e desactivar.
- [x] **Vendas en efectivo**: botoeira, cantidades, total e cobro.
- [x] **Histórico**: todas as vendas confirmadas, da máis recente á máis antiga.
- [x] **Anulacións sen borrado**: unha venda incorrecta márcase como ANULADA e
      consérvase íntegra; **nunca se borra**.
- [x] **Resumo diario**: vendas válidas, efectivo válido, anulacións, importe
      anulado e unidades por produto.
- [x] **Peche diario**: foto definitiva do día, con numeración correlativa.
      Un día pechado non admite novas vendas nin anulacións.
- [x] **PDF A4**: xerado a partir do peche gardado, imprimible e reproducible.
- [x] **Copia de seguridade**: copia validada da base nunha carpeta externa.
- [x] **Recuperación ante fallo**: o código vive nun repositorio Git e os datos
      nas copias de seguridade.

---

## Tecnoloxías

| Tecnoloxía | Uso |
|---|---|
| **Python 3.12** | Linguaxe da aplicación |
| **Flask** | Servidor web e enrutado |
| **SQLite** | Base de datos local, sen servidor |
| **HTML + Jinja2** | 8 plantillas |
| **CSS** | Follas de estilo propias, sen frameworks |
| **JavaScript mínimo** | Só `confirm()` nativo para confirmar accións irreversibles |
| **unittest** | 263 probas automatizadas |
| **Git / GitHub** | Control de versións por fases |

**Unha soa dependencia directa: Flask.** O resto son as súas transitivas. O PDF
xérase coa biblioteca estándar de Python, sen ningunha libraría externa.

---

## Instalación

Require **Python 3.12** e **Git**.

```bash
git clone https://github.com/diegoamaro-dev/cafeteria-cash.git
cd cafeteria-cash
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```

O script crea o contorno virtual en `.venv/` e instala as dependencias fixadas
en `requirements.txt`.

### Arranque

```bash
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
```

E abrir <http://127.0.0.1:5000> no navegador.

A aplicación escoita **só en `127.0.0.1`**: non é accesible desde outros equipos
da rede nin desde internet.

---

## Datos de demostración

Para probar a aplicación con contido, sen introducir nada a man:

```bash
.venv\Scripts\python.exe scripts\seed_demo.py
```

Crea `data/demo.sqlite` con **datos totalmente ficticios**:

- un establecemento de demostración;
- 10 produtos de cafetería;
- **dous días xa pechados**, con vendas e unha anulación en cada un, para ver o
  histórico, o resumo, o peche e o PDF;
- **o día de hoxe aberto** con vendas, para poder pechalo en directo.

Para arrancar a aplicación con esa base:

```bash
$env:CAFETERIA_DB = "data\demo.sqlite"
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
```

O script **négase a escribir sobre a base real** e sobre calquera base que xa
exista, salvo que se lle pase `--reset`.

---

## Probas

```bash
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

**263 probas** repartidas en 11 arquivos. Usan `unittest` da biblioteca
estándar: non hai ningún framework de probas engadido.

| Arquivo | Cobre |
|---|---|
| `test_cart.py` | Cálculo de subtotais e totais en céntimos |
| `test_sales.py` | Persistencia, numeración, snapshots e atomicidade |
| `test_historial.py` | Histórico, anulacións e ausencia de borrado |
| `test_resumen.py` | Resumo diario: totais, datas e snapshots |
| `test_cierre.py` | Peche: cifras, numeración, atomicidade e bloqueo |
| `test_iva.py` | Desglose de IVE conxelado no peche |
| `test_congelar_cierres.py` | Migración controlada de peches antigos |
| `test_pdf.py` | PDF: contido, A4 e rexeneración idéntica |
| `test_establecimiento.py` | Datos do establecemento |
| `test_backup.py` | Copia de seguridade: validación e illamento |
| `test_seed_demo.py` | Datos de demostración |

Cada proba usa a súa propia base SQLite temporal: **a base real nunca se toca**.

---

## Arquitectura

```
app/
├── __init__.py          Fábrica create_app()
├── routes.py            21 rutas HTTP
├── db.py                Conexión SQLite, esquema e migracións
├── money.py             Importes en céntimos (nunca float)
├── products.py          Catálogo
├── cart.py              Venda actual (en memoria)
├── sales.py             Cobro, histórico e anulacións
├── resumen.py           Resumo diario (só lectura)
├── cierre.py            Peche diario, desglose de IVE e bloqueo do día pechado
├── pdf_cierre.py        Xeración do PDF A4
├── establecimiento.py   Datos identificativos do establecemento
├── backup.py            Copia de seguridade validada
├── templates/           8 plantillas Jinja2
└── static/              Estilos (css/style.css) e favicon.svg

tests/                   11 arquivos, 263 probas
scripts/                 Instalación, arranque e datos demo
docs/                    Documentación técnica
```

### Modelo de datos

Seis táboas en SQLite:

| Táboa | Contido |
|---|---|
| `product` | Catálogo: nome, prezo, activo, orde visual |
| `sale` | Cabeceira da venda: número, data, total, estado |
| `sale_item` | Liñas da venda, con nome e prezo copiados do momento do cobro |
| `daily_close` | Peche do día: número, cifras e datos conxelados |
| `daily_close_item` | Unidades por produto conxeladas no peche |
| `establishment` | Datos identificativos do establecemento (unha soa fila) |

As migracións do esquema son **idempotentes** e execútanse en cada arranque:
nunca borran datos.

---

## Decisións técnicas

**Importes en enteiros de céntimos, nunca `float`.**
En coma flotante `0.1 + 0.2 != 0.3`, e iso produciría descadramentos nos totais
diarios. Todos os cálculos son enteiros; só se formatea ao mostrar.

**Unha venda confirmada non se borra nunca.**
Se é incorrecta, anúlase: consérvase o número, o importe e as liñas, e só cambia
o estado. Unha anulación non se pode desfacer.

**Snapshots no histórico.**
Cada liña de venda garda o nome e o prezo do momento do cobro. Se mañá un
produto cambia de prezo, a venda de hoxe segue a dicir o prezo que pagou a
clientela. O mesmo co peche, que conxela ademais os datos do establecemento.

**Un día pechado é inmutable.**
Despois de pechar non se poden rexistrar nin anular vendas desa data. A
comprobación faise **dentro da mesma transacción** que escribiría, non antes:
así un peche e unha venda simultáneos non poden gañar os dous a carreira. Hai
probas con fíos reais que o verifican.

**PDF coa biblioteca estándar.**
Compáranse as alternativas: WeasyPrint instala 13 paquetes e precisa librarías
nativas en Windows; ReportLab, 3 paquetes. Para unha páxina de texto, escribir
o PDF directamente evita esa instalación e simplifica a recuperación nun equipo
novo. O PDF é determinista: rexenerar o mesmo peche produce os mesmos bytes.

**Código e datos separados.**
No repositorio só hai código e documentación. A base de datos, as copias de
seguridade e os PDF xerados quedan fóra do control de versións.

---

## Alcance e limitacións

Fóra do alcance, de xeito deliberado:

tarxetas · API de TPV externo · stock · provedores · usuarios e roles · mesas ·
pedidos · cociña · ERP · reservas · execución na nube

Limitacións coñecidas:

- Só funciona en **local**, nun equipo, para unha caixa.
- A venda en curso vive na memoria do proceso: pérdese se se reinicia a
  aplicación. Aínda non é unha venda rexistrada.
- A subida da copia de seguridade á nube faina o programa de sincronización do
  equipo; a aplicación non o comproba.
- É unha **solución temporal**, pensada para un período acoutado.

---

## Documentación

Documentación técnica do proxecto:

| Documento | Contido |
|---|---|
| [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) | Capas, módulos, dependencias e fluxos |
| [docs/MODELO_DATOS.md](docs/MODELO_DATOS.md) | As seis táboas, diagrama ER e regras de integridade |
| [docs/DECISIONS_TECNICAS.md](docs/DECISIONS_TECNICAS.md) | Trece decisións: problema, decisión e alternativa descartada |
| [docs/PROBAS.md](docs/PROBAS.md) | Que se proba, como e o que **non** se cobre |
| [docs/MANUAL_USUARIO.md](docs/MANUAL_USUARIO.md) | Guía de uso con capturas |

Especificación e continxencia:

| Documento | Contido |
|---|---|
| [REQUIREMENTS.md](REQUIREMENTS.md) | Requisitos funcionais, restricións e criterio de terminado |
| [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md) | Recuperación ante fallo do equipo |

---

## Licenza

**MIT** — ver [LICENSE](LICENSE).

Pódese usar, copiar, modificar e distribuír libremente, conservando o aviso de
copyright. O software ofrécese sen garantía.
