"""Business rules are conservative support signals, never legal certifications."""
import json
import unicodedata
from .models import db, Audit, Evidence, Treatment, Control, Risk, Incident, Transfer, RightRequest, Jurisdiction
from .catalog import DOMAINS

NOTICE = 'Evaluación de apoyo. Requiere validación del responsable.'

def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFD', value or '') if unicodedata.category(c) != 'Mn').lower().strip()

def has_health(value):
    return 'salud' in normalized(value)

def unknown(value):
    return normalized(value) in ('', 'por verificar', 'pendiente', 'sin validar', 'pendiente de revision')

def valid_evidence(evidence):
    return bool(evidence and evidence.status == 'Validada' and evidence.reference.strip())

def snapshot(record):
    data = {c.name: getattr(record, c.name) for c in record.__table__.columns if c.name != 'password_hash'}
    if isinstance(record, Treatment):
        data['jurisdictions'] = sorted(j.id for j in record.jurisdictions)
    return json.dumps(data, ensure_ascii=False, default=str, sort_keys=True)

def audit(actor, action, module, record_id=None, before='', after=''):
    db.session.add(Audit(actor=actor, action=action, module=module, record_id=record_id, before=before, after=after))

def treatment_alerts(treatment):
    alerts = []
    if treatment.secondary_purpose and normalized(treatment.secondary_purpose) != normalized(treatment.purpose):
        alerts.append('Nueva finalidad: verificar compatibilidad y base jurídica')
    if has_health(treatment.data_type) and 'publicidad' in normalized(treatment.purpose+' '+treatment.secondary_purpose):
        alerts.append('Categoría especial y nueva finalidad: requiere revisión reforzada')
    if unknown(treatment.legal_basis):
        alerts.append('Base jurídica / autorización pendiente de revisión')
    if treatment.sensitive and any(t.jurisdiction_id != t.destination_id for t in treatment.transfers):
        alerts.append('Dato sensible + transferencia internacional: riesgo inicial elevado')
    if not any(valid_evidence(e) for e in treatment.evidences):
        alerts.append('Falta evidencia validada para este tratamiento')
    return alerts

def control_status(control):
    if control.status == 'Cumple' and not (valid_evidence(control.evidence) and control.rationale and control.reviewed_at):
        return 'Parcial'
    return control.status

def aggregate(statuses):
    if not statuses:
        return 'Por verificar'
    if any(s in ('No cumple','Alto riesgo') for s in statuses):
        return 'No cumple'
    if all(s == 'Cumple' for s in statuses):
        return 'Cumple'
    if all(s == 'Por verificar' for s in statuses):
        return 'Por verificar'
    return 'Parcial'

def transfer_status(transfer):
    international = transfer.jurisdiction_id != transfer.destination_id
    sensitive = transfer.treatment.sensitive or has_health(transfer.data_type)
    if international and sensitive and unknown(transfer.mechanism):
        return 'Alto riesgo'
    if unknown(transfer.mechanism):
        return 'Por verificar'
    if transfer.status == 'Cumple' and not (valid_evidence(transfer.evidence) and transfer.contract and transfer.security and transfer.reviewer and transfer.review_date):
        return 'Parcial'
    return transfer.status

def matrix_rows(filters=None):
    """One row per treatment/jurisdiction; status follows linked controls and proof."""
    rows = []
    filters = filters or {}
    from .assessment import current_review, review_ready, explain_row
    for t in db.session.scalars(db.select(Treatment).order_by(Treatment.id)):
        for j in t.jurisdictions:
            controls = [c for c in t.controls if c.jurisdiction_id == j.id]
            evidence = [e for e in t.evidences if e.jurisdiction_id == j.id and valid_evidence(e)]
            transfers = [x for x in t.transfers if x.jurisdiction_id == j.id]
            dimensions = {domain: aggregate([control_status(c) for c in controls if c.domain == domain]) for domain in DOMAINS}
            review,fresh = current_review(t,j)
            review_state = review.status if fresh and review_ready(review,t) else 'Por verificar'
            if fresh and review and review.status == 'No cumple':
                review_state = 'No cumple'
            checks = list(dimensions.values()) + [t.status,review_state]
            if transfers:
                checks += [transfer_status(x) for x in transfers]
            if not evidence or unknown(review.legal_basis if fresh else t.legal_basis):
                checks.append('Por verificar')
            state = aggregate(checks)
            row = dict(treatment=t,jurisdiction=j,controls=controls,evidence=evidence,transfers=transfers,dimensions=dimensions,status=state,
                review=review,review_fresh=fresh,legal_basis=review.legal_basis if fresh and review.legal_basis else t.legal_basis)
            row['reasons'] = explain_row(row)
            if filters.get('country') and str(j.id) != str(filters['country']): continue
            if filters.get('data') and normalized(filters['data']) not in normalized(t.data_type): continue
            if filters.get('purpose') and normalized(filters['purpose']) not in normalized(t.purpose+' '+t.secondary_purpose): continue
            if filters.get('status') and state != filters['status']: continue
            rows.append(row)
    return rows

def dashboard_data():
    treatments = db.session.scalars(db.select(Treatment)).all()
    risks = db.session.scalars(db.select(Risk)).all()
    controls = db.session.scalars(db.select(Control)).all()
    incidents = db.session.scalars(db.select(Incident).where(Incident.status != 'Cerrado')).all()
    evaluated = sum(c.status != 'Por verificar' and bool(c.rationale and c.reviewed_at) for c in controls)
    rows = matrix_rows()
    counts = {s: sum(r['status'] == s for r in rows) for s in ['Cumple','Parcial','No cumple','Por verificar']}
    return dict(treatments=treatments,risks=risks,controls=controls,incidents=incidents,rows=rows,
        stats=[('Tratamientos registrados',len(treatments),'database','Inventario de actividades','tratamientos'),
               ('Tratamientos sensibles',sum(t.sensitive for t in treatments),'shield','Incluyen categorías especiales','tratamientos'),
               ('Transferencias internacionales',db.session.query(Transfer).count(),'arrows','Flujos de datos documentados','transferencias'),
               ('Riesgos altos / críticos',sum(r.level in ('Alto','Crítico') and r.status != 'Mitigado' for r in risks),'alert','Requieren atención prioritaria','riesgos'),
               ('Incidentes abiertos',len(incidents),'shield','Investigación y respuesta','incidentes'),
               ('Evidencias pendientes',db.session.query(Evidence).filter(Evidence.status != 'Validada').count(),'file','Por completar o validar','evidencias'),
               ('Solicitudes de derechos',db.session.query(RightRequest).filter(RightRequest.status != 'Cerrada').count(),'users','Solicitudes en seguimiento','derechos'),
               ('Controles evaluados',f'{round(evaluated/len(controls)*100) if controls else 0}%','check',f'{evaluated} de {len(controls)} con revisión registrada','controles')],
        chart_data=dict(risks={s:sum(r.level==s for r in risks) for s in ['Bajo','Medio','Alto','Crítico']},states=counts,
        countries={j.name:len(j.treatments) for j in Jurisdiction.query.all()}),
        evaluated=evaluated)

def badge_class(status):
    if status in ('Cumple','Validada','Mitigado','Cerrado','Cerrada','Respondida','Bajo'): return 'good'
    if status in ('No cumple','Alto riesgo','Alto','Crítico'): return 'danger'
    if status in ('Parcial','Medio','En investigación','Pendiente','En revisión','En mitigación','En evaluación'): return 'warning'
    return 'neutral'
