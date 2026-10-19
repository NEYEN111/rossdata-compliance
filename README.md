# CrossData Compliance

**Sistema de Control de Protección de Datos Transfronterizos** · Prototipo académico para el Caso 7 de Derecho Informático.

AndeClass S.A.C. es una organización ficticia de educación digital peruana, con estudiantes en Perú y España, infraestructura cloud en Estados Unidos y expansión proyectada a México y Colombia. Todos los titulares, proveedores, documentos y evaluaciones del sistema son simulados.

> Evaluación de apoyo. Requiere validación del responsable.

El sistema registra decisiones y sus respaldos. No emite certificaciones jurídicas, no determina automáticamente obligaciones de notificación y no envía comunicaciones externas.

## Instalación y ejecución

Requiere Python 3.10 o posterior. Probado con Python 3.12 en Windows. La primera instalación necesita Internet para descargar paquetes. Bootstrap y Chart.js están incluidos localmente: después de instalar Python y las dependencias, la aplicación no necesita Internet para su interfaz. Los enlaces a fuentes normativas sí requieren conexión.

Desde esta carpeta, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Si `venv` no consigue ejecutar `ensurepip` pero existe pip en Python global:

```powershell
python -m pip --python .venv install -r requirements.txt
```

En Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py
```

Abrir **http://127.0.0.1:5000**. Detener con `Ctrl+C`. No es necesario activar el entorno virtual ni cambiar la política de ejecución de PowerShell.

También puede usarse `iniciar.ps1` en PowerShell o `iniciar.bat` con doble clic, una vez instaladas las dependencias. El lanzador usa Waitress, sin depurador.

La base SQLite se crea automáticamente en `instance/crossdata.db`. El seed solo se ejecuta si no existe la organización inicial: reiniciar **no borra los cambios**. `instance/.secret` conserva la clave de sesión local y está excluida de Git.

### Credenciales demo

| Usuario | Contraseña inicial | Rol |
| --- | --- | --- |
| `admin` | `AndeClass2026!` | Administrador |
| `cumplimiento` | `AndeClass2026!` | Responsable de Cumplimiento |
| `auditor` | `AndeClass2026!` | Auditor |

Administrador: registro, edición, evaluación, configuración y eliminación cuando no existan vínculos. Cumplimiento: registro, edición y evaluación; no elimina ni modifica organización/jurisdicciones. Auditor: lectura, auditoría y exportación. Todos pueden cambiar su propia contraseña desde Configuración. Las contraseñas se almacenan con hash de Werkzeug; nunca se registran en auditoría.

## Estructura

```text
run.py                       Servidor local Waitress
requirements.txt             Dependencias principales fijadas
requirements-lock.txt        Entorno exacto utilizado en las pruebas
crossdata/
  __init__.py                Factory Flask, configuración, CSRF y SQLite
  models.py                  Entidades SQLAlchemy y relaciones
  catalog.py                 Definiciones de formularios, módulos y campos
  services.py                Reglas, evaluación de matriz y métricas
  seed.py                    Caso AndeClass, carga inicial idempotente
  views.py                   Rutas, permisos, validaciones y exportación
  enhancements.py            Revisiones por país, archivos y laboratorio
  assessment.py              Vigencia del contexto y explicación de matriz
  simulator.py               Reglas del ensayo independiente
  legal_reference.py         Listas de revisión y fuentes oficiales
  templates/                 Vistas Jinja2
  static/
    app.css                  Diseño adaptable y estilos de impresión
    app.js                   Navegación móvil y alertas de formularios
    charts.js                Gráficos del dashboard
    vendor/                  Bootstrap 5.3.3 y Chart.js 4.4.8
tests/                       Pruebas con SQLite en memoria
docs/                        Guía de exposición y verificación
instance/                    Base de datos y clave local (no versionadas)
```

## Alcance funcional

- Los módulos originales y el nuevo Laboratorio del Caso 7 están implementados. Controles es un submódulo accesible desde Matriz y desde cada tratamiento.
- Tratamientos, jurisdicciones, transferencias, riesgos, incidentes, derechos, evidencias y controles admiten registro, consulta y edición según el rol.
- Los formularios validan campos, fechas, rangos y claves foráneas. Una evidencia vinculada debe pertenecer al mismo tratamiento y jurisdicción del control, transferencia o solicitud.
- Las evidencias admiten **referencia y archivos PDF, PNG, JPG o TXT de hasta 1 MiB**. Se conserva contenido, autor, fecha y SHA-256. Subir un archivo devuelve su evidencia a «En revisión». Las referencias del seed y los ejemplos de `docs/evidencias_demo/` son ficticios.
- La matriz tiene una fila por tratamiento y jurisdicción vinculada, 11 dimensiones visibles, filtros combinables y exportación CSV que respeta los filtros.
- Estados de matriz: cualquier control negativo o transferencia de alto riesgo produce «No cumple»; solo todas las dimensiones favorables con revisión y evidencia permiten «Cumple»; una evaluación incompleta resulta «Parcial» o «Por verificar». Son estados de apoyo, no juicios jurídicos definitivos.
- Las cuatro dimensiones de control son base/finalidad, transferencia, seguridad y derechos. La fila considera además la evaluación del tratamiento, su base, las transferencias y la evidencia de esa jurisdicción. Cada país incorpora una revisión humana de aplicabilidad, base, condición sensible y finalidad secundaria. Los cambios relevantes de contexto invalidan esa revisión hasta que se actualice.
- Estados Unidos figura inicialmente como receptor cloud en las transferencias. No se le asignan automáticamente obligaciones como jurisdicción de origen; su filtro puede no tener filas hasta que se vincule a un tratamiento. México y Colombia están etiquetados como expansión proyectada.
- Riesgos: probabilidad 1–5 × impacto 1–5. Bajo 1–5, Medio 6–14, Alto 15–19 y Crítico 20–25. Datos sensibles con transferencia internacional elevan el nivel a Alto como mínimo sin alterar la puntuación P × I visible.
- La identificación de «salud» es una regla textual demostrativa, no un clasificador jurídico exhaustivo. También se puede marcar manualmente una categoría sensible.
- El porcentaje del dashboard cuenta controles con estado distinto de «Por verificar», fecha y fundamento; **no es porcentaje de cumplimiento jurídico**. Los estados de matriz se recalculan al consultar, incluso si una evidencia antes validada pasa a pendiente.
- INC-001 contiene 320 titulares ficticios, nombres/correos/salud, configuración incorrecta, proveedor estadounidense y usuarios UE. Se inicia en Contener, con investigación abierta.
- El flujo del incidente conserva notas, actor, hora y evidencias. Exige decisión humana al revisar obligaciones; una revisión pendiente bloquea el avance. Las decisiones sobre autoridad y titulares se registran por país. «Notificar» exige plazo fundamentado y evidencia validada de tipo Notificación para cada país correspondiente. Corregir y Cerrar requieren evidencia validada.
- Las solicitudes respondidas o cerradas requieren respuesta y evidencia validada. Sus plazos son registrados por el responsable, no calculados como conclusión legal.
- Las acciones de creación, modificación, eliminación, sesión y exportación quedan en auditoría. Se almacenan antes/después para los cambios. Fechas de auditoría en UTC, mostradas en Lima; detección del incidente se captura explícitamente en hora de Lima.
- Reportes contiene 10 secciones, motivos de la matriz y decisiones por país; incluye descarga del informe académico fijo de 10 páginas. El reporte de registros se actualiza con la base; el botón Imprimir / Guardar PDF abre la impresión del navegador. CSV disponible para todos los registros, auditoría y matriz, con UTF-8 BOM y neutralización de fórmulas.

## Demostración interactiva

Abrir **Laboratorio del Caso 7**. Los tres escenarios permiten cambiar datos, finalidad y países; las alertas se actualizan al editar. El contador compara revisiones pendientes antes y después de documentarlas con evidencia validada y fundamento. No equivale a un porcentaje de cumplimiento y no modifica la matriz. El ensayo guardado se puede consultar y exportar.

Desde la matriz, seleccionar el estado para ver motivos, controles, responsables, fuentes y revisión por país. En Riesgos, vincular controles del mismo tratamiento y jurisdicción. En INC-001, completar decisiones independientes para cada país antes de continuar el flujo.

El informe académico está en `output/pdf/Informe_Tecnico_Juridico_CrossData.pdf`; su fuente editable es `docs/INFORME_ACADEMICO.md`. Para regenerarlo: `python docs/generar_informe.py` con ReportLab disponible. La aplicación no necesita ReportLab para funcionar ni para descargar el PDF ya incluido.

Al actualizar una demo existente se agregan tablas, vínculos iniciales y una marca de actualización, sin reiniciar el inventario. Se corrigió la hora inicial de detección a las 10:15 de la consigna solo si el incidente demo permanecía sin intervención. Antes de esta actualización se guardó una copia local en `instance/backups/antes-mejoras-2026-10-18.db`.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Las pruebas utilizan una base **en memoria**, separada de la demo local. Cubren todas las rutas GET con registros iniciales, formularios, mutaciones por módulo, tres roles, CSRF, auditoría, reglas de salud/publicidad, integridad de vínculos, cambios de evidencia, filtros y CSV, escape HTML, solicitudes de derechos y flujo del incidente hasta su cierre.

Consulta `docs/VERIFICACION.md` para los resultados de esta entrega y `docs/GUIA_EXPOSICION.md` para un recorrido del Caso 7.

## Referencias para revisión

Fuentes revisadas para la entrega del 18 de octubre de 2026. No se interpretan como certificación de vigencia exhaustiva ni asesoramiento automático:

- Perú: [D.S. 016-2024-JUS, publicación oficial](https://www3.congreso.gob.pe/Docs/DGP/DIDP/files/ds_016-2024-jus.pdf), reglamento de la Ley 29733. El sistema remite a la revisión del artículo 34 y sus condiciones.
- UE: [RGPD en EUR-Lex](https://eur-lex.europa.eu/eli/reg/2016/679/oj?locale=es) y [orientación de AEPD sobre notificación de brechas](https://www.aepd.es/derechos-y-deberes/cumple-tus-deberes/medidas-de-cumplimiento/brechas-de-datos-personales-notificacion).
- México: [Ley Federal de Protección de Datos Personales en Posesión de los Particulares, Cámara de Diputados](https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf). La autoridad se ofrece como campo configurable.
- Colombia: [Ley 1581 de 2012, SIC](https://sedeelectronica.sic.gov.co/transparencia/normativa/ley-estatutaria-1581-de-2012).

## Preparación para despliegue posterior

Para Render se incluye `render.yaml` con plan gratuito, HTTPS, contraseña inicial configurable y comprobación `/healthz`. Ver [docs/DESPLEGAR_RENDER.md](docs/DESPLEGAR_RENDER.md). La demo gratuita usa SQLite efímero: los cambios en línea pueden perderse al reiniciarse o suspenderse la instancia. La base local queda fuera del repositorio.

La factory `crossdata.create_app` y `run:app` permiten desplegar con WSGI. Variables opcionales: `SECRET_KEY`, `DATABASE_URL`, `HOST`, `PORT`, `COOKIE_SECURE=1` (solo con HTTPS). `DATABASE_URL` acepta una URL SQLAlchemy; otros motores necesitan su controlador y migraciones. SQLite es suficiente para la demostración local.

Antes de un entorno real se requiere cambiar credenciales, retirar la exposición de accesos demo, HTTPS, revisión de sesiones y limitación de intentos de acceso, migraciones, copias de seguridad y evaluación de seguridad. La auditoría es de solo lectura en la aplicación, pero no es un registro criptográficamente inmutable frente a alguien con acceso al archivo SQLite. No introducir datos reales en esta demo.

Las bibliotecas incluidas conservan sus avisos de licencia; ver `crossdata/static/vendor/NOTICE.md`.
