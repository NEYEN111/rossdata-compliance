"""Authenticated UI, validated mutations, workflow and reports."""
import csv
import io
from datetime import datetime, timezone, timedelta
from functools import wraps
from urllib.parse import urlparse
from flask import Blueprint, render_template, request, redirect, url_for, session, g, abort, flash, Response
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.exc import IntegrityError
from .models import db, User, Treatment, Jurisdiction, Evidence, Transfer, Risk, Control, Incident, IncidentEvent, RightRequest, Audit, Organization
from .catalog import CATALOG, NAV, STATES, STAGES
from .services import NOTICE, snapshot, audit, has_health, valid_evidence, treatment_alerts, matrix_rows, dashboard_data, transfer_status, unknown
from .assessment import incident_countries, incident_review_issues, incident_context
from .models import RiskControl, JurisdictionReview, IncidentReview
from .legal_reference import reference_for

bp = Blueprint('web', __name__)

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for('web.login'))
        return fn(*args, **kwargs)
    return wrapped

def require_editor(module=None):
    if not g.user or g.user.role == 'Auditor': abort(403)
    if module in ('jurisdicciones','configuracion') and g.user.role != 'Administrador': abort(403)

@bp.before_app_request
def load_user():
    g.user = db.session.get(User, session.get('user_id')) if session.get('user_id') else None

@bp.app_context_processor
def context():
    user = g.get('user')
    return dict(user=user, nav=NAV, notice=NOTICE, catalog=CATALOG, stages=STAGES,
        organization=db.session.get(Organization,1), can_edit=bool(user and user.role != 'Auditor'),
        is_admin=bool(user and user.role == 'Administrador'), getattr=getattr, valid_evidence=valid_evidence,
        display_value=display_value)

def display_value(record, key):
    value = getattr(record,key,None)
    if value is None or value == '': return 'Por registrar'
    if isinstance(value,bool): return 'Sí' if value else 'No'
    if isinstance(value,list): return ', '.join(x.name for x in value)
    return value.name if hasattr(value,'name') else str(value)

@bp.route('/login',methods=['GET','POST'])
def login():
    if g.user: return redirect(url_for('web.dashboard'))
    if request.method == 'POST':
        user = db.session.scalar(db.select(User).where(User.username == request.form.get('username','').strip()))
        if user and check_password_hash(user.password_hash,request.form.get('password','')):
            session.clear()
            session['user_id'] = user.id
            session.permanent = True
            audit(user.username,'Inicio de sesión','Autenticación')
            db.session.commit()
            return redirect(url_for('web.dashboard'))
        flash('Usuario o contraseña incorrectos.','danger')
        return render_template('login.html'),401
    return render_template('login.html')

@bp.post('/logout')
@login_required
def logout():
    audit(g.user.username,'Cierre de sesión','Autenticación')
    db.session.commit()
    session.clear()
    return redirect(url_for('web.login'))

@bp.get('/')
@login_required
def dashboard():
    return render_template('dashboard.html',active='dashboard',title='Dashboard',**dashboard_data())

def module_spec(module):
    if module not in CATALOG: abort(404)
    return CATALOG[module]

def field_options(field):
    kind = field['kind']
    if kind in ('jurisdiction','countries','treatment','evidence'):
        model = {'jurisdiction':Jurisdiction,'countries':Jurisdiction,'treatment':Treatment,'evidence':Evidence}[kind]
        return [(str(x.id), x.name + (f' · {x.treatment.name} / {x.jurisdiction.name}' if kind == 'evidence' else '')) for x in db.session.scalars(db.select(model).order_by(model.id))]
    return [(x,x) for x in field['choices']]

def validate_form(spec, record):
    errors, values = [], {}
    for field in spec['fields']:
        key, kind, required = field['key'],field['kind'],field['required']
        if kind == 'countries':
            raw = request.form.getlist(key)
            allowed = {x[0] for x in field_options(field)}
            if not raw or any(x not in allowed for x in raw):
                errors.append('Selección de jurisdicciones inválida.')
            values[key] = [db.session.get(Jurisdiction,int(x)) for x in set(raw) if x in allowed]
            continue
        if kind == 'bool':
            values[key] = request.form.get(key) == 'on'
            continue
        raw = request.form.get(key,'').strip()
        if required and not raw: errors.append(f'{field["label"]}: campo obligatorio.')
        if len(raw) > (4000 if kind == 'textarea' else 500): errors.append(f'{field["label"]}: texto demasiado largo.')
        if kind in ('select','jurisdiction','treatment','evidence'):
            allowed = {x[0] for x in field_options(field)}
            if raw and raw not in allowed: errors.append(f'{field["label"]}: selección inválida.')
        if kind in ('jurisdiction','treatment','evidence','number','score'):
            try:
                values[key] = int(raw) if raw else None
                if kind == 'score' and not 1 <= values[key] <= 5: raise ValueError
                if kind == 'number' and not 0 <= values[key] <= 100000000: raise ValueError
            except (ValueError,TypeError): errors.append(f'{field["label"]}: número fuera de rango.')
        else:
            values[key] = raw
        if raw and kind in ('date','datetime-local'):
            try: datetime.strptime(raw,'%Y-%m-%d' if kind == 'date' else '%Y-%m-%dT%H:%M')
            except ValueError: errors.append(f'{field["label"]}: fecha inválida.')
        if raw and kind == 'url' and urlparse(raw).scheme not in ('http','https'):
            errors.append('La fuente debe ser una URL http o https.')
    if errors: return errors, values
    model = spec['model']
    if 'treatment_id' in values:
        treatment = db.session.get(Treatment,values['treatment_id'])
        if 'jurisdiction_id' in values and values['jurisdiction_id'] not in [j.id for j in treatment.jurisdictions]:
            errors.append('La jurisdicción debe estar asociada al tratamiento seleccionado.')
    ev = db.session.get(Evidence,values['evidence_id']) if values.get('evidence_id') else None
    if ev and (ev.treatment_id != values.get('treatment_id') or ev.jurisdiction_id != values.get('jurisdiction_id')):
        errors.append('La evidencia debe corresponder al mismo tratamiento y jurisdicción.')
    if model == Treatment:
        if has_health(values['data_type']) or values['category'] == 'Especial / sensible' or values['sensitive']:
            values.update(sensitive=True,category='Especial / sensible')
        if values['status'] == 'Cumple' and (unknown(values['legal_basis']) or not record or not any(valid_evidence(e) for e in record.evidences)):
            values['status'] = 'Parcial'
            flash('La evaluación se ajustó a Parcial: falta base identificada o evidencia validada.','warning')
        if record:
            country_ids = {j.id for j in values['jurisdictions']}
            linked = record.transfers + record.risks + record.controls + record.evidences + record.rights + record.jurisdiction_reviews
            if any(x.jurisdiction_id not in country_ids for x in linked):
                errors.append('No puede retirar una jurisdicción con registros vinculados; reasígnelos primero.')
    if model == Evidence:
        if values['status'] == 'Validada' and not values['reference']:
            errors.append('Una evidencia validada necesita una referencia documental.')
        if record and (record.treatment_id != values['treatment_id'] or record.jurisdiction_id != values['jurisdiction_id']):
            for cls in (Control,Transfer,RightRequest,IncidentEvent,JurisdictionReview,IncidentReview):
                if db.session.scalar(db.select(cls.id).where(cls.evidence_id == record.id).limit(1)):
                    errors.append('Esta evidencia está vinculada. Mantenga su tratamiento y jurisdicción.'); break
    if model == Control and values['status'] != 'Por verificar':
        if not values['rationale'] or not values['reviewed_at']:
            errors.append('Toda evaluación necesita fecha de revisión y fundamento.')
        if values['status'] == 'Cumple' and not valid_evidence(ev):
            errors.append('Para registrar Cumple se requiere una evidencia validada.')
    if model in (Control,Risk) and record and (record.treatment_id!=values['treatment_id'] or record.jurisdiction_id!=values['jurisdiction_id']):
        if (record.risk_links if model==Control else record.control_links):
            errors.append('Retire los vínculos riesgo-control antes de cambiar tratamiento o país.')
    if model == Transfer:
        if values['jurisdiction_id'] == values['destination_id']:
            errors.append('Una transferencia internacional requiere países diferentes.')
        if values['status'] == 'Cumple' and not (valid_evidence(ev) and not unknown(values['mechanism']) and values['contract'] and values['security'] and values['reviewer'] and values['review_date']):
            errors.append('Para registrar Cumple complete mecanismo, contrato, seguridad, revisión y evidencia validada.')
        if unknown(values['mechanism']):
            values['status'] = 'Alto riesgo' if treatment.sensitive or has_health(values['data_type']) else 'Por verificar'
            flash('Transferencia pendiente de evaluación.','warning')
    if model == Incident:
        if has_health(values['data_type']): values['sensitive'] = True
        values['level'] = 'Crítico' if values['sensitive'] else 'Alto'
        if record and record.events and values['treatment_id'] != record.treatment_id:
            errors.append('Un incidente con bitácora debe mantener su tratamiento asociado.')
    if model == RightRequest:
        if values['due_date'] < values['date']: errors.append('El plazo no puede ser anterior a la recepción.')
        if values['status'] in ('Respondida','Cerrada') and not (values['response'] and valid_evidence(ev)):
            errors.append('Una solicitud respondida o cerrada necesita respuesta y evidencia validada.')
    return errors,values

@bp.get('/registros/<module>')
@login_required
def listing(module):
    spec = module_spec(module)
    records = db.session.scalars(db.select(spec['model']).order_by(spec['model'].id)).all()
    q = request.args.get('q','').strip().lower()
    if q: records = [r for r in records if q in ' '.join(display_value(r,k) for k,_ in spec['columns']).lower()]
    if request.args.get('treatment'):
        records = [r for r in records if str(getattr(r,'treatment_id','')) == request.args['treatment']]
    if request.args.get('status'):
        records = [r for r in records if getattr(r,'status','') == request.args['status']]
    return render_template('listing.html',title=spec['title'],active=module,spec=spec,module=module,records=records,q=q)

@bp.route('/registros/<module>/nuevo',methods=['GET','POST'])
@bp.route('/registros/<module>/<int:record_id>/editar',methods=['GET','POST'])
@login_required
def edit(module,record_id=None):
    spec = module_spec(module)
    require_editor(module)
    record = db.get_or_404(spec['model'],record_id) if record_id else None
    if request.method == 'POST':
        errors, values = validate_form(spec,record)
        if not errors:
            before = snapshot(record) if record else ''
            obj = record or spec['model']()
            for key,value in values.items(): setattr(obj,key,value)
            db.session.add(obj)
            try:
                db.session.flush()
                audit(g.user.username,'Actualizar' if record else 'Crear',module,obj.id,before,snapshot(obj))
                if module == 'incidentes' and not record:
                    db.session.add(IncidentEvent(incident_id=obj.id,stage=0,note='Detección registrada. Requiere revisión del responsable.',actor=g.user.username))
                db.session.commit()
                flash('Registro guardado. La trazabilidad se actualizó.','success')
                return redirect(url_for('web.detail',module=module,record_id=obj.id))
            except IntegrityError:
                db.session.rollback()
                errors.append('No se pudo guardar: código duplicado o relación no válida.')
        for message in errors: flash(message,'danger')
    return render_template('form.html',title=('Editar ' if record else 'Nuevo registro · ')+spec['singular'],active=module,spec=spec,module=module,record=record,field_options=field_options), (422 if request.method=='POST' else 200)

@bp.get('/registros/<module>/<int:record_id>')
@login_required
def detail(module,record_id):
    spec = module_spec(module)
    record = db.get_or_404(spec['model'],record_id)
    extra = {}
    if module == 'tratamientos': extra['alerts'] = treatment_alerts(record)
    if module == 'incidentes':
        extra['evidences'] = db.session.scalars(db.select(Evidence).where(Evidence.treatment_id == record.treatment_id)).all()
        extra['country_reviews'] = [(j,next((r for r in record.country_reviews if r.jurisdiction_id==j.id),None)) for j in incident_countries(record)]
        extra['review_issues'] = incident_review_issues(record,require_notification=record.stage>=5)
        extra['incident_hash'] = incident_context(record)
    if module == 'riesgos':
        extra['available_controls'] = [c for c in record.treatment.controls if c.jurisdiction_id==record.jurisdiction_id]
    return render_template('incident.html' if module=='incidentes' else 'detail.html',title=record.name if hasattr(record,'name') else spec['title'],active=module,spec=spec,module=module,record=record,**extra)

@bp.post('/registros/<module>/<int:record_id>/eliminar')
@login_required
def delete(module,record_id):
    if g.user.role != 'Administrador': abort(403)
    spec = module_spec(module)
    record = db.get_or_404(spec['model'],record_id)
    before = snapshot(record)
    try:
        db.session.delete(record)
        db.session.flush()
        audit(g.user.username,'Eliminar',module,record_id,before,'')
        db.session.commit()
        flash('Registro eliminado. Se conserva su entrada de auditoría.','success')
        return redirect(url_for('web.listing',module=module))
    except IntegrityError:
        db.session.rollback()
        flash('No se puede eliminar: hay registros vinculados. La trazabilidad debe conservarse.','warning')
        return redirect(url_for('web.detail',module=module,record_id=record_id))

@bp.get('/matriz')
@login_required
def matrix():
    return render_template('matrix.html',title='Matriz de cumplimiento',active='matriz',rows=matrix_rows(request.args),countries=Jurisdiction.query.all(),states=STATES)

@bp.post('/incidentes/<int:record_id>/avanzar')
@login_required
def incident_advance(record_id):
    require_editor()
    incident = db.get_or_404(Incident,record_id)
    note = request.form.get('note','').strip()
    decision = request.form.get('decision','').strip()
    evidence = db.session.get(Evidence,request.form.get('evidence_id',type=int)) if request.form.get('evidence_id') else None
    next_stage = incident.stage + 1
    errors = []
    if incident.stage >= 7: errors.append('El incidente ya está cerrado.')
    if request.form.get('expected_stage',type=int) != incident.stage: errors.append('La etapa cambió. Actualice la página antes de continuar.')
    if len(note) < 12 or len(note) > 4000: errors.append('Documente la acción con entre 12 y 4000 caracteres.')
    if request.form.get('evidence_id') and not evidence: errors.append('La evidencia seleccionada no existe.')
    if evidence and evidence.treatment_id != incident.treatment_id: errors.append('La evidencia debe pertenecer al tratamiento del incidente.')
    if next_stage == 4 and decision not in ('Notificar','No corresponde','Pendiente de información'):
        errors.append('Registre la decisión del responsable sobre las obligaciones.')
    if next_stage>=4:
        errors.extend(incident_review_issues(incident,require_notification=next_stage>=5))
    if next_stage==4 and incident.country_reviews:
        any_notice=any('Notificar' in (r.authority_decision,r.subject_decision) for r in incident.country_reviews if r.jurisdiction_id in [j.id for j in incident_countries(incident)])
        if decision != ('Notificar' if any_notice else 'No corresponde'):
            errors.append('La decisión general debe coincidir con las revisiones por país.')
    if next_stage == 5:
        review = next((e for e in reversed(incident.events) if e.stage == 4),None)
        if not review or review.decision == 'Pendiente de información':
            errors.append('Complete la revisión de obligaciones antes de continuar.')
        # The country reviews above require notification evidence for each relevant country.
    if next_stage in (6,7) and not valid_evidence(evidence):
        errors.append('La corrección y el cierre requieren evidencia validada.')
    if errors:
        for error in errors: flash(error,'danger')
    else:
        before = snapshot(incident)
        incident.stage = next_stage
        incident.status = 'Cerrado' if next_stage == 7 else 'En corrección' if next_stage == 6 else 'En investigación'
        if next_stage == 1: incident.containment = note
        if next_stage == 4: incident.notifications = decision+' · '+note
        db.session.add(IncidentEvent(incident_id=incident.id,stage=next_stage,note=note,decision=decision,evidence_id=evidence.id if evidence else None,actor=g.user.username))
        audit(g.user.username,'Avanzar a '+STAGES[next_stage],'incidentes',incident.id,before,snapshot(incident))
        db.session.commit()
        flash('Etapa documentada. Registro académico; no se ha enviado ninguna comunicación.','success')
    return redirect(url_for('web.detail',module='incidentes',record_id=incident.id))

@bp.post('/incidentes/<int:record_id>/revision')
@login_required
def incident_review(record_id):
    """Re-evaluate an undecided notification review without skipping workflow gates."""
    require_editor()
    incident = db.get_or_404(Incident,record_id)
    decision = request.form.get('decision','')
    note = request.form.get('note','').strip()
    country_issues=incident_review_issues(incident)
    needs_notice=any('Notificar' in (r.authority_decision,r.subject_decision) for r in incident.country_reviews if r.jurisdiction_id in [j.id for j in incident_countries(incident)])
    if incident.stage != 4 or decision != ('Notificar' if needs_notice else 'No corresponde') or not 12 <= len(note) <= 4000 or country_issues:
        flash('Revise la etapa, decisión y fundamento (12–4000 caracteres).','danger')
    else:
        before = snapshot(incident)
        incident.notifications = decision+' · '+note
        db.session.add(IncidentEvent(incident_id=incident.id,stage=4,note=note,decision=decision,actor=g.user.username))
        audit(g.user.username,'Revisar obligaciones','incidentes',incident.id,before,snapshot(incident))
        db.session.commit()
        flash('Revisión actualizada y conservada en la bitácora.','success')
    return redirect(url_for('web.detail',module='incidentes',record_id=incident.id))

@bp.get('/auditoria')
@login_required
def audit_view():
    query = db.select(Audit).order_by(Audit.id.desc())
    if request.args.get('q'):
        q = '%'+request.args['q']+'%'
        query = query.where(db.or_(Audit.actor.ilike(q),Audit.module.ilike(q),Audit.action.ilike(q)))
    return render_template('audit.html',title='Auditoría',active='auditoria',entries=db.session.scalars(query).all())

@bp.get('/reportes')
@login_required
def reports():
    return render_template('reports.html',title='Reporte del Caso AndeClass',active='reportes',report_date=datetime.now(timezone(timedelta(hours=-5))).strftime('%Y-%m-%d'),
        jurisdictions=Jurisdiction.query.all(),transfers=Transfer.query.all(),evidences=Evidence.query.all(),all_incidents=Incident.query.all(),incident_review_issues=incident_review_issues,incident_context=incident_context,**dashboard_data())

def safe_csv(value):
    value = str(value if value is not None else '')
    return "'"+value if value.lstrip().startswith(('=','+','-','@','\t','\r','\n')) else value

@bp.get('/exportar/<module>.csv')
@login_required
def export(module):
    stream = io.StringIO()
    writer = csv.writer(stream)
    if module == 'matriz':
        writer.writerow(['Jurisdicción','Tratamiento','Dato','Categoría','Finalidad','Base jurídica / autorización','Transferencia','Seguridad','Derechos','Autoridad','Evidencia','Estado','Aviso','Motivos y pendientes','Revisor por país','Fuente de referencia'])
        for r in matrix_rows(request.args):
            t,j = r['treatment'],r['jurisdiction']
            writer.writerow([safe_csv(v) for v in [j.name,t.name,t.data_type,t.category,t.purpose,r['legal_basis'],'; '.join(x.destination.name+': '+x.mechanism for x in r['transfers']) or 'Revisar alcance',r['dimensions']['Seguridad'],r['dimensions']['Derechos'],j.authority,'; '.join(e.name for e in r['evidence']),r['status'],NOTICE,'; '.join(x['title']+': '+x['detail'] for x in r['reasons']),r['review'].reviewer if r['review'] else 'Pendiente',reference_for(j)['source']]])
    elif module == 'auditoria':
        writer.writerow(['Usuario','Acción','Módulo','Registro','Fecha UTC','Anterior','Nuevo'])
        for r in Audit.query.order_by(Audit.id): writer.writerow([safe_csv(v) for v in [r.actor,r.action,r.module,r.record_id,r.created_at,r.before,r.after]])
    else:
        spec = module_spec(module)
        fields = spec['fields']
        writer.writerow([f['label'] for f in fields])
        for r in db.session.scalars(db.select(spec['model'])):
            writer.writerow([safe_csv(display_value(r,f['key'])) for f in fields])
    audit(g.user.username,'Exportar CSV',module)
    db.session.commit()
    return Response('\ufeff'+stream.getvalue(),mimetype='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="crossdata-{module}.csv"'})

@bp.route('/configuracion',methods=['GET','POST'])
@login_required
def settings():
    org = db.get_or_404(Organization,1)
    if request.method == 'POST':
        require_editor('configuracion')
        fields = {k:request.form.get(k,'').strip() for k in ('name','country','sector','reviewer')}
        if not all(fields.values()) or any(len(v)>160 for v in fields.values()):
            flash('Complete los cuatro campos (máximo 160 caracteres por campo).','danger')
        else:
            before = snapshot(org)
            for key,value in fields.items(): setattr(org,key,value)
            audit(g.user.username,'Actualizar','configuracion',1,before,snapshot(org))
            db.session.commit()
            flash('Configuración guardada.','success')
            return redirect(url_for('web.settings'))
    return render_template('settings.html',title='Configuración',active='configuracion',org=org,users=User.query.all())

@bp.post('/configuracion/password')
@login_required
def change_password():
    current = request.form.get('current_password','')
    new = request.form.get('new_password','')
    if not check_password_hash(g.user.password_hash,current) or not 12 <= len(new) <= 128:
        flash('Verifique la contraseña actual y use una nueva de 12 a 128 caracteres.','danger')
    else:
        g.user.password_hash = generate_password_hash(new)
        audit(g.user.username,'Cambiar contraseña','Autenticación')
        db.session.commit()
        flash('Contraseña actualizada.','success')
    return redirect(url_for('web.settings'))
