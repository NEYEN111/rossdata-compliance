# Verificación de la entrega

Fecha: 18 de octubre de 2026. Flask, SQLAlchemy, SQLite y Waitress, en Windows.

## Pruebas automatizadas

Comando final: `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider`

Resultado: **30 passed in 51.79s**. SQLite en memoria, sin alterar el incidente de la demo local. Se mantuvieron las comprobaciones originales y se ampliaron para las funciones interactivas.

- Tres roles, sesiones, CSRF, restricciones de escritura y auditoría.
- Formularios, fechas, relaciones, salud, nueva finalidad y transferencias.
- Matriz, filtros, cambios de evidencia, CSV y escape HTML/fórmulas.
- Flujo completo del incidente con revisión y evidencia de notificación por país.
- Revisión de aplicabilidad, condición sensible y fundamento por jurisdicción.
- Invalidación de revisiones cuando cambia el contexto del tratamiento o incidente.
- Simulador: reglas, datos inválidos, evidencia del ámbito correcto y separación de la matriz real.
- Guardado de ensayo, exportación y permisos del auditor.
- Adjuntos: descarga, hash, rechazo de contenido/tamaño y retorno a En revisión.
- Vínculos riesgo-control restringidos al mismo tratamiento y país.

La primera ejecución también pasó las 30 pruebas, pero pytest advirtió que no podía escribir su caché. La ejecución final deshabilitó únicamente esa caché y terminó sin advertencias.

Comprobación adicional con cliente Flask aislado: reporte HTML 200 con explicación, PDF 200 con firma `%PDF`, CSV con motivos, revisor y fuente. No se requirieron cambios a los datos de usuario para estas pruebas.

## Revisión en navegador

- Inicio de sesión, dashboard y navegación al Laboratorio del Caso 7.
- Escenario salud/publicidad: alertas de categoría sensible, nueva finalidad, transferencia y alcance europeo.
- Uso académico: contador inicial 2; revisión con evidencia y fundamento: 0 pendientes en el ensayo.
- Guardado confirmado de la comparación de ejemplo, independiente de la matriz.
- Matriz explicada de Bienestar / España: motivos, enlaces de acción, riesgo-control-evidencia y revisión por país.
- Laboratorio móvil a 390 x 844: ancho del documento igual al visible; sin desbordamiento horizontal.
- Consola consultada sin errores ni advertencias durante estas interacciones.
- Capturas en `docs/capturas/`.

El servidor se reinició con los cambios finales y se dejó en http://127.0.0.1:5000.

## Informe académico

PDF de 10 páginas creado con ReportLab. Se renderizaron las 10 páginas con Poppler; se inspeccionó la lámina de conjunto y las páginas de tablas y del incidente en detalle. Sin cortes, solapamientos ni caracteres ilegibles observados. Fuentes oficiales enlazadas dentro del documento.

Fuente editable: `docs/INFORME_ACADEMICO.md`. Generador: `docs/generar_informe.py`. Salida: `output/pdf/Informe_Tecnico_Juridico_CrossData.pdf`.

## Persistencia y límites

Se guardó una copia previa de SQLite en `instance/backups/antes-mejoras-2026-10-18.db`. La actualización añade tablas y vínculos, no reinicia el inventario ni el incidente. Se ajustó la hora demo de detección a las 10:15 de la consigna cuando el registro no tenía intervención.

No se enviaron notificaciones, no se cargaron datos personales reales ni se publicó la aplicación en Internet. Las plantillas de evidencia son ejercicios ficticios y no acreditan actuaciones reales. Estas pruebas no constituyen una auditoría de seguridad ni una validación jurídica.
