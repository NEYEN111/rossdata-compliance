import csv
import io
import re
from crossdata.models import db, User, Treatment, Evidence, Control, Incident, Audit, Organization, Transfer, Jurisdiction
from crossdata.catalog import CATALOG
from crossdata.services import matrix_rows, dashboard_data, treatment_alerts, transfer_status
from crossdata.seed import seed_demo

def payload(app,module,record_id=1):
    with app.app_context():
        record = db.session.get(CATALOG[module]['model'],record_id)
        result = {}
        for field in CATALOG[module]['fields']:
            value = getattr(record,field['key'])
            if field['kind']=='countries': value=[str(j.id) for j in value]
            elif field['kind']=='bool':
                if value: result[field['key']]='on'
                continue
            elif value is None: value=''
            result[field['key']]=value
        return result

def test_every_read_route_and_local_assets(app,client):
    routes=['/','/matriz','/matriz?country=2&data=salud','/auditoria','/reportes','/configuracion']
    with app.app_context():
        for module,spec in CATALOG.items():
            routes += [f'/registros/{module}',f'/registros/{module}/nuevo',f'/exportar/{module}.csv']
            for record in db.session.scalars(db.select(spec['model'])):
                routes += [f'/registros/{module}/{record.id}',f'/registros/{module}/{record.id}/editar']
    routes += ['/exportar/matriz.csv','/exportar/auditoria.csv','/static/app.css','/static/app.js','/static/charts.js','/static/vendor/chart.umd.js','/static/vendor/bootstrap.min.css','/static/favicon.svg']
    for route in routes:
        response=client.get(route)
        assert response.status_code==200,route
    assert client.get('/missing').status_code==404
    assert client.get('/registros/no-existe').status_code==404
    assert client.get('/registros/tratamientos/99999').status_code==404
    assert client.get('/exportar/no-existe.csv').status_code==404

def test_login_logout_and_protected_routes(app):
    c=app.test_client()
    assert c.get('/').status_code==302
    assert c.get('/reportes').status_code==302
    assert c.get('/exportar/matriz.csv').status_code==302
    assert c.post('/login',data={'username':'admin','password':'wrong'}).status_code==401
    assert c.post('/login',data={'username':'admin','password':'AndeClass2026!'}).status_code==302
    assert c.post('/logout').status_code==302
    assert c.get('/matriz').status_code==302

def test_auditor_cannot_mutate_compliance_records(app):
    c=app.test_client()
    c.post('/login',data={'username':'auditor','password':'AndeClass2026!'})
    for module in CATALOG:
        assert c.get(f'/registros/{module}/nuevo').status_code==403
        assert c.post(f'/registros/{module}/1/editar',data={}).status_code==403
        assert c.post(f'/registros/{module}/1/eliminar').status_code==403
    assert c.post('/incidentes/1/avanzar').status_code==403
    assert c.post('/incidentes/1/revision').status_code==403
    assert c.post('/configuracion').status_code==403
    assert c.get('/matriz').status_code==200
    assert c.get('/exportar/matriz.csv').status_code==200
    assert b'Nuevo tratamiento' not in c.get('/').data

def test_compliance_role_boundaries(app):
    c=app.test_client()
    c.post('/login',data={'username':'cumplimiento','password':'AndeClass2026!'})
    assert c.get('/registros/tratamientos/nuevo').status_code==200
    assert c.post('/registros/jurisdicciones/1/editar').status_code==403
    assert c.post('/registros/evidencias/1/eliminar').status_code==403
    assert c.post('/configuracion').status_code==403

def test_seed_is_idempotent(app):
    with app.app_context():
        seed_demo()
        assert User.query.count()==3
        assert Treatment.query.count()==5
        assert Incident.query.one().affected==320
        assert Jurisdiction.query.count()==5

def test_successful_edit_all_modules_audits_before_and_after(app,client):
    for module,spec in CATALOG.items():
        data=payload(app,module)
        first=next(f['key'] for f in spec['fields'] if f['kind']=='text')
        data[first]=str(data[first])+' revisado'
        response=client.post(f'/registros/{module}/1/editar',data=data)
        assert response.status_code==302,(module,response.data.decode())
        with app.app_context():
            event=Audit.query.filter_by(module=module,action='Actualizar').order_by(Audit.id.desc()).first()
            assert event and event.before and 'revisado' in event.after

def test_create_all_modules(app,client):
    for module,spec in CATALOG.items():
        data=payload(app,module)
        if module=='incidentes': data['code']='INC-NEW'
        response=client.post(f'/registros/{module}/nuevo',data=data)
        assert response.status_code==302,(module,response.data.decode())
        with app.app_context():
            assert Audit.query.filter_by(module=module,action='Crear').first()

def test_health_advertising_rule_and_missing_evidence(app,client):
    data=payload(app,'tratamientos')
    data.update(name='Prueba salud',data_type='SALUD, correos',category='Personal',purpose='Bienestar',secondary_purpose='Publicidad',status='Cumple')
    data.pop('sensitive',None)
    response=client.post('/registros/tratamientos/nuevo',data=data)
    assert response.status_code==302
    with app.app_context():
        t=Treatment.query.filter_by(name='Prueba salud').one()
        assert t.sensitive and t.category=='Especial / sensible' and t.status=='Parcial'
        assert 'Categoría especial y nueva finalidad: requiere revisión reforzada' in treatment_alerts(t)

def test_invalid_inputs_are_rejected_without_mutation(app,client):
    data=payload(app,'riesgos')
    data['probability']='6'
    assert client.post('/registros/riesgos/1/editar',data=data).status_code==422
    assert client.post('/registros/tratamientos/nuevo',data={}).status_code==422
    data=payload(app,'derechos')
    data['due_date']='2020-01-01'
    assert client.post('/registros/derechos/1/editar',data=data).status_code==422
    data=payload(app,'incidentes')
    data['affected']='-10'
    assert client.post('/registros/incidentes/1/editar',data=data).status_code==422
    data=payload(app,'jurisdicciones')
    data['source']='javascript:alert(1)'
    assert client.post('/registros/jurisdicciones/1/editar',data=data).status_code==422

def test_evidence_scope_and_control_review_gate(app,client):
    data=payload(app,'controles')
    data['evidence_id']='5'
    assert client.post('/registros/controles/1/editar',data=data).status_code==422
    data=payload(app,'controles')
    data['rationale']=''
    assert client.post('/registros/controles/1/editar',data=data).status_code==422
    data=payload(app,'evidencias')
    data['reference']=''
    assert client.post('/registros/evidencias/1/editar',data=data).status_code==422
    data=payload(app,'evidencias')
    data['treatment_id']='2'
    assert client.post('/registros/evidencias/1/editar',data=data).status_code==422

def test_matrix_reacts_to_evidence_revocation_and_filters(app,client):
    with app.app_context():
        initial=matrix_rows({'country':'1','data':'DNI'})
        assert len(initial)==1 and initial[0]['status']=='Parcial'
        assert any('país pendiente' in r['title'] for r in initial[0]['reasons'])
        evidence=db.session.get(Evidence,1)
        evidence.status='Pendiente'
        db.session.commit()
        assert matrix_rows({'country':'1','data':'DNI'})[0]['status']=='Parcial'
        assert len(matrix_rows({'country':'2','data':'salud','purpose':'publicidad','status':'No cumple'}))==1
        assert matrix_rows({'data':'inexistente'})==[]
        assert dashboard_data()['evaluated']>0
    response=client.get('/exportar/matriz.csv?country=2&data=salud&purpose=publicidad')
    rows=list(csv.reader(io.StringIO(response.data.decode('utf-8-sig'))))
    assert len(rows)==2 and rows[1][0]=='España / UE'

def test_transfer_unverified_sensitive_is_high_risk(app,client):
    data=payload(app,'transferencias',3)
    data['mechanism']=''
    data['status']='Por verificar'
    assert client.post('/registros/transferencias/3/editar',data=data).status_code==302
    with app.app_context():
        assert transfer_status(db.session.get(Transfer,3))=='Alto riesgo'
    data['destination_id']=data['jurisdiction_id']
    assert client.post('/registros/transferencias/3/editar',data=data).status_code==422

def test_incident_workflow_review_gates_and_closure(app,client):
    def advance(stage,**extra):
        return client.post('/incidentes/1/avanzar',data={'expected_stage':str(stage),'note':'Acción documentada en el ejercicio académico.',**extra})
    advance(0)
    with app.app_context(): assert db.session.get(Incident,1).stage==1
    advance(1); advance(2)
    advance(3,decision='Notificar')
    with app.app_context(): assert db.session.get(Incident,1).stage==3
    for country in (1,2):
        review={'applicability':'Aplicable','authority_decision':'Notificar','subject_decision':'No corresponde',
            'authority':'Autoridad demo','consequence':'Consecuencias revisadas para este país en el ejercicio.',
            'rationale':'Decisión académica simulada y fundamentada por jurisdicción.',
            'deadline':'2026-10-16T12:00','deadline_reason':'Plazo simulado revisado; inicio en la detección del incidente.'}
        assert client.post(f'/incidentes/1/pais/{country}',data=review).status_code==302
    advance(3,decision='Notificar')
    advance(4)
    with app.app_context(): assert db.session.get(Incident,1).stage==4
    for country in (1,2):
        with app.app_context():
            ev=Evidence(name='Notificación simulada',kind='Notificación',date='2026-10-15',owner='Demo',treatment_id=2,jurisdiction_id=country,status='Validada',reference='DEMO-NOT, evidencia simulada')
            db.session.add(ev); db.session.commit(); ev_id=ev.id
        review['evidence_id']=str(ev_id)
        assert client.post(f'/incidentes/1/pais/{country}',data=review).status_code==302
    advance(4)
    advance(5)
    with app.app_context(): assert db.session.get(Incident,1).stage==5
    advance(5,evidence_id='5'); advance(6,evidence_id='5')
    with app.app_context():
        incident=db.session.get(Incident,1)
        assert incident.stage==7 and incident.status=='Cerrado'
        assert len(incident.events)==8
        assert Audit.query.filter_by(action='Avanzar a Cerrar').first()
    advance(7,evidence_id='5')
    with app.app_context(): assert len(db.session.get(Incident,1).events)==8

def test_rights_response_needs_evidence(app,client):
    data=payload(app,'derechos')
    data.update(status='Cerrada',response='Respuesta ficticia completa.',evidence_id='')
    assert client.post('/registros/derechos/1/editar',data=data).status_code==422
    data['evidence_id']='1'
    assert client.post('/registros/derechos/1/editar',data=data).status_code==302

def test_delete_protects_links_and_records_audit(app,client):
    response=client.post('/registros/tratamientos/1/eliminar',follow_redirects=True)
    assert b'No se puede eliminar' in response.data
    with app.app_context(): assert db.session.get(Treatment,1)
    data=payload(app,'evidencias')
    data['name']='Evidencia descartable'
    client.post('/registros/evidencias/nuevo',data=data)
    with app.app_context(): new_id=Evidence.query.filter_by(name='Evidencia descartable').one().id
    assert client.post(f'/registros/evidencias/{new_id}/eliminar').status_code==302
    with app.app_context():
        assert db.session.get(Evidence,new_id) is None
        assert Audit.query.filter_by(action='Eliminar',record_id=new_id).first()

def test_csv_formula_and_html_injection_are_escaped(app,client):
    data=payload(app,'tratamientos')
    data.update(name='=HYPERLINK("bad")',notes='<script>alert(1)</script>')
    client.post('/registros/tratamientos/1/editar',data=data)
    rows=list(csv.reader(io.StringIO(client.get('/exportar/tratamientos.csv').data.decode('utf-8-sig'))))
    assert rows[1][0].startswith("'=")
    html=client.get('/registros/tratamientos/1').data.decode()
    assert '<script>alert(1)</script>' not in html
    assert '&lt;script&gt;' in html

def test_csrf_protects_mutations(app):
    app.config['WTF_CSRF_ENABLED']=True
    c=app.test_client()
    assert c.post('/login',data={'username':'admin','password':'AndeClass2026!'}).status_code==400
    html=c.get('/login').data.decode()
    token=re.search(r'name="csrf_token" value="([^"]+)"',html).group(1)
    assert c.post('/login',data={'username':'admin','password':'AndeClass2026!','csrf_token':token}).status_code==302
    assert c.post('/registros/tratamientos/1/eliminar').status_code==400

def test_settings_and_password_change(app,client):
    response=client.post('/configuracion',data={'name':'AndeClass Demo S.A.C.','country':'Perú','sector':'Educación digital','reviewer':'Equipo ficticio'})
    assert response.status_code==302
    client.post('/configuracion/password',data={'current_password':'AndeClass2026!','new_password':'NuevaClaveDemo2026!'})
    client.post('/logout')
    assert client.post('/login',data={'username':'admin','password':'AndeClass2026!'}).status_code==401
    assert client.post('/login',data={'username':'admin','password':'NuevaClaveDemo2026!'}).status_code==302
    with app.app_context():
        assert db.session.get(Organization,1).name=='AndeClass Demo S.A.C.'
        event=Audit.query.filter_by(action='Cambiar contraseña').one()
        assert not event.before and not event.after
