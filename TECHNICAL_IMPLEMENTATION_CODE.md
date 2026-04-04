# LEGAL AI PLATFORM: ТЕХНІЧНА РЕАЛІЗАЦІЯ
## Детальний код та архітектура для всіх 5 фаз

---

## ЧАСТИНА 1: АРХІТЕКТУРА БАЗДАНИХ (SQL + Alembic)

### migration_20260301_0011_legal_strategy_tables.py

```python
"""
Alembic migration: Add legal strategy tables (Phase 1-5)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import UUID, JSONB, ARRAY, String

def upgrade():
    # PHASE 1: Document intake & risk stratification
    op.create_table(
        'document_analysis_intake',
        sa.Column('id', UUID, primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column('user_id', UUID, nullable=False),
        sa.Column('document_id', UUID, nullable=False),
        
        # Classification
        sa.Column('classified_type', String, nullable=False),  # contract|decision|claim|...
        sa.Column('document_language', String),
        sa.Column('jurisdiction', String, nullable=False),  # UA|EU|RU|MIXED|OTHER
        
        # Parties & subject
        sa.Column('primary_party_role', String),  # plaintiff|defendant|creditor|debtor|...
        sa.Column('identified_parties', JSONB),  # [{name, inn, address, role}]
        sa.Column('subject_matter', String),  # commercial|labor|family|admin|...
        
        # Financial
        sa.Column('financial_exposure_amount', sa.Numeric),
        sa.Column('financial_exposure_currency', String),
        sa.Column('financial_exposure_type', String),  # claim|debt|damages|penalty|fee
        
        # Timeline
        sa.Column('document_date', sa.Date),
        sa.Column('deadline_from_document', sa.Date),
        sa.Column('urgency_level', String),  # critical|high|medium|low
        
        # Risk levels
        sa.Column('risk_level_legal', String),  # high|medium|low
        sa.Column('risk_level_procedural', String),
        sa.Column('risk_level_financial', String),
        
        # Issues
        sa.Column('detected_issues', JSONB),  # [{issue_type, severity, description, impact}]
        sa.Column('classifier_confidence', sa.Float),
        sa.Column('classifier_model', String),  # claude-3-5-sonnet|gpt-4|gemini
        
        sa.Column('raw_text_preview', sa.Text),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, onupdate=sa.func.now()),
        
        sa.ForeignKeyConstraint(['user_id'], ['auth.users.id']),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
        sa.Index('idx_intake_user_document', 'user_id', 'document_id'),
    )
    
    # Contract clause analysis
    op.create_table(
        'contract_clause_analysis',
        sa.Column('id', UUID, primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column('intake_id', UUID, nullable=False),
        
        sa.Column('clause_index', sa.Integer),
        sa.Column('clause_title', String),
        sa.Column('clause_text', sa.Text),
        sa.Column('clause_type', String),  # payment_terms|liability|ip|confidentiality|...
        
        # Risk
        sa.Column('risk_score', sa.Float),  # 0.0-1.0
        sa.Column('risk_category', String),  # compliance|financial|liability|performance|dispute
        
        # Issues
        sa.Column('conflicts_detected', JSONB),  # [{conflict_with_clause, reason}]
        sa.Column('ambiguity_score', sa.Float),
        sa.Column('missing_provisions', JSONB),  # [{missing, why_needed, impact}]
        
        # Recommendations
        sa.Column('applicable_law', JSONB),  # [{law_code, article, applicability}]
        sa.Column('recommended_change', String),
        
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        
        sa.ForeignKeyConstraint(['intake_id'], ['document_analysis_intake.id']),
        sa.Index('idx_clause_intake', 'intake_id'),
    )
    
    # Decision analysis
    op.create_table(
        'decision_analysis',
        sa.Column('id', UUID, primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column('intake_id', UUID, nullable=False),
        
        sa.Column('judge_name', String),
        sa.Column('court_name', String),
        sa.Column('court_instance', String),  # first_instance|appellate|supreme
        sa.Column('decision_date', sa.Date),
        sa.Column('case_number', String),
        
        sa.Column('legal_grounds', JSONB),  # [{law_code, article, how_applied}]
        sa.Column('key_facts', JSONB),  # [{fact, evidentiary_basis, relevance}]
        sa.Column('judge_reasoning', JSONB),  # [{conclusion, supporting_logic}]
        
        sa.Column('appeal_vulnerabilities', JSONB),  # [{weakness, why_appeallable, likelihood}]
        
        sa.Column('precedential_value', String),  # high|medium|low
        sa.Column('applicable_to_cases', JSONB),  # [{case_type, how_applicable}]
        
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        
        sa.ForeignKeyConstraint(['intake_id'], ['document_analysis_intake.id']),
    )
    
    # Identified risks
    op.create_table(
        'identified_risks',
        sa.Column('id', UUID, primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column('intake_id', UUID, nullable=False),
        
        sa.Column('risk_type', String),  # legal_gap|procedural_error|time_risk|...
        sa.Column('severity', String),  # critical|high|medium|low
        sa.Column('description', sa.Text),
        sa.Column('impact_if_unchecked', sa.Text),
        sa.Column('mitigation_strategy', sa.Text),
        
        sa.Column('affected_clause_ids', ARRAY(UUID)),
        
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        
        sa.ForeignKeyConstraint(['intake_id'], ['document_analysis_intake.id']),
    )
    
    # PHASE 2: Case-law precedent groups
    op.create_table(
        'case_law_precedent_groups',
        sa.Column('id', UUID, primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column('user_id', UUID, nullable=False),
        sa.Column('intake_id', UUID, nullable=False),
        
        sa.Column('pattern_type', String, nullable=False),  # winning|losing|neutral|emerging|split
        sa.Column('pattern_description', String),
        sa.Column('pattern_keywords', JSONB),  # [key terms]
        
        sa.Column('precedent_ids', ARRAY(UUID)),
        sa.Column('precedent_count', sa.Integer),
        sa.Column('pattern_strength', sa.Float),  # 0.0-1.0
        
        sa.Column('common_winning_arguments', JSONB),  # [{argument, citations, success_rate}]
        sa.Column('common_losing_arguments', JSONB),  # [{argument, why_failed, how_to_overcome}]
        sa.Column('counter_arguments', JSONB),  # [{expected_defense, how_to_preempt, cases}]
        
        sa.Column('mitigation_strategy', sa.Text),
        sa.Column('strategic_advantage', sa.Text),
        sa.Column('vulnerability_to_appeal', sa.Text),
        
        sa.Column('search_query', String),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        
        sa.ForeignKeyConstraint(['user_id'], ['auth.users.id']),
        sa.ForeignKeyConstraint(['intake_id'], ['document_analysis_intake.id']),
        sa.Index('idx_precedent_group_intake', 'intake_id'),
    )
    
    # Link between intake and case law
    op.create_table(
        'intake_case_law_refs',
        sa.Column('id', UUID, primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column('intake_id', UUID, nullable=False),
        sa.Column('case_law_id', UUID, nullable=False),
        
        sa.Column('relevance_score', sa.Float),
        sa.Column('relevance_reason', sa.Text),
        sa.Column('how_it_applies', String),  # favorable|unfavorable|neutral
        sa.Column('precedent_group_id', UUID),
        
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        
        sa.ForeignKeyConstraint(['intake_id'], ['document_analysis_intake.id']),
        sa.ForeignKeyConstraint(['case_law_id'], ['case_law_cache.id']),
        sa.ForeignKeyConstraint(['precedent_group_id'], ['case_law_precedent_groups.id']),
    )
    
    # Counter-argument map
    op.create_table(
        'counter_argument_map',
        sa.Column('id', UUID, primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column('intake_id', UUID, nullable=False),
        
        sa.Column('counterparty_likely_argument', sa.Text),
        sa.Column('why_they_will_use_it', sa.Text),
        sa.Column('success_probability_if_unopposed', sa.Float),
        
        sa.Column('our_preemptive_response', sa.Text),
        sa.Column('supporting_case_law', JSONB),  # [{case_number, court, year, holding}]
        sa.Column('legal_authority', sa.Text),
        
        sa.Column('risk_if_unopposed', sa.Text),
        
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        
        sa.ForeignKeyConstraint(['intake_id'], ['document_analysis_intake.id']),
    )
    
    # PHASE 3: Legal strategy blueprint
    op.create_table(
        'legal_strategy_blueprint',
        sa.Column('id', UUID, primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column('user_id', UUID, nullable=False),
        sa.Column('document_id', UUID, nullable=False),
        sa.Column('intake_id', UUID, nullable=False),
        sa.Column('precedent_group_id', UUID),
        
        sa.Column('immediate_actions', JSONB),
        sa.Column('procedural_roadmap', JSONB),
        sa.Column('evidence_strategy', JSONB),
        sa.Column('negotiation_playbook', JSONB),
        sa.Column('risk_heat_map', JSONB),
        sa.Column('damages_calculation', JSONB),
        sa.Column('critical_deadlines', JSONB),
        
        sa.Column('confidence_score', sa.Float),
        sa.Column('confidence_rationale', sa.Text),
        
        sa.Column('recommended_next_steps', sa.Text),
        
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, onupdate=sa.func.now()),
        
        sa.ForeignKeyConstraint(['user_id'], ['auth.users.id']),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
        sa.ForeignKeyConstraint(['intake_id'], ['document_analysis_intake.id']),
        sa.ForeignKeyConstraint(['precedent_group_id'], ['case_law_precedent_groups.id']),
        sa.Index('idx_strategy_user', 'user_id'),
        sa.Index('idx_strategy_document', 'document_id'),
    )
    
    # Strategy versions (for tracking changes)
    op.create_table(
        'strategy_blueprint_versions',
        sa.Column('id', UUID, primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column('strategy_id', UUID, nullable=False),
        
        sa.Column('version_number', sa.Integer),
        sa.Column('trigger_event', String),  # user_request|counterparty_move|deadline_passed
        sa.Column('trigger_description', sa.Text),
        
        sa.Column('changes_made', JSONB),
        sa.Column('confidence_score_change', sa.Float),
        
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        
        sa.ForeignKeyConstraint(['strategy_id'], ['legal_strategy_blueprint.id']),
    )
    
    # Case deadlines
    op.create_table(
        'case_deadlines',
        sa.Column('id', UUID, primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column('strategy_id', UUID, nullable=False),
        
        sa.Column('event_type', String),  # claim_filing|response|appeal_filing|evidence_submission|hearing_prep
        sa.Column('event_name', String),
        sa.Column('due_date', sa.Date),
        sa.Column('days_until', sa.Integer),
        sa.Column('consequence_if_missed', sa.Text),
        sa.Column('responsible_party', String),
        sa.Column('status', String),  # pending|completed|at_risk|overdue
        
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        
        sa.ForeignKeyConstraint(['strategy_id'], ['legal_strategy_blueprint.id']),
        sa.Index('idx_deadline_strategy', 'strategy_id'),
        sa.Index('idx_deadline_due_date', 'due_date'),
    )
    
    # PHASE 4: Generated document audit
    op.create_table(
        'document_generation_audit',
        sa.Column('id', UUID, primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column('document_id', UUID, nullable=False),
        sa.Column('strategy_blueprint_id', UUID),
        
        sa.Column('precedent_citations', ARRAY(String)),
        sa.Column('counter_argument_addresses', ARRAY(String)),
        sa.Column('evidence_positioning_notes', sa.Text),
        sa.Column('procedure_optimization_notes', sa.Text),
        sa.Column('appeal_proofing_notes', sa.Text),
        
        sa.Column('generated_at', sa.DateTime, server_default=sa.func.now()),
        
        sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
        sa.ForeignKeyConstraint(['strategy_blueprint_id'], ['legal_strategy_blueprint.id']),
    )
    
    # PHASE 5: Case outcome tracking
    op.create_table(
        'document_outcome_tracking',
        sa.Column('id', UUID, primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column('user_id', UUID, nullable=False),
        sa.Column('document_id', UUID, nullable=False),
        sa.Column('strategy_id', UUID, nullable=False),
        
        sa.Column('case_outcome', String),  # won|lost|settled|dismissed|appealed|pending
        
        sa.Column('judgment_date', sa.Date),
        sa.Column('judge_name', String),
        sa.Column('court_name', String),
        sa.Column('judgment_text', sa.Text),
        sa.Column('judgment_amount_awarded', sa.Numeric),
        sa.Column('judgment_amount_denied', sa.Numeric),
        
        sa.Column('predicted_confidence', sa.Float),
        sa.Column('actual_success_rate', sa.Float),
        sa.Column('prediction_accuracy', String),  # accurate|optimistic|pessimistic
        
        sa.Column('variance_explanation', sa.Text),
        
        sa.Column('successful_arguments', ARRAY(String)),
        sa.Column('failed_arguments', ARRAY(String)),
        sa.Column('successful_precedents', JSONB),
        sa.Column('failed_precedents', JSONB),
        
        sa.Column('appeal_outcome', String),
        sa.Column('appeal_judgment_date', sa.Date),
        
        sa.Column('final_amount_collected', sa.Numeric),
        sa.Column('collection_timeline_days', sa.Integer),
        
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, onupdate=sa.func.now()),
        
        sa.ForeignKeyConstraint(['user_id'], ['auth.users.id']),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
        sa.ForeignKeyConstraint(['strategy_id'], ['legal_strategy_blueprint.id']),
        sa.Index('idx_outcome_user', 'user_id'),
    )
    
    # Model performance metrics
    op.create_table(
        'model_performance_metrics',
        sa.Column('id', UUID, primary_key=True, server_default=sa.func.gen_random_uuid()),
        
        sa.Column('metric_type', String),  # classification_accuracy|precedent_relevance|...
        sa.Column('prediction', String),
        sa.Column('actual_outcome', String),
        sa.Column('confidence_score', sa.Float),
        sa.Column('correct', sa.Boolean),
        
        sa.Column('case_count', sa.Integer),
        sa.Column('accuracy_pct', sa.Float),
        
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        
        sa.Index('idx_metric_type', 'metric_type'),
    )


def downgrade():
    op.drop_table('model_performance_metrics')
    op.drop_table('document_outcome_tracking')
    op.drop_table('document_generation_audit')
    op.drop_table('case_deadlines')
    op.drop_table('strategy_blueprint_versions')
    op.drop_table('legal_strategy_blueprint')
    op.drop_table('counter_argument_map')
    op.drop_table('intake_case_law_refs')
    op.drop_table('case_law_precedent_groups')
    op.drop_table('identified_risks')
    op.drop_table('decision_analysis')
    op.drop_table('contract_clause_analysis')
    op.drop_table('document_analysis_intake')
```

---

## ЧАСТИНА 2: BACKEND IMPLEMENTATION (FastAPI)

### app/models/legal_strategy.py

```python
"""
SQLAlchemy models for legal strategy
"""
from sqlalchemy import Column, String, Float, Integer, Boolean, Date, DateTime, Text, UUID, ForeignKey, ARRAY, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class DocumentAnalysisIntake(Base):
    __tablename__ = "document_analysis_intake"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=False)
    document_id = Column(PG_UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    
    classified_type = Column(String)
    document_language = Column(String)
    jurisdiction = Column(String)
    
    primary_party_role = Column(String)
    identified_parties = Column(JSONB)
    subject_matter = Column(String)
    
    financial_exposure_amount = Column(Float)
    financial_exposure_currency = Column(String)
    financial_exposure_type = Column(String)
    
    document_date = Column(Date)
    deadline_from_document = Column(Date)
    urgency_level = Column(String)
    
    risk_level_legal = Column(String)
    risk_level_procedural = Column(String)
    risk_level_financial = Column(String)
    
    detected_issues = Column(JSONB)
    classifier_confidence = Column(Float)
    classifier_model = Column(String)
    
    raw_text_preview = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_intake_user_document', 'user_id', 'document_id'),
    )

class LegalStrategyBlueprint(Base):
    __tablename__ = "legal_strategy_blueprint"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=False)
    document_id = Column(PG_UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    intake_id = Column(PG_UUID(as_uuid=True), ForeignKey("document_analysis_intake.id"), nullable=False)
    precedent_group_id = Column(PG_UUID(as_uuid=True), ForeignKey("case_law_precedent_groups.id"))
    
    immediate_actions = Column(JSONB)
    procedural_roadmap = Column(JSONB)
    evidence_strategy = Column(JSONB)
    negotiation_playbook = Column(JSONB)
    risk_heat_map = Column(JSONB)
    damages_calculation = Column(JSONB)
    critical_deadlines = Column(JSONB)
    
    confidence_score = Column(Float)
    confidence_rationale = Column(Text)
    
    recommended_next_steps = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_strategy_user', 'user_id'),
        Index('idx_strategy_document', 'document_id'),
    )

class CaseDeadline(Base):
    __tablename__ = "case_deadlines"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(PG_UUID(as_uuid=True), ForeignKey("legal_strategy_blueprint.id"), nullable=False)
    
    event_type = Column(String)
    event_name = Column(String)
    due_date = Column(Date)
    days_until = Column(Integer)
    consequence_if_missed = Column(Text)
    responsible_party = Column(String)
    status = Column(String, default='pending')
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_deadline_strategy', 'strategy_id'),
        Index('idx_deadline_due_date', 'due_date'),
    )

class DocumentOutcomeTracking(Base):
    __tablename__ = "document_outcome_tracking"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=False)
    document_id = Column(PG_UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    strategy_id = Column(PG_UUID(as_uuid=True), ForeignKey("legal_strategy_blueprint.id"), nullable=False)
    
    case_outcome = Column(String)
    judgment_date = Column(Date)
    judge_name = Column(String)
    court_name = Column(String)
    judgment_text = Column(Text)
    judgment_amount_awarded = Column(Float)
    judgment_amount_denied = Column(Float)
    
    predicted_confidence = Column(Float)
    actual_success_rate = Column(Float)
    prediction_accuracy = Column(String)
    
    variance_explanation = Column(Text)
    
    successful_arguments = Column(ARRAY(String))
    failed_arguments = Column(ARRAY(String))
    successful_precedents = Column(JSONB)
    failed_precedents = Column(JSONB)
    
    appeal_outcome = Column(String)
    appeal_judgment_date = Column(Date)
    
    final_amount_collected = Column(Float)
    collection_timeline_days = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### app/routes/analyze_intake.py

```python
"""
Endpoints for Phase 1: Document classification and risk stratification
"""
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
import json
import PyPDF2
from docx import Document as DocxDocument

from app.models.legal_strategy import DocumentAnalysisIntake
from app.schemas.legal import DocumentIntakeResponse
from app.services.ai_classifier import classify_document_intake
from app.db import get_db
from app.auth import get_current_user_id

router = APIRouter(prefix="/api/analyze", tags=["analysis"])

class DocumentIntakeRequest(BaseModel):
    document_id: str
    include_contract_analysis: bool = False

@router.post("/intake", response_model=DocumentIntakeResponse)
async def analyze_document_intake(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Upload document and get classification + risk stratification.
    
    Workflow:
    1. Extract text from PDF/DOCX
    2. Call AI classifier
    3. Save results to database
    4. Return to frontend
    """
    
    try:
        # Step 1: Extract text
        if file.filename.endswith('.pdf'):
            text = extract_text_from_pdf(await file.read())
        elif file.filename.endswith('.docx'):
            text = extract_text_from_docx(await file.read())
        else:
            raise HTTPException(status_code=400, detail="Only PDF and DOCX supported")
        
        if not text or len(text) < 50:
            raise HTTPException(status_code=400, detail="Document text too short or empty")
        
        # Step 2: Create document record (if not exists)
        # Assume document_id was already created when file uploaded
        
        # Step 3: AI Classification
        classification_result = await classify_document_intake(
            text=text,
            filename=file.filename,
            user_id=user_id
        )
        
        # Step 4: Save to database
        intake_record = DocumentAnalysisIntake(
            user_id=user_id,
            classified_type=classification_result['classified_type'],
            jurisdiction=classification_result['jurisdiction'],
            primary_party_role=classification_result['primary_party_role'],
            subject_matter=classification_result['subject_matter'],
            financial_exposure_amount=classification_result.get('financial_exposure_amount'),
            financial_exposure_currency=classification_result.get('financial_exposure_currency'),
            financial_exposure_type=classification_result.get('financial_exposure_type'),
            document_date=classification_result.get('document_date'),
            deadline_from_document=classification_result.get('deadline_from_document'),
            urgency_level=classification_result['urgency_level'],
            risk_level_legal=classification_result['risk_level_legal'],
            risk_level_procedural=classification_result['risk_level_procedural'],
            risk_level_financial=classification_result['risk_level_financial'],
            detected_issues=classification_result['detected_issues'],
            identified_parties=classification_result.get('identified_parties'),
            classifier_confidence=classification_result['confidence'],
            classifier_model='claude-3-5-sonnet',
            raw_text_preview=text[:500]
        )
        
        db.add(intake_record)
        db.commit()
        db.refresh(intake_record)
        
        return DocumentIntakeResponse(
            id=intake_record.id,
            classified_type=intake_record.classified_type,
            jurisdiction=intake_record.jurisdiction,
            primary_party_role=intake_record.primary_party_role,
            subject_matter=intake_record.subject_matter,
            financial_exposure_amount=intake_record.financial_exposure_amount,
            urgency_level=intake_record.urgency_level,
            risk_level_legal=intake_record.risk_level_legal,
            risk_level_procedural=intake_record.risk_level_procedural,
            risk_level_financial=intake_record.risk_level_financial,
            detected_issues=intake_record.detected_issues,
            classifier_confidence=intake_record.classifier_confidence
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")

@router.get("/intake/{intake_id}", response_model=DocumentIntakeResponse)
async def get_intake_analysis(
    intake_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get saved intake analysis"""
    intake = db.query(DocumentAnalysisIntake).filter_by(
        id=intake_id,
        user_id=user_id
    ).first()
    
    if not intake:
        raise HTTPException(status_code=404, detail="Intake analysis not found")
    
    return DocumentIntakeResponse.from_orm(intake)

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF"""
    from io import BytesIO
    pdf = PyPDF2.PdfReader(BytesIO(pdf_bytes))
    text = ""
    for page in pdf.pages:
        text += page.extract_text()
    return text

def extract_text_from_docx(docx_bytes: bytes) -> str:
    """Extract text from DOCX"""
    from io import BytesIO
    doc = DocxDocument(BytesIO(docx_bytes))
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text
```

### app/services/ai_classifier.py

```python
"""
AI classifier service using Claude/OpenAI
"""
from typing import Dict, Any
import json
import os
from anthropic import Anthropic

# Initialize Anthropic client
client = Anthropic()

CLASSIFIER_SYSTEM_PROMPT = """You are an elite Ukrainian legal AI with 25+ years of experience.
Analyze the provided legal document and classify it with surgical precision.
Output ONLY valid JSON. No markdown, no explanations, no preamble.

[Full system prompt from Section 1.1 goes here]
"""

async def classify_document_intake(
    text: str,
    filename: str,
    user_id: str
) -> Dict[str, Any]:
    """
    Classify document using Claude API.
    """
    
    # Prepare prompt
    prompt = f"""
DOCUMENT TEXT (first 5000 chars):
{text[:5000]}

OUTPUT ONLY JSON:
"""
    
    # Call Claude API
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            system=CLASSIFIER_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract JSON from response
        response_text = response.content[0].text
        
        # Clean markdown if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        result = json.loads(response_text.strip())
        
        return result
    
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse AI response as JSON: {str(e)}")
    except Exception as e:
        raise Exception(f"AI classification error: {str(e)}")
```

### app/routes/precedent_mapping.py

```python
"""
Endpoints for Phase 2: Precedent mapping
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json
from datetime import datetime

from app.models.legal_strategy import (
    DocumentAnalysisIntake, CaseLawPrecedentGroup, 
    CounterArgumentMap
)
from app.services.precedent_mapper import generate_precedent_map
from app.db import get_db
from app.auth import get_current_user_id

router = APIRouter(prefix="/api/precedent", tags=["precedent"])

@router.post("/map/{intake_id}")
async def generate_precedent_map_endpoint(
    intake_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Generate precedent map for intake analysis.
    """
    
    # Get intake
    intake = db.query(DocumentAnalysisIntake).filter_by(
        id=intake_id,
        user_id=user_id
    ).first()
    
    if not intake:
        raise HTTPException(status_code=404, detail="Intake not found")
    
    # Generate precedent analysis
    precedent_map = await generate_precedent_map(
        intake=intake,
        db=db
    )
    
    # Save results
    for pattern in precedent_map['winning_patterns'] + precedent_map.get('losing_patterns', []):
        group = CaseLawPrecedentGroup(
            user_id=user_id,
            intake_id=intake_id,
            pattern_type=pattern['pattern_type'],
            pattern_description=pattern.get('pattern_name'),
            precedent_ids=pattern.get('precedent_ids'),
            precedent_count=len(pattern.get('precedent_ids', [])),
            pattern_strength=pattern.get('pattern_strength', 0.5),
            common_winning_arguments=pattern.get('common_winning_arguments'),
            common_losing_arguments=pattern.get('common_losing_arguments'),
            counter_arguments=pattern.get('counter_arguments'),
            mitigation_strategy=pattern.get('mitigation_strategy'),
            strategic_advantage=pattern.get('strategic_advantage')
        )
        db.add(group)
    
    db.commit()
    
    return {
        "intake_id": intake_id,
        "winning_patterns_count": len(precedent_map['winning_patterns']),
        "losing_patterns_count": len(precedent_map.get('losing_patterns', [])),
        "counter_arguments_mapped": len(precedent_map.get('counter_arguments', [])),
        "ready_for_strategy": True
    }
```

### app/routes/strategy_blueprint.py

```python
"""
Endpoints for Phase 3: Strategy generation
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.legal_strategy import (
    DocumentAnalysisIntake, LegalStrategyBlueprint, 
    CaseDeadline, CaseLawPrecedentGroup
)
from app.services.strategy_generator import generate_strategy_blueprint
from app.db import get_db
from app.auth import get_current_user_id

router = APIRouter(prefix="/api/strategy", tags=["strategy"])

@router.post("/blueprint/{intake_id}")
async def generate_blueprint_endpoint(
    intake_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Generate complete legal strategy for case.
    """
    
    # Get intake + precedents
    intake = db.query(DocumentAnalysisIntake).filter_by(
        id=intake_id,
        user_id=user_id
    ).first()
    
    if not intake:
        raise HTTPException(status_code=404, detail="Intake not found")
    
    precedent_groups = db.query(CaseLawPrecedentGroup).filter_by(
        intake_id=intake_id
    ).all()
    
    if not precedent_groups:
        raise HTTPException(status_code=400, detail="Run precedent mapping first")
    
    # Generate strategy
    strategy_data = await generate_strategy_blueprint(
        intake=intake,
        precedent_groups=precedent_groups,
        db=db
    )
    
    # Save strategy
    strategy = LegalStrategyBlueprint(
        user_id=user_id,
        document_id=intake.document_id,
        intake_id=intake_id,
        immediate_actions=strategy_data['immediate_actions'],
        procedural_roadmap=strategy_data['procedural_roadmap'],
        evidence_strategy=strategy_data['evidence_strategy'],
        negotiation_playbook=strategy_data['negotiation_playbook'],
        risk_heat_map=strategy_data['risk_heat_map'],
        damages_calculation=strategy_data.get('damages_calculation'),
        critical_deadlines=strategy_data['critical_deadlines'],
        confidence_score=strategy_data['confidence_score'],
        confidence_rationale=strategy_data['confidence_rationale'],
        recommended_next_steps=strategy_data['recommended_next_steps']
    )
    db.add(strategy)
    db.flush()
    
    # Create deadline records
    for deadline in strategy_data['critical_deadlines']:
        due_date = datetime.fromisoformat(deadline['due_date']).date()
        days_until = (due_date - datetime.now().date()).days
        
        case_deadline = CaseDeadline(
            strategy_id=strategy.id,
            event_type=deadline['event_type'],
            event_name=deadline['event_name'],
            due_date=due_date,
            days_until=days_until,
            consequence_if_missed=deadline['consequence']
        )
        db.add(case_deadline)
    
    db.commit()
    
    return {
        "strategy_id": strategy.id,
        "confidence": strategy.confidence_score,
        "immediate_actions": len(strategy.immediate_actions),
        "critical_deadlines": len([d for d in db.query(CaseDeadline).filter_by(strategy_id=strategy.id)])
    }
```

### app/routes/generate_with_strategy.py

```python
"""
Endpoints for Phase 4: Strategy-driven document generation
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json

from app.models.legal_strategy import LegalStrategyBlueprint, DocumentAnalysisIntake
from app.models.documents import Document
from app.services.strategic_generator import generate_strategic_document
from app.services.docx_export import export_to_docx
from app.db import get_db
from app.auth import get_current_user_id

router = APIRouter(prefix="/api/documents", tags=["documents"])

@router.post("/generate-with-strategy")
async def generate_with_strategy(
    strategy_id: str,
    document_type: str,  # claim_form|response|appeal_brief|etc
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    additional_context: str = None
):
    """
    Generate document optimized by strategy.
    
    Produces:
    - Strategic claim form (if document_type=claim_form)
    - Strategic response (if document_type=response)
    - Appeal brief (if document_type=appeal_brief)
    - etc.
    """
    
    # Get strategy
    strategy = db.query(LegalStrategyBlueprint).filter_by(
        id=strategy_id,
        user_id=user_id
    ).first()
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    intake = db.query(DocumentAnalysisIntake).get(strategy.intake_id)
    document = db.query(Document).get(strategy.document_id)
    
    # Generate strategic document
    generated_content = await generate_strategic_document(
        document_type=document_type,
        strategy=strategy,
        intake=intake,
        document_text="[full document text]",  # TODO: extract from document
        precedents=[],  # TODO: get from precedent_groups
        counter_arguments=[],  # TODO: get from counter_argument_map
        additional_context=additional_context
    )
    
    # Save as new document
    new_doc = Document(
        user_id=user_id,
        document_type=document_type,
        source_strategy_id=strategy_id,
        content=generated_content['body'],
        precedent_citations=generated_content['citations'],
        appeal_proofing_notes=generated_content['appeal_notes'],
        counter_arg_addresses=generated_content['counter_arg_addresses'],
        evidence_positioning=generated_content['evidence_notes']
    )
    db.add(new_doc)
    db.commit()
    
    # Export to DOCX
    docx_path = await export_to_docx(
        content=generated_content['body'],
        title=f"{document_type.upper()} - {intake.subject_matter}"
    )
    
    return {
        "document_id": new_doc.id,
        "document_type": document_type,
        "docx_download_url": f"/api/documents/{new_doc.id}/export?format=docx",
        "precedent_count": len(generated_content['citations']),
        "strategy_applied": strategy_id
    }
```

---

## ЧАСТИНА 3: AI INTEGRATION

### app/services/ai_provider.py

```python
"""
Unified AI provider interface (Claude, GPT-4, Gemini)
"""
import os
import json
from anthropic import Anthropic
from openai import OpenAI

# Initialize clients
anthropic_client = Anthropic()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def call_ai_provider(
    model: str,  # claude-3-5-sonnet|gpt-4|gemini-pro
    system: str,
    user_message: str,
    temperature: float = 0.2,
    max_tokens: int = 2000
) -> str:
    """
    Call AI provider with fallback support.
    """
    
    ai_provider = os.getenv("AI_PROVIDER", "anthropic")
    
    if ai_provider == "anthropic" or "claude" in model:
        response = anthropic_client.messages.create(
            model=model or "claude-3-5-sonnet-20241022",
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        return response.content[0].text
    
    elif ai_provider == "openai" or "gpt" in model:
        response = openai_client.chat.completions.create(
            model=model or "gpt-4-turbo",
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        return response.choices[0].message.content
    
    else:
        raise ValueError(f"Unsupported AI provider: {ai_provider}")
```

---

## ЧАСТИНА 4: FRONTEND COMPONENTS (Next.js + React)

### app/dashboard/strategy/page.tsx

```typescript
'use client'

import { useState } from 'react'
import { AlertCircle, CheckCircle, Clock, TrendingUp } from 'lucide-react'

interface StrategyPageProps {
  intakeId: string
}

export default function StrategyPage({ intakeId }: StrategyPageProps) {
  const [strategy, setStrategy] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const generateStrategy = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/strategy/blueprint/${intakeId}`, {
        method: 'POST'
      })
      const data = await response.json()
      setStrategy(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (!strategy) {
    return (
      <div className="space-y-6">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h2 className="text-xl font-bold mb-2">Generate Strategy</h2>
          <p className="text-gray-600 mb-4">
            Based on your intake analysis and precedent research, generate a comprehensive legal strategy.
          </p>
          <button
            onClick={generateStrategy}
            disabled={loading}
            className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
          >
            {loading ? 'Generating...' : 'Generate Strategy'}
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex gap-2">
            <AlertCircle className="text-red-600" size={20} />
            <div>
              <p className="font-semibold text-red-900">Error</p>
              <p className="text-red-700">{error}</p>
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Confidence Score */}
      <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-lg p-6">
        <h3 className="text-lg font-bold mb-2">Confidence Score</h3>
        <div className="flex items-center gap-4">
          <div className="text-4xl font-bold text-green-600">
            {Math.round(strategy.confidence * 100)}%
          </div>
          <p className="text-gray-600">
            High confidence in case success. Based on strong precedent support and solid evidence.
          </p>
        </div>
      </div>

      {/* Immediate Actions */}
      <div className="border rounded-lg p-6">
        <h3 className="text-lg font-bold mb-4">Immediate Actions (Next 14 Days)</h3>
        <div className="space-y-3">
          {strategy.immediate_actions?.map((action, idx) => (
            <div key={idx} className="border-l-4 border-red-500 pl-4 py-2 bg-red-50 rounded">
              <div className="flex gap-2">
                <Clock size={20} className="text-red-600 flex-shrink-0" />
                <div>
                  <p className="font-semibold">{action.action}</p>
                  <p className="text-sm text-gray-600">
                    Due: {action.deadline} ({action.days_from_now} days)
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Critical Deadlines */}
      <div className="border rounded-lg p-6">
        <h3 className="text-lg font-bold mb-4">Critical Deadlines</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-4 py-2 text-left">Event</th>
                <th className="px-4 py-2 text-left">Due Date</th>
                <th className="px-4 py-2 text-left">Days Until</th>
              </tr>
            </thead>
            <tbody>
              {strategy.critical_deadlines?.map((deadline, idx) => (
                <tr key={idx} className="border-b">
                  <td className="px-4 py-2">{deadline.event_name}</td>
                  <td className="px-4 py-2">{deadline.due_date}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-1 rounded text-white font-semibold ${
                      deadline.days_until <= 5 ? 'bg-red-600' :
                      deadline.days_until <= 14 ? 'bg-yellow-600' : 'bg-green-600'
                    }`}>
                      {deadline.days_until} days
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Generate Documents Button */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-bold mb-2">Next Step: Generate Documents</h3>
        <p className="text-gray-600 mb-4">
          Generate strategic court documents optimized by this strategy.
        </p>
        <button className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700">
          Generate Strategic Documents →
        </button>
      </div>
    </div>
  )
}
```

---

END OF TECHNICAL IMPLEMENTATION
