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

## 11.6. Estimación temporal e económica

Todo o que segue son **estimacións**, non medicións. O tempo non se cronometrou
e os importes non corresponden a ningunha factura: calcúlanse para poder
valorar economicamente o traballo, que é o que pide o contexto académico.

### O tempo

O desenvolvemento, as probas e a documentación estímanse en **90 horas**.

É unha estimación global do conxunto do traballo, feita a partir das fases do
proxecto. Non sae de ningunha ferramenta de medición.

### O valor dese tempo

Tomando como referencia unha tarifa profesional de **23 €/hora**:

> 90 h × 23 €/h = **2.070 €**

Esa tarifa é unha referencia para poder poñerlle un número ao tempo dedicado,
non un prezo cobrado a ninguén.

### O equipamento

O portátil empregado vale uns **700 €**. Sería incorrecto imputarllos enteiros
ao proxecto: o ordenador non se comprou para isto nin deixa de servir ao
rematar. Só corresponde **a parte proporcional de desgaste**.

Cunha amortización simple —vida útil de 4 anos e un uso profesional de
referencia de 1.760 horas ao ano—:

> 700 € ÷ (4 × 1.760 h) × 90 h ≈ **9 €**

### O despregamento

Poñer a aplicación a funcionar no establecemento estímase en **2 horas**,
adicionais ás 90 anteriores. Inclúen preparar o equipo, instalar o contorno e
as dependencias, configurar a base e as copias, comprobar o arranque e facer
unha proba básica.

> 2 h × 23 €/h = **46 €**

### Software e infraestrutura

| Concepto | Custo |
|---|---|
| Python | 0 € |
| Flask | 0 € |
| SQLite | 0 € |
| Resto de ferramentas empregadas | 0 € — ningunha esixe licenza comercial |
| Hospedaxe | 0 € — a aplicación funciona no propio equipo |
| Servidor propio da aplicación | 0 € — non existe |

Unha precisión importante: a carpeta de copias **pode** estar sincronizada cun
servizo externo, pero ese servizo **non forma parte de Cafetería Cash**. O seu
custo, se o ten, pertence a outro sistema e non se imputa aquí.

### Custo inicial estimado

| Concepto | Custo |
|---|---:|
| Desenvolvemento, probas e documentación | 2.070 € |
| Uso proporcional do portátil | ≈ 9 € |
| Despregamento inicial | 46 € |
| Software e licenzas | 0 € |
| Hospedaxe propia da aplicación | 0 € |
| **Total inicial estimado** | **≈ 2.125 €** |

### Mantemento

Convén separar dúas cousas que adoitan mesturarse.

**Infraestrutura:** o custo recorrente é **≈ 0 €**. Non hai servidor, nin
hospedaxe, nin cotas. É consecuencia directa de que a aplicación funcione no
propio equipo.

**Traballo humano:** para poder estimalo, resérvase **1 hora ao mes** para
revisións, pequenas correccións e soporte:

> 1 h/mes × 23 €/h = 23 €/mes → **276 €/ano**

É unha **reserva estimada**, non un gasto comprometido. Non significa que se
vaia consumir unha hora todos os meses: haberá meses sen ningunha intervención.

### Primeiro ano

> 2.125 € + 276 € = **≈ 2.401 €**

Entendido como **estimación económica do primeiro ano**, non como un
desembolso real que alguén teña que pagar.

### Valor comercial estimado

Custo de produción e valor comercial **non son o mesmo**, e convén non
confundilos. Que algo custe 2.125 € en producir non significa que valla iso no
mercado: pode valer máis ou menos.

Para estimar o valor comercial hai que mirar o que se entrega: unha aplicación
**feita a medida** e **en uso real**, con documentación técnica, 263 probas
automatizadas, peche diario, xeración de documentos PDF, copias de seguridade
validadas e instalación local sen dependencia de servizos externos.

Con eses elementos, establécese unha horquilla orientativa de **2.500 € a
3.000 €**, tomando como referencia:

> **2.750 €**

**É unha estimación académica**, feita para poder razoar sobre o valor do
traballo. **Non é o resultado dun estudo de mercado** nin unha oferta: non se
consultaron prezos de produtos comparables nin se sondeou a ningún cliente.

---

## 11.7. O que non se conseguiu

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
