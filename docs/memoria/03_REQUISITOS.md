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

É unha visión FUNCIONAL, non unha especificación. A especificación completa
segue sendo ../../REQUIREMENTS.md, que queda enlazada.

NON explicar aquí como funciona cada cousa por dentro: iso é o capítulo 4.
NON repetir o contexto do capítulo 2.
-->

# 3. Que tiña que facer

## 3.1. A necesidade

O encargo era acotado e podía resumirse nunha frase: **unha caixa para
efectivo que non perda nada**.

Iso significaba catro cousas. Cobrar rápido, cunha botoeira de produtos na que
non houbese que escribir prezos. Deixar un **histórico fiable**, no que un
erro corrixido seguise sendo visible como erro corrixido. **Pechar o día**
deixando unha cifra definitiva e un papel que a xustificase. E **conservar os
datos** aínda que o ordenador deixase de existir.

As catro teñen o mesmo peso. Unha aplicación que cobre rápido pero perda unha
venda, ou que garde todo e non o poida recuperar, non resolvería o problema.

---

## 3.2. Funcións principais

| Ten que poder facerse | Para que |
|---|---|
| **Xestionar os produtos** | Ter a botoeira ao día cando cambian os prezos ou a carta |
| **Compoñer a venda** | Ir sumando o que leva a persoa e ver o total antes de cobrar |
| **Cobrar en efectivo** | Deixar a venda gardada cun número propio ao que poder referirse |
| **Consultar o histórico** | Ver todo o cobrado, co seu importe e o seu estado |
| **Anular unha venda** | Corrixir un erro sen que desapareza o rastro do que pasara |
| **Ver o resumo do día** | Saber en calquera momento canto efectivo vai |
| **Pechar o día e xerar o PDF** | Fixar a cifra definitiva e ter un documento imprimible |
| **Facer copia de seguridade** | Que os datos existan tamén fóra do ordenador |

---

## 3.3. Condicións importantes

Por riba das funcións, había condicións que non eran negociables:

- a aplicación funciona **no propio ordenador**, sen saír a internet;
- os datos gárdanse nunha **base SQLite** nun único arquivo;
- **unha venda confirmada non se borra nunca**: anúlase;
- os **importes teñen que ser exactos**, sen erros de redondeo;
- os **datos reais do establecemento non entran en GitHub**;
- cada copia de seguridade **sae do ordenador**;
- funcionamento simple, cunha **soa caixa** á vez.

---

## 3.4. Que queda fóra

| Inclúe | Non inclúe |
|---|---|
| Vendas en efectivo | Pagamentos con tarxeta e Bizum, e a integración co TPV externo |
| Produtos e prezos | Control de stock e provedores |
| Histórico e anulacións | Usuarios, roles e permisos |
| Resumo e peche diario | Mesas, pedidos e comandas de cociña |
| Documento PDF imprimible | ERP e reservas |
| Copia de seguridade externa | Funcionamento na nube |
| | Facturación electrónica (Veri\*Factu) |

A columna da dereita é longa, e convén ler o que é: **unha lista de decisións,
non de carencias**.

Cada unha desas funcións resolvería un problema que esta cafetería non ten. O
cobro con tarxeta xa o fai un aparello aparte que deixa o seu propio rexistro,
e non hai mesas que xestionar nin almacén que controlar. Engadilas custaría
traballo de desenvolvemento, de configuración e de mantemento a cambio de
nada.

---

## 3.5. Estado dos requisitos

**A maior parte dos requisitos está cumprida.** Están rematadas e en uso todas
as funcións de venda, histórico, resumo, peche e documento PDF, así como a
creación da copia de seguridade e a instalación nun equipo limpo.

Quedan **dous pendentes**: restaurar unha copia e comprobar os datos
recuperados.

O detalle requisito a requisito, co seu estado e a súa evidencia, está no
[capítulo 11](11_RESULTADOS.md).

---

## 3.6. Cando se consideraría completo

O criterio que se fixou ao principio non remataba ao crear a copia de
seguridade. Para dar o proxecto por terminado había que **restaurar esa copia
nun equipo limpo e comprobar que os datos recuperados eran os correctos**.

Esa esixencia era deliberada: unha copia que nunca se restaurou non demostra
que os datos se poidan recuperar, só que se gardaron.

Por iso o balance é desigual, e convén dicilo así. A parte funcional está
rematada: a aplicación **está en uso real** e permite cobrar e pechar o día con
normalidade. A impresión física do documento tamén se probou.

O obxectivo de recuperación total, en cambio, está a medias: os datos saen do
ordenador nunha copia comprobada, pero volver poñelos en marcha segue sendo un
procedemento escrito que **non se executou**.

A especificación completa, requisito a requisito, está en
[REQUIREMENTS.md](../../REQUIREMENTS.md).
