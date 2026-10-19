"""Explainable assessments: context changes invalidate previous reviews."""
import hashlib
import json
from .models import db, Jurisdiction, JurisdictionReview
from .services import normalized, valid_evidence, unknown, control_status, transfer_status

def digest(data):
    return hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def review_context(t,j):
    return digest(dict(data=t.data_type,sensitive=t.sensitive,purpose=t.purpose,secondary=t.secondary_purpose,
        storage=t.storage_country,framework=j.framework,scope=j.scope))

def incident_context(i):
    return digest({k:getattr(i,k) for k in ['treatment_id','detected_at','data_type','affected','sensitive','eu_users','countries','provider_country','cause']})

def current_review(t,j):
    r = next((r for r in t.jurisdiction_reviews if r.jurisdiction_id==j.id),None)
    return r, bool(r and r.context_hash==review_context(t,j))

def secondary_changed(t):
    return bool(t.secondary_purpose and normalized(t.secondary_purpose)!=normalized(t.purpose))

def review_ready(r,t):
    return bool(r and r.applicability=='Aplicable' and r.scope_reason and not unknown(r.legal_basis)
        and (not t.sensitive or r.sensitive_condition)
        and (not secondary_changed(t) or (r.secondary_decision in ('Compatible','Nueva autorización documentada') and r.secondary_basis))
        and valid_evidence(r.evidence) and r.rationale)

def explain_row(row):
    t,j=row['treatment'],row['jurisdiction']
    review,fresh=current_review(t,j)
    reasons=[]
    def add(title,detail,module,record_id=None):
        reasons.append(dict(title=title,detail=detail,module=module,record_id=record_id))
    if not review:
        add('Revisión por país pendiente','Falta justificar alcance, base y finalidades para esta jurisdicción.','revision')
    elif not fresh:
        add('Revisión desactualizada','Cambió el dato, la finalidad, almacenamiento o marco de referencia. Revise nuevamente.','revision')
    elif not review_ready(review,t):
        add('Revisión incompleta','Compruebe aplicabilidad, base, condiciones de datos sensibles, nueva finalidad y evidencia validada.','revision')
    elif review.status!='Cumple':
        add('Decisión del responsable: '+review.status,review.rationale,'revision')
    if t.status!='Cumple':
        add('Evaluación del tratamiento: '+t.status,'La evaluación registrada del tratamiento sigue pendiente de completar o corregir.','tratamientos',t.id)
    for domain,state in row['dimensions'].items():
        controls=[c for c in row['controls'] if c.domain==domain]
        if not controls:
            add('Control faltante: '+domain,'Registre un control para esta dimensión y jurisdicción.','controles')
        else:
            for c in controls:
                if control_status(c)!='Cumple':
                    add(c.name,control_status(c)+' · '+(c.rationale or 'Sin fundamento de revisión.')+' Responsable: '+c.owner,'controles',c.id)
    for x in row['transfers']:
        if transfer_status(x)!='Cumple':
            add('Transferencia a '+x.destination.name,transfer_status(x)+' · revisar mecanismo, contrato, medidas y evidencia.','transferencias',x.id)
    if not row['evidence']:
        add('Evidencia validada pendiente','Se necesita respaldo correspondiente a este tratamiento y país.','evidencias')
    return reasons

def incident_countries(incident):
    """Countries explicitly named in the incident, plus EU flag. Provider is not a subject country."""
    text=normalized(incident.countries)
    result=[]
    for j in Jurisdiction.query.order_by(Jurisdiction.id):
        names=[normalized(j.name)]
        if j.code=='PE': names+=['peru']
        if j.code=='ES': names+=['espana','union europea']
        if j.code=='US': names+=['estados unidos']
        if any(n in text for n in names) or (incident.eu_users and j.code=='ES'):
            result.append(j)
    return result

def incident_review_issues(incident, require_notification=False):
    issues=[]
    countries=incident_countries(incident)
    if not countries: return ['Identifique países afectados reconocidos en Jurisdicciones.']
    for j in countries:
        review=next((r for r in incident.country_reviews if r.jurisdiction_id==j.id),None)
        if not review or review.context_hash!=incident_context(incident):
            issues.append(j.name+': falta revisión actualizada.'); continue
        if review.applicability=='Por verificar' or 'Pendiente' in (review.authority_decision,review.subject_decision):
            issues.append(j.name+': decisión pendiente.'); continue
        needs_notice='Notificar' in (review.authority_decision,review.subject_decision)
        if needs_notice and not review.deadline:
            issues.append(j.name+': registre el plazo revisado y su fundamento.')
        if require_notification and needs_notice and not (valid_evidence(review.evidence) and review.evidence.kind=='Notificación'):
            issues.append(j.name+': falta evidencia validada de notificación.')
    return issues
