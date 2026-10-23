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
Capítulo redactado. Manual completo, paso a paso, en ../MANUAL_USUARIO.md.

As capturas están todas feitas coa base de demostración: datos ficticios.
As rutas que aparecen nelas son de demostración, non do equipo real.
-->

# 10. Como se usa

## 10.1. Un día de traballo

A aplicación segue o ritmo real dunha cafetería. Ábrese pola mañá, cóbrase
durante a xornada e péchase a caixa ao rematar.

```
arrancar  →  cobrar (moitas veces)  →  resumo  →  pechar o día  →  PDF
```

Arrancar son dous pasos: executar o script de arranque e abrir a dirección
local no navegador. A partir de aí non se volve tocar nada do sistema.

Esta memoria está redactada en galego, pero a interface da aplicación conserva
o castelán no que foi desenvolvida orixinalmente, e así aparece nas capturas.

> Todas as capturas que seguen están feitas coa base de datos de demostración.
> **Ningún dato que aparece nelas é real.**

---

## 10.2. Cobrar

A pantalla principal ten dúas zonas: os produtos á esquerda e a venda que se
está a compoñer á dereita.

![Pantalla de venda](../capturas/01-venda.png)

Cada pulsación sobre un produto engade unha unidade. Se xa estaba na venda,
súmase á cantidade. Cada liña ten tres controis — **+**, **−** e **✕** — e
debaixo aparece o total.

Mentres non se cobre, **non se garda nada**. A venda pódese modificar ou
cancelar enteira sen deixar rastro.

Ao pulsar **COBRAR EN EFECTIVO**, a venda gárdase cun número e a pantalla
queda baleira, lista para a seguinte persoa.

![Venda rexistrada](../capturas/02-venda-rexistrada.png)

O botón está desactivado se non hai ningunha liña, e tamén se o día de hoxe xa
está pechado.

---

## 10.3. Corrixir un erro

Desde **Histórico** vense todas as vendas, da máis recente á máis antiga, co
seu número, o seu importe e o seu estado.

![Histórico de vendas](../capturas/03-historico.png)

Se unha venda está mal, anúlase. O navegador pide confirmación antes de facer
nada.

A venda **segue aí**, marcada como anulada e coa hora da anulación. Non se
borra nada. E non se pode desfacer: unha venda anulada non volve ser válida.

As vendas dun día xa pechado non teñen botón de anular; no seu lugar aparece
«Día cerrado».

---

## 10.4. Ver como vai o día

**Resumo do día** mostra o efectivo válido, cantas vendas houbo, canto se
anulou e as unidades vendidas de cada produto.

![Resumo do día](../capturas/04-resumo.png)

É unha consulta: mirar o resumo **non pecha nada** nin modifica a base de
datos.

---

## 10.5. Pechar a caixa

Desde **Peche do día** aparece primeiro unha previsualización coas cifras que
quedarían gardadas, incluídos os datos do establecemento.

![Previsualización do peche](../capturas/05-peche-previo.png)

Os botóns **Hoxe** e **Onte** permiten escoller entre esas dúas datas, para
poder pechar despois da medianoite.

Ao pulsar **CERRAR DÍA** e confirmar, o día queda pechado, recibe un número e
créase automaticamente unha copia de seguridade.

![Día pechado](../capturas/06-peche-realizado.png)

A partir dese momento **non se poden rexistrar nin anular vendas desa data**,
e non hai reapertura. É a acción menos reversible de toda a aplicación, e por
iso pide confirmación.

---

## 10.6. O documento do peche

Co día pechado aparece **ABRIR PDF**, que xera e abre o documento A4.

![PDF do peche](../capturas/07-pdf-peche.png)

Inclúe a cabeceira do establecemento, o número e a data do peche, a primeira e
a última venda, as unidades por produto, os totais e o desglose de IVE.

Pódese xerar as veces que faga falla: **sempre sae igual**. Para imprimilo,
abonda co atallo de impresión do navegador.

---

## 10.7. As pantallas de configuración

Non se usan a diario, pero convén coñecelas.

| Pantalla | Para que |
|---|---|
| **Xestionar produtos** | Crear produtos, cambiar nomes e prezos, activar e desactivar |
| **Datos do establecemento** | Os catro datos que aparecen na cabeceira do PDF |
| **Copia de seguridade** | Repetir a copia a man se fose necesario |

![Xestión de produtos](../capturas/09-produtos.png)

Un produto **non se borra nunca**: desactívase. Desaparece da pantalla de
venda pero segue na base, porque as vendas antigas o referencian.

![Datos do establecemento](../capturas/10-establecemento.png)

Os datos do establecemento son **obrigatorios para poder pechar o día**, e
cada peche conxela os que había nese momento.

![Pantalla de copia de seguridade](../capturas/08-backup.png)

Normalmente non fai falla entrar aquí: a copia créase soa ao pechar o día.

---

## 10.8. Dúas accións que non teñen volta atrás

Para rematar, o que convén ter claro antes de usar a aplicación:

- **anular unha venda** non se pode desfacer;
- **pechar un día** non se pode reabrir.

As dúas piden confirmación. Todo o demais é reversible.

O manual detallado, con todos os casos e mensaxes, está en
[MANUAL_USUARIO.md](../MANUAL_USUARIO.md).
