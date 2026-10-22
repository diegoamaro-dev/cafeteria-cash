# Decisións técnicas

Cada decisión responde a tres preguntas: **cal é o problema**, **que se
decidiu** e **que se descartou**.

---

## 1. Importes en céntimos enteiros, nunca `float`

**Problema.** Os números en coma flotante non representan exactamente os
decimais. En Python:

```python
0.1 + 0.2        # 0.30000000000000004
6 * 1.40 + 4 * 1.65   # 14.999999999999998, non 15.0
```

Nunha aplicación de caixa, ese erro acumúlase e acaba producindo descadramentos
entre o diñeiro do caixón e o rexistrado.

**Decisión.** Un café de 1,40 € gárdase como o enteiro `140`. Todas as sumas e
multiplicacións son enteiras, que en Python son exactas e sen límite de tamaño.
A conversión a `1,40 €` faise **só ao mostrar**, nunca nos cálculos.

**Descartouse** `Decimal`: é correcto, pero obriga a vixiar o contexto de
precisión e o redondeo en cada operación. Os enteiros non teñen ese risco.

Hai probas que comproban precisamente os casos onde `float` fallaría.

---

## 2. SQLite como base de datos

**Problema.** Fai falla persistencia fiable nun portátil dunha cafetería, sen
administrador de sistemas.

**Decisión.** SQLite: a base é **un só arquivo**. Non hai servidor que arrancar,
nin usuarios que crear, nin porto que abrir.

Isto é o que fai viable o plan de recuperación ante fallo: **restaurar consiste
en poñer de novo ese arquivo no seu sitio**, sen reinstalar nin reconfigurar
ningún servizo.

**Un matiz importante sobre as copias.** Que a base sexa un arquivo *non*
significa que copiala sexa simplemente copiar o arquivo. Se se copiase «a pelo»
coa aplicación aberta, a copia podería quedar inconsistente, a medio escribir.
Por iso as copias créanse con **`sqlite3.Connection.backup()`**, a API oficial
de copia de SQLite, que garante unha foto coherente aínda coa base en uso. A
simplicidade está na **restauración**, non en saltarse o procedemento de copia.
Explícase na [decisión 10](#10-a-copia-de-seguridade-usa-a-api-de-sqlite).

Ademais, SQLite dá transaccións ACID reais, claves alleas e restricións `CHECK`,
que é o que sostén as regras de integridade do proxecto.

**Descartouse** MySQL ou PostgreSQL: requiren instalar e manter un servizo, e
complican moito a recuperación nun equipo novo, sen aportar nada a unha caixa.

---

## 3. Flask como framework web

**Problema.** Fai falla servir unhas poucas páxinas e procesar formularios.

**Decisión.** Flask: **unha soa dependencia directa**. Dá enrutado, plantillas
Jinja2 e procesamento de formularios, e nada máis. O proxecto completo instálase
con sete paquetes, contando as dependencias transitivas de Flask.

**Descartouse** Django: trae ORM, panel de administración e sistema de usuarios
que este proxecto non usa, e multiplicaría o que hai que entender e manter.

---

## 4. Execución local, só en `127.0.0.1`

**Problema.** A aplicación manexa datos económicos reais nun equipo sen
protección perimetral.

**Decisión.** O servidor escoita **só** en `127.0.0.1`. Non é accesible desde
outros equipos da rede nin desde internet. Non hai contrasinais que xestionar
nin superficie de ataque remota, porque non hai acceso remoto.

**Comprobación real.** Verificouse con `netstat` que o socket está atado a
`127.0.0.1` e que os intentos de conexión desde as IP de rede do equipo fallan.

**Descartouse** despregar na nube: engadiría custo, contas, copias de seguridade
externas e un problema de protección de datos, para unha caixa que só se usa nun
mostrador.

---

## 5. Unha venda confirmada non se borra nunca

**Problema.** Se se puidese borrar unha venda, o histórico deixaría de ser
fiable: non se distinguiría un erro corrixido dunha venda ocultada.

**Decisión.** Unha venda incorrecta **anúlase**: pasa a `status = 'VOID'` e
gárdase cando se anulou. Consérvanse o número, a data, o importe e todas as
liñas. No histórico segue a verse, marcada como ANULADA.

**Consecuencias.** O resumo distingue efectivo válido de importe anulado, e o
peche garda ambos. Unha anulación **non se pode desfacer**: unha venda `VOID`
non volve a `VALID`.

Hai unha proba que **falla** se alguén engade un `DELETE FROM sale` ao código:
a regra está protexida fronte a cambios futuros, non só fronte ao esquecemento.

---

## 6. Snapshots históricos

**Problema.** Se unha venda gardase só o `id` do produto, subir o prezo do café
cambiaría o importe de todas as vendas pasadas.

**Decisión.** Cada liña de venda garda o **nome e o prezo do momento do cobro**.
O mesmo principio aplícase ao peche, que conxela ademais as unidades por
produto, os datos do establecemento e o desglose de IVE.

**Que se garda, exactamente:** o que a clientela viu na pantalla e pagou. Non se
relé o produto ao cobrar, porque entón o total gardado podería diferir do que se
mostrou.

Hai probas que cambian nomes e prezos despois de vender e comproban que o
histórico non se move.

---

## 7. Un día pechado é inmutable

**Problema.** Se despois de pechar un día se puidese rexistrar ou anular unha
venda desa data, o peche deixaría de corresponderse coas vendas que representa.

**Decisión.** Tras pechar, rexístranse como erro tanto unha venda nova como unha
anulación desa data. **Non existe reapertura, edición nin borrado de peches.**

**O detalle que importa.** A comprobación faise **dentro da mesma transacción
`BEGIN IMMEDIATE`** que escribiría, non antes. Se se fixese antes, unha venda
podería pasar a comprobación co día aínda aberto e escribirse xusto despois do
peche.

Hai probas con **fíos reais** que o verifican, e comprobouse que esas probas
**detectan o fallo**: executadas contra unha versión coa comprobación feita
antes do bloqueo, fallan.

---

## 8. O PDF é determinista

**Problema.** Un documento contable debe poder rexenerarse e dar o mesmo
resultado. Se dependese do momento ou da configuración actual, dous PDF do mesmo
peche poderían diferir.

**Decisión.** O PDF **non inclúe a hora de xeración** e lese **só** de
`daily_close` e `daily_close_item`. Non consulta vendas, nin produtos, nin a
configuración actual do establecemento.

**Resultado comprobado.** Rexenerar o mesmo peche produce un arquivo **idéntico
byte a byte**. Comprobouse tamén alterando a man as vendas do día pechado: o PDF
non cambia, porque non as le.

O arquivo chámase sempre igual: `cierre_<data>_<número>.pdf`.

---

## 9. O PDF escríbese coa biblioteca estándar

**Problema.** Fai falla xerar un A4 imprimible. As librarías de PDF engaden
dependencias que hai que instalar nun equipo novo durante unha recuperación.

**Decisión.** Escribir o PDF directamente, coa biblioteca estándar de Python.
É un documento 1.4 cunha ou varias páxinas A4, coas fontes estándar Courier e
Courier-Bold en codificación WinAnsi, que cobre o galego, o castelán e o símbolo
do euro. Ao ser monoespaciada, aliñar importes é contar caracteres.

**Comparación real**, medida con `pip install --dry-run`:

| Opción | Paquetes | Ademais |
|---|---|---|
| WeasyPrint | 13 | Librarías nativas Pango/GTK en Windows |
| ReportLab | 3 | — |
| **Biblioteca estándar** | **0** | — |

**Custo asumido:** unhas 300 liñas propias. Compénsao que `requirements.txt` non
cambia, que a recuperación nun equipo novo non necesita nada máis e que o
resultado é determinista.

---

## 10. A copia de seguridade usa a API de SQLite

**Problema.** Copiar o arquivo da base «a pelo» mentres a aplicación está aberta
pode producir unha copia inconsistente, a medio escribir.

**Decisión.** Úsase `sqlite3.Connection.backup()`, a API oficial de copia de
SQLite, que dá unha **foto coherente aínda coa base aberta**.

Ademais, a escritura é **atómica**: primeiro escríbese nun temporal da propia
carpeta de destino, cun nome que non parece unha copia, e só ao final se renomea.
Así nunca queda á vista unha copia a medio facer.

O histórico acumúlase: `cafeteria_AAAA-MM-DD_HHMMSS.sqlite`. **Nunca se
sobrescribe nin se borra unha copia anterior.**

---

## 11. Unha copia non se dá por boa ata validala

**Problema.** Unha copia que non se comproba pode estar corrupta sen que ninguén
o saiba ata o día en que faga falla.

**Decisión.** Antes de aceptar unha copia, ábrese e compróbase que existe, que
abre como SQLite, que `PRAGMA integrity_check` devolve `ok` e que están as
táboas esenciais. Se algo falla, bórrase o temporal e avísase.

**E unha limitación que se recoñece:** segundo o propio plan de recuperación do
proxecto, **validar non é restaurar**. Unha copia non se considera
completamente verificada ata que se restaura e se comproba o contido. Esa é unha
fase posterior do proxecto.

Outra decisión relacionada: se a carpeta de destino non existe, **non se crea**.
Unha unidade desconectada non debe converterse nunha carpeta local onde as
copias parecerían estar a salvo sen estalo. Comprobouse co caso real: coa unidade
sen montar, a aplicación falla cunha mensaxe clara e non crea nada.

---

## 12. Alcance deliberadamente pequeno

**Problema.** A tentación de engadir funcionalidades «que xa que estamos».

**Decisión.** Quedan **fóra, a propósito**: tarxetas, API de TPV externo, stock,
provedores, usuarios e roles, mesas, pedidos, cociña, ERP, reservas e execución
na nube.

A pregunta de control que se aplicou a cada engadido foi sempre a mesma:

> *É necesario para rexistrar efectivo, pechar o día ou recuperar o sistema se
> falla o equipo?*

Se a resposta era non, non se implementou.

**Por que isto é unha decisión técnica e non unha renuncia.** Un alcance pequeno
e definido é o que permitiu probar a fondo o que si existe: 263 probas sobre
unha superficie reducida cobren moito máis que esas mesmas probas repartidas
nunha aplicación cinco veces maior.

---

## 13. Decisións menores, pero conscientes

| Decisión | Motivo breve |
|---|---|
| A venda en curso vive na memoria do proceso | Aínda non é unha venda rexistrada. Evita gardar en disco algo que pode cancelarse, e non precisa cookie de sesión nin un segredo no repositorio |
| Unha soa caixa simultánea | É unha cafetería cun mostrador. Dúas lapelas do navegador comparten a mesma venda |
| O día é o día natural de `created_at`, en hora local | O peche é o día da cafetería. Con UTC, unha venda das 23:30 podería caer no día seguinte |
| A pantalla de peche permite pechar hoxe **ou onte** | Para poder facer o peche despois da medianoite sen cambiar a que día pertencen as vendas |
| Migracións idempotentes en cada arranque | Actualizar é abrir a aplicación. Nunca borran datos |
| Un tipo único de IVE do 10 % | Todo o que se rexistra son cafés e bocadillos. Conxélase en cada peche |
