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

ATENCIÓN: as seccións 12.2, 12.3 e 12.4 están escritas en primeira persoa
porque son valoración persoal. Convén relelas e axustalas á propia voz antes
da entrega: ninguén debe defender unha opinión que non recoñece como súa.

Os feitos están no capítulo 11. Aquí vai a lectura deses feitos.
-->

# 12. Conclusións

## 12.1. Que se conseguiu

O obxectivo era construír unha ferramenta fiable para rexistrar vendas en
efectivo e pechar a caixa, que funcionase no propio equipo e que se puidese
recuperar se ese equipo fallase.

As dúas primeiras partes están conseguidas e demostradas: a aplicación
funciona nun mostrador real e está respaldada por 263 probas. A terceira está
**a medias**: os datos saen do ordenador nunha copia comprobada, pero volver
poñelos en funcionamento é aínda un procedemento escrito que non se executou.

Dito en curto: o proxecto protexe os datos, pero aínda non demostrou que sabe
recuperalos.

---

## 12.2. O que funcionou ben

Mirando cara atrás, hai tres cousas que me alegro de ter decidido ao
principio.

**Gardar os prezos en céntimos enteiros.** Tomei esa decisión antes de
escribir a primeira venda, e creo que foi a máis rendible de todas. Os erros
de redondeo non dan a cara: descóbrense cando o caixón non cadra, e daquela xa
non sabes de onde veñen.

**Non borrar nada.** Decidir que unha venda se anula pero nunca se elimina
quitoume moitas dúbidas despois. Cando a regra non ten excepcións, non hai que
pensala cada vez.

**Empezar a probar cedo.** As probas naceron cando empezou a haber datos que
podía perder, e foron medrando con cada parte. Grazas a iso puiden cambiar
cousas a medio proxecto —ata o modelo de datos— sen medo a estar rompendo algo
sen enterarme.

Engadiría unha cuarta, menos evidente: **non deixar medrar o alcance**. É o
que me deu tempo a probar ben o pouco que hai.

E ten un efecto que non buscaba ao principio: que a aplicación funcione no
propio equipo e faga poucas cousas mantén os **custos recorrentes de
infraestrutura practicamente a cero**. Non hai servidor que pagar nin servizo
do que depender.

---

## 12.3. O que faría distinto

**Faría a restauración á vez que a copia.** Planifiqueina como unha fase
posterior e pareceume o lóxico, pero unha copia que non sabes restaurar está a
medias, e finalmente foi a parte que quedou pendente. Se volvese empezar,
faríaas xuntas.

**Pensaría antes en como se usa isto de verdade.** Os problemas de deseño do
[capítulo 6](06_DESENVOLVEMENTO.md) saíron ao probar situacións reais, non ao
escribir o código: pechar a caixa pasada a medianoite, ou un documento que
cambiaba se tocabas un dato. Un rato pensando no mostrador antes de empezar
teríame aforrado bastante traballo de corrección.

---

## 12.4. Que aprendín

**Que unha proba que sempre pasa non demostra por si soa que detecte o fallo
que pretende cubrir.** O momento máis útil do proxecto foi romper o código a
propósito para ver se as probas o detectaban. Ata ese día non sabía se estaban
protexendo algo ou simplemente pasando.

**Que decidir é sobre todo descartar.** Ao principio custábame non engadir
funcionalidades. Obrigarme a escribir, en cada caso, que alternativa deixaba
fóra e por que, converteu esas renuncias en algo que podo defender.

**Que traballar con datos reais cambia o método.** Desenvolver sobre unha
aplicación que xa estaba en uso, cos datos dun negocio concreto, obrigoume a
separar unha base de demostración, a non versionar nada sensible e a
comprobalo automaticamente en vez de fiarme da memoria.

---

## 12.5. Limitacións

Por orde de importancia:

| Limitación | Alcance |
|---|---|
| **A restauración non está feita nin probada** | É a principal. Deixa o plan de recuperación en documentado, non demostrado |
| Non hai probas automáticas da interface | O comportamento do navegador comprobouse a man |
| Só admite unha caixa á vez | Correcto para esta cafetería; non serviría nun local con varios puntos de cobro |
| Non se mide a cobertura de código | O criterio foi cubrir cada regra e cada camiño de erro, non alcanzar unha porcentaxe |

Ningunha destas é unha sorpresa aparecida ao final: todas estaban
identificadas e documentadas mentres se traballaba.

---

## 12.6. Liñas futuras

**Primeira prioridade, e cunha distancia clara sobre as demais: completar a
restauración.** Implementala na aplicación, executala de verdade sobre un
equipo limpo e comprobar que os datos recuperados son os correctos. Iso
pecharía os dous obxectivos pendentes e, sobre todo, convertería o plan de
recuperación nun procedemento demostrado.

Despois, e só se o uso real o pide:

- un histórico de copias na propia aplicación, para ver e escoller;
- probas automáticas da interface no navegador;
- consultas por períodos máis longos que un día.

Calquera outra idea pasaría polo mesmo filtro que se aplicou durante todo o
proxecto: *é necesario para rexistrar efectivo, pechar o día ou recuperar o
sistema?* Se a resposta é non, non entra.

---

## 12.7. Conclusión

O proxecto resolve o problema que o orixinou. Rexistra o efectivo dunha
cafetería de forma rápida e fiable, deixa un rastro que non se pode falsear e
produce un documento diario que serve como xustificante.

Faino ademais cunha base técnica que se pode defender: cada decisión ten o seu
motivo e a súa alternativa descartada, e cada regra importante ten unha proba
que a protexe.

Queda un paso por dar, e está identificado. Que esa sexa a conclusión —un
proxecto que sabe exactamente o que lle falta— paréceme mellor resultado que
un que dea todo por terminado.
