"""Declarative form definitions shared by validation, forms and exports."""
from .models import Jurisdiction, Treatment, Transfer, Risk, Evidence, RightRequest, Control, Incident

STATES = ['Cumple', 'Parcial', 'No cumple', 'Por verificar']
STAGES = ['Detectar', 'Contener', 'Evaluar', 'Registrar', 'Revisar obligaciones', 'Notificar si corresponde', 'Corregir', 'Cerrar']
DOMAINS = ['Base y finalidad', 'Transferencia', 'Seguridad', 'Derechos']

def f(key, label, kind='text', required=True, choices=None):
    return dict(key=key, label=label, kind=kind, required=required, choices=choices or [])

TR = f('treatment_id', 'Tratamiento asociado', 'treatment')
JU = f('jurisdiction_id', 'Jurisdicción', 'jurisdiction')
EV = f('evidence_id', 'Evidencia vinculada', 'evidence', False)
OWNER = f('owner', 'Responsable')
STATUS = f('status', 'Evaluación registrada', 'select', choices=STATES)

CATALOG = {
    'tratamientos': dict(model=Treatment, title='Tratamientos de datos', singular='tratamiento', description='De cada dato a su finalidad, base y controles asociados.', fields=[
        f('name','Nombre del tratamiento'), OWNER, f('data_type','Tipos de datos'),
        f('category','Categoría','select', choices=['Personal','Especial / sensible']),
        f('sensitive','¿Contiene datos sensibles?','bool',False),
        f('jurisdictions','Jurisdicciones involucradas','countries'),
        f('purpose','Finalidad original','textarea'), f('secondary_purpose','Finalidad secundaria','textarea',False),
        f('legal_basis','Base jurídica / autorización','textarea',False), f('origin','Origen de los datos'),
        f('system','Sistema'), f('provider','Encargado / proveedor'), f('storage_country','País de almacenamiento'),
        f('retention','Tiempo de conservación'), STATUS, f('notes','Observaciones','textarea',False)],
        columns=[('name','Tratamiento'),('data_type','Datos tratados'),('purpose','Finalidad'),('owner','Responsable'),('status','Evaluación')]),
    'jurisdicciones': dict(model=Jurisdiction, title='Jurisdicciones', singular='jurisdicción', description='Referencias normativas para revisión y alcance de la operación.', fields=[
        f('name','País / jurisdicción'),f('code','Código de país'),f('framework','Marco normativo de referencia','textarea'),
        f('authority','Autoridad / institución vigente (configurable)'),
        f('scope','Alcance','select',choices=['Operación actual','Receptor cloud','Expansión proyectada']),
        f('source','Fuente oficial','url'), f('notes','Notas de revisión','textarea',False)],
        columns=[('name','Jurisdicción'),('framework','Marco normativo'),('authority','Autoridad'),('scope','Alcance')]),
    'transferencias': dict(model=Transfer, title='Transferencias internacionales', singular='transferencia', description='Trazabilidad del dato desde el origen hasta el proveedor receptor.', fields=[
        TR, f('jurisdiction_id','País de origen','jurisdiction'),f('destination_id','País de destino','jurisdiction'),
        f('data_type','Categoría / tipos de datos'),f('exporter','Responsable exportador'),f('importer','Receptor / importador'),
        f('provider','Proveedor'), f('purpose','Finalidad','textarea'),f('mechanism','Mecanismo o garantía','textarea',False),
        f('contract','Contrato / referencia',required=False),f('security','Medidas de seguridad','textarea',False),
        f('review_date','Fecha de revisión','date',False),f('reviewer','Responsable de revisión',required=False),EV,
        f('status','Estado','select',choices=STATES+['Alto riesgo'])],
        columns=[('treatment','Tratamiento'),('jurisdiction','Origen'),('destination','Destino'),('mechanism','Mecanismo'),('status','Estado')]),
    'riesgos': dict(model=Risk, title='Riesgos', singular='riesgo', description='Priorización demostrativa por probabilidad e impacto; sujeta a revisión.', fields=[
        f('name','Descripción del riesgo'),TR,JU,f('probability','Probabilidad (1–5)','score'),f('impact','Impacto (1–5)','score'),
        f('proposed_control','Control propuesto','textarea'),OWNER,f('due_date','Fecha límite','date'),
        f('status','Estado','select',choices=['Abierto','En mitigación','Mitigado'])],
        columns=[('name','Riesgo'),('treatment','Tratamiento'),('level','Nivel'),('score','P × I'),('owner','Responsable'),('status','Estado')]),
    'incidentes': dict(model=Incident, title='Incidentes', singular='incidente', description='Documentar, contener y evaluar el impacto sobre los titulares.', fields=[
        f('code','Código único'),f('name','Descripción'),TR,f('detected_at','Detección (hora de Lima, UTC−5)','datetime-local'),OWNER,
        f('data_type','Datos comprometidos'),f('affected','Titulares afectados','number'),
        f('sensitive','¿Incluye datos sensibles?','bool',False),f('eu_users','¿Incluye usuarios de la UE?','bool',False),
        f('countries','Países afectados'),f('provider_country','País del proveedor'),f('cause','Origen / causa','textarea'),
        f('consequences','Posibles consecuencias','textarea',False),f('containment','Acciones de contención','textarea',False)],
        columns=[('code','Código'),('name','Incidente'),('affected','Afectados'),('level','Nivel'),('status','Estado')]),
    'derechos': dict(model=RightRequest, title='Derechos de los titulares', singular='solicitud', description='Solicitudes, plazos revisados y evidencia de la respuesta.', fields=[
        f('name','Titular (usar identificador ficticio)'),TR,JU,
        f('kind','Derecho solicitado','select',choices=['Acceso','Rectificación','Cancelación / eliminación','Oposición','Portabilidad','Limitación','Otro derecho aplicable']),
        f('date','Fecha de recepción','date'),OWNER,f('due_date','Plazo revisado por el responsable','date'),
        f('status','Estado','select',choices=['Recibida','En evaluación','Respondida','Cerrada']),
        f('response','Respuesta / fundamento','textarea',False),EV],
        columns=[('name','Titular'),('kind','Derecho'),('jurisdiction','Jurisdicción'),('due_date','Plazo'),('status','Estado')]),
    'evidencias': dict(model=Evidence, title='Evidencias', singular='evidencia', description='Referencias documentales que respaldan cada control registrado.', fields=[
        f('name','Nombre de la evidencia'),f('kind','Tipo','select',choices=['Política de privacidad','Consentimiento','Contrato con proveedor','Cláusula contractual','Evaluación de impacto','Captura de configuración','Log','Auditoría','Procedimiento','Notificación','Informe']),
        f('date','Fecha','date'),OWNER,TR,JU,
        f('status','Estado documental','select',choices=['Pendiente','En revisión','Validada']),
        f('reference','Referencia documental / URL (ficticia)','textarea',False)],
        columns=[('name','Evidencia'),('kind','Tipo'),('treatment','Tratamiento'),('jurisdiction','Jurisdicción'),('status','Estado')]),
    'controles': dict(model=Control, title='Controles y evaluación', singular='control', description='Una evaluación humana, con fundamento y evidencia vinculada.', fields=[
        f('name','Control'),TR,JU,f('domain','Dimensión','select',choices=DOMAINS),OWNER,STATUS,EV,
        f('reviewed_at','Fecha de revisión','date',False),f('rationale','Fundamento de la evaluación','textarea',False)],
        columns=[('name','Control'),('treatment','Tratamiento'),('jurisdiction','País'),('domain','Dimensión'),('status','Evaluación')]),
}

NAV = [
    ('dashboard','Dashboard','dashboard'), ('simulador','Laboratorio del Caso 7','globe'), ('tratamientos','Tratamientos de datos','database'),
    ('jurisdicciones','Jurisdicciones','globe'), ('transferencias','Transferencias','arrows'),
    ('matriz','Matriz de cumplimiento','grid'), ('riesgos','Riesgos','alert'), ('incidentes','Incidentes','shield'),
    ('derechos','Derechos','users'), ('evidencias','Evidencias','file'), ('auditoria','Auditoría','clock'),
    ('reportes','Reportes','chart'), ('configuracion','Configuración','settings'),
]
