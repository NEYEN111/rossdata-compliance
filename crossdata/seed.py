"""Idempotent, fictional academic case. Never resets an existing database."""
from werkzeug.security import generate_password_hash
from flask import current_app
from .models import db, User, Organization, Jurisdiction, Treatment, Transfer, Evidence, Risk, Control, Incident, IncidentEvent, RightRequest, Audit
from .catalog import DOMAINS

def seed_demo():
    if db.session.get(Organization, 1):
        return
    db.session.add(Organization(id=1,name='AndeClass S.A.C.',country='Perú',sector='Educación digital',reviewer='Equipo de cumplimiento demo'))
    for username, role in [('admin','Administrador'),('cumplimiento','Responsable de Cumplimiento'),('auditor','Auditor')]:
        db.session.add(User(username=username,role=role,password_hash=generate_password_hash(current_app.config['DEMO_PASSWORD'])))
    specs = [
        ('Perú','PE','Ley 29733 y D.S. 016-2024-JUS','ANPD','Operación actual','https://www.gob.pe/institucion/smv/normas-legales/6426760-016-2024-jus','Referencia para revisión. Verificar ámbito, condiciones y obligaciones aplicables.'),
        ('España / UE','ES','Reglamento General de Protección de Datos (RGPD)','AEPD','Operación actual','https://eur-lex.europa.eu/eli/reg/2016/679/oj?locale=es','Revisar bases del artículo 6, condiciones del artículo 9 y transferencias del capítulo V.'),
        ('Estados Unidos','US','País receptor / proveedor cloud','Identificar según contexto y sector','Receptor cloud','https://www.dataprivacyframework.gov/','No se presume adecuación. Identificar mecanismo y comprobar su aplicabilidad al receptor concreto.'),
        ('México','MX','Ley Federal de Protección de Datos Personales en Posesión de los Particulares','Secretaría Anticorrupción y Buen Gobierno — verificar competencia vigente','Expansión proyectada','https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf','Autoridad configurable. Revisar el marco vigente antes de iniciar operaciones.'),
        ('Colombia','CO','Ley 1581 de 2012','SIC — Delegatura de Protección de Datos','Expansión proyectada','https://sedeelectronica.sic.gov.co/transparencia/normativa/ley-estatutaria-1581-de-2012','Revisar régimen de autorización y diferencias entre transferencia y transmisión.'),
    ]
    countries = []
    for name, code, framework, authority, scope, source, notes in specs:
        j = Jurisdiction(name=name,code=code,framework=framework,authority=authority,scope=scope,source=source,notes=notes)
        db.session.add(j)
        countries.append(j)
    db.session.flush()
    pe, es, us, mx, co = countries
    treatments = []
    data = [
        ('Registro académico','Nombres, correos, DNI/pasaporte, historial académico','Gestión de matrícula y aprendizaje','', 'Relación contractual; alcance y necesidad sujetos a revisión','24 meses tras finalizar el servicio','Cumple',[pe,es]),
        ('Bienestar estudiantil','Nombres, correos, salud','Acompañamiento del bienestar estudiantil','', 'Consentimiento explícito específico: pendiente de validación','12 meses; justificar necesidad','Parcial',[pe,es]),
        ('Analítica','Ubicación aproximada, historial académico','Mejora de la experiencia educativa','', 'Por verificar','6 meses','Por verificar',[pe,es,mx,co]),
        ('Publicidad','Correos, salud','Comunicación educativa','Publicidad personalizada','Consentimiento genérico; revisar nueva finalidad','Por definir','No cumple',[pe,es]),
        ('Sistema de recomendaciones','Historial académico, ubicación aproximada','Recomendar contenidos educativos','', 'Autorización específica: pendiente de revisión','12 meses','Parcial',[pe,es,mx,co]),
    ]
    for name, types, purpose, secondary, base, retention, status, js in data:
        health = 'salud' in types
        t = Treatment(name=name,owner='Equipo académico demo',data_type=types,category='Especial / sensible' if health else 'Personal',sensitive=health,
            purpose=purpose,secondary_purpose=secondary,legal_basis=base,origin='Formulario de estudiantes ficticios',system='AndeClass Campus Demo',
            provider='Cloud Provider Demo',storage_country='Estados Unidos',retention=retention,status=status,jurisdictions=js,
            notes='Caso académico 7. Registros y documentos simulados; expansión a México y Colombia aún proyectada.')
        db.session.add(t)
        treatments.append(t)
    db.session.flush()
    evidences = []
    for idx, (name, kind, ti, ji, status, reference) in enumerate([
        ('Política de privacidad · v1 demo','Política de privacidad',0,0,'Validada','DEMO-POL-001 · Documento ficticio revisado para el ejercicio'),
        ('Registro de revisión de controles · ES','Auditoría',0,1,'Validada','DEMO-AUD-002 · Evaluación académica simulada'),
        ('Consentimiento de bienestar','Consentimiento',1,0,'En revisión','DEMO-CONS-003 · Borrador específico para revisión'),
        ('Garantía contractual del proveedor','Cláusula contractual',1,1,'Pendiente',''),
        ('Captura del bloqueo de acceso público','Captura de configuración',1,0,'Validada','DEMO-INC-005 · Referencia simulada a configuración privada'),
        ('Evaluación de impacto de analítica','Evaluación de impacto',2,0,'Pendiente',''),
        ('Autorización de nueva finalidad','Consentimiento',3,0,'Pendiente',''),
        ('Política de conservación','Procedimiento',4,0,'En revisión','DEMO-RET-008 · Borrador ficticio'),
    ]):
        e = Evidence(name=name,kind=kind,treatment_id=treatments[ti].id,jurisdiction_id=countries[ji].id,date='2026-10-15',owner='Cumplimiento demo',status=status,reference=reference)
        db.session.add(e)
        evidences.append(e)
    db.session.flush()
    for ti, ji, mechanism, status, ei in [(0,0,'Garantía contractual demo, revisada solo para el ejercicio','Cumple',0),(0,1,'Cláusulas contractuales demo; evaluación académica registrada','Cumple',1),(1,0,'Por verificar','Alto riesgo',None),(1,1,'Por verificar','Alto riesgo',None),(2,0,'Por verificar','Por verificar',None),(4,1,'Borrador contractual en revisión','Parcial',None)]:
        db.session.add(Transfer(treatment_id=treatments[ti].id,jurisdiction_id=countries[ji].id,destination_id=us.id,
            data_type=treatments[ti].data_type,exporter='AndeClass S.A.C.',importer='Cloud Provider Demo LLC (ficticio)',provider='Cloud Provider Demo',
            purpose=treatments[ti].purpose,mechanism=mechanism,contract='DEMO-CTR-001' if ei is not None else '',
            security='Cifrado en tránsito, control de acceso y registros; verificar implementación',review_date='2026-10-15' if ei is not None else '',
            reviewer='Cumplimiento demo' if ei is not None else '',evidence_id=evidences[ei].id if ei is not None else None,status=status))
    for ti, t in enumerate(treatments):
        for j in t.jurisdictions:
            for di, domain in enumerate(DOMAINS):
                state = 'Cumple' if ti == 0 else 'No cumple' if ti == 3 and di == 0 else 'Parcial' if ti in (1,4) and di in (0,2) and j.id in (pe.id,es.id) else 'Por verificar'
                ev = evidences[0 if j.id == pe.id else 1] if ti == 0 else None
                db.session.add(Control(name={'Base y finalidad':'Validar base y compatibilidad de finalidad','Transferencia':'Revisar mecanismo y contrato internacional','Seguridad':'Verificar acceso mínimo y cifrado','Derechos':'Verificar canal y respuesta a titulares'}[domain],
                    treatment_id=t.id,jurisdiction_id=j.id,domain=domain,owner='Cumplimiento demo',status=state,evidence_id=ev.id if ev else None,
                    reviewed_at='2026-10-15' if state != 'Por verificar' else '',rationale='Evaluación simulada del Caso 7; requiere validación del responsable.' if state != 'Por verificar' else ''))
    for name, ti, ji, p, i, control in [
        ('Exposición de datos de salud',1,0,4,5,'Bloquear acceso público y revisar permisos'),
        ('Uso secundario para publicidad',3,1,4,5,'Suspender reutilización y revisar finalidad y autorización'),
        ('Transferencia internacional sin garantía validada',1,1,3,5,'Validar mecanismo, contrato y evaluación del receptor'),
        ('Consentimiento genérico',3,0,3,4,'Separar finalidades y autorización específica'),
        ('Conservación excesiva',0,0,2,3,'Definir plazos y borrado verificable'),
        ('Falta de evidencias',2,0,3,3,'Completar registro de controles y referencias documentales'),
        ('Acceso no autorizado',4,1,3,5,'Aplicar mínimo privilegio y revisar logs'),
    ]:
        db.session.add(Risk(name=name,treatment_id=treatments[ti].id,jurisdiction_id=countries[ji].id,probability=p,impact=i,proposed_control=control,owner='Seguridad demo',due_date='2026-10-22',status='Abierto'))
    incident = Incident(code='INC-001',name='Archivo de prueba visible en Internet',treatment_id=treatments[1].id,detected_at='2026-10-15T10:15',owner='Equipo de respuesta demo',data_type='Nombres, correos, salud',affected=320,sensitive=True,eu_users=True,countries='Perú, España / UE',provider_country='Estados Unidos',cause='Configuración incorrecta de acceso al almacenamiento cloud',consequences='Posible exposición de información de salud; evaluar riesgo de discriminación y pérdida de confidencialidad.',containment='Acceso público bloqueado en el escenario simulado; verificar réplicas y enlaces.',status='En investigación',level='Crítico',stage=1)
    db.session.add(incident)
    db.session.flush()
    db.session.add(IncidentEvent(incident_id=incident.id,stage=0,note='Detección simulada. Archivo expuesto durante unas horas; 320 titulares ficticios.',actor='Sistema demo'))
    db.session.add(IncidentEvent(incident_id=incident.id,stage=1,note='Bloqueo inicial del acceso público. Pendiente verificar efectividad y alcance.',evidence_id=evidences[4].id,actor='Sistema demo'))
    for name, kind, ti, ji, due in [('Titular ficticio A-001','Acceso',0,0,'2026-10-27'),('Titular ficticio A-002','Cancelación / eliminación',1,1,'2026-11-12'),('Titular ficticio A-003','Oposición',3,0,'2026-10-28')]:
        db.session.add(RightRequest(name=name,kind=kind,treatment_id=treatments[ti].id,jurisdiction_id=countries[ji].id,date='2026-10-15',owner='Atención demo',due_date=due,status='Recibida',response='Plazo de demostración: requiere revisión de aplicabilidad.'))
    db.session.add(Audit(actor='Sistema demo',action='Carga inicial',module='Caso AndeClass',after='Datos ficticios del Caso 7. Sin personas reales.'))
    db.session.commit()

def seed_interactive_links():
    """One-time additive demo links. Never records a legal review on behalf of a person."""
    from .models import RiskControl
    from .services import snapshot
    if Audit.query.filter_by(module='Actualización interactiva').first(): return
    mapping={'Exposición de datos de salud':'Seguridad','Uso secundario para publicidad':'Base y finalidad',
        'Transferencia internacional sin garantía validada':'Transferencia','Consentimiento genérico':'Base y finalidad',
        'Conservación excesiva':'Seguridad','Falta de evidencias':'Base y finalidad','Acceso no autorizado':'Seguridad'}
    for risk in Risk.query.all():
        domain=mapping.get(risk.name)
        if not domain: continue
        control=Control.query.filter_by(treatment_id=risk.treatment_id,jurisdiction_id=risk.jurisdiction_id,domain=domain).first()
        if control and not RiskControl.query.filter_by(risk_id=risk.id,control_id=control.id).first():
            db.session.add(RiskControl(risk_id=risk.id,control_id=control.id))
    incident=Incident.query.filter_by(code='INC-001').first()
    if incident and incident.detected_at=='2026-10-15T09:20' and len(incident.events)==2 and all(e.actor=='Sistema demo' for e in incident.events):
        before=snapshot(incident)
        incident.detected_at='2026-10-15T10:15'
        db.session.add(Audit(actor='Sistema demo',action='Alinear hora con enunciado',module='incidentes',record_id=incident.id,before=before,after=snapshot(incident)))
    db.session.add(Audit(actor='Sistema demo',action='Vincular riesgos y controles demo',module='Actualización interactiva',after='Relaciones iniciales del Caso 7; las evaluaciones jurídicas permanecen pendientes.'))
    db.session.commit()
