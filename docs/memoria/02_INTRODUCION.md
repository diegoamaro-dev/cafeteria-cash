<!--
========================= REXISTRO DA MEMORIA =========================
A memoria debe ser levadeira de ler e fácil de defender oralmente.

  - linguaxe clara e natural; parágrafos curtos;
  - primeiro o POR QUE, despois o COMO;
  - sen xerga innecesaria;
  - táboas, diagramas e capturas cando expliquen mellor ca o texto;
  - non repetir o que xa está noutro capítulo;
  - cada sección ten que poder explicarse en voz alta sen memorizar
    tecnicismos.
=======================================================================
-->

<!--
Capítulo redactado.
NON repetir aquí a especificación: os requisitos van no capítulo 3.
NON repetir a narración do desenvolvemento: vai no capítulo 6.
-->

# 2. Introdución

## 2.1. O contexto

Nunha cafetería o mostrador non espera. Hai cola, hai présa e hai que cobrar
sen pararse a pensar. E, ao final do día, alguén ten que saber canto diñeiro
entrou e poder xustificalo.

Os pagamentos con tarxeta resólvense cun aparello que xa fai o seu traballo e
deixa o seu propio rexistro. O problema está no **efectivo**: é o que non
queda anotado en ningunha parte a menos que alguén o anote.

## 2.2. O problema

Levar as contas do efectivo a man ten tres problemas que se repiten sempre:

- **lentitude**, porque anotar quita tempo que non hai;
- **erros**, porque as sumas feitas con présa fallan;
- **falta de rastro**, porque unha anotación corrixida non deixa constancia do
  que había antes.

O terceiro é o máis serio. Se non se pode distinguir un erro corrixido dunha
cifra cambiada despois, as contas perden valor como xustificante.

## 2.3. Por que unha ferramenta propia e pequena

A necesidade do negocio é moi concreta e cabe en catro palabras: **efectivo,
histórico, peche e copia**. Nada máis.

Partindo diso, o proxecto decidiu construír unha ferramenta axustada
exactamente a esas catro cousas, en lugar de adoptar un sistema de xestión
completo do que se usaría unha fracción mínima. Ese tipo de ferramentas
resolven moitos problemas que esta cafetería non ten —mesas, pedidos, stock,
provedores, varios puntos de cobro—, e cada función que non se usa é
igualmente algo que hai que configurar, entender e manter.

Á decisión de alcance engádense dúas condicións que viñan do propio negocio:

- a caixa ten que **funcionar sempre**, tamén se non hai conexión;
- as vendas son do establecemento e **non teñen por que saír do ordenador**.

E, por último, o motivo académico: construír a ferramenta enteira —da base de
datos ao documento imprimible— obriga a tomar e xustificar decisións de deseño
reais, que é o que se avalía neste traballo.

## 2.4. Obxectivo

O obxectivo xeral é **construír unha ferramenta fiable para rexistrar vendas
en efectivo e pechar a caixa diaria**, que funcione no propio equipo do
establecemento e que se poida recuperar se ese equipo falla.

«Fiable» significa aquí tres cousas concretas, e as tres condicionaron o
deseño:

1. que as contas **cadren ao céntimo**;
2. que o que se garda **non se poida perder nin alterar despois**;
3. que, se o ordenador desaparece, **os datos sigan existindo noutro sitio**.

Os requisitos derivados deste obxectivo están no
[capítulo 3](03_REQUISITOS.md).

## 2.5. Alcance

A ferramenta cobre o ciclo completo do efectivo: produtos, venda, cobro,
corrección de erros, resumo, peche do día, documento imprimible e copia de
seguridade.

Quedan **fóra a propósito**, entre outras: os pagamentos con tarxeta, o control
de stock, os provedores, os usuarios e permisos, as mesas e pedidos, e o
funcionamento na nube. A lista completa está no
[capítulo 3](03_REQUISITOS.md).

Non é unha lista de carencias, senón de decisións. O criterio que se aplicou a
cada posible engadido explícase no [capítulo 7](07_DECISIONS_TECNICAS.md).

## 2.6. Como se traballou

O proxecto construíuse **por partes**, engadindo unha capacidade completa de
cada vez e comprobándoa antes de pasar á seguinte. Non houbo unha fase de
probas ao final: cada parte trouxo as súas.

Esa forma de traballar ten un efecto visible no resultado, e é o que o
[capítulo 6](06_DESENVOLVEMENTO.md) conta en detalle.

## 2.7. Como ler esta memoria

| Se interesa… | Capítulo |
|---|---|
| Que tiña que facer a aplicación | 3 |
| Como está construída | 4 e 5 |
| Como foi o desenvolvemento | 6 |
| Por que se tomou cada decisión | 7 |
| Como se comprobou que funciona | 8 |
| Seguridade, copias e recuperación | 9 |
| Como se usa | 10 |
| Que se conseguiu e que non | 11 e 12 |

O repositorio público contén ademais a documentación técnica completa, á que
estes capítulos remiten cando fai falla máis detalle.
