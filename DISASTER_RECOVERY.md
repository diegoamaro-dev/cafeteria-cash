# Recuperación ante fallo

Como recuperar **Cafetería Cash** se o equipo se perde, rompe, se formatea ou
queda inutilizable.

---

## Principio

**O equipo é substituíble.** A recuperación non depende del, senón de dúas
cousas que viven fóra:

1. o **repositorio de código**;
2. a **última copia de seguridade válida** dos datos.

Son dúas vías independentes a propósito: o código recupérase do repositorio e
os datos das copias. Se falla unha, a outra segue servindo.

---

## Que vive en cada sitio

| No repositorio | Fóra do repositorio |
|---|---|
| Código | A base de datos real |
| Documentación | As copias de seguridade |
| `requirements.txt` | Os datos de vendas |
| Scripts de instalación e arranque | Calquera segredo |
| Esquema e migracións | |

Esta separación é unha regra, non unha casualidade: **a base real e as copias
nunca se versionan**.

---

## Onde debe estar a copia

Debe existir **polo menos unha copia válida fóra do equipo**. Vale calquera
destino que non dependa del:

- memoria USB;
- NAS ou servidor local;
- carpeta sincronizada cunha nube;
- unidade externa.

A carpeta de destino configúrase na variable de entorno
`CAFETERIA_BACKUP_DIR`, que neste documento se escribe como
`<CARPETA_DE_BACKUP>`. A aplicación **non crea esa carpeta**: se non está
dispoñible, avisa e non crea ningunha copia, para que unha unidade desconectada
non se converta nunha carpeta local onde as copias parecerían estar a salvo sen
estalo.

---

## Recuperación desde cero

```
equipo novo → clonar → instalar → restaurar a copia → arrancar → verificar
```

1. preparar outro equipo;
2. instalar **Git** e **Python 3.12**;
3. clonar o repositorio;
4. executar `scripts\install.ps1`, que crea o contorno virtual e instala as
   dependencias fixadas en `requirements.txt`;
5. arrancar a aplicación baleira con `scripts\start.ps1` e comprobar que abre;
6. escoller a última copia válida de `<CARPETA_DE_BACKUP>`;
7. restaurar, poñendo ese arquivo como base de datos da aplicación;
8. comprobar produtos, últimas vendas, peches e **numeración correlativa**;
9. rexenerar un PDF antigo e comparalo co orixinal;
10. continuar a operación normal.

---

## Estado real deste procedemento

Convén ser preciso sobre o que está probado e o que non:

| Paso | Estado |
|---|---|
| Creación da copia | **Implementado e probado.** Úsase a API oficial de copia de SQLite, a escritura é atómica e a copia valídase antes de darse por boa |
| Validación da copia | **Implementado e probado.** Compróbase que abre como SQLite, que `PRAGMA integrity_check` devolve `ok` e que están as táboas esenciais |
| Copia fóra do equipo | **Comprobado manualmente** nunha carpeta sincronizada |
| **Restauración** | **Non implementada na aplicación.** É un procedemento manual: substituír o arquivo da base pola copia |
| **Verificación tras restaurar** | **Non realizada aínda** |

**A regra que se aplica:** unha copia que nunca se restaurou **non se considera
verificada**. Validala non é restaurala. Mentres non se complete unha
restauración real e se comprobe o contido, este plan é un procedemento
documentado, non un procedemento demostrado.

Antes de substituír unha base existente por unha copia, **crear primeiro unha
copia preventiva da que hai**.

---

## RPO — canto se pode perder

A perda máxima aceptable é o traballo posterior á última copia.

Coa copia creada **ao pechar o día**, o peor caso é perder o día en curso. Para
reducilo, pódese crear unha copia manual en calquera momento desde a pantalla
de copia de seguridade.

---

## RTO — canto se tarda

Obxectivo: **menos dunha hora**, sempre que se cumpran tres condicións:

- o repositorio é accesible;
- existe unha copia válida;
- hai conexión para instalar as dependencias.

É un obxectivo estimado a partir dos pasos descritos, non un tempo medido nun
simulacro real.
