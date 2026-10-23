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
Capítulo redactado. É a porta de entrada: ten que entenderse sen ler nada máis.
O Abstract é equivalente ao resumo, non unha tradución literal palabra a
palabra.
-->

# 1. Resumo

## 1.1. Resumo

**Cafetería Cash** é unha aplicación web local para rexistrar as vendas en
efectivo dunha cafetería, pechar a caixa cada día e deixar constancia do
resultado.

Nace dunha necesidade real. Nun mostrador fai falla cobrar rápido, non perder
ningunha venda e poder xustificar ao final do día canto efectivo entrou. Os
pagamentos con tarxeta xestiónanse por separado cun aparello externo e quedan
fóra desta ferramenta.

A aplicación funciona no propio ordenador do establecemento: **non necesita
internet para operar nin se expón á rede**, e non depende de ningún servizo
externo para rexistrar vendas, pechar o día ou xerar o documento do peche. A
copia de seguridade escríbese nunha carpeta que outro programa pode
sincronizar despois. Está construída con **Python e Flask**, cunha base
de datos **SQLite** nun único arquivo, e ten **unha soa dependencia externa
directa**. Permite xestionar o catálogo de produtos, cobrar en efectivo,
corrixir erros sen borrar nada, consultar o resumo do día, pechar a caixa,
xerar un documento A4 imprimible e crear unha copia de seguridade comprobada
fóra do equipo.

O resultado non é un prototipo: a aplicación **está en uso real** nunha
cafetería. Está respaldada por **263 probas automatizadas** e por documentación
técnica publicada nun repositorio público.

Queda unha limitación coñecida: a copia de seguridade créase e compróbase,
pero **restaurala segue sendo un procedemento manual que non se chegou a
executar**. Mentres iso non se complete, o plan de recuperación é un
procedemento documentado, non demostrado.

---

## 1.2. Abstract

**Cafetería Cash** is a local web application for recording a coffee shop's
cash sales, closing the register every day and keeping a record of the result.

It comes from a real need. Behind a counter you have to charge quickly, lose
no sale, and be able to account for the cash taken at the end of the day. Card
payments are handled separately through an external device and fall outside
this tool.

The application runs on the shop's own computer: it **needs no internet
connection to operate and is not exposed to the network**, and it relies on no
external service to record sales, close the day or produce the closing
document. Backups are written to a folder that another program may later
synchronise. It is built with **Python and Flask**, uses a
**SQLite** database held in a single file, and has **one single direct
external dependency**. It supports managing the product catalogue, taking cash
payments, correcting mistakes without deleting anything, reviewing the daily
summary, closing the register, producing a printable A4 document and creating
a verified backup outside the machine.

The result is not a prototype: the application **is in real use** in a coffee
shop. It is backed by **263 automated tests** and by technical documentation
published in a public repository.

One known limitation remains: backups are created and verified, but
**restoring one is still a manual procedure that has not been carried out**.
Until that is completed, the recovery plan is documented rather than proven.

---

## 1.3. Palabras chave

Terminal punto de venda · vendas en efectivo · peche de caixa · Python ·
Flask · SQLite · copia de seguridade · probas automatizadas

*Keywords:* point of sale · cash sales · daily closing · Python · Flask ·
SQLite · backup · automated testing
