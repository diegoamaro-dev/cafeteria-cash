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
Capítulo redactado. Detalle completo da suite en ../PROBAS.md.
CIFRAS: 250 probas da aplicación + 13 da ferramenta de demo = 263.
-->

# 8. Como se comprobou que funciona

## 8.1. Por que non abonda con probalo a man

Nunha caixa, un erro non avisa. Se unha venda se perde ou unha conta sae un
céntimo curta, non aparece ningunha mensaxe: aparece un descadre no caixón ao
final do día, cando xa non se sabe cal foi a venda nin cando.

Por iso o proxecto ten **probas automatizadas**: pequenos programas que usan a
aplicación e comproban que fai o que debe. Execútanse cun só comando e, se
algo deixou de funcionar, dino antes de que o faga a cafetería.

Non se engadiu ningunha ferramenta externa para iso. Úsase a que xa trae
Python, para que instalar o proxecto nun ordenador novo siga sendo igual de
simple. É a mesma lóxica que levou a escribir o PDF sen librarías.

---

## 8.2. Canto se proba

| | Probas |
|---|---:|
| Da aplicación | **250** |
| Da ferramenta que crea os datos de exemplo | 13 |
| **Total** | **263** |

Convén distinguir os dous grupos. As 250 proban o programa que usa a
cafetería. As outras 13 proban un script auxiliar que crea datos ficticios
para demostracións e que **non forma parte da aplicación**.

A suite enteira tarda arredor dun minuto. Iso non é un dato de adorno: é o que
permite executala despois de cada cambio, que é cando serve de algo.

---

## 8.3. Que se proba

### Que as contas son exactas

Hai probas construídas a propósito cos casos nos que os decimais darían un
resultado incorrecto — como o exemplo dos cafés do
[capítulo 6](06_DESENVOLVEMENTO.md) —, e tamén cos casos límite: prezos
baleiros, con texto, negativos ou con máis de dous decimais.

### Que non se perde nin se falsea nada

Que o que se garda se recupera igual despois de apagar e volver abrir. Que
anular unha venda non borra ningunha fila. Que, se a escritura falla a medias,
non queda nada escrito. E que o mesmo peche sempre produce o mesmo documento.

Dentro deste bloque hai unha proba distinta das demais, e vale a pena
destacala: en lugar de probar o comportamento, **le o propio código** da
aplicación e falla se alguén engade no futuro unha instrución de borrado sobre
as vendas ou os peches. A regra queda protexida fronte a cambios posteriores,
non só fronte ao código de hoxe.

### Que dúas cousas á vez non rompen nada

Que pasa se unha venda se confirma xusto cando alguén está pechando o día.
Hai probas que provocan esa situación a propósito e comproban que o resultado
é coherente: ou a venda entra no peche, ou se rexeita, pero nunca queda a
medias.

Como se contou no [capítulo 6](06_DESENVOLVEMENTO.md), estas probas
verificáronse contra código roto a posta, e detectaron o fallo nos dous casos.

### Que a base real nunca se toca

Cada proba traballa sobre unha base de datos temporal propia, que se crea ao
empezar e se borra ao rematar. Ningunha toca os datos da cafetería.

A este bloque pertencen tamén as probas que vixían que ningún dato real chegue
ao repositorio, que se describen no
[capítulo 9](09_SEGURIDADE_BACKUP_RECUPERACION.md).

A consecuencia práctica é a que importa: a suite pódese executar en calquera
momento, incluso coa cafetería aberta e cobrando.

---

## 8.4. O que non se proba

Tan importante como o anterior, e máis honesto:

| Que queda fóra | Por que |
|---|---|
| A interface no navegador | Compróbase o HTML que devolve a aplicación, non o comportamento real do navegador. O aviso de confirmación verificouse a man |
| A impresión en papel | Compróbase que o PDF é correcto; que saia ben na impresora verificouse imprimíndoo |
| A subida á nube da copia | A aplicación escribe nunha carpeta; a sincronización faina outro programa |
| Canta carga aguanta | Non ten sentido nunha caixa cun só usuario |
| A porcentaxe de código cuberto | Medila esixiría outra ferramenta. O criterio seguido foi cubrir cada regra e cada camiño de erro |

E unha limitación que non é de probas, pero que lles afecta: **a restauración
dunha copia de seguridade non está probada porque non está feita**. Trátase no
[capítulo 9](09_SEGURIDADE_BACKUP_RECUPERACION.md).

O desglose completo, arquivo por arquivo, está en [PROBAS.md](../PROBAS.md).
