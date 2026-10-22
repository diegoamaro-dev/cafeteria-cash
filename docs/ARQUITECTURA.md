# Arquitectura

Documentación técnica do Proxecto Final de Ciclo · DAW · CIFP A Carballeira ·
curso 2026–2027.

---

## Visión xeral

A aplicación é un **monolito web que se executa no propio equipo da cafetería**.
Non hai servidores externos, nin nube, nin API de terceiros.

```
┌──────────┐   pulsa    ┌────────────┐   HTTP      ┌──────────────────┐
│ Usuario  │ ─────────► │ Navegador  │ ──────────► │  Flask / Python  │
│ (caixa)  │ ◄───────── │  (local)   │ ◄────────── │   127.0.0.1:5000 │
└──────────┘   ve HTML  └────────────┘   HTML      └────────┬─────────┘
                                                            │ sqlite3
                                                            ▼
                                                   ┌──────────────────┐
                                                   │     SQLite       │
                                                   │ data/*.sqlite    │
                                                   └────────┬─────────┘
                                                            │
                                      ┌─────────────────────┴───────────┐
                                      ▼                                 ▼
                              ┌───────────────┐               ┌──────────────────┐
                              │   PDF do      │               │  Copia de        │
                              │   peche (A4)  │               │  seguridade      │
                              │   exports/    │               │  carpeta externa │
                              └───────────────┘               └──────────────────┘
```

As dúas **saídas** do sistema son o **PDF do peche** e a **copia de seguridade**.
Ambas se xeran a partir do que xa está gardado en SQLite, nunca ao revés.

---

## Por que esta arquitectura

| Decisión | Motivo |
|---|---|
| Aplicación web, pero **local** | O navegador dá unha interface táctil e coñecida sen instalar nada máis. Ao escoitar só en `127.0.0.1`, non se expón á rede |
| **Monolito** | Un só proceso para unha soa caixa. Separalo en servizos engadiría complexidade sen resolver ningún problema real |
| **Sen ORM** | O proxecto usa `sqlite3` da biblioteca estándar. Con seis táboas e consultas sinxelas, un ORM sería unha dependencia máis que manter |
| **Sen framework de JavaScript** | A interface son formularios HTML. O único JavaScript é `confirm()` nativo antes das accións irreversibles |

---

## Capas

A aplicación ten tres capas ben separadas. **Ningún módulo de lóxica sabe que
existe a web**: non importan Flask nin coñecen peticións HTTP.

```
┌─────────────────────────────────────────────────────────┐
│  PRESENTACIÓN   templates/*.html (Jinja2) + static/css  │
├─────────────────────────────────────────────────────────┤
│  ENRUTADO       routes.py                               │
│                 recibe HTTP, chama á lóxica, devolve     │
│                 HTML. Non calcula nada.                 │
├─────────────────────────────────────────────────────────┤
│  LÓXICA         products · cart · sales · resumen        │
│                 cierre · establecimiento                 │
│                 pdf_cierre · backup · money              │
├─────────────────────────────────────────────────────────┤
│  DATOS          db.py → SQLite                           │
└─────────────────────────────────────────────────────────┘
```

Esta separación é o que permite que a suite automatizada se execute **sen
levantar o servidor**: as probas chaman directamente á lóxica.

---

## Módulos

Doce módulos en `app/`, cada un cunha responsabilidade.

| Módulo | Responsabilidade |
|---|---|
| `__init__.py` | Fábrica `create_app()`: crea a aplicación Flask, prepara a base e rexistra as rutas |
| `routes.py` | As 21 rutas HTTP. Traduce peticións en chamadas á lóxica e respostas en HTML |
| `db.py` | Conexión a SQLite, esquema, migracións idempotentes e transaccións |
| `money.py` | Importes monetarios: converte texto a céntimos e ao revés. Nunca usa `float` |
| `products.py` | Catálogo: crear, editar, activar e desactivar produtos |
| `cart.py` | Venda en curso, **en memoria**, e cálculo de subtotais e total |
| `sales.py` | Cobro, numeración das vendas, histórico e anulacións |
| `resumen.py` | Resumo do día. **Só lectura**: non escribe nada |
| `cierre.py` | Peche do día, desglose de IVE e bloqueo do día pechado |
| `establecimiento.py` | Datos identificativos do establecemento |
| `pdf_cierre.py` | Xera o PDF A4 a partir do peche gardado |
| `backup.py` | Copia de seguridade validada da base |

Ademais, en `scripts/`:

| Script | Para que |
|---|---|
| `install.ps1` | Crea o contorno virtual e instala as dependencias |
| `start.ps1` | Arranca a aplicación en `127.0.0.1:5000` |
| `seed_demo.py` | Crea unha base de demostración con datos ficticios |
| `congelar_establecimiento_en_cierres.py` | Migración controlada de peches antigos |

---

## Dependencias entre módulos

As frechas indican «usa». **Non hai ciclos**: a dependencia vai sempre cara
abaixo.

```
                              routes.py
                                  │
   ┌──────────┬────────┬──────────┼──────────┬────────────┬─────────┐
   ▼          ▼        ▼          ▼          ▼            ▼         ▼
products    cart    sales     resumen     cierre     pdf_cierre   backup
   │          ▲       │  │                 │  │           │  │      │
   │          └───────┘  │     ┌───────────┘  │           │  │      │
   │                     └────►│              ▼           │  │      │
   │                           │       establecimiento    │  │      │
   │                    cierre ─┴──► resumen              │  │      │
   │                                                      │  │      │
   │                    money ◄───────────────────────────┘  │      │
   │                                          cierre ◄───────┘      │
   │                                                                │
   └────────────────────────────────────────────────────────────────┴──► db.py
                                                                          │
                                                                          ▼
                                                                       SQLite
```

Relacións reais entre módulos (extraídas do código):

| Módulo | Usa |
|---|---|
| `routes` | `products`, `cart`, `sales`, `resumen`, `cierre`, `pdf_cierre`, `backup`, `establecimiento`, `money` |
| `sales` | `cart`, `cierre`, `db` |
| `cierre` | `resumen`, `establecimiento`, `db` |
| `pdf_cierre` | `cierre`, `money`, `db` |
| `products`, `resumen`, `establecimiento`, `backup` | `db` |
| `cart`, `money`, `db` | — (non dependen de ningún outro módulo) |

Catro detalles que explican o deseño:

- **`sales` usa `cierre`** para preguntar se o día está pechado, dentro da mesma
  transacción na que escribiría.
- **`sales` usa `cart`** para o cálculo de subtotais e totais: a aritmética está
  nun só sitio.
- **`cierre` usa `resumen`** para calcular as cifras do día: non se duplica o
  cálculo en dous sitios.
- **`pdf_cierre` usa `cierre`** só para ler o peche xa gardado.

---

## Fluxo dunha venda

O camiño completo desde que se pulsa un produto ata que a venda queda gardada.

```
1. O usuario pulsa «Café»
      POST /venta/anadir/1
      routes → cart.anadir()           ← só memoria, aínda non hai nada en disco

2. Repite con máis produtos, axusta cantidades con + / − / ✕

3. Pulsa COBRAR EN EFECTIVO
      POST /venta/cobrar
      routes → sales.confirmar_venta()

         BEGIN IMMEDIATE  ────────────────────────────┐
           comproba que o día non está pechado        │  unha soa
           calcula o número correlativo               │  transacción:
           INSERT na cabeceira (sale)                 │  ou todo,
           INSERT nas liñas (sale_item)               │  ou nada
         COMMIT  ───────────────────────────────────┘

4. Só se a transacción rematou ben, baléirase a venda en curso
5. Móstrase «Venda V-2026-000001 rexistrada — 4,45 €»
```

Se algo falla, faise **rollback completo** e a venda en curso **non se baleira**,
para poder reintentar sen volver pulsar todos os produtos.

---

## Fluxo do peche do día

```
1. O usuario revisa a previsualización en /cierre
2. Pulsa CERRAR DÍA e confirma

      POST /cierre
      routes → cierre.cerrar_dia()

         BEGIN IMMEDIATE  ────────────────────────────┐
           comproba que o día non está xa pechado     │
           conxela os datos do establecemento         │  todo dentro
           calcula as cifras (reutiliza resumen)      │  da mesma
           calcula o número correlativo de peche      │  transacción
           INSERT na cabeceira (daily_close)          │
           INSERT no desglose (daily_close_item)      │
         COMMIT  ───────────────────────────────────┘

3. Xa fóra da transacción, créase a copia de seguridade
      routes → backup.crear_backup()
```

O backup faise **despois** de confirmar o peche, a propósito: se fallase, o
peche xa está gardado e a copia pódese repetir desde a pantalla.

---

## Onde vive cada cousa

| Dato | Onde | No repositorio? |
|---|---|---|
| Código e documentación | `app/`, `tests/`, `docs/` | **Si** |
| Base de datos | `data/*.sqlite` | **Non** |
| PDF xerados | `exports/` | **Non** |
| Copias de seguridade | Carpeta externa configurable | **Non** |
| Datos do establecemento | Táboa `establishment` | **Non** |

Esta separación é deliberada: o código recupérase do repositorio e os datos das
copias de seguridade. Son dúas vías independentes.
