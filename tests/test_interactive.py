import io
import json
import re
from crossdata.models import db, JurisdictionReview, Treatment, Jurisdiction, Evidence, EvidenceFile, RiskControl, Incident, IncidentReview, SimulationRun, Audit
from crossdata.assessment import review_context, incident_review_issues
from crossdata.services import matrix_rows

def scenario(**changes):
    result=dict(treatment_id=1,country_id=1,destination_id=3,data_type='Salud',original='Bienestar',proposed='Publicidad',mechanism='',checks=[],evidence_id='',rationale='')
    result.update(changes);return result

def review(**changes):
    result=dict(applicability='Aplicable',scope_reason='Alcance territorial y material revisado para el caso académico.',legal_basis='Base específica revisada para este país.',sensitive_condition='',secondary_decision='Sin nueva finalidad',secondary_basis='',status='Cumple',rationale='Revisión de obligaciones documentada con evidencia ficticia.',evidence_id='1')
    result.update(changes);return result

def test_new_get_routes_and_unknowns(client):
    for path in ['/simulador','/matriz/1/1','/matriz/2/2','/incidentes/1/pais/1','/incidentes/1/pais/2']:
        assert client.get(path).status_code==200,path
    for path in ['/matriz/1/3','/simulador/999','/incidentes/1/pais/999','/evidencias/archivo/999']:
        assert client.get(path).status_code==404,path

def test_scenario_rules_and_evidence_gate(app,client):
    initial=client.post('/simulador/evaluar',json=scenario()).get_json()
    assert initial['initial_risk']=='Crítico' and initial['before_pending']==4 and initial['after_pending']==4
    assert any('Categoría especial y nueva finalidad' in x for x in initial['alerts'])
    checked=client.post('/simulador/evaluar',json=scenario(checks=['base','purpose','security','transfer'])).get_json()
    assert checked['after_pending']==4
    documented=scenario(checks=['base','purpose','security','transfer'],evidence_id='1',rationale='Se documenta la revisión hipotética con evidencia demo.')
    assert client.post('/simulador/evaluar',json=documented).get_json()['after_pending']==1
    documented['mechanism']='Garantía contractual ficticia para evaluación'
    response=client.post('/simulador/evaluar',json=documented)
    assert response.get_json()['after_pending']==0
    assert 'cumplimiento' in response.get_json()['notice']
    with app.app_context():
        assert JurisdictionReview.query.count()==0 and Treatment.query.count()==5
        assert SimulationRun.query.count()==0

def test_simulator_validation_scope_and_rejected_evidence(client):
    for changes in [dict(country_id=3),dict(treatment_id=999),dict(checks=['inventado']),dict(evidence_id=5),dict(data_type='Otra'),dict(rationale=[])]:
        assert client.post('/simulador/evaluar',json=scenario(**changes)).status_code==422
    assert client.post('/simulador/evaluar',json=[]).status_code==422
    assert client.post('/simulador/evaluar',json=None).status_code==422

def test_simulation_saved_snapshot_csv_and_audit(app,client):
    response=client.post('/simulador/guardar',json=scenario(title='=Ensayo exportable'))
    assert response.status_code==201
    assert client.get(response.get_json()['url']).status_code==200
    export=client.get('/simulador/1/exportar.csv')
    assert "'=Ensayo exportable" in export.data.decode('utf-8-sig')
    with app.app_context():
        run=db.session.get(SimulationRun,1)
        assert json.loads(run.result)['after_pending']==4
        assert Audit.query.filter_by(action='Guardar simulación').first()

def test_country_review_changes_matrix_and_invalidates_on_context(app,client):
    assert client.post('/matriz/1/1',data=review()).status_code==302
    with app.app_context():
        assert matrix_rows({'country':1,'data':'DNI'})[0]['status']=='Cumple'
        t=db.session.get(Treatment,1);t.secondary_purpose='Publicidad';db.session.commit()
        row=matrix_rows({'country':1,'data':'DNI'})[0]
        assert row['status']=='Parcial' and not row['review_fresh']
        assert any('desactualizada' in x['title'] for x in row['reasons'])
    assert client.post('/matriz/1/1',data=review()).status_code==422
    assert client.post('/matriz/1/1',data=review(secondary_decision='Compatible',secondary_basis='Evaluación específica de compatibilidad de la nueva finalidad.')).status_code==302

def test_review_requires_health_condition_and_scoped_proof(app,client):
    data=review(evidence_id='5')
    assert client.post('/matriz/2/1',data=data).status_code==422
    data['sensitive_condition']='Condición habilitante de datos sensibles verificada en el ejercicio.'
    assert client.post('/matriz/2/1',data=data).status_code==302
    data['evidence_id']='1'
    assert client.post('/matriz/2/1',data=data).status_code==422
    data=review(applicability='No aplicable')
    assert client.post('/matriz/1/1',data=data).status_code==422

def test_upload_download_and_review_invalidation(app,client):
    client.post('/matriz/1/1',data=review())
    response=client.post('/evidencias/1/archivo',data={'file':(io.BytesIO(b'REVISION ACADEMICA FICTICIA'),'../revision.txt')},content_type='multipart/form-data')
    assert response.status_code==302
    with app.app_context():
        file=EvidenceFile.query.one()
        assert file.filename=='revision.txt' and len(file.sha256)==64
        assert db.session.get(Evidence,1).status=='En revisión'
        assert matrix_rows({'country':1,'data':'DNI'})[0]['status']=='Parcial'
    download=client.get('/evidencias/archivo/1')
    assert download.status_code==200 and download.data==b'REVISION ACADEMICA FICTICIA'
    assert 'attachment;' in download.headers['Content-Disposition']
    assert download.headers['X-Content-Type-Options']=='nosniff'
    assert app.test_client().get('/evidencias/archivo/1').status_code==302

def test_upload_rejects_bad_content_or_oversize(app,client):
    for data,name in [(b'<script>x</script>','x.html'),(b'not pdf','x.pdf'),(b'not png','x.png'),(b'\x00binary','x.txt'),(b'a'*(1024*1024+1),'huge.txt')]:
        client.post('/evidencias/1/archivo',data={'file':(io.BytesIO(data),name)},content_type='multipart/form-data')
    with app.app_context(): assert EvidenceFile.query.count()==0

def test_risk_control_link_integrity_and_audit(app,client):
    with app.app_context():
        count=RiskControl.query.count()
        assert count==7
    client.post('/riesgos/1/vincular-control',data={'control_id':'1'})
    with app.app_context(): assert RiskControl.query.count()==count
    client.post('/riesgos/1/vincular-control',data={'control_id':'9'})
    with app.app_context():
        assert RiskControl.query.count()==count+1
        link=RiskControl.query.filter_by(risk_id=1,control_id=9).one();link_id=link.id
    assert client.post(f'/riesgos/2/desvincular/{link_id}').status_code==404
    assert client.post(f'/riesgos/1/desvincular/{link_id}').status_code==302
    with app.app_context(): assert Audit.query.filter_by(action='Desvincular control').first()

def test_incident_country_review_validation_and_staleness(app,client):
    data=dict(applicability='Aplicable',authority_decision='Notificar',subject_decision='No corresponde',authority='ANPD demo',consequence='Consecuencias documentadas y revisadas por el responsable.',rationale='Fundamento simulado por jurisdicción, sin envío de comunicaciones.',deadline='2026-10-16T10:15',deadline_reason='Plazo ilustrativo revisado manualmente desde la detección.')
    assert client.post('/incidentes/1/pais/1',data={**data,'deadline':''}).status_code==422
    assert client.post('/incidentes/1/pais/1',data={**data,'evidence_id':'5'}).status_code==422
    assert client.post('/incidentes/1/pais/1',data=data).status_code==302
    with app.app_context():
        i=db.session.get(Incident,1)
        assert any('España' in x for x in incident_review_issues(i))
        i.affected=321;db.session.commit()
        assert any('Perú: falta revisión actualizada' in x for x in incident_review_issues(i))

def test_auditor_can_simulate_but_cannot_persist_or_review(app):
    c=app.test_client();c.post('/login',data={'username':'auditor','password':'AndeClass2026!'})
    assert c.post('/simulador/evaluar',json=scenario()).status_code==200
    for path in ['/simulador/guardar','/matriz/1/1','/incidentes/1/pais/1','/evidencias/1/archivo','/riesgos/1/vincular-control','/riesgos/1/desvincular/1']:
        assert c.post(path,json=scenario()).status_code==403,path

def test_simulator_csrf(app):
    app.config['WTF_CSRF_ENABLED']=True
    c=app.test_client()
    html=c.get('/login').data.decode();token=re.search(r'name="csrf_token" value="([^"]+)"',html).group(1)
    c.post('/login',data={'username':'admin','password':'AndeClass2026!','csrf_token':token})
    assert c.post('/simulador/evaluar',json=scenario()).status_code==400
    html=c.get('/simulador').data.decode();token=re.search(r'name="csrf_token" value="([^"]+)"',html).group(1)
    assert c.post('/simulador/evaluar',json=scenario(),headers={'X-CSRFToken':token}).status_code==200
