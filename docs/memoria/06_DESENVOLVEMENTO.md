<!--
Capítulo redactado.

Rexistro: narrativo e sinxelo. Conta a evolución do produto, non o diario de
traballo. Non se enumeran commits nin detalles de baixo nivel.

O historial de Git do proxecto usouse como columna vertebral cronolóxica para
reconstruír a evolución; os feitos verificáronse contra o rexistro interno de
desenvolvemento, que non forma parte deste repositorio.

O detalle técnico queda nos documentos de docs/ e enlázase desde aquí.
-->

# 6. Desenvolvemento

## 6.1. Como se traballou

O proxecto fíxose **por partes, unha de cada vez**. Cada parte engade algo que
xa se pode usar, e non se empeza a seguinte ata que a anterior funciona e está
comprobada.

Antes de escribir código decidíase que arquivos se ían tocar e que quedaba
fóra. Ao rematar, executábanse as probas e probábase a man na aplicación en
marcha. Só entón se daba a parte por pechada.

Isto deixa dous rastros visibles. O primeiro é que **cada fase di tamén o que
non fai**, o que evitou que o proxecto medrase sen decidilo. O segundo é o
crecemento das probas, que nunca baixou:

| Parte do proxecto | Probas acumuladas |
|---|---:|
| Produtos e venda en curso | *(probas manuais)* |
| Gardar as vendas | 28 |
| Histórico e anulacións | 49 |
| Resumo do día | 65 |
| Peche do día | 113 |
| PDF e datos do establecemento | 214 |
| Copias de seguridade | 250 |

As probas automatizadas naceron no momento en que empezou a haber datos que
se podían perder. Antes diso, o que había na pantalla comprobábase mirándoo.

---

## 6.2. Preparación

Antes de programar nada había que asegurar dúas cousas: que o proxecto se pode
reconstruír noutro ordenador, e que **nunca se publican datos reais**. De aí
saíu todo o traballo desta primeira parte: a estrutura do proxecto, os scripts
de instalación e arranque, e as regras que impiden que as bases de datos, as
copias e os documentos xerados entren no repositorio.

A decisión que máis consecuencias tivo foi fixar as versións de **todas** as
dependencias, non só as principais. Se nun ordenador novo se instalase unha
versión distinta dunha libraría secundaria, a instalación podería fallar
precisamente no momento en que máis falta fai: unha recuperación.

Para comprobalo non chegaba con que funcionase aquí. Descargouse o proxecto
desde cero noutro directorio, instalouse seguindo as instrucións publicadas e
verificouse que arrancaba e que **só era accesible desde o propio ordenador**.

Houbo tamén un detalle práctico que custou tempo e que convén deixar escrito:
en Windows, o comando `python` pode existir sen que Python estea instalado de
verdade. Quen siga as instrucións nun ordenador recén formatado atoparíase cun
erro confuso, así que está avisado no plan de recuperación.

---

## 6.3. Produtos e venda en curso

**Por que.** Para cobrar fan falla dúas cousas: unha lista de produtos con
prezo e unha pantalla onde ir compoñendo a venda.

**Que se fixo.** A xestión de produtos e a pantalla principal: botóns á
esquerda, venda en curso á dereita.

**As dúas decisións que marcaron todo o resto.**

Primeira: **os prezos gárdanse en céntimos enteiros**. Un café de 1,40 € é o
número 140. A razón é que os números con decimais gárdanse de forma
aproximada, non exacta: 1,40 non se pode representar con precisión, e cada
operación arrastra un erro mínimo. Un erro así non se ve nunha conta solta,
pero nunha caixa acumúlase ata que o diñeiro do caixón non coincide co
rexistrado. Cos números enteiros non existe esa aproximación.

Segunda: **un produto non se borra, desactívase**. Deixa de aparecer na
pantalla pero segue na base de datos, porque as vendas antigas apuntan a el.

**Como se comprobou.** Hai probas feitas a propósito cos casos onde os
decimais darían un resultado incorrecto. Por exemplo: seis cafés de 1,40 € e
catro de 1,65 € teñen que dar exactamente 15,00 €, e con decimais o resultado
é 14,999999999999998.

A venda que se está compoñendo aínda non se garda en ningún sitio: só existe
mentres dura. Iso significa que a aplicación dá servizo a **unha soa caixa**,
que é o que ten a cafetería.

---

## 6.4. Gardar as vendas

**Por que.** Que ao cobrar quede constancia permanente, cun número ao que
poder referirse.

**Que se fixo.** O cobro en efectivo e a numeración correlativa das vendas.

**As decisións.** A venda gárdase **enteira ou non se garda**: nunca pode
quedar unha venda a medias, cos totais pero sen as liñas.

E cada liña garda o **nome e o prezo do momento en que se cobrou**, non unha
referencia ao produto. Parece repetir información, pero é o que impide que
subir o prezo do café cambie o importe de todas as vendas xa feitas.

**Como se comprobou.** Provocouse un fallo a posta no medio do gardado para
confirmar que non queda nada escrito a medias, e que a venda que estaba na
pantalla **non se perde**, para poder reintentar sen volver pulsar todo.

---

## 6.5. Histórico e anulacións

Hai que poder corrixir unha venda mal cobrada sen destruír o rexistro. Diso
saíron a pantalla de histórico e a anulación.

E tamén a decisión máis importante do proxecto: **unha venda non se borra
nunca**. Se está mal, anúlase: queda marcada como anulada, coa hora na que se
anulou, e segue á vista co seu número, o seu importe e as súas liñas.

O motivo é sinxelo. Se se puidese borrar, ninguén podería distinguir un erro
corrixido dunha venda que alguén quixo facer desaparecer. A contrapartida é
que **unha anulación non se pode desfacer**.

A comprobación fíxose dunha maneira pouco habitual. Ademais de verificar que
a anulación funciona, hai unha proba que **le o propio código** da aplicación
e falla se alguén engade no futuro unha instrución de borrado. A regra non
queda protexida só hoxe, senón fronte a cambios posteriores.

---

## 6.6. Resumo e peche do día

**Por que.** Saber canto se leva vendido, e ao final da xornada pechar a caixa
deixando unha foto definitiva do día.

**Que se fixo.** Primeiro o resumo, que só consulta e non modifica nada.
Despois o peche, que crea un rexistro permanente co seu propio número.

**As decisións.** Un día pechado **non se pode tocar**: nin novas vendas nin
anulacións desa data, e non hai reapertura.

Ademais, o día dunha venda é o día en que se cobrou, aínda que se anule máis
tarde.

**Como se comprobou.** Esta foi unha das comprobacións máis relevantes do
proxecto. Hai probas que simulan dúas cousas ocorrendo **á vez** — unha venda
que chega xusto cando se está pechando o día — e verifican que o resultado é
o correcto.

E despois comprobouse que esas probas **serven de algo**: rompeuse o código a
propósito de dúas maneiras distintas e, nas dúas, as probas fallaron. Non son
probas que pasen por casualidade.

> **Un problema real do negocio.** A primeira versión só deixaba pechar o día
> actual. Pero unha cafetería pecha a caixa moitas veces pasada a medianoite,
> e nese momento «hoxe» xa é outro día. Arranxouse permitindo pechar **hoxe ou
> onte**, sen cambiar a que día pertence cada venda.

---

## 6.7. O documento do peche

Fai falla un papel imprimible do peche, cos datos do establecemento. Para iso
engadíronse a xeración dun PDF A4 e a pantalla onde se introducen os datos
identificativos.

O PDF constrúese **sen engadir ningunha libraría**. As alternativas habituais
obrigaban a instalar entre tres e trece paquetes máis; escribilo directamente
non engade ningún. A cambio houbo que escribir máis código, pero a instalación
nun ordenador novo segue sendo igual de simple.

A outra decisión é que o documento **sempre sae igual**: xerar dúas veces o
mesmo peche produce exactamente o mesmo arquivo.

> **Algo que houbo que refacer.** Ao principio o PDF collía os datos do
> establecemento da configuración actual. Iso significaba que cambiar o
> enderezo reescribía a cabeceira de **todos os documentos antigos**, o que
> nun documento contable non vale. Houbo que gardar eses datos dentro de cada
> peche e arranxar os peches xa feitos. Despois fíxose o mesmo co IVE.

A comprobación fíxose por partes: que o arquivo é un PDF A4 correcto, que
rexenerado dá o mesmo resultado, e que non cambia aínda que se modifiquen os
produtos. A última non se podía automatizar: **imprimiuse nunha impresora
real** e verificouse que sae nunha folla, sen cortes e cos acentos e o símbolo
do euro ben.

---

## 6.8. Copias de seguridade

**Por que.** É o único punto onde un fallo non ten volta atrás. O código pódese
descargar outra vez; as vendas, non.

**Que se fixo.** Unha copia automática ao pechar o día, e outra manual cando
se queira, nunha carpeta configurable fóra do ordenador.

**As decisións.** A copia **non se fai copiando o arquivo sen máis**. Se se
copiase coa aplicación aberta, podería quedar a medio escribir. Úsase o
mecanismo propio de SQLite, pensado para iso.

E unha copia **non se dá por boa ata comprobala**: ábrese e verifícase que
está completa antes de aceptala.

Hai tamén unha decisión que parece pequena e non o é: se a carpeta de destino
non existe, **non se crea**. Un disco desconectado non debe converterse nunha
carpeta local onde as copias *parecerían* estar a salvo.

**Como se comprobou.** Verificouse que a copia ten exactamente o mesmo contido
que a base orixinal e que nunca substitúe a unha anterior. O caso máis
ilustrativo probouse de verdade: **coa unidade desconectada**, a aplicación
avisa, non crea nada e o peche queda gardado igual.

> **A limitación que queda aberta.** Comprobar unha copia **non é
> restaurala**. A restauración non está feita na
> aplicación: é un procedemento manual descrito en
> [DISASTER_RECOVERY.md](../../DISASTER_RECOVERY.md). Mentres non se restaure
> unha copia e se mire o contido, non está verificada do todo.

---

## 6.9. Preparar a versión pública

A aplicación estaba en uso real, cos datos dunha cafetería concreta. Para
publicala como traballo académico había que separar completamente o programa
do seu contido.

A solución foi unha ferramenta que crea unha **base de datos de demostración**
con datos inventados: un establecemento ficticio, dez produtos, dous días
pechados e o día actual aberto. A ferramenta **négase a escribir sobre a base
real**, e todas as capturas desta memoria están feitas con ela: **ningún dato
que se vea nelas é real**.

> **Un detalle que obrigou a repetir traballo.** A pantalla de copias mostra a
> ruta completa da carpeta de destino, que revelaría a estrutura de
> directorios do ordenador. A solución non foi retocar a imaxe — editar unha
> captura para tapar datos resta credibilidade —, senón **cambiar a
> configuración** e repetir as capturas.

---

## 6.10. Control de versións

Todo o traballo quedou rexistrado no historial do proxecto, que é a súa
cronoloxía real.

A regra do repositorio é clara: **só código, documentación e scripts**. Nunca
bases de datos, copias nin documentos xerados. E non se deixa á boa vontade de
ninguén: hai **probas que fallan** se un arquivo prohibido chega a colarse.

Para a versión académica usouse unha rama separada, de modo que a versión en
uso real quedase intacta. O repositorio público creouse despois **sen
historial anterior**, para que nada que puidese ter existido nun paso
intermedio chegase a facerse público.

Antes de publicar revisáronse un a un todos os arquivos — incluídas as imaxes
e os seus metadatos — buscando datos identificativos, rutas persoais e
arquivos que non debían estar.

---

## 6.11. Problemas e solucións

Os principais problemas atopados durante o desenvolvemento poden resumirse
así:

| Problema | Solución |
|---|---|
| A comprobación de «día pechado» facíase un instante antes de tempo. Non se nota no uso normal | Moveuse ao sitio correcto. Para verificalo, rompeuse o código a propósito e confirmouse que as probas o detectan |
| O PDF collía os datos do establecemento da configuración actual, así que cambialos reescribía os documentos antigos | Gárdanse dentro de cada peche. Houbo que arranxar tamén os peches xa feitos |
| Non se podía pechar a caixa pasada a medianoite | Permítese pechar hoxe ou onte |
| En Windows, as probas deixaban arquivos temporais que non se podían borrar | Péchanse as conexións ao rematar cada proba |

Os tres primeiros teñen algo en común: **ningún apareceu programando**.
Apareceron ao pensar como se usa isto de verdade nunha cafetería.

---

## 6.12. Onde quedou

O resultado é unha aplicación **en uso real**, non un exercicio. Rexistra
vendas en efectivo, garda un histórico que non se pode falsear, pecha o día,
emite un documento imprimible e deixa unha copia de seguridade comprobada fóra
do ordenador.

En números: **263 probas automatizadas e unha soa dependencia externa
directa**.

Dos doce obxectivos que se fixaron ao principio, **dez están cumpridos**. Os
dous que faltan son restaurar unha copia e comprobar os datos recuperados. Non
é un descoido: a copia créase, compróbase e sae do ordenador, pero o paso de
volver a metela está documentado e non se chegou a executar.

Por iso, en toda a documentación do proxecto, o plan de recuperación
preséntase como **documentado, non demostrado**.

---

> **Para ampliar:** as decisións técnicas, co seu razoamento completo e as
> alternativas que se descartaron, están en
> [DECISIONS_TECNICAS.md](../DECISIONS_TECNICAS.md). O detalle das probas, en
> [PROBAS.md](../PROBAS.md).
