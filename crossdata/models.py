"""Persistent entities. Relationships preserve the compliance evidence chain."""
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

treatment_countries = db.Table('treatment_countries',
    db.Column('treatment_id', db.Integer, db.ForeignKey('treatment.id'), primary_key=True),
    db.Column('jurisdiction_id', db.Integer, db.ForeignKey('jurisdiction.id'), primary_key=True))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(60), nullable=False)

class Jurisdiction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(8), nullable=False)
    framework = db.Column(db.Text, default='')
    authority = db.Column(db.Text, default='')
    scope = db.Column(db.String(120), default='Operación actual')
    source = db.Column(db.Text, default='')
    notes = db.Column(db.Text, default='')

class Treatment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    owner = db.Column(db.String(120), nullable=False)
    data_type = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(80), default='Personal')
    sensitive = db.Column(db.Boolean, default=False)
    purpose = db.Column(db.Text, nullable=False)
    secondary_purpose = db.Column(db.Text, default='')
    legal_basis = db.Column(db.Text, default='')
    origin = db.Column(db.Text, default='')
    system = db.Column(db.String(160), default='')
    provider = db.Column(db.String(160), default='')
    storage_country = db.Column(db.String(120), default='')
    retention = db.Column(db.String(160), default='')
    notes = db.Column(db.Text, default='')
    status = db.Column(db.String(40), default='Por verificar')
    jurisdictions = db.relationship('Jurisdiction', secondary=treatment_countries, backref='treatments')

class LinkedRecord:
    id = db.Column(db.Integer, primary_key=True)
    treatment_id = db.Column(db.Integer, db.ForeignKey('treatment.id'), nullable=False)
    jurisdiction_id = db.Column(db.Integer, db.ForeignKey('jurisdiction.id'), nullable=False)

class Evidence(LinkedRecord, db.Model):
    name = db.Column(db.String(160), nullable=False)
    kind = db.Column(db.String(80), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    owner = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(40), default='Pendiente')
    reference = db.Column(db.Text, default='')
    treatment = db.relationship('Treatment', backref='evidences')
    jurisdiction = db.relationship('Jurisdiction')

class Transfer(LinkedRecord, db.Model):
    destination_id = db.Column(db.Integer, db.ForeignKey('jurisdiction.id'), nullable=False)
    data_type = db.Column(db.Text, nullable=False)
    exporter = db.Column(db.String(160), default='AndeClass S.A.C.')
    importer = db.Column(db.String(160), nullable=False)
    provider = db.Column(db.String(160), nullable=False)
    purpose = db.Column(db.Text, nullable=False)
    mechanism = db.Column(db.Text, default='Por verificar')
    contract = db.Column(db.Text, default='')
    security = db.Column(db.Text, default='')
    review_date = db.Column(db.String(10), default='')
    reviewer = db.Column(db.String(120), default='')
    evidence_id = db.Column(db.Integer, db.ForeignKey('evidence.id'))
    status = db.Column(db.String(40), default='Por verificar')
    treatment = db.relationship('Treatment', backref='transfers')
    jurisdiction = db.relationship('Jurisdiction', foreign_keys='Transfer.jurisdiction_id')
    destination = db.relationship('Jurisdiction', foreign_keys='Transfer.destination_id')
    evidence = db.relationship('Evidence')

class Risk(LinkedRecord, db.Model):
    name = db.Column(db.String(180), nullable=False)
    probability = db.Column(db.Integer, default=3)
    impact = db.Column(db.Integer, default=3)
    proposed_control = db.Column(db.Text, nullable=False)
    owner = db.Column(db.String(120), nullable=False)
    due_date = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(40), default='Abierto')
    treatment = db.relationship('Treatment', backref='risks')
    jurisdiction = db.relationship('Jurisdiction')

    @property
    def score(self):
        return self.probability * self.impact

    @property
    def level(self):
        # International transfers involving sensitive data raise the initial score band.
        score = self.score
        if self.treatment.sensitive and any(t.jurisdiction_id != t.destination_id for t in self.treatment.transfers):
            score = max(score, 15)
        return 'Crítico' if score >= 20 else 'Alto' if score >= 15 else 'Medio' if score >= 6 else 'Bajo'

class Control(LinkedRecord, db.Model):
    name = db.Column(db.String(180), nullable=False)
    domain = db.Column(db.String(60), nullable=False)
    owner = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(40), default='Por verificar')
    evidence_id = db.Column(db.Integer, db.ForeignKey('evidence.id'))
    reviewed_at = db.Column(db.String(10), default='')
    rationale = db.Column(db.Text, default='')
    treatment = db.relationship('Treatment', backref='controls')
    jurisdiction = db.relationship('Jurisdiction')
    evidence = db.relationship('Evidence')

class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(180), nullable=False)
    treatment_id = db.Column(db.Integer, db.ForeignKey('treatment.id'), nullable=False)
    detected_at = db.Column(db.String(16), nullable=False)
    owner = db.Column(db.String(120), nullable=False)
    data_type = db.Column(db.Text, nullable=False)
    affected = db.Column(db.Integer, nullable=False)
    sensitive = db.Column(db.Boolean, default=False)
    eu_users = db.Column(db.Boolean, default=False)
    countries = db.Column(db.String(200), nullable=False)
    provider_country = db.Column(db.String(120), default='Estados Unidos')
    cause = db.Column(db.Text, default='')
    consequences = db.Column(db.Text, default='')
    containment = db.Column(db.Text, default='')
    notifications = db.Column(db.Text, default='Pendiente de revisión')
    status = db.Column(db.String(60), default='En investigación')
    level = db.Column(db.String(30), default='Alto')
    stage = db.Column(db.Integer, default=0)
    treatment = db.relationship('Treatment', backref='incidents')

class IncidentEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incident.id'), nullable=False)
    stage = db.Column(db.Integer, nullable=False)
    note = db.Column(db.Text, nullable=False)
    decision = db.Column(db.String(80), default='')
    evidence_id = db.Column(db.Integer, db.ForeignKey('evidence.id'))
    actor = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    incident = db.relationship('Incident', backref=db.backref('events', order_by='IncidentEvent.id'))
    evidence = db.relationship('Evidence')

class RightRequest(LinkedRecord, db.Model):
    name = db.Column(db.String(160), nullable=False)
    kind = db.Column(db.String(80), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    owner = db.Column(db.String(120), nullable=False)
    due_date = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(40), default='Recibida')
    response = db.Column(db.Text, default='')
    evidence_id = db.Column(db.Integer, db.ForeignKey('evidence.id'))
    treatment = db.relationship('Treatment', backref='rights')
    jurisdiction = db.relationship('Jurisdiction')
    evidence = db.relationship('Evidence')

class Audit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor = db.Column(db.String(80), nullable=False)
    action = db.Column(db.String(80), nullable=False)
    module = db.Column(db.String(80), nullable=False)
    record_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=utcnow)
    before = db.Column(db.Text, default='')
    after = db.Column(db.Text, default='')

class Organization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    country = db.Column(db.String(120), nullable=False)
    sector = db.Column(db.String(160), nullable=False)
    reviewer = db.Column(db.String(120), default='Equipo de cumplimiento')

# Additive tables: existing SQLite records remain intact when upgrading the demo.
class JurisdictionReview(LinkedRecord, db.Model):
    __table_args__ = (db.UniqueConstraint('treatment_id', 'jurisdiction_id'),)
    applicability = db.Column(db.String(40), default='Por verificar')
    scope_reason = db.Column(db.Text, default='')
    legal_basis = db.Column(db.Text, default='')
    sensitive_condition = db.Column(db.Text, default='')
    secondary_decision = db.Column(db.String(60), default='Pendiente')
    secondary_basis = db.Column(db.Text, default='')
    status = db.Column(db.String(40), default='Por verificar')
    rationale = db.Column(db.Text, default='')
    evidence_id = db.Column(db.Integer, db.ForeignKey('evidence.id'))
    reviewer = db.Column(db.String(80), nullable=False)
    reviewed_at = db.Column(db.DateTime, default=utcnow)
    context_hash = db.Column(db.String(64), nullable=False)
    treatment = db.relationship('Treatment', backref='jurisdiction_reviews')
    jurisdiction = db.relationship('Jurisdiction')
    evidence = db.relationship('Evidence')

class RiskControl(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    risk_id = db.Column(db.Integer, db.ForeignKey('risk.id'), nullable=False)
    control_id = db.Column(db.Integer, db.ForeignKey('control.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('risk_id','control_id'),)
    risk = db.relationship('Risk', backref='control_links')
    control = db.relationship('Control', backref='risk_links')

class IncidentReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer, db.ForeignKey('incident.id'), nullable=False)
    jurisdiction_id = db.Column(db.Integer, db.ForeignKey('jurisdiction.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('incident_id','jurisdiction_id'),)
    applicability = db.Column(db.String(40), default='Por verificar')
    authority_decision = db.Column(db.String(40), default='Pendiente')
    subject_decision = db.Column(db.String(40), default='Pendiente')
    authority = db.Column(db.String(300), default='')
    consequence = db.Column(db.Text, default='')
    rationale = db.Column(db.Text, default='')
    deadline = db.Column(db.String(16), default='')
    deadline_reason = db.Column(db.Text, default='')
    evidence_id = db.Column(db.Integer, db.ForeignKey('evidence.id'))
    reviewer = db.Column(db.String(80), nullable=False)
    reviewed_at = db.Column(db.DateTime, default=utcnow)
    context_hash = db.Column(db.String(64), nullable=False)
    incident = db.relationship('Incident', backref='country_reviews')
    jurisdiction = db.relationship('Jurisdiction')
    evidence = db.relationship('Evidence')

class EvidenceFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    evidence_id = db.Column(db.Integer, db.ForeignKey('evidence.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    mime_type = db.Column(db.String(80), nullable=False)
    content = db.Column(db.LargeBinary, nullable=False)
    sha256 = db.Column(db.String(64), nullable=False)
    actor = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    evidence = db.relationship('Evidence', backref='files')

class SimulationRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    actor = db.Column(db.String(80), nullable=False)
    payload = db.Column(db.Text, nullable=False)
    result = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
