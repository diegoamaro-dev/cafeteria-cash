# Requisitos

Especificación de requisitos de **Cafetería Cash**. Recolle o que a aplicación
debe facer, as restricións que acepta e os límites que se fixaron a propósito.

---

## Alcance

Aplicación local para rexistrar **exclusivamente vendas en efectivo**.

Os pagamentos con tarxeta xestiónanse por separado cun TPV externo e quedan
**fóra** desta ferramenta.

---

## Pantalla principal

Botóns grandes de produto, con nome e prezo.

Exemplos: café, café con leite, auga, refresco, bocadillo, tostada.

---

## Venda actual

Debe mostrar, por cada liña:

- produto;
- cantidade;
- prezo unitario;
- subtotal;

e, para o conxunto, o **total**.

Controis:

- **+** engadir unha unidade;
- **−** quitar unha unidade;
- eliminar a liña enteira antes de confirmar;
- cancelar a venda;
- **COBRAR EN EFECTIVO**.

---

## Confirmar a venda

Ao cobrar:

1. validar que hai produtos;
2. gardar a venda;
3. asignar un número correlativo;
4. gardar data e hora;
5. gardar as liñas;
6. baleirar a venda actual;
7. mostrar a confirmación.

Non fai falla imprimir un tícket individual na versión 1.

---

## Produtos

Debe permitir:

- crear;
- editar o nome;
- editar o prezo;
- activar e desactivar;
- opcionalmente, reordenar.

**Non se eliminan produtos con histórico.**

---

## Histórico e anulacións

Debe mostrar hora, número de venda, importe e estado.

Estados: **válida** e **anulada**.

**Unha venda confirmada non se borra nunca.**

---

## Resumo diario

- número de vendas válidas;
- total en efectivo;
- número de anulacións;
- total anulado;
- unidades por produto.

---

## Peche diario

Botón **CERRAR DÍA**. Debe:

1. mostrar unha previsualización;
2. pedir confirmación;
3. crear o rexistro de peche;
4. xerar o PDF;
5. gardar o PDF;
6. crear a copia de seguridade;
7. confirmar que a copia é correcta.

---

## PDF

A4, simple e lexible. Debe incluír:

- data;
- número de peche;
- hora;
- primeira e última venda;
- número de vendas válidas;
- número de anulacións;
- táboa por produto;
- total bruto;
- total anulado;
- total efectivo válido.

---

## Persistencia

SQLite local.

Táboas mínimas: `Product`, `Sale`, `SaleItem`, `DailyClose`.

---

## Copia de seguridade

- automática ao pechar o día;
- manual;
- carpeta de destino configurable;
- nome con data e hora;
- consérvanse varias copias;
- a copia vai fóra do equipo.

Exemplo de nome: `cafeteria_2026-12-18_221530.sqlite`

---

## Restauración

Fluxo previsto:

```
instalar a aplicación limpa → escoller unha copia → restaurar → arrancar
```

Debe comprobar:

- que o arquivo é un SQLite válido;
- que están as táboas esperadas;
- que o esquema é compatible;
- que a restauración remata sen erro.

Antes de substituír unha base existente, **crear unha copia preventiva**.

---

## Recuperación total

Debe ser posible recuperar todo usando unicamente:

- acceso ao repositorio de código;
- a última copia de seguridade válida;
- Python, Git e ferramentas básicas.

---

## Seguridade mínima

- só `localhost`;
- non expoñer a internet;
- non almacenar datos de tarxetas;
- non gardar credenciais do TPV externo de tarxetas;
- **non versionar a base real nin as copias de seguridade**.

---

## Criterio de terminado

A versión 1 está terminada cando se pode:

| # | Debe poderse… | Estado |
|---:|---|---|
| 1 | arrancar a aplicación | ✅ |
| 2 | rexistrar vendas | ✅ |
| 3 | anular erros | ✅ |
| 4 | ver o total do día | ✅ |
| 5 | pechar o día | ✅ |
| 6 | xerar o PDF | ✅ |
| 7 | imprimir | ✅ |
| 8 | consultar o histórico | ✅ |
| 9 | crear unha copia de seguridade | ✅ |
| 10 | instalar desde o repositorio nun equipo limpo | ✅ |
| 11 | restaurar unha copia de seguridade | **pendente** |
| 12 | comprobar os datos recuperados | **pendente** |

Os puntos **11 e 12 aínda non están implementados**. O estado real do ciclo de
copia e restauración é este:

| Parte | Estado |
|---|---|
| Creación da copia de seguridade | **Completada** |
| Validación da copia | **Completada** |
| Copia fóra do equipo | **Comprobada** |
| **Restauración** | **Pendente** |
| **Verificación tras restaurar** | **Pendente** |

A copia créase e valídase automaticamente, e comprobouse que chega fóra do
equipo. Pero a restauración segue sendo un **procedemento manual** descrito en
[DISASTER_RECOVERY.md](DISASTER_RECOVERY.md), non unha función da aplicación.
Mentres non se restaure e se comprobe o contido, **unha copia non se considera
completamente verificada**.
