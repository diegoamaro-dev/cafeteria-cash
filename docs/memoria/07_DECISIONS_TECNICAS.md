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
Capítulo redactado. As trece decisións, con todo o seu razoamento, están en
../DECISIONS_TECNICAS.md.

ENFOQUE para non repetir o capítulo 6: alí cóntase QUE se decidiu, dentro da
historia do proxecto. Aquí cóntase POR QUE, e sobre todo QUE SE DESCARTOU.
-->

# 7. Decisións técnicas

## 7.1. A pregunta que filtraba todo

Nun proxecto pequeno, o difícil non é engadir cousas: é non engadilas. Por
iso, cada vez que aparecía unha idea nova, aplicábase sempre a mesma pregunta:

> *É necesario para rexistrar efectivo, pechar o día ou recuperar o sistema se
> falla o ordenador?*

Se a resposta era non, non se implementaba. Ese filtro explica case todo o que
este proxecto **non** ten.

E unha segunda regra, para as decisións que si se tomaban: **unha decisión sen
alternativa descartada non é unha decisión, é unha descrición**. Por iso cada
unha quedou rexistrada coa opción que se deixou fóra e o motivo.

---

## 7.2. As escollas de fondo

| Decisión | Que se descartou | Por que |
|---|---|---|
| Importes en céntimos enteiros | Un tipo decimal específico | É correcto, pero obriga a vixiar o redondeo en cada operación. Cos enteiros ese risco non existe |
| SQLite | MySQL ou PostgreSQL | Requiren instalar e manter un servizo, e complican moito a recuperación nun ordenador novo. Nunha caixa non aportan nada |
| Flask | Django | Trae xestión de usuarios, panel de administración e moito máis que este proxecto non usa. Multiplicaría o que hai que entender e manter |
| Só no propio ordenador | Despregar na nube | Engadiría custo, contas, copias externas e un problema de protección de datos, para unha caixa que só se usa nun mostrador |
| Anular, nunca borrar | Permitir borrar vendas | Se se puidese borrar, o histórico deixaría de distinguir un erro corrixido dunha venda ocultada |

As dúas primeiras condicionan todo o resto. A dos céntimos explicouse no
[capítulo 6](06_DESENVOLVEMENTO.md); a de SQLite merece un matiz que adoita
malinterpretarse.

**Un matiz sobre SQLite.** O habitual é dicir que é simple porque a base de
datos é un só arquivo. É certo, e é o que fai viable a recuperación: restaurar
consiste en poñer ese arquivo no seu sitio, sen reinstalar nin configurar
ningún servizo.

Pero iso **non** significa que copiala sexa simplemente copiar o arquivo, como
se explicou no [capítulo 9](09_SEGURIDADE_BACKUP_RECUPERACION.md). A
simplicidade está na restauración, non en saltarse o procedemento de copia.

---

## 7.3. O PDF: unha comparación medida

A decisión de xerar o documento sen librarías non se tomou por intuición.
Mediuse o que custaba cada opción:

| Opción | Paquetes que engade | Ademais |
|---|---:|---|
| WeasyPrint | 13 | Compoñentes adicionais do sistema en Windows |
| ReportLab | 3 | — |
| **Escribilo directamente** | **0** | — |

O custo asumido foi escribir o xerador do documento: **331 liñas** nun só
arquivo. A cambio, o arquivo de dependencias non cambia, a instalación nun
ordenador novo non necesita nada máis e o resultado é sempre idéntico.

Nun proxecto cuxo obxectivo declarado é poder recuperarse nun equipo limpo,
cada dependencia que se evita é un risco menos no peor momento posible.

---

## 7.4. O alcance pequeno, como decisión e non como renuncia

Quedaron fóra, a propósito: tarxetas, conexión co TPV externo, control de
stock, provedores, usuarios e roles, mesas, pedidos, cociña, ERP, reservas e
funcionamento na nube.

É unha lista longa, e podería lerse como un proxecto que se quedou curto. É o
contrario, e convén poder explicalo: **un alcance pequeno e ben definido é o
que permitiu probar a fondo o que si existe**.

As mesmas 263 probas repartidas nunha aplicación cinco veces máis grande
cubrirían moito menos. Preferiuse unha ferramenta que fai poucas cousas e as
fai ben, nun contexto onde o que está en xogo é que o diñeiro cadre.

---

## 7.5. Decisións menores, pero conscientes

| Decisión | Motivo |
|---|---|
| A venda en curso vive só na memoria | Aínda non é unha venda rexistrada. Evita gardar en disco algo que pode cancelarse |
| Unha soa caixa á vez | É unha cafetería cun mostrador. Dúas lapelas do navegador comparten a mesma venda |
| O día é o día natural, en hora local | O peche é o día da cafetería. Con hora universal, unha venda das 23:30 podería caer no día seguinte |
| Pódese pechar hoxe ou onte | Para poder pechar despois da medianoite sen cambiar a que día pertencen as vendas |
| Un tipo único de IVE do 10 % | Todo o que se rexistra son cafés e bocadillos. Conxélase en cada peche |

Ningunha destas é relevante por si mesma. O que importa é que **todas se
decidiron**, en lugar de quedar como estaban por descoido.

O razoamento completo das trece decisións, coas alternativas valoradas, está
en [DECISIONS_TECNICAS.md](../DECISIONS_TECNICAS.md).
