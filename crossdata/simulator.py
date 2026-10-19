"""Deterministic scenario rules, isolated from compliance records."""
from .models import db, Treatment, Jurisdiction, Evidence
from .services import normalized, has_health, valid_evidence, unknown
from .legal_reference import reference_for

PURPOSES=['Gestión académica','Bienestar','Analítica','Publicidad','Recomendaciones']
DATA_TYPES=['Identificación y contacto','Historial académico','Ubicación aproximada','Salud']
CHECKS={'base':'Base / condición para datos sensibles','purpose':'Compatibilidad o nueva autorización','transfer':'Mecanismo y garantía internacional','security':'Medidas de seguridad y derechos'}

def evaluate_scenario(payload):
    """Accept only explicit inputs. Evaluations are hypothetical, never persisted to controls."""
    if not isinstance(payload,dict): raise ValueError('El escenario debe ser un objeto válido.')
    def entity(model,key):
        try: value=int(payload.get(key,''))
        except (ValueError,TypeError): raise ValueError('Seleccione tratamiento y países válidos.')
        obj=db.session.get(model,value)
        if not obj: raise ValueError('El registro seleccionado no existe.')
        return obj
    treatment=entity(Treatment,'treatment_id')
    country=entity(Jurisdiction,'country_id')
    destination=entity(Jurisdiction,'destination_id')
    if country.id not in [j.id for j in treatment.jurisdictions]:
        raise ValueError('Seleccione una jurisdicción vinculada al tratamiento.')
    datatype=payload.get('data_type','')
    original=payload.get('original','')
    proposed=payload.get('proposed','')
    if datatype not in DATA_TYPES or original not in PURPOSES or proposed not in PURPOSES:
        raise ValueError('Dato o finalidad no válidos.')
    mechanism=payload.get('mechanism','')
    if not isinstance(mechanism,str) or len(mechanism)>500: raise ValueError('Mecanismo inválido (máximo 500 caracteres).')
    selected=payload.get('checks',[])
    if not isinstance(selected,list) or any(c not in CHECKS for c in selected): raise ValueError('Controles no válidos.')
    rationale=payload.get('rationale','')
    if not isinstance(rationale,str) or len(rationale)>4000: raise ValueError('Fundamento inválido.')
    evidence=None
    if payload.get('evidence_id'):
        try: evidence=db.session.get(Evidence,int(payload['evidence_id']))
        except (ValueError,TypeError): raise ValueError('Evidencia inválida.')
        if not evidence or evidence.treatment_id!=treatment.id or evidence.jurisdiction_id!=country.id:
            raise ValueError('La evidencia debe corresponder al tratamiento y país del escenario.')
    supported=bool(valid_evidence(evidence) and len(rationale.strip())>=20)
    health=has_health(datatype)
    changed=original!=proposed
    international=country.id!=destination.id
    alerts=[]
    if health: alerts.append('Salud: categoría especial / sensible; identificar una condición habilitante específica.')
    if changed: alerts.append('Nueva finalidad: verificar compatibilidad y base jurídica.')
    if health and proposed=='Publicidad': alerts.append('Categoría especial y nueva finalidad: requiere revisión reforzada.')
    if international and unknown(mechanism): alerts.append('Transferencia pendiente de evaluación: falta mecanismo identificado.')
    if country.code=='ES': alerts.append('Revisar ámbito territorial del RGPD; la estancia temporal en España no decide por sí sola la aplicabilidad.')
    required=['base','security']
    if changed: required.append('purpose')
    if international: required.append('transfer')
    items=[]
    for key in required:
        addressed=bool(key in selected and supported and (key!='transfer' or not unknown(mechanism)))
        items.append(dict(key=key,title=CHECKS[key],addressed=addressed,
            reason='Respaldo y fundamento vinculados al ensayo; sujeto a verificación del responsable.' if addressed else
            'Identifique el mecanismo además de la revisión y evidencia.' if key=='transfer' and unknown(mechanism) else
            'Seleccione la revisión, una evidencia validada y un fundamento de al menos 20 caracteres.'))
    addressed=sum(x['addressed'] for x in items)
    pending=len(items)-addressed
    initial='Crítico' if health and proposed=='Publicidad' else 'Alto' if health and international else 'Medio'
    return dict(treatment=treatment.name,country=country.name,destination=destination.name,category='Especial / sensible' if health else 'Personal',
        alerts=alerts,items=items,initial_risk=initial,before_pending=len(items),after_pending=pending,addressed=addressed,
        evidence=evidence.name if evidence else 'Sin evidencia',supported=supported,
        outcome='Revisiones documentadas en simulación' if not pending else 'Revisión incompleta',
        reference=reference_for(country),notice='Ensayo hipotético. No modifica la matriz real ni certifica cumplimiento jurídico.')
