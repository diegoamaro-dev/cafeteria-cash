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

REGRA: aquí só vai o que EXISTE e está COMPROBADO. As valoracións e as ideas
de futuro van no capítulo 12. Toda cifra que apareza aquí ten que poder
comprobarse executando algo.
-->

# 11. Resultados

## 11.1. Unha aplicación que se usa de verdade

O resultado máis importante non é unha cifra: **a aplicación está rexistrando
vendas reais nunha cafetería**, non só en probas.

Isto cambia o valor do traballo. Unha ferramenta que só funciona co que
imaxinou quen a programou é un exercicio. Unha que aguanta un mostrador
—présas, erros que hai que corrixir, días que se pechan despois da medianoite—
tivo que resolver problemas que non estaban no plan inicial.

Varios dos axustes que se contan no [capítulo 6](06_DESENVOLVEMENTO.md)
apareceron precisamente así: usándoa.

---

## 11.2. O que quedou funcionando

| Capacidade | Estado |
|---|---|
| Xestionar produtos e prezos | ✅ |
| Cobrar en efectivo con numeración correlativa | ✅ |
| Corrixir erros sen borrar nada | ✅ |
| Consultar o resumo do día | ✅ |
| Pechar a caixa e deixala pechada | ✅ |
| Xerar o documento A4 do peche | ✅ |
| Imprimilo | ✅ |
| Crear unha copia de seguridade comprobada | ✅ |
| Levar esa copia fóra do ordenador | ✅ |
| Instalar todo nun equipo limpo | ✅ |
| **Restaurar unha copia** | ❌ **pendente** |
| **Verificar os datos recuperados** | ❌ **pendente** |

**Dez de doce.** Os dous que faltan trátanse máis abaixo.

---

## 11.3. As cifras

| | |
|---|---:|
| Probas automatizadas | **263** |
| Dependencias externas directas | **1** |
| Táboas na base de datos | 6 |

Das 263 probas, **250 son da aplicación** e 13 dunha ferramenta auxiliar que
crea datos de exemplo. A suite completa pasa enteira.

A cifra de dependencias é a que mellor resume o criterio seguido. Instalar o
proxecto nun ordenador novo non require nada máis que Python e Git.

---

## 11.4. O documento do peche

É a saída máis visible do traballo e a que se pode mostrar nunha folla:

![PDF do peche](../capturas/07-pdf-peche.png)

Contén os datos do establecemento, o número e a data do peche, as unidades
vendidas, os totais e o desglose de IVE. Xerouse, abriuse e **imprimiuse nunha
impresora real**, que foi a condición para dar esa parte por terminada.

Ademais, o mesmo peche produce sempre exactamente o mesmo documento, polo que
se pode volver imprimir cando faga falla sen risco de que cambie.

*(A captura está feita coa base de demostración: os datos son ficticios.)*

---

## 11.5. O repositorio público

O proxecto publicouse como repositorio público con licenza MIT, cun historial
limpo e sen ningún dato real do establecemento.

Contén o código completo, as probas, a documentación técnica —arquitectura,
modelo de datos, decisións, probas e manual— e as capturas, todas xeradas
cunha base de datos de demostración.

Antes de publicalo revisouse arquivo por arquivo, incluídas as imaxes e os
seus metadatos, para comprobar que non quedaba ningún dato identificativo,
ruta persoal nin arquivo que non debese estar.

---

## 11.6. O que non se conseguiu

Dos doce obxectivos iniciais, dous quedaron sen cumprir: **restaurar unha
copia de seguridade e comprobar os datos recuperados**.

Non é un detalle menor e convén dicilo con claridade. A copia créase
automaticamente, compróbase antes de darse por boa e sae do ordenador, pero o
paso de volver poñela en funcionamento está só documentado. **Non se executou
nunca.**

A consecuencia é que o plan de recuperación segue sendo un procedemento
**documentado, non demostrado**, tal como se explica no
[capítulo 9](09_SEGURIDADE_BACKUP_RECUPERACION.md). Completalo é a primeira
tarefa pendente do proxecto.
