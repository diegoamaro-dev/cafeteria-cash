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
Capítulo redactado. Dicionario de datos completo en ../MODELO_DATOS.md.
O núcleo deste capítulo é a sección 5.3: os tres niveis de histórico.
-->

# 5. Como se gardan os datos

## 5.1. Seis táboas

Toda a información vive nun **único arquivo** de base de datos, repartida en
seis táboas. O diagrama completo, coas columnas de cada unha, está en
[MODELO_DATOS.md](../MODELO_DATOS.md); aquí interesa máis entender por que son
esas seis e non outras.

Son seis porque hai **dúas cousas que se gardan por partida dobre** —a venda e
o peche, cada un cunha táboa para a cabeceira e outra para o detalle— máis
**dúas táboas soltas**: o catálogo de produtos e os datos do establecemento.

---

## 5.2. Que garda cada unha

| Táboa | Que garda |
|---|---|
| `product` | Os produtos e os seus prezos actuais |
| `sale` | Unha venda cobrada: número, data, importe e estado |
| `sale_item` | As liñas desa venda |
| `daily_close` | O peche dun día, coas cifras conxeladas |
| `daily_close_item` | As unidades por produto dese peche |
| `establishment` | Os datos identificativos do establecemento |

A última merece unha nota. Os catro datos que aparecen na cabeceira do
documento de peche — titular, NIF, nome comercial e enderezo — **escríbense
desde a propia aplicación e gárdanse só nesa táboa**. Non están no código, nin
nas páxinas, nin no repositorio. Como se protexe iso explícase no
[capítulo 9](09_SEGURIDADE_BACKUP_RECUPERACION.md).

---

## 5.3. Por que se garda o mesmo dato tres veces

Esta é a parte do deseño que máis paga a pena entender, e nace dunha pregunta
razoable: **se o prezo do café xa está na táboa de produtos, por que se volve
gardar en cada venda?**

A resposta vese cun exemplo. Imaxinemos que hoxe o café custa 1,40 € e mañá
sobe a 1,50 €. Se as vendas gardasen só «o produto número 1», ao consultar
onte veríanse os cafés de onte **ao prezo de mañá**. O histórico cambiaría
só porque alguén tocou un prezo.

Para evitalo, cada venda garda o **nome e o prezo do momento en que se
cobrou**. E o peche do día vai aínda máis alá: garda tamén as cifras totais,
as unidades vendidas de cada produto e os datos do establecemento.

Quedan así tres niveis, cada un protexendo ao anterior:

```
   catálogo vivo    →    venda conxelada    →    peche conxelado
   (cambia cando        (non cambia nunca        (non cambia nunca
    se queira)           máis)                    máis)
```

Á esquerda, o que se pode modificar libremente. Á dereita, o que xa é
histórico. **Nada do que pase á esquerda pode mover nada do que está á
dereita.**

É tamén o que explica unha cousa que de primeiras parece un erro de deseño:
que o nome dun produto apareza repetido en moitas filas. Non é repetición, é
constancia.

---

## 5.4. As regras que protexen os datos

Catro regras sosteñen a integridade do conxunto:

**Os importes gárdanse en céntimos enteiros.** Un café de 1,40 € é o número
140. O motivo explicouse no [capítulo 6](06_DESENVOLVEMENTO.md).

**Unha venda cobrada non se borra.** Se está mal, cambia de estado a
«anulada», pero segue aí coas súas liñas e o seu importe orixinal.

**Un día pechado non admite cambios.** Nin vendas novas desa data, nin
anulacións, nin reapertura.

**Os números non se repiten nunca.** Cada venda e cada peche levan un número
correlativo único, e un número xa usado non se reutiliza aínda que a operación
que o ía levar fallase.

A base de datos non se limita a confiar en que o programa cumpra estas regras:
está configurada para **rexeitar** os datos que non as cumpran. Tres exemplos
reais do esquema:

- unha venda só pode estar en dous estados, **válida ou anulada**: calquera
  outro valor rexéitase;
- **un día só se pode pechar unha vez**, porque a data do peche ten que ser
  única;
- nun peche, **o bruto ten que ser igual ao efectivo válido máis o anulado**.
  Se as cifras non cadran, o peche non se garda.

A última é a máis interesante: non comproba un dato illado, senón que as
cantidades sexan coherentes entre si. Aínda que un erro no programa calculase
mal, a base de datos non o deixaría pasar.

Os detalles de como está implementada cada restrición están en
[MODELO_DATOS.md](../MODELO_DATOS.md).

---

## 5.5. Como evoluciona o esquema

As táboas foron medrando ao longo do proxecto: o peche, por exemplo, non tiña
ao principio os datos do establecemento nin o desglose de IVE.

Para que iso non obrigue a reinstalar nada, **a aplicación comproba o seu
propio esquema cada vez que arranca** e engade o que falte. Se xa está todo,
non fai nada.

Para quen usa a cafetería, isto significa que actualizar é simplemente abrir a
aplicación. E, por deseño, esas comprobacións só poden **engadir**: nunca
borran datos nin columnas existentes.
