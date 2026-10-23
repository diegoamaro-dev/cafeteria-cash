<!--
========================= REXISTRO DA MEMORIA =========================
A memoria debe ser levadeira de ler e fácil de defender oralmente.

  - linguaxe clara e natural; parágrafos curtos;
  - primeiro o POR QUE, despois o COMO;
  - sen xerga innecesaria;
  - táboas, diagramas e capturas cando expliquen mellor ca o texto;
  - non repetir o que xa está noutro capítulo;
  - o detalle técnico profundo NON se trae aquí: resúmese a idea e
    enlázase o documento de docs/ que xa o explica;
  - cada sección ten que poder explicarse en voz alta sen memorizar
    tecnicismos.
=======================================================================
-->

<!--
Capítulo redactado. Detalle completo en ../ARQUITECTURA.md.
As decisións e as alternativas descartadas van no capítulo 7; os datos, no 5.
-->

# 4. Arquitectura

## 4.1. Unha aplicación web que non sae do ordenador

A aplicación ábrese no navegador, pero **non está en internet**. O programa
corre no propio ordenador da cafetería e só se pode abrir desde el.

É unha combinación pouco habitual e buscada a propósito. Do navegador
aprovéitase o que fai ben: unha pantalla cómoda, con botóns grandes, que
funciona nunha táctil sen instalar nada. Do funcionamento local, que non haxa
servidores, nin contas, nin conexión da que depender, nin ninguén de fóra que
poida chegar aos datos.

```
┌──────────┐   pulsa    ┌────────────┐   HTTP      ┌──────────────────┐
│ Usuario  │ ─────────► │ Navegador  │ ──────────► │  A aplicación    │
│ (caixa)  │ ◄───────── │  (local)   │ ◄────────── │   127.0.0.1:5000 │
└──────────┘   ve HTML  └────────────┘   HTML      └────────┬─────────┘
                                                            │
                                                            ▼
                                                   ┌──────────────────┐
                                                   │ Base de datos    │
                                                   │ (un só arquivo)  │
                                                   └────────┬─────────┘
                                                            │
                                      ┌─────────────────────┴───────────┐
                                      ▼                                 ▼
                              ┌───────────────┐               ┌──────────────────┐
                              │  PDF do peche │               │     Copia de     │
                              │               │               │    seguridade    │
                              └───────────────┘               └──────────────────┘
```

O sistema ten **dúas saídas**: o PDF do peche e a copia de seguridade. As dúas
se producen a partir do que xa está gardado, nunca ao revés.

As tecnoloxías son poucas a propósito: **Python** como linguaxe, **Flask** para
servir as páxinas, **SQLite** para gardar os datos e **CSS escrito a man** para
a presentación. Non hai ningún framework de JavaScript: a interface son
formularios, e o único código que se executa no navegador é o aviso de
confirmación antes das accións que non teñen volta atrás.

---

## 4.2. Por que está feita así

| Decisión | Motivo |
|---|---|
| Web, pero local | O navegador dá unha interface táctil coñecida sen instalar nada. Ao non saír do ordenador, non se expón a ninguén |
| Un só programa | Hai unha caixa e un mostrador. Dividilo en programas separados engadiría traballo sen resolver ningún problema real |
| Sen intermediario coa base de datos | Con seis táboas e consultas sinxelas, unha capa adicional sería unha dependencia máis que manter |
| Sen framework de JavaScript | A interface son formularios. O que se gaña non compensa o que se complica |

As alternativas que se valoraron e se descartaron están no
[capítulo 7](07_DECISIONS_TECNICAS.md).

---

## 4.3. Tres capas da aplicación e a base de datos

O programa está dividido en tres capas, que se apoian nunha cuarta peza: a
base de datos.

```
┌───────────────────────────────────────────────┐
│  O QUE SE VE      as páxinas e os estilos     │
├───────────────────────────────────────────────┤
│  O QUE RESPONDE   recibe o que se pulsa,      │
│                   chama a quen toca e devolve │
│                   a páxina. Non calcula nada  │
├───────────────────────────────────────────────┤
│  O QUE DECIDE     produtos, vendas, resumo,   │
│                   peche, PDF, copias          │
├───────────────────────────────────────────────┤
│  O QUE GARDA      a base de datos             │
└───────────────────────────────────────────────┘
```

A regra que sostén todo isto é que **a parte que decide non sabe que existe a
web**. Non coñece páxinas, nin botóns, nin navegadores: recibe datos e devolve
resultados.

Pode parecer un detalle de organización, pero ten unha consecuencia moi
práctica: as probas poden chamar directamente a esa parte **sen levantar a
aplicación**. É o que fai que 263 probas tarden arredor dun minuto en lugar de
necesitar un navegador aberto.

---

## 4.4. Os módulos

Cada módulo fai unha cousa e ten un nome que di cal:

| Módulo | De que se encarga |
|---|---|
| `products` | O catálogo: nomes, prezos, activar e desactivar |
| `cart` | A venda que se está a compoñer, e as súas contas |
| `sales` | Cobrar, numerar, histórico e anulacións |
| `resumen` | As cifras do día. Só consulta |
| `cierre` | Pechar o día e manter pechado o que xa está pechado |
| `pdf_cierre` | Converter un peche gardado nun documento A4 |
| `backup` | Facer a copia e comprobar que é boa |
| `establecimiento` | Os datos identificativos |
| `money` | Converter importes a céntimos e ao revés |
| `db` | Falar coa base de datos |
| `routes` | Atender o que se pulsa na pantalla |

---

## 4.5. Como se relacionan

Os módulos apóianse sempre **cara abaixo**: ningún depende dun que, á súa vez,
dependa del. Non hai círculos.

Tres relacións explican o deseño mellor que un diagrama completo:

- **Cobrar pregunta antes se o día está pechado.** Non o decide por si mesmo.
  O momento exacto en que fai esa pregunta é o que se contou no
  [capítulo 6](06_DESENVOLVEMENTO.md).
- **Pechar reutiliza o resumo.** As cifras do día calcúlanse nun só sitio, así
  que a previsualización e o peche nunca poden discrepar.
- **O PDF só le.** Non consulta vendas nin produtos: colle o peche xa gardado
  e nada máis. Por iso o mesmo peche dá sempre o mesmo documento.

O mapa completo de dependencias, extraído do código real, está en
[ARQUITECTURA.md](../ARQUITECTURA.md).

---

## 4.6. O camiño dunha venda

```
1. Pulsar «Café»            → engádese á venda en curso (só na memoria)
2. Engadir máis, axustar cantidades
3. Pulsar COBRAR EN EFECTIVO

      ┌─ comproba que o día non está pechado ─┐
      │  calcula o número seguinte            │  ou se garda
      │  garda a venda                        │  todo, ou
      │  garda as súas liñas                  │  non se garda nada
      └───────────────────────────────────────┘

4. Só se todo foi ben, baléirase a pantalla
5. «Venda V-2026-000001 rexistrada — 4,45 €»
```

O peche do día segue o mesmo esquema, cunha diferenza deliberada: **a copia de
seguridade faise despois**, fóra do bloque que garda. Se a copia falla, o peche
xa está feito e a copia pódese repetir. Nunca ao revés.

---

## 4.7. Onde vive cada cousa

| | Onde está | ¿Entra no repositorio? |
|---|---|---|
| Código e documentación | No proxecto | **Si** |
| Base de datos | Un arquivo no ordenador | **Non** |
| PDF xerados | Unha carpeta local | **Non** |
| Copias de seguridade | Unha carpeta externa | **Non** |
| Datos do establecemento | Dentro da base de datos | **Non** |

Esta separación non é casual: o **código recupérase do repositorio** e os
**datos das copias**. Son dúas vías independentes, e é a base do plan de
recuperación que se explica no [capítulo 9](09_SEGURIDADE_BACKUP_RECUPERACION.md).
