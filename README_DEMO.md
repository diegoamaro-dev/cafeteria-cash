# Cafetería Cash — demostración

Versión de demostración para probar la aplicación en Windows.

> **Todos los datos que verás son ficticios.** El establecimiento, los
> productos y las ventas están inventados. Esta demo no contiene ni utiliza
> ningún dato real.

---

## Requisitos

- **Windows**
- **Python 3.12** instalado y en el `PATH`
  *(al instalarlo, marca la casilla «Add python.exe to PATH»)*
- Conexión a internet **solo la primera vez**, para descargar las
  dependencias

Descárgalo en <https://www.python.org/downloads/>

---

## 1. Instalar

Doble clic en:

```
INSTALAR_DEMO.bat
```

Comprueba que tienes Python, prepara el entorno, instala las dependencias y
crea la base de datos de demostración. Tarda un minuto.

### Aviso de seguridad de Windows

Al descargar el paquete desde internet, Windows puede mostrar un aviso de
seguridad (SmartScreen) al ejecutar los archivos `.bat`.

Ese aviso se debe **a la procedencia del archivo descargado**, no a que la
aplicación instale software adicional ni haga nada fuera de esta carpeta.

Si aparece, comprueba que el paquete procede de la *release* oficial de este
repositorio antes de continuar.

---

## 2. Iniciar

Doble clic en:

```
INICIAR_DEMO.bat
```

Se abre el navegador en **<http://127.0.0.1:5000>**. Si no se abre solo,
escribe esa dirección a mano.

Arriba verás siempre el aviso **MODO DEMOSTRACIÓN — datos ficticios**.

Para detener la aplicación: `Ctrl+C` en la ventana negra, o ciérrala.

> La aplicación **solo es accesible desde este ordenador**. No se publica en
> la red ni en internet.

---

## 3. Qué puedes probar

| Qué | Dónde |
|---|---|
| **Cobrar una venta** | Pulsa productos y dale a *COBRAR EN EFECTIVO* |
| **Corregir un error** | *Historial* → *ANULAR*. La venta no se borra: queda marcada como anulada |
| **Ver cómo va el día** | *Resumen del día* |
| **Cerrar la caja** | *Cierre del día* → *CERRAR DÍA*. No se puede reabrir |
| **Abrir el PDF** | Con el día cerrado, *ABRIR PDF*. Genéralo dos veces: sale idéntico |
| **Copia de seguridad** | Se crea sola al cerrar el día. También a mano desde *Copia de seguridad* |
| **Productos y precios** | *Gestionar productos*. Un producto no se borra: se desactiva |

La demo empieza con **10 productos**, **dos días ya cerrados** y **el día de
hoy abierto**, para que puedas cerrarlo tú.

**Dónde queda cada cosa:**

| | |
|---|---|
| Base de datos | `data\demo.sqlite` |
| Documentos PDF | `exports\` |
| Copias de seguridad | `copias-demo\`, **junto a esta carpeta, no dentro** |

> Las copias se guardan fuera de la carpeta de la aplicación a propósito: en la
> versión real la copia va siempre a un destino externo, y hay una prueba
> automática que comprueba que no quede ninguna copia dentro del proyecto. La
> ventana de inicio te dice la ruta exacta.

---

## 4. Ejecutar las pruebas

La aplicación tiene **263 pruebas automatizadas**. Puedes ejecutarlas todas
desde una ventana de comandos, en esta misma carpeta:

```
.venv\Scripts\python.exe -m unittest discover -s tests
```

Tarda alrededor de un minuto. Para ver el detalle de cada prueba:

```
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

**Resultado esperado en este paquete:**

```
Ran 263 tests
OK (skipped=8)
```

Las 263 pruebas se ejecutan correctamente. Las **8 marcadas como `skipped` no
son fallos**: son comprobaciones que no tienen sentido fuera del repositorio
de desarrollo y que se saltan a propósito.

- **7** se saltan porque esta carpeta no es un repositorio Git. Comprueban que
  no se versionen bases de datos, copias ni datos reales, y necesitan el
  historial de Git para hacerlo.
- **1** se salta porque **no existe ninguna base de datos real**, que es
  justamente lo que se busca: compara los datos reales con lo publicado, y
  aquí no hay datos reales con los que comparar.

Si ejecutas la suite dentro del repositorio completo, esas 8 sí se ejecutan.

> Las pruebas **no tocan** la base de la demo: cada una crea y borra su propia
> base temporal. Puedes ejecutarlas con la aplicación abierta, y también
> después de haber cerrado días o creado copias.

---

## 5. Volver a empezar

Si quieres dejar la demo como estaba:

```
REINICIAR_DEMO.bat
```

Pide confirmación, borra **únicamente** `data\demo.sqlite` y vuelve a crear
los datos ficticios de partida. No toca las copias ni los PDF que hayas
generado.

---

## Qué es esto

Cafetería Cash es una caja registradora para el **efectivo** de una cafetería.
Registra ventas, mantiene un histórico que no se puede falsear, cierra el día
con una cifra definitiva, genera un documento A4 imprimible y hace copias de
seguridad validadas.

Funciona en el propio ordenador, sin necesitar internet para operar.

La documentación completa —arquitectura, modelo de datos, decisiones técnicas,
pruebas y manual de usuario— está en el repositorio del proyecto.
