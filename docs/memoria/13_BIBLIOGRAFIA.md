<!--
========================= REXISTRO DA MEMORIA =========================
A memoria debe ser levadeira de ler e fácil de defender oralmente.
=======================================================================
-->

<!--
Capítulo redactado.

PENDENTE ANTES DA ENTREGA — notas internas, non visibles para quen le:

1. CONSULTA REAL. A lista reúne as fontes oficiais nas que se apoia unha parte
   identificable do proxecto. Iso NON equivale a afirmar que se consultasen:
   a confirmación corresponde ao autor. As que non se poidan confirmar deben
   retirarse.

2. ESTILO DE CITA. Non se aplicou ningún (APA, IEEE…) ata saber se o centro
   impón un. As entradas están en formato neutro; cando se coñeza o estilo,
   hai que darlles forma de referencia completa (autor, título, versión, URL
   e data de consulta).

Deliberadamente NON se inclúen: o módulo `decimal`, Jinja2, o texto da licenza
MIT, Git e GitHub. Están presentes no proxecto, pero citalos sería inventariar
tecnoloxías, non documentar fontes.
-->

# 13. Bibliografía

Esta lista é curta a propósito. Recolle **só documentación oficial** sobre a
que se apoia unha parte concreta e identificable do proxecto. Non pretende ser
un inventario das tecnoloxías empregadas.

---

## Documentación oficial

| Fonte | En que se apoia |
|---|---|
| **Python — módulo `sqlite3`** | O módulo de copias de seguridade emprega `Connection.backup()`, a API de copia en quente, en lugar de copiar o arquivo. É a base da decisión sobre as copias (capítulo 9) |
| **Python — módulo `unittest`** | Toda a suite de probas está escrita con el. Foi o que permitiu non engadir ningunha ferramenta externa de probas (capítulo 8) |
| **Flask** | Enrutado, plantillas e procesamento de formularios: `Blueprint`, `render_template`, `url_for`, `request`, `redirect` e `Response` (capítulo 4) |
| **SQLite** | Tres aspectos que sosteñen o deseño: o control de transaccións (`BEGIN IMMEDIATE`), as comprobacións de estado e esquema (`PRAGMA integrity_check` e `PRAGMA table_info`) e as restricións de integridade `CHECK` e `UNIQUE` (capítulos 5 e 9) |
| **Especificación do formato PDF 1.4** | O documento do peche escríbese byte a byte, sen librarías: estrutura de obxectos e táboa de referencias cruzadas, fontes estándar Courier e Courier-Bold, e codificación WinAnsi (capítulo 7) |

---

## Nota sobre esta lista

**O proxecto apóiase nestas cinco referencias técnicas**, cada unha nun punto
concreto. Non se enumeran aquí as demais bibliotecas e ferramentas
empregadas, que figuran no arquivo de dependencias do repositorio.

O caso máis evidente é a especificación do PDF: a estrutura interna dun
documento escrito a man —e en particular a súa táboa de referencias cruzadas—
non se pode construír sen ela.
