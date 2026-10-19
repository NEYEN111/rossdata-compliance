"""Interactive explanation, human reviews, evidence files and academic simulation."""
import csv
import hashlib
import io
import json
from pathlib import Path
from datetime import datetime
from flask import Blueprint, request, render_template, g, flash, redirect, url_for, abort, jsonify, send_file, current_app, Response
from werkzeug.utils import secure_filename
from .models import db, Treatment, Jurisdiction, Evidence, Control, Risk, RiskControl, JurisdictionReview, Incident, IncidentReview, EvidenceFile, SimulationRun, utcnow
from .views import login_required, require_editor, safe_csv
from .services import matrix_rows, snapshot, audit, valid_evidence, unknown
from .assessment import review_context, incident_context, secondary_changed, review_ready, incident_countries, incident_review_issues
from .legal_reference import reference_for
from .simulator import evaluate_scenario, CHECKS, PURPOSES, DATA_TYPES

bp=Blueprint('enhance',__name__)

def row_for(treatment_id,country_id):
    row=next((r for r in matrix_rows({'country':str(country_id)}) if r['treatment'].id==treatment_id),None)
    if row is None: abort(404)
    return row

def text_field(key,limit=4000):
    value=request.form.get(key,'').strip()
    if len(value)>limit: raise ValueError('El campo '+key+' excede el tamaño permitido.')
    return value

def scoped_evidence(raw,treatment_id,country_id):
    if not raw: return None
    try: evidence=db.session.get(Evidence,int(raw))
    except (ValueError,TypeError): raise ValueError('Evidencia inválida.')
    if not evidence or evidence.treatment_id!=treatment_id or evidence.jurisdiction_id!=country_id:
        raise ValueError('La evidencia debe pertenecer al mismo tratamiento y país.')
    return evidence

@bp.route('/matriz/<int:treatment_id>/<int:country_id>',methods=['GET','POST'])
@login_required
def matrix_detail(treatment_id,country_id):
    row=row_for(treatment_id,country_id)
    t,j=row['treatment'],row['jurisdiction']
    review=row['review']
    if request.method=='POST':
        require_editor()
        try:
            values={k:text_field(k) for k in ['applicability','scope_reason','legal_basis','sensitive_condition','secondary_decision','secondary_basis','status','rationale']}
            if values['applicability'] not in ['Por verificar','Aplicable','No aplicable']: raise ValueError('Seleccione aplicabilidad válida.')
            if values['status'] not in ['Por verificar','Parcial','No cumple','Cumple']: raise ValueError('Seleccione un estado válido.')
            if values['secondary_decision'] not in ['Sin nueva finalidad','Pendiente','Compatible','Nueva autorización documentada','No autorizar']: raise ValueError('Decisión de finalidad no válida.')
            if len(values['scope_reason'])<20 or len(values['rationale'])<20:
                raise ValueError('Documente alcance y fundamento con al menos 20 caracteres cada uno.')
            evidence=scoped_evidence(request.form.get('evidence_id'),t.id,j.id)
            if values['status']=='Cumple':
                if values['applicability']!='Aplicable' or unknown(values['legal_basis']) or not valid_evidence(evidence):
                    raise ValueError('Cumple requiere alcance aplicable, base identificada y evidencia validada.')
                if t.sensitive and not values['sensitive_condition']:
                    raise ValueError('Identifique la condición habilitante para datos sensibles.')
                if secondary_changed(t) and (values['secondary_decision'] not in ['Compatible','Nueva autorización documentada'] or not values['secondary_basis']):
                    raise ValueError('Justifique compatibilidad o nueva autorización para la finalidad secundaria.')
            before=snapshot(review) if review else ''
            review=review or JurisdictionReview(treatment_id=t.id,jurisdiction_id=j.id)
            for key,value in values.items(): setattr(review,key,value)
            review.evidence_id=evidence.id if evidence else None
            review.reviewer=g.user.username
            review.reviewed_at=utcnow()
            review.context_hash=review_context(t,j)
            db.session.add(review); db.session.flush()
            audit(g.user.username,'Revisar por jurisdicción','matriz',review.id,before,snapshot(review))
            db.session.commit()
            flash('Revisión guardada. La matriz y sus motivos se recalcularon.','success')
            return redirect(url_for('enhance.matrix_detail',treatment_id=t.id,country_id=j.id))
        except ValueError as error: flash(str(error),'danger')
    return render_template('matrix_detail.html',title=t.name+' · '+j.name,active='matriz',row=row,review=review,
        legal=reference_for(j),evidences=[e for e in t.evidences if e.jurisdiction_id==j.id],
        risks=[r for r in t.risks if r.jurisdiction_id==j.id],secondary_changed=secondary_changed(t)),(422 if request.method=='POST' else 200)

@bp.post('/riesgos/<int:risk_id>/vincular-control')
@login_required
def link_control(risk_id):
    require_editor()
    risk=db.get_or_404(Risk,risk_id)
    control=db.session.get(Control,request.form.get('control_id',type=int)) if request.form.get('control_id',type=int) else None
    if not control or (control.treatment_id,control.jurisdiction_id)!=(risk.treatment_id,risk.jurisdiction_id):
        flash('El control debe corresponder al tratamiento y jurisdicción del riesgo.','danger')
    elif db.session.scalar(db.select(RiskControl).where(RiskControl.risk_id==risk.id,RiskControl.control_id==control.id)):
        flash('Ese control ya está vinculado.','warning')
    else:
        link=RiskControl(risk_id=risk.id,control_id=control.id)
        db.session.add(link); db.session.flush()
        audit(g.user.username,'Vincular control','riesgos',risk.id,'',snapshot(link)); db.session.commit()
        flash('Riesgo vinculado al control y a su evidencia.','success')
    return redirect(url_for('web.detail',module='riesgos',record_id=risk.id))

@bp.post('/riesgos/<int:risk_id>/desvincular/<int:link_id>')
@login_required
def unlink_control(risk_id,link_id):
    require_editor()
    link=db.get_or_404(RiskControl,link_id)
    if link.risk_id!=risk_id: abort(404)
    audit(g.user.username,'Desvincular control','riesgos',risk_id,snapshot(link),'')
    db.session.delete(link); db.session.commit()
    return redirect(url_for('web.detail',module='riesgos',record_id=risk_id))

@bp.route('/incidentes/<int:incident_id>/pais/<int:country_id>',methods=['GET','POST'])
@login_required
def incident_country(incident_id,country_id):
    incident=db.get_or_404(Incident,incident_id)
    country=next((j for j in incident_countries(incident) if j.id==country_id),None)
    if country is None: abort(404)
    review=next((r for r in incident.country_reviews if r.jurisdiction_id==country_id),None)
    if request.method=='POST':
        require_editor()
        if incident.stage==7: abort(409,description='El incidente está cerrado.')
        try:
            values={k:text_field(k,300 if k=='authority' else 4000) for k in ['applicability','authority_decision','subject_decision','authority','consequence','rationale','deadline','deadline_reason']}
            if values['applicability'] not in ['Por verificar','Aplicable','No aplicable']: raise ValueError('Aplicabilidad inválida.')
            for key in ['authority_decision','subject_decision']:
                if values[key] not in ['Pendiente','Notificar','No corresponde']: raise ValueError('Decisión inválida.')
            if any(len(values[k])<20 for k in ['consequence','rationale','deadline_reason']):
                raise ValueError('Complete consecuencias, fundamento y revisión del plazo con al menos 20 caracteres.')
            if values['applicability']=='No aplicable' and 'Notificar' in (values['authority_decision'],values['subject_decision']):
                raise ValueError('Revise la coherencia entre alcance no aplicable y decisión de notificar.')
            if values['authority_decision']=='Notificar' and not values['authority']: raise ValueError('Identifique la autoridad destinataria.')
            if 'Notificar' in (values['authority_decision'],values['subject_decision']) and not values['deadline']:
                raise ValueError('Registre fecha/hora límite revisada (Lima) y fundamento del cómputo.')
            if values['deadline']:
                deadline=datetime.strptime(values['deadline'],'%Y-%m-%dT%H:%M')
                if deadline<datetime.strptime(incident.detected_at,'%Y-%m-%dT%H:%M'): raise ValueError('El plazo no puede ser anterior a la detección.')
            evidence=scoped_evidence(request.form.get('evidence_id'),incident.treatment_id,country.id)
            if evidence and (evidence.kind!='Notificación' or not valid_evidence(evidence)):
                raise ValueError('El respaldo de envío debe ser una evidencia validada de tipo Notificación.')
            before=snapshot(review) if review else ''
            review=review or IncidentReview(incident_id=incident.id,jurisdiction_id=country.id)
            for key,value in values.items(): setattr(review,key,value)
            review.evidence_id=evidence.id if evidence else None
            review.reviewer=g.user.username; review.reviewed_at=utcnow(); review.context_hash=incident_context(incident)
            db.session.add(review); db.session.flush()
            audit(g.user.username,'Revisar incidente por país','incidentes',incident.id,before,snapshot(review)); db.session.commit()
            flash('Decisiones por jurisdicción registradas en auditoría.','success')
            return redirect(url_for('web.detail',module='incidentes',record_id=incident.id))
        except ValueError as error: flash(str(error),'danger')
    return render_template('incident_country.html',title=incident.code+' · Revisión de '+country.name,active='incidentes',incident=incident,country=country,
        review=review,legal=reference_for(country),evidences=[e for e in incident.treatment.evidences if e.jurisdiction_id==country.id and e.kind=='Notificación']), (422 if request.method=='POST' else 200)

@bp.post('/evidencias/<int:evidence_id>/archivo')
@login_required
def upload_evidence(evidence_id):
    require_editor()
    evidence=db.get_or_404(Evidence,evidence_id)
    uploaded=request.files.get('file')
    try:
        if not uploaded or not uploaded.filename: raise ValueError('Seleccione un archivo.')
        filename=secure_filename(uploaded.filename)[:180]
        extension=Path(filename).suffix.lower()
        allowed={'.pdf':'application/pdf','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.txt':'text/plain'}
        if extension not in allowed: raise ValueError('Formatos admitidos: PDF, PNG, JPG o TXT.')
        data=uploaded.read(1024*1024+1)
        if not data or len(data)>1024*1024: raise ValueError('El archivo debe tener entre 1 byte y 1 MB.')
        if extension=='.pdf' and not data.startswith(b'%PDF-'): raise ValueError('El contenido no corresponde a un PDF.')
        if extension=='.png' and not data.startswith(b'\x89PNG\r\n\x1a\n'): raise ValueError('El contenido no corresponde a un PNG.')
        if extension in ('.jpg','.jpeg') and not data.startswith(b'\xff\xd8\xff'): raise ValueError('El contenido no corresponde a un JPG.')
        if extension=='.txt':
            try: text=data.decode('utf-8-sig')
            except UnicodeDecodeError: raise ValueError('El TXT debe usar UTF-8.')
            if '\x00' in text: raise ValueError('El TXT contiene datos binarios.')
        digest=hashlib.sha256(data).hexdigest()
        before=snapshot(evidence)
        attachment=EvidenceFile(evidence_id=evidence.id,filename=filename,mime_type=allowed[extension],content=data,sha256=digest,actor=g.user.username)
        db.session.add(attachment)
        evidence.status='En revisión'
        if not evidence.reference: evidence.reference='Archivo adjunto: '+filename+' · SHA-256 '+digest
        db.session.flush()
        audit(g.user.username,'Adjuntar archivo','evidencias',evidence.id,before,json.dumps({'filename':filename,'sha256':digest,'bytes':len(data),'estado':'En revisión'},ensure_ascii=False))
        db.session.commit()
        flash('Archivo guardado. La evidencia pasó a En revisión; compruebe su pertinencia antes de validarla.','success')
    except ValueError as error: flash(str(error),'danger')
    return redirect(url_for('web.detail',module='evidencias',record_id=evidence.id))

@bp.get('/evidencias/archivo/<int:file_id>')
@login_required
def download_evidence(file_id):
    attachment=db.get_or_404(EvidenceFile,file_id)
    audit(g.user.username,'Descargar evidencia','evidencias',attachment.evidence_id,after=json.dumps({'archivo':attachment.filename,'sha256':attachment.sha256}))
    db.session.commit()
    return send_file(io.BytesIO(attachment.content),mimetype='application/octet-stream',as_attachment=True,download_name=attachment.filename)

@bp.get('/simulador')
@login_required
def simulator():
    treatments=Treatment.query.order_by(Treatment.id).all()
    catalog=[]
    for t in treatments:
        catalog.append(dict(id=t.id,name=t.name,countries=[j.id for j in t.jurisdictions],sensitive=t.sensitive,
            purpose=t.purpose,secondary=t.secondary_purpose,evidences=[dict(id=e.id,name=e.name,country=e.jurisdiction_id,status=e.status) for e in t.evidences]))
    return render_template('simulator.html',title='Laboratorio del Caso 7',active='simulador',treatments=treatments,countries=Jurisdiction.query.all(),
        scenario_catalog=catalog,checks=CHECKS,purposes=PURPOSES,datatypes=DATA_TYPES,runs=SimulationRun.query.order_by(SimulationRun.id.desc()).limit(8).all())

@bp.post('/simulador/evaluar')
@login_required
def simulate():
    try: result=evaluate_scenario(request.get_json(silent=True))
    except ValueError as error: return jsonify(error=str(error)),422
    return jsonify(result)

@bp.post('/simulador/guardar')
@login_required
def save_simulation():
    require_editor()
    payload=request.get_json(silent=True)
    try:
        result=evaluate_scenario(payload)
        title=payload.get('title','Ensayo del Caso 7')
        if not isinstance(title,str) or not 3<=len(title.strip())<=160: raise ValueError('Título: entre 3 y 160 caracteres.')
    except ValueError as error: return jsonify(error=str(error)),422
    run=SimulationRun(title=title.strip(),actor=g.user.username,payload=json.dumps(payload,ensure_ascii=False),result=json.dumps(result,ensure_ascii=False))
    db.session.add(run); db.session.flush()
    audit(g.user.username,'Guardar simulación','simulador',run.id,after=run.result); db.session.commit()
    return jsonify(url=url_for('enhance.simulation_detail',run_id=run.id)),201

@bp.get('/simulador/<int:run_id>')
@login_required
def simulation_detail(run_id):
    run=db.get_or_404(SimulationRun,run_id)
    return render_template('simulation_detail.html',title=run.title,active='simulador',run=run,payload=json.loads(run.payload),result=json.loads(run.result))

@bp.get('/simulador/<int:run_id>/exportar.csv')
@login_required
def simulation_export(run_id):
    run=db.get_or_404(SimulationRun,run_id)
    result=json.loads(run.result)
    stream=io.StringIO(); writer=csv.writer(stream)
    writer.writerow(['Ensayo','Tratamiento','Origen','Destino','Revisión','Estado simulado','Fundamento','Aviso'])
    payload=json.loads(run.payload)
    for item in result['items']:
        writer.writerow([safe_csv(v) for v in [run.title,result['treatment'],result['country'],result['destination'],item['title'],'Documentada' if item['addressed'] else 'Pendiente',payload.get('rationale',''),result['notice']]])
    audit(g.user.username,'Exportar simulación','simulador',run.id); db.session.commit()
    return Response('\ufeff'+stream.getvalue(),mimetype='text/csv',headers={'Content-Disposition':f'attachment; filename="ensayo-{run.id}.csv"'})

@bp.get('/informe-academico.pdf')
@login_required
def academic_pdf():
    path=Path(current_app.root_path).parent/'output'/'pdf'/'Informe_Tecnico_Juridico_CrossData.pdf'
    if not path.exists(): abort(404)
    return send_file(path,as_attachment=True,download_name=path.name)
