# Publicar CrossData en Render

Configuración preparada el 19 de octubre de 2026 para la demostración académica.

## Configuración incluida

`render.yaml` define un Web Service Python con plan **free**, instalación mediante `pip install -r requirements.txt` y arranque `python run.py`. `.python-version` selecciona Python 3.12. El servidor escucha en `0.0.0.0` y usa el puerto asignado por Render. `/healthz` comprueba la conexión a la base y responde sin exponer datos.

Render genera `SECRET_KEY`. Durante la creación del Blueprint se solicita **DEMO_PASSWORD**: elige una contraseña de al menos 12 caracteres y guárdala. Se usa para los tres usuarios iniciales: `admin`, `cumplimiento` y `auditor`. No se muestra en la página. Las sesiones usan cookies Secure para HTTPS.

## Pasos

1. Subir el contenido del proyecto a `https://github.com/NEYEN111/rossdata-compliance`, con `render.yaml`, `run.py` y `requirements.txt` en la raíz.
2. Comprobar que los archivos aparecen en la rama del repositorio que se va a desplegar.
3. En Render: **New > Blueprint**, seleccionar el repositorio y la rama. Si falta acceso a GitHub, conectar la cuenta propietaria.
4. Revisar que solo se crea un servicio y que su plan indica **Free**. Introducir `DEMO_PASSWORD` y aplicar.
5. Esperar al estado Live. Abrir la URL que Render muestra; entrar con `cumplimiento` y la contraseña elegida.
6. Comprobar laboratorio, matriz, incidente de 320 titulares, descarga del informe y exportación CSV.

## Datos de la demo gratuita

El despliegue usa SQLite local. En Render Free, los cambios se pierden cuando se recrea, reinicia o suspende la instancia; al volver a arrancar se genera nuevamente el caso ficticio. Exportar las comparaciones y reportes antes de salir. La copia local del proyecto y su base conservan su funcionamiento habitual.

El servicio gratuito se suspende tras un periodo sin tráfico y puede tardar en responder al primer acceso. Abrirlo antes de la exposición. No hay tareas que lo mantengan despierto artificialmente.

Para conservar datos de forma duradera se requiere configurar almacenamiento persistente o una base externa; esa ampliación no está incluida en este Blueprint gratuito. No se crea ningún disco ni servicio de pago.

## Qué se sube al repositorio

Código, bibliotecas locales de interfaz, documentación, pruebas, informe PDF y configuración. La base local, la clave de sesión, el entorno `.venv`, archivos `.env` y ZIP de distribución quedan excluidos. El despliegue inicia con el caso de demostración incluido en el código, sin importar datos ni contraseñas de la base local.

## Contraseñas y cambios posteriores

`DEMO_PASSWORD` se utiliza solo cuando se crea la base. Cambiar esta variable no modifica cuentas ya existentes. En la demo efímera se aplicará cuando Render genere una base nueva. La contraseña también puede cambiarse desde Configuración con una sesión válida, pero en esta modalidad el cambio no tiene conservación garantizada.

## Verificación de esta preparación

Las pruebas del proyecto comprueban las credenciales de despliegue, las cookies HTTPS, el aviso de pérdida de cambios y el estado de salud. Validar `render.yaml` con `render blueprints validate render.yaml` si la CLI está disponible; la comprobación de esquema no equivale a un despliegue confirmado. El enlace final solo puede comunicarse después de que Render cree el servicio y lo marque Live.

Fuentes: [Blueprints](https://render.com/docs/blueprint-spec), [servicios web](https://render.com/docs/web-services), [plan gratuito](https://render.com/docs/free) y [versiones de Python](https://render.com/docs/python-version).
