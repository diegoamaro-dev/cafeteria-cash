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
Capítulo redactado. Plan completo en ../../DISASTER_RECOVERY.md.

REGRA INNEGOCIABLE: a restauración NON está implementada nin probada.
Non suavizar isto en ningunha frase.
-->

# 9. Seguridade, copias e recuperación

## 9.1. A seguridade aquí é sobre todo non expoñerse

A aplicación manexa datos económicos reais nun ordenador que está nun
mostrador, sen administrador de sistemas detrás. Nese contexto, a mellor
protección non é engadir medidas: é **non ter superficie que protexer**.

Por iso o programa **só escoita no propio ordenador**, nun enderezo que non
sae del.

Comprobouse de dúas maneiras: verificando a que enderezo queda atado o
programa ao arrancar, e intentando acceder a el polas direccións de rede do
equipo, sen conseguilo. Non queda exposto en ningunha interface de rede.

A consecuencia é que **non hai contrasinais que xestionar**, porque non hai
acceso remoto que protexer. Tampouco se gardan datos de tarxetas: os
pagamentos con tarxeta van por un aparello aparte e quedan fóra.

---

## 9.2. Os datos do establecemento

Os catro datos identificativos que aparecen na cabeceira do documento de peche
son reais e son do titular do negocio. Tratáronse con coidado desde o
principio.

Introdúcense desde unha pantalla da aplicación e **gárdanse só na base de
datos local**. Non están escritos no código, nin nas páxinas, nin nas probas,
nin no repositorio público.

Non se deixou á boa memoria de ninguén: hai **probas automáticas que revisan
todos os arquivos do proxecto** e fallan se atopan algo con forma de
identificador fiscal ou unha ruta privada. Todas as capturas desta memoria
están feitas cunha base de datos de demostración con datos inventados.

---

## 9.3. As copias de seguridade

O código pódese volver descargar. **As vendas, non**: só existen nun arquivo.
É o único punto do proxecto onde un fallo non ten volta atrás, e por iso é o
que máis atención recibiu.

**Cando se fai a copia.** Automaticamente ao pechar o día, e a man cando se
queira desde a pantalla de copias.

**Como se fai.** Non copiando o arquivo sen máis. Se se copiase coa aplicación
aberta, podería quedar a medio escribir e non valer para nada. Úsase o
mecanismo propio da base de datos, pensado precisamente para iso, que dá unha
copia coherente aínda que se estea usando.

Mentres se escribe, a copia leva un nome provisional e só ao rematar recibe o
nome definitivo. Así nunca queda á vista unha copia a medio facer que alguén
puidese confundir cunha boa.

**Que se comproba antes de aceptala.** Ábrese, verifícase que é unha base de
datos válida, que está completa e que contén as táboas que ten que conter. Se
algo falla, descártase e avísase.

**Tres regras máis:**

- cada copia leva data e hora no nome, e **nunca substitúe a unha anterior**;
- a copia garda nunha carpeta que está fóra do ordenador;
- se esa carpeta non está dispoñible, **non se crea**.

A última parece menor e non o é. Se a aplicación crease a carpeta ao non
atopala, un disco desconectado convertiríase nunha carpeta local onde as
copias *parecerían* estar a salvo. Probouse o caso real: coa unidade
desconectada, a aplicación avisa, non crea nada e o peche queda gardado igual.

---

## 9.4. O plan de recuperación

A idea de fondo é simple: **o ordenador é substituíble**. O que non se pode
perder vive en dous sitios distintos e independentes.

```
   o código          →   no repositorio
   os datos          →   nas copias de seguridade
```

Se falla unha vía, a outra segue servindo. Esta separación é a mesma que se
describiu no [capítulo 4](04_ARQUITECTURA.md), e aquí é onde se entende para
que serve.

O procedemento previsto, se o ordenador se perde ou rompe:

```
equipo novo → clonar → instalar → restaurar a copia → arrancar → verificar
```

Verificar significa comprobar que están os produtos, as últimas vendas e os
peches, que a numeración continúa onde debía e que un documento antigo se
rexenera igual.

---

## 9.5. Que está feito e que non

Aquí convén ser exacto, porque é fácil dar por bo máis do que se probou:

| Parte do ciclo | Estado |
|---|---|
| Crear a copia | **Feito e probado** |
| Comprobar que a copia é válida | **Feito e probado** |
| Que a copia saia do ordenador | **Comprobado** |
| **Restaurar unha copia** | **Pendente** |
| **Verificar os datos recuperados** | **Pendente** |

A restauración **non está implementada na aplicación**. É un procedemento
manual descrito en [DISASTER_RECOVERY.md](../../DISASTER_RECOVERY.md), e non se
chegou a executar.

Por iso o proxecto aplica unha regra que convén deixar dita con todas as
letras: **comprobar unha copia non é restaurala**. Unha copia que nunca se
restaurou non se considera verificada, por moito que pasase todas as
comprobacións no momento de crearse.

En consecuencia, este plan de recuperación é un procedemento **documentado,
non demostrado**. Completalo é a primeira liña de traballo futuro, e trátase
no capítulo 12.

---

## 9.6. Canto se podería perder, e canto se tardaría

**Canto se podería perder.** Coa copia que se fai ao pechar o día, o peor caso
é perder o traballo do día en curso. Pódese reducir facendo copias manuais
cando interese.

**Canto se tardaría.** O obxectivo é ter a cafetería funcionando noutro
ordenador en **menos dunha hora**, sempre que o repositorio sexa accesible,
exista unha copia válida e haxa conexión para instalar.

É unha estimación a partir dos pasos descritos, **non un tempo medido nun
simulacro**. Mentres non se faga a proba completa, segue sendo unha previsión
razoable e non un resultado.
