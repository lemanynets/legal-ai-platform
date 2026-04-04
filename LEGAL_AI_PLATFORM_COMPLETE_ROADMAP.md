# LEGAL AI PLATFORM: ПОЛНИЙ ПЛАН РОЗРОБКИ
## Від MVP до Top-Tier Legal Tech (5 Фаз)

---

## ЧАСТИНА 1: АРХІТЕКТУРА ТА АНАЛІЗ ЛАКУН

### Поточна архітектура (README)
- ✅ FastAPI backend + Next.js frontend
- ✅ PostgreSQL + Supabase Auth
- ✅ OpenAI/Claude/Gemini API integration
- ✅ DOCX/PDF export
- ✅ Case-law caching
- ✅ Full Lawyer модуль (базовий)

### Критичні пробіли (Top-Tier Benchmark)
| Компонента | Поточно | Top-Tier | Вплив |
|-----------|---------|----------|-------|
| Документ-аналіз | Простий чат | Риск-стратифікація + OSINT | HIGH |
| Case-law grounding | Додати цитати | Precedent mapping + counter-args | HIGH |
| Генерація | Fill-template | Strategy-driven generation | HIGH |
| Процедурна логіка | Базова | Дедлайни + судові типи + escalation | MEDIUM |
| Negotiation layer | Немає | Playbook + price anchoring | MEDIUM |

---

## ЧАСТИНА 2: 5-ФАЗОВИЙ ПЛАН РОЗРОБКИ

### ФАЗА 1: DOCUMENT INTAKE & RISK STRATIFICATION (2 тижні)

#### 1.1 Database Schema
```sql
-- Класифікація та ризик документів
CREATE TABLE document_analysis_intake (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    document_id UUID NOT NULL REFERENCES documents(id),
    
    -- Класифікація
    classified_type VARCHAR NOT NULL,  -- contract|court_decision|claim_notice|regulatory_letter|agreement|judgment
    document_language VARCHAR,         -- uk|ru|en
    jurisdiction VARCHAR NOT NULL,    -- UA|EU|RU|other
    
    -- Сторони та предмет
    primary_party_role VARCHAR,       -- plaintiff|defendant|creditor|debtor|claimant|respondent|third_party
    identified_parties JSONB,         -- [{name, inn, address, role}]
    subject_matter VARCHAR,           -- commercial|labor|family|admin|intellectual|real_estate|tax|employment
    
    -- Фінансова експозиція
    financial_exposure_amount DECIMAL,
    financial_exposure_currency VARCHAR,
    financial_exposure_type VARCHAR,  -- claim|debt|damages|penalty|fee
    
    -- Строкові параметри
    document_date DATE,
    deadline_from_document DATE,
    urgency_level VARCHAR,            -- critical|high|medium|low
    
    -- Ризик-матриця (базова)
    risk_level_legal VARCHAR,         -- high|medium|low (법적 ризик)
    risk_level_procedural VARCHAR,    -- high|medium|low (процедурний)
    risk_level_financial VARCHAR,     -- high|medium|low (фінансовий)
    
    -- Виявлені проблеми
    detected_issues JSONB,            -- [{issue_type, severity, description}]
    
    -- Класифікаційна впевненість
    classifier_confidence FLOAT,      -- 0.0-1.0
    classifier_model VARCHAR,         -- claude-3-5-sonnet|gpt-4|gemini-pro
    
    -- Метаданні
    raw_text_preview TEXT,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    
    CONSTRAINT valid_risk_level CHECK (risk_level_legal IN ('high', 'medium', 'low')),
    CONSTRAINT valid_urgency CHECK (urgency_level IN ('critical', 'high', 'medium', 'low'))
);

-- Структурний аналіз (для договорів)
CREATE TABLE contract_clause_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intake_id UUID NOT NULL REFERENCES document_analysis_intake(id),
    
    clause_index INT,
    clause_title VARCHAR,
    clause_text TEXT,
    clause_type VARCHAR,  -- payment_terms|liability|ip|confidentiality|termination|force_majeure|dispute_resolution|warranty
    
    -- Ризик-оцінка
    risk_score FLOAT,     -- 0.0-1.0 (0=безпечна, 1=максимальний ризик)
    risk_category VARCHAR,  -- compliance_risk|financial_risk|liability_risk|performance_risk|dispute_risk
    
    -- Конфлікти і проблеми
    conflicts_detected JSONB,    -- [{conflict_with_clause, reason}]
    ambiguity_score FLOAT,
    missing_provisions JSONB,    -- [{missing, why_needed, impact}]
    
    -- Законодавчо-обґрунтовані рекомендації
    applicable_law JSONB,        -- [{law_code, article, applicability}]
    recommended_change VARCHAR,
    
    created_at TIMESTAMP DEFAULT now()
);

-- Структурний аналіз (для судових рішень)
CREATE TABLE decision_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intake_id UUID NOT NULL REFERENCES document_analysis_intake(id),
    
    -- Основні дані рішення
    judge_name VARCHAR,
    court_name VARCHAR,
    court_instance VARCHAR,  -- first_instance|appellate|supreme
    decision_date DATE,
    case_number VARCHAR,
    
    -- Аналіз
    legal_grounds JSONB,     -- [{law_code, article, how_applied}]
    key_facts JSONB,         -- [{fact, evidentiary_basis, relevance}]
    judge_reasoning JSONB,   -- [{conclusion, supporting_logic}]
    
    -- Уразливості для оскарження
    appeal_vulnerabilities JSONB,  -- [{weakness, why_appeallable, likelihood_of_success}]
    
    -- Прецедентна цінність
    precedential_value VARCHAR,  -- high|medium|low
    applicable_to_cases JSONB,   -- [{case_type, how_applicable}]
    
    created_at TIMESTAMP DEFAULT now()
);

-- Виявлені риски (універсальна таблиця)
CREATE TABLE identified_risks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intake_id UUID NOT NULL REFERENCES document_analysis_intake(id),
    
    risk_type VARCHAR,         -- legal_gap|procedural_error|time_risk|evidence_risk|counterparty_defense
    severity VARCHAR,          -- critical|high|medium|low
    description TEXT,
    
    impact_if_unchecked TEXT,
    mitigation_strategy TEXT,
    
    affected_clause_ids UUID[],  --링크 до contract_clause_analysis
    
    created_at TIMESTAMP DEFAULT now()
);
```

#### 1.2 Backend Endpoints
```python
# routes/analyze_intake.py

from fastapi import APIRouter, File, UploadFile, Depends
from typing import Optional
from pydantic import BaseModel
import PyPDF2
from docx import Document as DocxDocument

router = APIRouter(prefix="/api/analyze", tags=["analysis"])

class DocumentIntakeResponse(BaseModel):
    id: str
    classified_type: str
    jurisdiction: str
    primary_party_role: str
    subject_matter: str
    financial_exposure_amount: Optional[float]
    urgency_level: str
    risk_level_legal: str
    risk_level_procedural: str
    risk_level_financial: str
    detected_issues: list
    classifier_confidence: float

@router.post("/intake", response_model=DocumentIntakeResponse)
async def analyze_document_intake(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id)
):
    """
    Завантажити документ і отримати класифікацію + риск-стратифікацію.
    
    Процес:
    1. Извлечь текст (PDF/DOCX)
    2. Отправить в AI classifier
    3. Сохранить результаты в document_analysis_intake
    4. Вернуть результаты
    """
    
    # Крок 1: Извлечение текста
    if file.filename.endswith('.pdf'):
        text = extract_text_from_pdf(file)
    elif file.filename.endswith('.docx'):
        text = extract_text_from_docx(file)
    else:
        raise ValueError("Только PDF и DOCX")
    
    # Крок 2: AI классификация
    intake_result = await classify_document_intake(
        text=text,
        filename=file.filename,
        file_size=len(text),
        user_id=user_id
    )
    
    # Крок 3: Сохранение в БД
    intake_record = DocumentAnalysisIntake(
        user_id=user_id,
        document_id=document_id,
        classified_type=intake_result['classified_type'],
        jurisdiction=intake_result['jurisdiction'],
        primary_party_role=intake_result['primary_party_role'],
        subject_matter=intake_result['subject_matter'],
        financial_exposure_amount=intake_result.get('financial_exposure_amount'),
        urgency_level=intake_result['urgency_level'],
        risk_level_legal=intake_result['risk_level_legal'],
        risk_level_procedural=intake_result['risk_level_procedural'],
        risk_level_financial=intake_result['risk_level_financial'],
        detected_issues=intake_result['detected_issues'],
        classifier_confidence=intake_result['confidence'],
        classifier_model='claude-3-5-sonnet'
    )
    db.add(intake_record)
    db.commit()
    
    return intake_record

@router.get("/intake/{intake_id}")
async def get_intake_analysis(
    intake_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Получить сохраненный анализ документа"""
    return db.query(DocumentAnalysisIntake).filter_by(
        id=intake_id,
        user_id=user_id
    ).first()

# helpers/classifier.py

async def classify_document_intake(
    text: str,
    filename: str,
    file_size: int,
    user_id: str
) -> dict:
    """
    AI-powered классификатор документов.
    Используем Claude или GPT-4 для анализа.
    """
    
    prompt = f"""
You are a Ukrainian legal document classifier with 20+ years of experience.
Analyze the provided legal document and classify it.

DOCUMENT TEXT (first 5000 chars):
{text[:5000]}

OUTPUT ONLY JSON (no markdown, no explanations):
{{
    "classified_type": "contract|court_decision|claim_notice|regulatory_letter|agreement|judgment",
    "document_language": "uk|ru|en",
    "jurisdiction": "UA|EU|RU|other",
    "primary_party_role": "plaintiff|defendant|creditor|debtor|claimant|respondent|third_party",
    
    "identified_parties": [
        {{
            "name": "...",
            "inn": "...",
            "address": "...",
            "role": "party1|party2|third_party"
        }}
    ],
    
    "subject_matter": "commercial|labor|family|admin|intellectual|real_estate|tax|employment|debt|contract",
    
    "financial_exposure_amount": 50000,
    "financial_exposure_currency": "UAH",
    "financial_exposure_type": "claim|debt|damages|penalty",
    
    "document_date": "2024-01-15",
    "deadline_from_document": "2024-02-15",
    
    "urgency_level": "critical|high|medium|low",
    
    "risk_level_legal": "high|medium|low",
    "risk_level_procedural": "high|medium|low", 
    "risk_level_financial": "high|medium|low",
    
    "detected_issues": [
        {{
            "issue_type": "missing_deadline|procedural_error|unclear_parties|ambiguous_claim|statute_of_limitations|missing_evidence",
            "severity": "critical|high|medium|low",
            "description": "...",
            "impact": "..."
        }}
    ],
    
    "confidence": 0.85
}}
"""
    
    response = await call_ai_provider(
        model='claude-3-5-sonnet',
        system="You are a Ukrainian legal AI. Output ONLY valid JSON.",
        user_message=prompt,
        temperature=0.3,
        max_tokens=2000
    )
    
    # Parse JSON response
    import json
    result = json.loads(response)
    return result
```

#### 1.3 AI Classifier Prompt
```
# SYSTEM PROMPT: Document Intake Classifier

You are an elite Ukrainian legal AI trained by top-20 law firms.
Your task: Classify legal documents with surgical precision.

## Input Format
You receive:
1. Document text (first 5000 characters)
2. Filename
3. File size
4. User role (if available)

## Classification Framework

### DOCUMENT TYPE (11 categories)
- **contract**: 2-party binding agreement (sale, service, lease, etc.)
- **court_decision**: Judge ruling (verdict, judgment, resolution)
- **claim_notice**: Initial claim/petition to court (позов, заявка)
- **regulatory_letter**: Letter from gov agency, tax authority, prosecutor
- **agreement**: Settlement, memorandum, protocol
- **demand_letter**: Formal demand (претензія) before litigation
- **judgment**: Court ruling WITH case details
- **appeal_brief**: Appeal to appellate court
- **motion**: Motion to court (клопотання)
- **statute_notice**: Notice of statutory deadline

### JURISDICTION
Identify where this applies:
- **UA**: Ukrainian law, Ukrainian courts only
- **EU**: EU jurisdiction/law
- **RU**: Russian law (legacy docs)
- **MIXED**: Multi-jurisdictional
- **OTHER**: Unknown

### PRIMARY PARTY ROLE
- plaintiff = actor suing
- defendant = party being sued
- creditor = demanding payment
- debtor = owing money
- claimant = making claim
- respondent = responding to claim
- third_party = not directly involved

### SUBJECT MATTER (13 categories)
- **commercial**: B2B disputes, supply contracts, trade
- **labor**: Employment, wages, firing, working conditions
- **family**: Divorce, custody, inheritance, alimony
- **admin**: Appeals against government decisions
- **intellectual**: Copyright, trademark, patent disputes
- **real_estate**: Land, property, eviction
- **tax**: Tax disputes, VAT, customs
- **employment**: Labor relationships, non-compete
- **debt**: Loan defaults, unpaid invoices, credit disputes
- **contract**: General contract disputes
- **criminal_administrative**: Fines, administrative liability
- **consumer**: Consumer rights, product liability
- **liability**: Negligence, damage claims

### FINANCIAL EXPOSURE
Extract exact amount if present:
- Look for numbers in UAH, EUR, USD, RUB
- Identify type: claim amount vs. defendant's liability
- Mark as "unknown" if not explicit

### URGENCY LEVEL (Based on Signals)
- **critical** (5-10 days): Imminent deadline, criminal matter, urgent regulatory requirement
- **high** (10-30 days): Appeal deadline approaching, limitation period active
- **medium** (30-90 days): Standard litigation deadline
- **low** (90+ days): Planning phase, no immediate deadline

### RISK STRATIFICATION

#### LEGAL RISK (High/Medium/Low)
Signals of HIGH legal risk:
- Unclear statute of limitations
- Ambiguous parties
- Conflicting contractual terms
- Missing mandatory procedures
- Unfavorable jurisdiction
- Weak precedent support

Signals of MEDIUM legal risk:
- Some procedural gaps but recoverable
- Mixed case law precedents
- Standard dispute category

Signals of LOW legal risk:
- Clear law applies
- Strong precedent support
- No ambiguity in parties/claims

#### PROCEDURAL RISK (High/Medium/Low)
Signals of HIGH procedural risk:
- Wrong court type chosen
- Missed deadlines approaching
- Incorrect document form
- Missing mandatory attachments
- Locus standi issues (party has no right to sue)

Signals of MEDIUM procedural risk:
- Some procedural steps missing but recoverable
- Tight timeline

Signals of LOW procedural risk:
- All procedural requirements met
- No urgent timing issues

#### FINANCIAL RISK (High/Medium/Low)
Signals of HIGH financial risk:
- Amount > 1,000,000 UAH AND unclear recovery
- Multiple creditors (priority issues)
- Insolvent counterparty
- No security/guarantee
- Contingent liability

Signals of MEDIUM financial risk:
- Amount > 100,000 UAH
- Some dispute over amount
- Standard collection case

Signals of LOW financial risk:
- Amount < 100,000 UAH
- Clear obligation
- Creditworthy counterparty

### DETECTED ISSUES (Categories)
Return array of specific issues:
1. **missing_deadline**: "Document mentions 30-day deadline, but today is day 25"
2. **procedural_error**: "Plaintiff not served with notice yet - must happen before filing"
3. **unclear_parties**: "Second party name is incomplete: 'OOO Firma...'"
4. **ambiguous_claim**: "Claim amount unclear: mentions both 50,000 and 75,000 UAH"
5. **statute_of_limitations**: "Claim is for event in 2019, 6-year limit expires in 2025"
6. **missing_evidence**: "Claim alleges damages but no estimates provided"
7. **jurisdiction_mismatch**: "Document is Russian contract but jurisdiction set to UA"
8. **locus_standi**: "Plaintiff appears to lack standing: not party to agreement"
9. **wrong_defendant**: "Multiple potential defendants - unclear who should be sued"
10. **res_judicata**: "Similar claim was already decided in Case #123/2023"

## Output JSON Structure

```json
{
    "classified_type": "contract|court_decision|claim_notice|...",
    "document_language": "uk|ru|en",
    "jurisdiction": "UA|EU|RU|MIXED|OTHER",
    "primary_party_role": "plaintiff|defendant|creditor|debtor|claimant|respondent|third_party",
    
    "identified_parties": [
        {
            "name": "ПриватБанк ПАО",
            "inn": "14360570",
            "address": "м. Київ, вул. Льва Толстого, 1-3",
            "role": "creditor"
        }
    ],
    
    "subject_matter": "commercial|labor|...",
    "financial_exposure_amount": 250000,
    "financial_exposure_currency": "UAH",
    "financial_exposure_type": "claim|debt|damages|penalty|fee",
    
    "document_date": "2024-01-15",
    "deadline_from_document": "2024-02-15",
    
    "urgency_level": "critical|high|medium|low",
    
    "risk_level_legal": "high|medium|low",
    "risk_level_procedural": "high|medium|low",
    "risk_level_financial": "high|medium|low",
    
    "detected_issues": [
        {
            "issue_type": "missing_deadline",
            "severity": "critical",
            "description": "Document dated 2024-01-15, 30-day deadline = 2024-02-14",
            "impact": "If not filed by 2024-02-14, claim is time-barred"
        }
    ],
    
    "confidence": 0.92
}
```

## Confidence Scoring
- 0.95-1.0: All document markers clear, unambiguous
- 0.85-0.94: Most markers clear, minor ambiguities
- 0.70-0.84: Some ambiguity, but confident classification
- 0.50-0.69: Significant ambiguity, may need user review
- <0.50: Too ambiguous, return confidence and ask user for clarification

## Special Cases
- **Multilingual docs**: Classify by PRIMARY language, note secondary
- **Partially corrupted docs**: Use available text, note limitations
- **Templates**: If document is blank template, classify by title/structure
- **Mixed docs**: If contains multiple documents, identify the PRIMARY document type
```

#### 1.4 Contract Clause Analysis Endpoint
```python
@router.post("/contract-clauses/{intake_id}")
async def analyze_contract_clauses(
    intake_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Для контрактов: провести анализ клаузула-за-клаузулой.
    Результаты: контрактные риски, конфликты, рекомендации.
    """
    
    intake = db.query(DocumentAnalysisIntake).filter_by(
        id=intake_id,
        user_id=user_id
    ).first()
    
    if intake.classified_type != "contract":
        raise ValueError("This endpoint is for contracts only")
    
    # Получить полный текст документа
    document = db.query(Document).get(intake.document_id)
    contract_text = extract_full_text(document)
    
    # Разбить на клаузулы
    clauses = split_contract_into_clauses(contract_text)
    
    # Для каждой клаузулы: AI анализ
    for idx, clause in enumerate(clauses):
        clause_analysis = await analyze_single_clause(
            clause_text=clause['text'],
            clause_index=idx,
            contract_type=intake.subject_matter,
            jurisdiction=intake.jurisdiction
        )
        
        # Сохранить результаты
        clause_record = ContractClauseAnalysis(
            intake_id=intake_id,
            clause_index=idx,
            clause_title=clause.get('title'),
            clause_text=clause['text'],
            clause_type=clause_analysis['clause_type'],
            risk_score=clause_analysis['risk_score'],
            risk_category=clause_analysis['risk_category'],
            conflicts_detected=clause_analysis['conflicts'],
            ambiguity_score=clause_analysis['ambiguity_score'],
            missing_provisions=clause_analysis['missing_provisions'],
            applicable_law=clause_analysis['applicable_law'],
            recommended_change=clause_analysis['recommended_change']
        )
        db.add(clause_record)
    
    db.commit()
    
    # Вернуть результаты + общие конфликты между клаузулами
    inter_clause_conflicts = detect_inter_clause_conflicts(clauses)
    
    return {
        "intake_id": intake_id,
        "total_clauses": len(clauses),
        "clauses_analyzed": [c.dict() for c in db.query(ContractClauseAnalysis).filter_by(intake_id=intake_id).all()],
        "inter_clause_conflicts": inter_clause_conflicts
    }
```

#### 1.5 Frontend UI Components (Next.js)
```typescript
// app/dashboard/analyze/page.tsx

'use client'

import { useState } from 'react'
import { Upload, AlertCircle, CheckCircle } from 'lucide-react'

export default function AnalyzePage() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<DocumentIntakeResult | null>(null)

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return

    setLoading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('/api/analyze/intake', {
        method: 'POST',
        body: formData
      })
      const data = await response.json()
      setResult(data)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="border-2 border-dashed rounded-lg p-8">
        <input
          type="file"
          accept=".pdf,.docx"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        <button onClick={handleUpload} disabled={!file || loading}>
          {loading ? 'Analyzing...' : 'Upload & Analyze'}
        </button>
      </div>

      {result && (
        <div className="space-y-4">
          {/* Risk Heat Map */}
          <div className="grid grid-cols-3 gap-4">
            <RiskCard
              title="Legal Risk"
              level={result.risk_level_legal}
            />
            <RiskCard
              title="Procedural Risk"
              level={result.risk_level_procedural}
            />
            <RiskCard
              title="Financial Risk"
              level={result.risk_level_financial}
            />
          </div>

          {/* Detected Issues */}
          <div>
            <h3 className="font-bold text-lg">Detected Issues</h3>
            {result.detected_issues.map((issue, idx) => (
              <div key={idx} className="border-l-4 border-red-500 pl-4 py-2">
                <p className="font-semibold">{issue.issue_type}</p>
                <p className="text-sm text-gray-600">{issue.description}</p>
              </div>
            ))}
          </div>

          {/* Classification Details */}
          <div className="bg-blue-50 p-4 rounded">
            <h3 className="font-bold">Classification</h3>
            <p>Type: {result.classified_type}</p>
            <p>Jurisdiction: {result.jurisdiction}</p>
            <p>Subject: {result.subject_matter}</p>
            <p>Urgency: <span className={`font-bold text-${result.urgency_level}`}>
              {result.urgency_level}
            </span></p>
          </div>

          {/* Next Steps */}
          <button className="bg-blue-600 text-white px-6 py-2 rounded">
            Proceed to Strategy Analysis →
          </button>
        </div>
      )}
    </div>
  )
}

function RiskCard({ title, level }: { title: string; level: string }) {
  const colors = {
    high: 'bg-red-100 border-red-500 text-red-900',
    medium: 'bg-yellow-100 border-yellow-500 text-yellow-900',
    low: 'bg-green-100 border-green-500 text-green-900'
  }

  return (
    <div className={`border-l-4 p-4 rounded ${colors[level as keyof typeof colors]}`}>
      <p className="font-bold">{title}</p>
      <p className="text-lg font-bold uppercase">{level}</p>
    </div>
  )
}
```

---

### ФАЗА 2: CASE-LAW PRECEDENT MAPPING (2 тижні)

#### 2.1 Database Schema
```sql
CREATE TABLE case_law_precedent_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    intake_id UUID NOT NULL REFERENCES document_analysis_intake(id),
    
    -- Группировка по паттернам
    pattern_type VARCHAR NOT NULL,  -- winning_pattern|losing_pattern|neutral|emerging|split_decision
    pattern_description VARCHAR,
    pattern_keywords JSONB,         -- [key terms used by courts]
    
    -- Прецеденты
    precedent_ids UUID[],
    precedent_count INT,
    pattern_strength FLOAT,         -- 0.0-1.0 confidence this pattern applies
    
    -- Анализ
    common_winning_arguments JSONB, -- [{argument, citations, success_rate}]
    common_losing_arguments JSONB,  -- [{argument, why_failed, how_to_overcome}]
    counter_arguments JSONB,        -- [{expected_defense, how_to_preempt, supporting_cases}]
    
    -- Стратегические выводы
    mitigation_strategy TEXT,
    strategic_advantage TEXT,
    vulnerability_to_appeal TEXT,
    
    -- Metadata
    search_query VARCHAR,           -- что мы искали в case_law
    created_at TIMESTAMP DEFAULT now(),
    
    CONSTRAINT valid_pattern_type CHECK (
        pattern_type IN ('winning_pattern', 'losing_pattern', 'neutral', 'emerging', 'split_decision')
    )
);

-- Связь между intake и case_law
CREATE TABLE intake_case_law_refs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intake_id UUID NOT NULL REFERENCES document_analysis_intake(id),
    case_law_id UUID NOT NULL REFERENCES case_law_cache(id),
    
    relevance_score FLOAT,         -- 0.0-1.0
    relevance_reason TEXT,
    how_it_applies VARCHAR,        -- favorable|unfavorable|neutral
    precedent_group_id UUID REFERENCES case_law_precedent_groups(id),
    
    created_at TIMESTAMP DEFAULT now()
);

-- Контр-аргументы и как их опровергать
CREATE TABLE counter_argument_map (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intake_id UUID NOT NULL REFERENCES document_analysis_intake(id),
    
    counterparty_likely_argument TEXT,
    why_they_will_use_it TEXT,
    success_probability_if_unopposed FLOAT,
    
    -- Наш ответ
    our_preemptive_response TEXT,
    supporting_case_law JSONB,     -- [{case_number, court, year, holding}]
    legal_authority TEXT,
    
    -- Риск если не ответить
    risk_if_unopposed TEXT,
    
    created_at TIMESTAMP DEFAULT now()
);
```

#### 2.2 Backend Endpoint: Precedent Mapping
```python
# routes/precedent_mapping.py

@router.post("/precedent-map/{intake_id}")
async def generate_precedent_map(
    intake_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    По документу из intake: найти relevant precedents и сгруппировать в паттерны.
    
    Процес:
    1. Извлечь keywords и legal issues из intake
    2. Поиск в case_law_cache (Supreme Court 2022-2026)
    3. Классификация precedents по паттернам (winning/losing/etc)
    4. Анализ common arguments и counter-arguments
    5. Генерация стратегических выводов
    """
    
    intake = get_intake_safe(intake_id, user_id)
    
    # Крок 1: Извлечь search keywords
    search_query = generate_search_query(intake)
    
    # Крок 2: Поиск precedents
    precedents = search_case_law(
        query=search_query,
        jurisdiction='UA',
        court_level='supreme',  # Только Верховный Суд
        date_from=datetime(2022, 1, 1),
        date_to=datetime.now(),
        limit=50
    )
    
    # Крок 3-4: Классификация и анализ
    pattern_groups = {}
    for precedent in precedents:
        pattern = classify_precedent_pattern(precedent, intake)
        
        if pattern not in pattern_groups:
            pattern_groups[pattern] = {
                'precedents': [],
                'arguments': [],
                'counter_args': []
            }
        
        pattern_groups[pattern]['precedents'].append(precedent)
    
    # Анализ arguments для каждого паттерна
    for pattern_type, group_data in pattern_groups.items():
        # AI анализ: какие аргументы работают, почему
        analysis = await analyze_pattern_arguments(
            pattern_type=pattern_type,
            precedents=group_data['precedents'],
            intake=intake
        )
        
        # Сохранить результаты
        group_record = CaseLawPrecedentGroup(
            user_id=user_id,
            intake_id=intake_id,
            pattern_type=pattern_type,
            precedent_ids=[p.id for p in group_data['precedents']],
            precedent_count=len(group_data['precedents']),
            pattern_strength=analysis['pattern_strength'],
            common_winning_arguments=analysis['winning_arguments'],
            common_losing_arguments=analysis['losing_arguments'],
            counter_arguments=analysis['counter_arguments'],
            mitigation_strategy=analysis['mitigation'],
            strategic_advantage=analysis['advantage'],
            vulnerability_to_appeal=analysis['appeal_vulnerability'],
            search_query=search_query
        )
        db.add(group_record)
    
    db.commit()
    
    # Крок 5: Генерация counter-argument map
    counter_args = await generate_counter_argument_map(
        intake=intake,
        pattern_groups=pattern_groups
    )
    
    for ca in counter_args:
        db.add(CounterArgumentMap(
            intake_id=intake_id,
            counterparty_likely_argument=ca['argument'],
            why_they_will_use_it=ca['reasoning'],
            success_probability_if_unopposed=ca['risk_if_unopposed'],
            our_preemptive_response=ca['our_response'],
            supporting_case_law=ca['case_law_support'],
            legal_authority=ca['authority'],
            risk_if_unopposed=ca['risk_description']
        ))
    
    db.commit()
    
    return {
        "intake_id": intake_id,
        "precedent_groups": pattern_groups.keys(),
        "counter_arguments_mapped": len(counter_args),
        "ready_for_strategy": True
    }

# AI Analyzer для паттернов

async def analyze_pattern_arguments(
    pattern_type: str,
    precedents: list,
    intake: DocumentAnalysisIntake
) -> dict:
    """
    AI анализ: какие аргументы делают паттерн winning/losing?
    """
    
    precedent_summaries = "\n".join([
        f"Case {p.case_number} ({p.year}):\n{p.holding}\n"
        for p in precedents
    ])
    
    prompt = f"""
You are a Ukrainian legal AI analyzing Supreme Court precedents.

PATTERN TYPE: {pattern_type}
CASE CATEGORY: {intake.subject_matter}
YOUR ROLE: {intake.primary_party_role}

PRECEDENTS SUMMARY:
{precedent_summaries}

ANALYZE:
1. What are the COMMON ARGUMENTS that make this pattern successful?
   - What facts did courts focus on?
   - What legal principles?
   - What procedural moves?

2. What are LOSING VARIANTS of this pattern?
   - When does it fail?
   - What counterarguments destroy it?
   - How to strengthen it?

3. What will COUNTERPARTY likely argue against this pattern?
   - Their most likely defense?
   - How to preempt it?
   - What case law supports our preemption?

OUTPUT JSON:
{{
    "pattern_strength": 0.85,
    "winning_arguments": [
        {{
            "argument": "Statute of limitations began from notice date, not event date",
            "citations": ["Case #123/2023", "Judgment in Case #456/2022"],
            "success_rate": 0.78,
            "why_it_works": "..."
        }}
    ],
    "losing_arguments": [
        {{
            "argument": "Implied agreement existed",
            "why_failed": "Court requires explicit terms",
            "how_to_overcome": "Add documentary evidence",
            "counterexample": "Case #789/2023 where implied term failed"
        }}
    ],
    "counter_arguments": [
        {{
            "expected_defense": "Counterparty will claim force majeure exception",
            "how_to_preempt": "Provide contemporaneous evidence proving no interruption",
            "supporting_cases": ["Case #111/2023"]
        }}
    ],
    "mitigation": "Focus on documentary evidence over witness testimony",
    "advantage": "3 recent precedents support our position",
    "appeal_vulnerability": "Appellate courts split on this issue; strengthen with statute cites"
}}
"""
    
    response = await call_ai_provider(
        model='claude-3-5-sonnet',
        system="You are a Ukrainian legal AI. Output ONLY valid JSON.",
        user_message=prompt,
        temperature=0.2,
        max_tokens=2500
    )
    
    return json.loads(response)

async def generate_counter_argument_map(
    intake: DocumentAnalysisIntake,
    pattern_groups: dict
) -> list:
    """
    Генерировать карту контр-аргументов: что скажет противник и как это опровергнуть.
    """
    
    prompt = f"""
You are a Ukrainian legal AI analyzing a case.

CASE SUMMARY:
- Type: {intake.classified_type}
- Subject: {intake.subject_matter}
- Our role: {intake.primary_party_role}
- Jurisdiction: {intake.jurisdiction}

WINNING PATTERNS WE IDENTIFIED:
{json.dumps(pattern_groups, indent=2)}

TASK: What are TOP 5 counter-arguments that COUNTERPARTY will likely make?

For each:
1. What is their argument?
2. Why will they use it? (strategic advantage)
3. What is success probability if unopposed? (0.0-1.0)
4. How do WE preempt it? (our response)
5. What case law supports our response?
6. What is our risk if we don't address it?

OUTPUT JSON:
{{
    "counter_arguments": [
        {{
            "argument": "...",
            "reasoning": "...",
            "risk_if_unopposed": 0.65,
            "our_response": "...",
            "case_law_support": ["Case #123/2023", "Judgment in #456/2022"],
            "legal_authority": "...",
            "risk_description": "..."
        }}
    ]
}}
"""
    
    response = await call_ai_provider(
        model='claude-3-5-sonnet',
        system="You are a Ukrainian legal AI specialized in counter-argument analysis.",
        user_message=prompt,
        temperature=0.3,
        max_tokens=3000
    )
    
    result = json.loads(response)
    return result['counter_arguments']
```

#### 2.3 AI Precedent Mapping Prompt
```
# SYSTEM PROMPT: Case-Law Precedent Pattern Mapper

You are an elite Ukrainian legal AI trained to analyze Supreme Court precedents.

## Task
Given a legal case/document classification, find ALL relevant Supreme Court decisions (2022-2026)
and group them into strategic patterns that either:
1. WIN (precedent supports plaintiff/claimant)
2. LOSE (precedent supports defendant/respondent)
3. NEUTRAL/MIXED (depends on specific facts)
4. EMERGING (court position is shifting)

## Precedent Classification

### WINNING PATTERN
A precedent supports YOUR position if:
- Court ruled in YOUR party's favor on similar facts
- Legal reasoning applies directly to your case
- Decision is recent and not overruled
- Court is Supreme Court (highest authority)

Example:
- Your case: Company X failed to pay invoice
- Precedent: Supreme Court ruled "oral agreement + partial performance = valid contract"
- Pattern: Winning pattern (oral contracts enforceable)

### LOSING PATTERN
A precedent works AGAINST your position if:
- Court ruled against your party type on similar facts
- Court explicitly rejected your likely arguments
- Decision weakens your legal theory

Example:
- Your case: Force majeure claim due to pandemic disruption
- Precedent: Supreme Court ruled "pandemic ≠ force majeure without specific contract language"
- Pattern: Losing pattern (force majeure narrowly construed)

### NEUTRAL/SPLIT PATTERN
- Court decided case on different grounds than you'll rely on
- Decision on similar facts but different jurisdiction
- Court split among judges (no clear precedent)
- Recent decision may contradict older precedent

### EMERGING PATTERN
- Court position is evolving (shifting over time)
- Recent decisions suggest new direction
- Old precedent may be reversed soon

## Pattern Analysis Process

### Step 1: Extract Legal Issues
From the document/case, identify:
- Primary legal claim type (contract breach, employment, debt, etc.)
- Key facts that matter (amount, parties, timeline, jurisdiction)
- Statutory provisions involved
- Procedural route (general/simplified court, first/appeal)

### Step 2: Generate Search Queries
Create 3-5 targeted searches:
```
Query 1: [Exact claim type] + [subject matter]
Query 2: [Key fact] + [legal principle]
Query 3: [Statute/law] + [case type]
Query 4: [Procedural issue] (if complex)
Query 5: [Counter-argument] (what opponent will cite)
```

### Step 3: Retrieve Precedents
For each search:
- Find top 10-15 relevant Supreme Court decisions
- Filter: 2022-2026 only (most recent)
- Note: More recent = stronger authority

### Step 4: Classify Each Precedent
For every precedent, determine:
```
Pattern: winning | losing | neutral | emerging
Relevance: 0.0-1.0 (0=irrelevant, 1.0=directly on point)
Court level: first_instance | appellate | supreme
Year: 2022-2026
Key holding: [1-2 sentence summary]
Application: How does this apply to our case?
Vulnerability: Can opponent distinguish it?
```

### Step 5: Group into Patterns
Cluster precedents by:
- Pattern type (winning/losing/etc)
- Common legal principles
- Procedent strength (more recent + more similar = stronger)

### Step 6: Analyze Pattern Strength
For each pattern:
```
Pattern strength = 
  (number_of_precedents × 0.2) + 
  (recency_score × 0.3) +
  (similarity_to_facts × 0.3) +
  (court_level × 0.2)
```

Range: 0.0-1.0
- 0.8-1.0 = Very strong (multiple recent Supreme Court decisions)
- 0.6-0.8 = Strong (consistent precedent)
- 0.4-0.6 = Moderate (precedent exists but some counter-authority)
- <0.4 = Weak (limited precedent or mostly opposing)

## Argument Analysis

For each pattern, identify:

### WINNING ARGUMENTS
What arguments made courts rule in your favor?
- "Lack of payment for 90+ days = material breach"
- "Expert testimony on custom usage establishes contract term"
- "Statute explicitly requires written notice within 30 days"

### LOSING ARGUMENTS
What arguments FAILED in court?
- "Implied contract based only on course of dealing" (failed in 2023)
- "Force majeure exception without specific contract language" (failed in 2024)

For losing arguments, always provide:
- Why did it fail? (court's reasoning)
- How to overcome? (stronger version of argument)
- Alternative approach? (different legal theory)

### COUNTER-ARGUMENTS
What will OPPONENT likely argue?
- "Our failure to pay was due to force majeure (pandemic)"
- "Implied agreement to extend deadline existed"
- "Your company breached first, excusing our payment"

For each counter-argument:
- What is their strongest version?
- How do WE preempt it? (facts, law, procedure)
- What precedent supports OUR preemption?

## Output Format

```json
{
    "precedent_map": {
        "winning_patterns": [
            {
                "pattern_name": "Payment default = material breach",
                "pattern_strength": 0.92,
                "precedents": [
                    {
                        "case_number": "Judgment #123/2023",
                        "court": "Supreme Court",
                        "year": 2023,
                        "holding": "Non-payment for 30+ days constitutes material breach of sales contract",
                        "relevance": 0.95,
                        "how_applies": "Direct precedent: parties here agreed to 15-day payment term"
                    }
                ],
                "common_arguments": [
                    {
                        "argument": "Payment not made within contractual deadline",
                        "why_works": "Court focuses on objective fact (date), not intentions",
                        "evidence_needed": "Invoice date + payment records",
                        "success_rate": 0.88
                    }
                ],
                "strategic_advantage": "Multiple recent precedents; high likelihood of success"
            }
        ],
        
        "losing_patterns": [
            {
                "pattern_name": "Force majeure exception",
                "pattern_strength": 0.15,
                "why_weak": "Courts interpret narrowly; pandemic alone insufficient",
                "how_to_overcome": "Add specific contract language showing force majeure",
                "precedent_example": "Judgment #456/2023: pandemic not automatic force majeure"
            }
        ],
        
        "counter_arguments": [
            {
                "counterparty_likely_argument": "Seller breached first by late delivery",
                "success_if_unopposed": 0.45,
                "our_preemption": "Delivery timeline allowed 15-day window; arrived day 12",
                "supporting_cases": ["Case #789/2023"],
                "risk_if_unopposed": "Court might excuse non-payment if seller breached"
            }
        ],
        
        "strategic_summary": {
            "confidence_level": 0.87,
            "recommended_focus": "Lead with payment-breach argument (strongest precedent)",
            "risky_arguments": ["Force majeure (will fail)", "Implied agreement (mixed authority)"],
            "next_steps": "Strengthen evidence: get documentary proof of invoice + payment deadline"
        }
    }
}
```

## Precedent Search Keywords (Ukrainian Law)

### Contract Disputes
- "договір" + "порушення умов"
- "непогашена заборгованість"
- "неустойка" (penalty clauses)
- "форс-мажор"
- "розглядання договору"

### Labor/Employment
- "трудовий договір" + "незаконне звільнення"
- "оплата праці"
- "компенсація за шкоду"

### Debt/Collection
- "стягнення боргу"
- "відсутність платежу"
- "неспроможність" (insolvency)

### Administrative
- "оскарження рішення органу" (appeal government decision)
- "відшкодування збитків" (damages from state)

## Quality Checklist

- [ ] Identified 3+ relevant precedent patterns
- [ ] Each pattern has 2+ supporting cases minimum
- [ ] Pattern strength scored 0.0-1.0
- [ ] Winning arguments substantiated by case law
- [ ] Losing arguments identified with mitigation
- [ ] Counter-arguments have preemptive responses
- [ ] All case citations are actual Supreme Court decisions
- [ ] Precedent dates are 2022-2026
- [ ] Relevance scores justify pattern strength
```

---

### ФАЗА 3: LEGAL STRATEGY BLUEPRINT (2 тижні)

#### 3.1 Database Schema
```sql
CREATE TABLE legal_strategy_blueprint (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    document_id UUID NOT NULL REFERENCES documents(id),
    intake_id UUID NOT NULL REFERENCES document_analysis_intake(id),
    precedent_group_id UUID REFERENCES case_law_precedent_groups(id),
    
    -- Немедленные действия (Next 14 days)
    immediate_actions JSONB,  -- [{action, deadline, rationale, priority, evidence_to_collect}]
    
    -- Процедурная дорожная карта
    procedural_roadmap JSONB, -- [{step, legal_action, expected_outcome, timeline, pivot_if_lost, appeal_chain}]
    
    -- Стратегия доказательств
    evidence_strategy JSONB,  -- [{phase, evidence_type, relevance, admissibility, collection_timeline}]
    
    -- Playbook переговоров
    negotiation_playbook JSONB, -- [{scenario, counterparty_offer, our_counter, reasoning, walkaway_point}]
    
    -- Тепловая карта рисков
    risk_heat_map JSONB,  -- [{scenario, likelihood_pct, consequences, mitigation}]
    
    -- Судебная практика по расчету убытков
    damages_calculation JSONB, -- [{type, amount_claim, precedent_support, likelihood_recovery}]
    
    -- Сроки и дедлайны
    critical_deadlines JSONB, -- [{event, date, consequence_if_missed}]
    
    -- Уровень уверенности
    confidence_score FLOAT,  -- 0.0-1.0
    confidence_rationale TEXT,
    
    -- Следующие шаги
    recommended_next_steps TEXT,
    
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- История версий стратегии (когда противник что-то делает, мы обновляем стратегию)
CREATE TABLE strategy_blueprint_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL REFERENCES legal_strategy_blueprint(id),
    version_number INT,
    trigger_event VARCHAR,  -- user_request|counterparty_move|deadline_passed|new_evidence
    trigger_description TEXT,
    
    changes_made JSONB,
    confidence_score_change FLOAT,
    
    created_at TIMESTAMP DEFAULT now()
);

-- Индивидуальные deadlines по делу
CREATE TABLE case_deadlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL REFERENCES legal_strategy_blueprint(id),
    
    event_type VARCHAR,  -- claim_filing|response_to_response|appeal_filing|evidence_submission|hearing_prep
    event_name VARCHAR,
    due_date DATE,
    days_until INT,
    consequence_if_missed TEXT,
    responsible_party VARCHAR,
    status VARCHAR,  -- pending|completed|at_risk|overdue
    
    created_at TIMESTAMP DEFAULT now()
);
```

#### 3.2 Strategy Generation Endpoint
```python
# routes/strategy_blueprint.py

@router.post("/strategy/blueprint/{intake_id}")
async def generate_strategy_blueprint(
    intake_id: str,
    user_id: str = Depends(get_current_user_id),
    include_evidence: bool = True
):
    """
    Генерировать полную стратегическую карту по делу.
    
    Включает:
    - Немедленные действия (next 14 days)
    - Процедурная дорожная карта (full timeline)
    - Стратегия доказательств (что подать когда)
    - Playbook переговоров (if settlement possible)
    - Тепловая карта рисков (scenarios)
    - Расчет убытков (если applicable)
    """
    
    # Получить intake + precedent analysis
    intake = get_intake_safe(intake_id, user_id)
    precedent_groups = db.query(CaseLawPrecedentGroup).filter_by(
        intake_id=intake_id
    ).all()
    
    counter_args = db.query(CounterArgumentMap).filter_by(
        intake_id=intake_id
    ).all()
    
    # AI генерирует всю стратегию
    strategy = await generate_comprehensive_strategy(
        intake=intake,
        precedent_groups=precedent_groups,
        counter_arguments=counter_args
    )
    
    # Сохранить в БД
    blueprint = LegalStrategyBlueprint(
        user_id=user_id,
        document_id=intake.document_id,
        intake_id=intake_id,
        immediate_actions=strategy['immediate_actions'],
        procedural_roadmap=strategy['procedural_roadmap'],
        evidence_strategy=strategy['evidence_strategy'],
        negotiation_playbook=strategy['negotiation_playbook'],
        risk_heat_map=strategy['risk_heat_map'],
        damages_calculation=strategy.get('damages_calculation'),
        critical_deadlines=strategy['critical_deadlines'],
        confidence_score=strategy['confidence_score'],
        confidence_rationale=strategy['confidence_rationale'],
        recommended_next_steps=strategy['recommended_next_steps']
    )
    db.add(blueprint)
    db.flush()  # Get ID
    
    # Создать deadline записи
    for deadline in strategy['critical_deadlines']:
        case_deadline = CaseDeadline(
            strategy_id=blueprint.id,
            event_type=deadline['event_type'],
            event_name=deadline['event_name'],
            due_date=deadline['due_date'],
            days_until=(deadline['due_date'] - datetime.now().date()).days,
            consequence_if_missed=deadline['consequence'],
            responsible_party='client'
        )
        db.add(case_deadline)
    
    db.commit()
    
    return {
        "strategy_id": blueprint.id,
        "confidence": blueprint.confidence_score,
        "immediate_actions": blueprint.immediate_actions,
        "critical_deadlines": [
            {
                "event": d.event_name,
                "due_date": d.due_date.isoformat(),
                "days_until": d.days_until
            }
            for d in db.query(CaseDeadline).filter_by(strategy_id=blueprint.id).all()
        ]
    }

async def generate_comprehensive_strategy(
    intake: DocumentAnalysisIntake,
    precedent_groups: list,
    counter_arguments: list
) -> dict:
    """
    AI-powered генерация полной стратегии дела.
    Результат: действия, дорожная карта, доказательства, переговоры, риски.
    """
    
    # Подготовить контекст
    precedent_summary = json.dumps([
        {
            "pattern": g.pattern_type,
            "strength": g.pattern_strength,
            "arguments": g.common_winning_arguments
        }
        for g in precedent_groups
    ], ensure_ascii=False)
    
    counter_summary = json.dumps([
        {
            "argument": ca.counterparty_likely_argument,
            "our_response": ca.our_preemptive_response
        }
        for ca in counter_arguments
    ], ensure_ascii=False)
    
    # Вызвать AI с масивным промптом (см. ниже)
    response = await call_ai_provider(
        model='claude-3-5-sonnet',
        system=STRATEGY_BLUEPRINT_SYSTEM_PROMPT,
        user_message=f"""
CASE CLASSIFICATION:
{json.dumps({
    'type': intake.classified_type,
    'subject': intake.subject_matter,
    'jurisdiction': intake.jurisdiction,
    'role': intake.primary_party_role,
    'urgency': intake.urgency_level,
    'financial_exposure': intake.financial_exposure_amount
}, ensure_ascii=False)}

PRECEDENT ANALYSIS:
{precedent_summary}

COUNTER-ARGUMENTS:
{counter_summary}

GENERATE FULL STRATEGY:
""",
        temperature=0.2,
        max_tokens=4000
    )
    
    result = json.loads(response)
    return result
```

#### 3.3 Strategy Blueprint System Prompt
```
# SYSTEM PROMPT: Comprehensive Legal Strategy Generator

You are an elite Ukrainian legal strategist with 30+ years of experience.
Your task: Generate a COMPLETE strategy for winning this case.

## Output JSON Structure

```json
{
    "immediate_actions": [
        {
            "action": "Send formal demand letter (претензія) to counterparty",
            "deadline": "2024-02-10",
            "days_until": 5,
            "priority": "critical",
            "rationale": "Statute requires demand before litigation in commercial disputes",
            "evidence_to_collect": [
                "Copy of invoice/contract",
                "Proof of delivery (if applicable)",
                "Email correspondence"
            ],
            "failure_consequence": "Claim may be dismissed as premature"
        },
        {
            "action": "Document all contemporaneous facts (photos, emails, witnesses)",
            "deadline": "2024-02-08",
            "days_until": 3,
            "priority": "high",
            "rationale": "Evidence may disappear; memories fade; counterparty may destroy docs",
            "evidence_to_collect": [
                "Photographs/video of condition",
                "Written statements from witnesses (get NOW, while fresh)",
                "Preserve all electronic communications"
            ],
            "failure_consequence": "Court may find facts against us if evidence lost"
        }
    ],
    
    "procedural_roadmap": [
        {
            "step": 1,
            "legal_action": "Send demand letter (претензія)",
            "jurisdiction": "out-of-court",
            "timeline": "Deliver within 14 days of today",
            "expected_outcome": "70% chance: counterparty pays to avoid litigation",
            "if_unsuccessful_pivot": "File claim in court (Step 2)",
            
            "litigation_route": "commercial_dispute",
            "court_type": "district_court",
            "why_this_court": "Jurisdiction > 50,000 UAH; faster than local court",
            
            "procedural_steps": [
                "Demand must include: claim amount, legal basis, deadline (10+ days)",
                "Send via email + postal (proof of service)",
                "Keep evidence of delivery"
            ]
        },
        {
            "step": 2,
            "legal_action": "File claim (позов) in district court",
            "timeline": "If Step 1 fails, file within 30 days",
            "expected_outcome": "Claim should be accepted; judge may schedule hearing within 60 days",
            
            "claim_must_include": [
                "Your name + counterparty name + address",
                "Description of facts (chronological, clear)",
                "Legal basis (which law was violated)",
                "Amount claimed + calculation",
                "Proof of demand sent in Step 1",
                "All evidence attachments"
            ],
            
            "common_mistakes_to_avoid": [
                "Vague claim (avoid 'you violated contract')",
                "Wrong court (check amount jurisdiction)",
                "Missing evidence attachments",
                "Wrong calculation of damages"
            ]
        },
        {
            "step": 3,
            "legal_action": "Respond to counterparty's response",
            "timeline": "20 days after receiving their response",
            "expected_outcome": "Judge gets full picture of dispute; preparation for hearing",
            
            "your_task": "Address their counter-claims point-by-point",
            "use_precedents": "Cite Supreme Court cases that support you",
            "challenge_their_evidence": "Point out weaknesses in their documents"
        },
        {
            "step": 4,
            "legal_action": "Hearing before judge",
            "timeline": "Typically 60-90 days after claim filing",
            "expected_outcome": "Judge hears both sides; may ask for additional evidence",
            
            "preparation": [
                "Bring original documents (not copies)",
                "Prepare witness testimony (if applicable)",
                "Prepare short oral presentation (5-10 min max)"
            ]
        },
        {
            "step": 5,
            "legal_action": "Judge issues ruling",
            "timeline": "Within 30 days of hearing (could be earlier)",
            "expected_outcome": "Full victory (100%), partial victory (50-80%), or loss",
            
            "if_we_win_fully": "Proceed to enforcement (Step 6)",
            "if_partial_victory": "Consider settlement for remaining amount",
            "if_we_lose": "Assess appeal options (Step 7)"
        },
        {
            "step": 6,
            "legal_action": "Enforcement of judgment (примусове виконання)",
            "timeline": "File enforcement within 3 years of judgment",
            "expected_outcome": "Court enforcement officer collects money from counterparty",
            
            "enforcement_options": [
                "Bank account garnishment (if known)",
                "Wage garnishment (if employed)",
                "Property seizure (if assets identified)",
                "Director liability (if LLC/corporation)"
            ]
        },
        {
            "step": 7,
            "legal_action": "Appeal to appellate court (if needed)",
            "timeline": "Within 30 days of judgment",
            "appeal_grounds": "Law misapplied, facts found incorrectly, procedure violated",
            
            "success_rate_if_we_lost": "Depends on appeal vulnerabilities in judge's decision",
            "likelihood_of_reversal": "Calculate based on precedent strength"
        }
    ],
    
    "evidence_strategy": [
        {
            "phase": "pre_litigation",
            "evidence_type": "documentary_evidence",
            "examples": ["invoice", "contract", "email correspondence", "payment records"],
            "relevance": "Establishes liability, timeline, parties",
            "admissibility": "Highly admissible if original or certified",
            "collection_timeline": "NOW - collect immediately",
            "where_to_get": "Company files, bank records, email",
            "priority": "critical"
        },
        {
            "phase": "pre_litigation",
            "evidence_type": "witness_statements",
            "examples": ["Employee testimony", "Third-party witness"],
            "how_to_collect": "Written statement + signature (notarize if possible)",
            "timing": "Collect NOW before memories fade and counterparty influences them",
            "priority": "high"
        },
        {
            "phase": "during_litigation",
            "evidence_type": "expert_analysis",
            "when_needed": "If technical/medical/accounting issues involved",
            "timeline": "Within 30 days of claim filing",
            "cost": "500-5000 UAH depending on complexity"
        },
        {
            "phase": "during_litigation",
            "evidence_type": "precedent_citations",
            "how_to_use": "Reference Supreme Court cases in your written responses",
            "timing": "In claim + in response + in hearing"
        }
    ],
    
    "negotiation_playbook": [
        {
            "scenario": "Counterparty offers 50% settlement",
            "our_floor": "75% (minimum acceptable)",
            "our_ceiling": "100% (ideal outcome)",
            "our_counter_offer": "85% (middle ground)",
            "reasoning": "We have 85% confidence based on precedent; settlement gives us certainty",
            "walkaway_point": "Below 70% = proceed to litigation",
            "timeline": "If not resolved in 14 days, file claim"
        },
        {
            "scenario": "Counterparty denies owing anything",
            "strategy": "Ignore settlement discussion; file claim immediately",
            "no_settlement_value": "No point negotiating with denying party"
        },
        {
            "scenario": "Counterparty offers payment plan instead of lump sum",
            "evaluate": "Is interest higher with payment plan? What if they default?",
            "our_preference": "Lump sum (lower risk)",
            "acceptable_terms": "If monthly payments + security deposit"
        }
    ],
    
    "risk_heat_map": [
        {
            "scenario": "We win 100% claim + damages",
            "likelihood_pct": 45,
            "consequences": "Counterparty pays full amount + court costs",
            "confidence_basis": "Strong precedent + solid evidence"
        },
        {
            "scenario": "We win 70% of claim",
            "likelihood_pct": 35,
            "consequences": "Partial recovery; some damages denied",
            "why_might_happen": "Judge may find some facts against us",
            "mitigation": "Strengthen evidence on weakest claim"
        },
        {
            "scenario": "We lose completely",
            "likelihood_pct": 15,
            "consequences": "Pay court costs; start appeal (expensive + slow)",
            "why_might_happen": "Court interprets law differently; unfavorable judge",
            "mitigation": "Appeal if legal grounds strong (precedent support)"
        },
        {
            "scenario": "Case drags on 2+ years",
            "likelihood_pct": 30,
            "consequences": "Legal fees accumulate; cash flow impact; stress",
            "why_might_happen": "Overloaded courts; appeals",
            "mitigation": "Settlement negotiations early + mediation option"
        }
    ],
    
    "damages_calculation": [
        {
            "type": "primary_claim",
            "description": "Non-payment for goods/services",
            "amount_claim": 500000,
            "currency": "UAH",
            "legal_basis": "Contract Article 3 (payment terms)",
            "precedent_support": "Case #123/2023 (similar fact pattern)",
            "likelihood_recovery": 0.90,
            "notes": "Direct damages; fully recoverable"
        },
        {
            "type": "interest_on_debt",
            "description": "Statutory interest (12% per year per Commercial Code)",
            "amount_claim": 45000,
            "legal_basis": "Commercial Code Art. 546",
            "precedent_support": "Standard; all courts award",
            "likelihood_recovery": 0.95,
            "notes": "Calculate from date of invoice to judgment date"
        },
        {
            "type": "court_costs",
            "description": "Court fee + service fee",
            "amount_claim": 12000,
            "legal_basis": "Civil Procedure Code",
            "likelihood_recovery": 0.95,
            "notes": "Court fee typically 1% of claim (max 12,000 UAH)"
        },
        {
            "type": "attorney_fees",
            "description": "Your legal representation costs",
            "amount_claim": 35000,
            "legal_basis": "Civil Procedure Code § 127 (if we win by more than 50%)",
            "likelihood_recovery": 0.70,
            "notes": "Judge has discretion; more likely if win was clear-cut"
        }
    ],
    
    "critical_deadlines": [
        {
            "event_type": "demand_letter",
            "event_name": "Send formal demand (претензія) to counterparty",
            "due_date": "2024-02-10",
            "consequence": "If not sent, judge may dismiss claim as premature"
        },
        {
            "event_type": "evidence_collection",
            "event_name": "Document all contemporaneous evidence",
            "due_date": "2024-02-08",
            "consequence": "Evidence may disappear; witness memories fade"
        },
        {
            "event_type": "claim_filing",
            "event_name": "File claim in court (if no settlement)",
            "due_date": "2024-02-28",
            "consequence": "After 30 days, counterparty may have statute of limitations defense"
        },
        {
            "event_type": "statute_limitation",
            "event_name": "Statute of limitations deadline",
            "due_date": "2027-01-15",
            "consequence": "After this date, claim forever time-barred"
        }
    ],
    
    "confidence_score": 0.82,
    "confidence_rationale": "Strong precedent support (pattern_strength=0.92) + solid documentary evidence + clear contractual terms",
    
    "recommended_next_steps": "1. Collect evidence immediately (today). 2. Send demand letter by 2024-02-10. 3. If no response, file claim by 2024-02-28."
}
```

## Confidence Score Calculation

```
confidence = 
  (precedent_strength × 0.35) +
  (evidence_quality × 0.25) +
  (legal_clarity × 0.20) +
  (procedural_readiness × 0.20)

precedent_strength = highest pattern strength in precedent_groups (0.0-1.0)
evidence_quality = estimate of how strong your evidence is (0.0-1.0)
legal_clarity = how clear the law supports you (0.0-1.0)
procedural_readiness = how well you can follow procedure (0.0-1.0)
```

Result: 0.0-1.0 overall confidence
- 0.85-1.0 = Proceed with confidence; strong case
- 0.70-0.85 = Proceed but mitigate risks
- 0.50-0.70 = Consider settlement; risky case
- <0.50 = High risk; consider alternative resolution

## Key Principles

1. **Immediacy First**: List what must happen in next 14 days
2. **Procedural Correctness**: Every step must follow Ukrainian law
3. **Precedent Grounding**: Every claim backed by Supreme Court decision
4. **Risk Mitigation**: Every risk scenario has mitigation strategy
5. **Evidence Chain**: Evidence collected before needed, not after
6. **Alternative Resolution**: Always include settlement playbook
```

---

### ФАЗА 4: STRATEGY-DRIVEN DOCUMENT GENERATION (2 тижні)

#### 4.1 Modified Generation Endpoint
```python
# routes/generate_with_strategy.py

@router.post("/documents/generate-with-strategy")
async def generate_document_with_strategy(
    strategy_id: str,
    document_type: str,  # claim_form|response|appeal_brief|demand_letter|settlement_proposal
    user_id: str = Depends(get_current_user_id),
    additional_context: Optional[str] = None
):
    """
    Генерировать документ, оптимизированный по стратегии.
    
    NOT: Fill template based on facts
    BUT: Generate document that:
      - Cites precedent strategically
      - Addresses counter-arguments proactively
      - Positions evidence for maximum impact
      - Optimizes for appeal-proofness
    """
    
    # Получить стратегию + intake + precedents
    strategy = db.query(LegalStrategyBlueprint).get(strategy_id)
    intake = db.query(DocumentAnalysisIntake).get(strategy.intake_id)
    document = db.query(Document).get(strategy.document_id)
    precedents = get_precedents_for_strategy(strategy_id)
    counter_args = db.query(CounterArgumentMap).filter_by(
        intake_id=strategy.intake_id
    ).all()
    
    # Получить полный текст документа
    doc_text = extract_full_text(document)
    
    # AI генерирует документ с учетом стратегии
    generated_content = await generate_strategic_document(
        document_type=document_type,
        strategy=strategy,
        intake=intake,
        document_text=doc_text,
        precedents=precedents,
        counter_arguments=counter_args,
        additional_context=additional_context
    )
    
    # Сохранить как новый документ
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
    
    # Экспортировать как DOCX
    docx_path = await export_to_docx(
        content=generated_content['body'],
        title=f"{document_type.upper()} - {intake.subject_matter}",
        author="Legal AI Platform"
    )
    
    return {
        "document_id": new_doc.id,
        "document_type": document_type,
        "docx_download_url": f"/api/documents/{new_doc.id}/export?format=docx",
        "preview": generated_content['body'][:500] + "...",
        "precedent_count": len(generated_content['citations']),
        "strategy_applied": strategy_id
    }

async def generate_strategic_document(
    document_type: str,
    strategy: LegalStrategyBlueprint,
    intake: DocumentAnalysisIntake,
    document_text: str,
    precedents: list,
    counter_arguments: list,
    additional_context: Optional[str] = None
) -> dict:
    """
    AI генерирует документ, оптимизированный по стратегии.
    
    Процес:
    1. Извлечь ключевые факты из document_text
    2. Определить стратегические приоритеты из strategy
    3. Выбрать relevant precedents
    4. Встроить counter-argument preemption
    5. Позиционировать доказательства
    6. Оптимизировать для appeal
    7. Генерировать документ с AI
    """
    
    # Шаг 1-2: Экстрактные факты + приоритеты
    facts = extract_key_facts(document_text)
    immediate_actions = strategy.immediate_actions[0:3]  # Top 3
    roadmap = strategy.procedural_roadmap
    
    # Шаг 3: Precedents для этого документа
    relevant_precedents = select_relevant_precedents(
        precedents=precedents,
        document_type=document_type
    )
    
    # Шаг 4: Counter-arguments to preempt
    counter_args_preempt = [ca for ca in counter_arguments if should_preempt(ca, document_type)]
    
    # Шаг 5: Evidence positioning
    evidence_order = order_evidence_strategically(
        strategy=strategy,
        document_type=document_type
    )
    
    # AI промпт
    prompt = build_strategic_generation_prompt(
        document_type=document_type,
        facts=facts,
        strategy=strategy,
        precedents=relevant_precedents,
        counter_arguments=counter_args_preempt,
        evidence_order=evidence_order,
        additional_context=additional_context
    )
    
    response = await call_ai_provider(
        model='claude-3-5-sonnet',
        system=STRATEGIC_DOCUMENT_GENERATION_SYSTEM_PROMPT,
        user_message=prompt,
        temperature=0.2,
        max_tokens=4000
    )
    
    # Parse результат (должен содержать структурированный JSON)
    result = json.loads(response)
    
    return {
        "body": result['document_body'],
        "citations": result['precedent_citations'],
        "counter_arg_addresses": result['counter_argument_addresses'],
        "evidence_notes": result['evidence_positioning_notes'],
        "appeal_notes": result['appeal_proofing_notes']
    }

def build_strategic_generation_prompt(
    document_type: str,
    facts: dict,
    strategy: LegalStrategyBlueprint,
    precedents: list,
    counter_arguments: list,
    evidence_order: list,
    additional_context: Optional[str] = None
) -> str:
    """
    Построить очень детальный промпт для генерации документа.
    """
    
    precedent_text = "\n".join([
        f"- Case {p['case_number']} ({p['year']}): {p['holding']} (relevance: {p['relevance']})"
        for p in precedents[:10]
    ])
    
    counter_args_text = "\n".join([
        f"- Counterparty will argue: '{ca.counterparty_likely_argument}'\n"
        f"  PREEMPT BY: {ca.our_preemptive_response}"
        for ca in counter_arguments[:5]
    ])
    
    evidence_text = "\n".join([
        f"- {idx+1}. {e['description']} (Phase: {e['phase']}, Relevance: {e['relevance']})"
        for idx, e in enumerate(evidence_order[:8])
    ])
    
    prompt = f"""
DOCUMENT TYPE: {document_type}

FACTS OF CASE:
{json.dumps(facts, ensure_ascii=False)}

STRATEGY PRIORITIES:
- Immediate actions: {strategy.immediate_actions[0]['action']} (deadline: {strategy.immediate_actions[0]['deadline']})
- Confidence level: {strategy.confidence_score * 100:.0f}%
- Next step: {strategy.recommended_next_steps}

RELEVANT PRECEDENTS:
{precedent_text}

COUNTER-ARGUMENTS TO PREEMPT:
{counter_args_text}

EVIDENCE (in strategic order):
{evidence_text}

GENERATE A {document_type.upper()} THAT:
1. Opens with strongest fact (establishes immediacy)
2. Cites precedent by case number (not lengthy quotes)
3. Addresses counter-arguments BEFORE opponent raises them
4. Orders evidence from strongest to supporting
5. Ends with clear ask (money amount, deadline, etc)
6. Uses formal Ukrainian legal language
7. Is appeal-proof: every major claim backed by law or precedent

OUTPUT JSON:
{{
    "document_body": "[Full document text here]",
    "precedent_citations": ["Case #123/2023", "Judgment #456/2022"],
    "counter_argument_addresses": ["Counter-claim 1 addressed in paragraph X", ...],
    "evidence_positioning_notes": ["Invoice cited in para 3", "Timeline established in para 5", ...],
    "appeal_proofing_notes": ["Strongest argument in opening para", "Precedent backup for every claim", ...]
}}
"""
    
    if additional_context:
        prompt += f"\nADDITIONAL CONTEXT FROM USER:\n{additional_context}"
    
    return prompt
```

#### 4.2 Strategic Document Generation System Prompt
```
# SYSTEM PROMPT: Strategy-Driven Document Generator

You are an elite Ukrainian legal document writer trained to:
1. WIN cases (not just fill templates)
2. SURVIVE appeals (every claim defended)
3. PREEMPT counter-arguments (address them first)
4. MAXIMIZE recovery (strategic evidence ordering)

## Document Types & Strategies

### 1. CLAIM FORM (ПОЗОВ)
Structure:
```
[HEADER: Court name, judge, case type]

1. PARTIES & JURISDICTION
   - Your name + role (plaintiff/creditor)
   - Counterparty name + role (defendant/debtor)
   - Why this court has jurisdiction (amount, location)

2. STATEMENT OF FACTS (хронологія)
   - Timeline: what happened, when, who involved
   - Be CHRONOLOGICAL (not topic-based)
   - Lead with strongest fact
   - Use DOCUMENTARY EVIDENCE to prove (invoice date, payment deadline, non-payment date)
   
3. LEGAL BASIS
   - Which law was violated? (Contract Article X, Law Article Y)
   - Cite PRECEDENT: "Supreme Court in Case #123/2023 held that..."
   - Connect fact to law: "Invoice was dated X (fact) → payment deadline was Y → payment not received by Y (law violated)"

4. COUNTER-ARGUMENT PREEMPTION
   - Counterparty will argue: "We couldn't pay due to force majeure"
   - YOU ADDRESS: "Force majeure requires [specific conditions]. This case lacks [condition], citing Case #456/2023."
   - Do this for TOP 3 counter-arguments
   
5. DAMAGES CALCULATION
   - Primary claim: [exact amount + formula]
   - Interest: 12% per year, calculated from [date] to [date]
   - Court costs: [amount]
   - TOTAL: [sum]

6. EVIDENCE ATTACHMENTS (список)
   - Numbered list: "Attachment 1: Invoice dated 2024-01-15"
   - Do NOT include full text in body; reference in facts
   
7. PRAYER FOR RELIEF (прохання)
   - "I request that court ORDER: Defendant to pay Plaintiff [amount] within [days]"
   - Be specific (not "pay the debt")
```

### 2. RESPONSE TO CLAIM (ВІДПОВІДЬ НА ПОЗОВ)
Structure:
```
[HEADER: Same court, same case number as plaintiff's claim]

1. RESPOND TO EACH CLAIM POINT-BY-POINT
   - Don't ramble; address their argument directly
   - If they cite law: cite counter-law or different interpretation
   - If they cite precedent: distinguish it (show differences) OR cite counter-precedent

2. COUNTER-CLAIM (if applicable)
   - "Plaintiff owes US money because..."
   - Use same structure as their claim (facts → law → damages)

3. PROCEDURAL OBJECTIONS (if any)
   - "Claim should be dismissed because..."
   - Examples: wrong court, premature (demand not sent), statute of limitations expired

4. EVIDENCE
   - Attach COUNTER-EVIDENCE
   - If they cite invoice: attach your payment records

5. PRAYER FOR RELIEF
   - "Dismiss plaintiff's claim in full"
   - OR "Plaintiff's claim reduced to [amount]"
   - OR "Plaintiff ordered to pay our counter-claim of [amount]"
```

### 3. APPEAL BRIEF (АПЕЛЯЦІЙНА СКАРГА)
Structure:
```
[HEADER: Appellate court, original case number]

1. ERRORS OF FIRST INSTANCE JUDGE
   - "Judge erred when she..."
   - Give specific paragraphs of judgment where error appeared
   - Explain how it was wrong (fact finding vs legal conclusion)

2. LEGAL ARGUMENTS
   - "The law actually says..."
   - Cite statute + precedent
   - Explain how it contradicts judge's ruling

3. FACTUAL ARGUMENTS (if fact-finding was wrong)
   - "Judge found that X happened, but evidence shows Y"
   - Quote evidence: "Document dated 2024-01-15 states..."
   - Explain why judge's finding was unreasonable

4. REQUEST FOR REVERSAL
   - "Appellate court should reverse judgment and..."
   - Order new trial OR uphold our position OR modify damages
```

## Strategic Writing Principles

### Precedent Integration
- Don't quote long passages; cite + paraphrase
- Example WRONG: "The Supreme Court held that 'non-payment for 30 days constitutes material breach under Ukrainian law'"
- Example RIGHT: "Supreme Court (Case #123/2023) recognized non-payment as material breach"
- Use precedent to strengthen argument, not replace it

### Counter-Argument Preemption
- Identify TOP 5 counter-arguments opponent will raise
- ADDRESS EACH DIRECTLY in your document
- Don't wait for opponent to raise it; beat them to it
- Example: "Defendant may argue force majeure excuses non-payment. However, Case #456/2023 requires specific conditions..."

### Evidence Ordering (Psychological & Legal)
- **Para 1-2**: Strongest fact (establishes liability immediately)
- **Para 3-4**: Supporting facts (build case)
- **Para 5-6**: Respond to counter-arguments
- **Para 7-8**: Damages + amounts
- Why? Judge reads para 1 with full attention; later paragraphs have less impact

### Appeal-Proofing
- Every major legal conclusion: back with statute or precedent
- Every factual claim: reference evidence attachment
- Avoid speculation ("likely", "probably", "seems")
- Use definitive language ("invoice dated X shows", "statute requires")
- Assume appellate court will second-guess EVERY finding

### Procedural Correctness
- Follow Ukrainian Civil Procedure Code format
- Sections, numbering, headings
- Plain language (not legalese)
- No typos/grammatical errors (signals carelessness to judge)

## Template Structure (ALL DOCUMENTS)

```
[COURT HEADER]
Case #___
Judge _____
Date _____

[DOCUMENT TYPE]: [Short title]

I. INTRODUCTION
   [Your role, what you want, why in 2-3 sentences]

II. FACTS
   [Chronological timeline, documentary evidence]

III. LEGAL BASIS
   [Laws + precedents that apply]

IV. COUNTER-ARGUMENT PREEMPTION (if applicable)
   [Address opposition's likely defense]

V. DAMAGES/CALCULATION
   [Specific amounts, formulas, precedent support]

VI. CONCLUSION
   [Request court order: specific relief]

VII. CERTIFICATION
   [Your name, date, signature]

ATTACHMENTS:
   1. Invoice dated 2024-01-15
   2. Email correspondence
   3. Payment records
   4. Precedent: Case #123/2023
   ...

```

## Quality Checklist

- [ ] Every legal argument has statute or precedent cite
- [ ] Counter-arguments preempted in document (don't wait)
- [ ] Facts chronological (not scattered)
- [ ] Evidence referenced by attachment number
- [ ] Precedents relevant to YOUR facts (not generic)
- [ ] No typos, grammatical errors
- [ ] Formal Ukrainian legal language
- [ ] Appeal-proof (assume appellate review)
- [ ] Calculations correct (double-check math)
- [ ] Prayer for relief specific (not vague)
```

---

### ФАЗА 5: FEEDBACK LOOP & CONTINUOUS LEARNING (Ongoing)

#### 5.1 Outcome Tracking
```sql
CREATE TABLE document_outcome_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    document_id UUID NOT NULL REFERENCES documents(id),
    strategy_id UUID NOT NULL REFERENCES legal_strategy_blueprint(id),
    
    -- Итоговый результат
    case_outcome VARCHAR,  -- won|lost|settled|dismissed|appealed|pending
    
    -- Судебное решение
    judgment_date DATE,
    judge_name VARCHAR,
    court_name VARCHAR,
    judgment_text TEXT,
    judgment_amount_awarded DECIMAL,
    judgment_amount_denied DECIMAL,
    
    -- Расчет прогноза vs реальность
    predicted_confidence FLOAT,  -- из strategy blueprint
    actual_success_rate FLOAT,   -- (amount_awarded / amount_claimed) * 100
    prediction_accuracy VARCHAR, -- accurate|optimistic|pessimistic
    
    -- Причины отклонения от прогноза
    variance_explanation TEXT,
    
    -- Какие аргументы сработали / не сработали
    successful_arguments TEXT,   -- "[argument A, argument B]"
    failed_arguments TEXT,
    successful_precedents JSONB,
    failed_precedents JSONB,
    
    -- Appeal decision (if appealed)
    appeal_outcome VARCHAR,
    appeal_judgment_date DATE,
    
    -- Финальный размер взыскания (с enforcement)
    final_amount_collected DECIMAL,
    collection_timeline_days INT,
    
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- Model performance table (для отслеживания, где ошибается AI)
CREATE TABLE model_performance_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    metric_type VARCHAR,  -- classification_accuracy|precedent_relevance|strategy_confidence|prediction_accuracy
    prediction VARCHAR,
    actual_outcome VARCHAR,
    confidence_score FLOAT,
    correct BOOLEAN,
    
    case_count INT,
    accuracy_pct FLOAT,
    
    created_at TIMESTAMP DEFAULT now()
);
```

#### 5.2 Feedback Endpoints
```python
@router.post("/outcomes/track/{document_id}")
async def track_case_outcome(
    document_id: str,
    case_outcome: str,  # won|lost|settled|...
    judgment_data: dict,
    user_id: str = Depends(get_current_user_id)
):
    """
    User reports final case outcome.
    System learns: какие аргументы сработали, какие нет.
    """
    
    document = get_document_safe(document_id, user_id)
    strategy = db.query(LegalStrategyBlueprint).filter_by(
        document_id=document_id
    ).first()
    
    # Сохранить результат
    outcome = DocumentOutcomeTracking(
        user_id=user_id,
        document_id=document_id,
        strategy_id=strategy.id,
        case_outcome=case_outcome,
        judgment_date=judgment_data['judgment_date'],
        judgment_amount_awarded=judgment_data.get('amount_awarded'),
        predicted_confidence=strategy.confidence_score,
        actual_success_rate=calculate_success_rate(judgment_data, strategy),
        successful_arguments=identify_successful_arguments(judgment_data),
        failed_arguments=identify_failed_arguments(judgment_data)
    )
    db.add(outcome)
    db.commit()
    
    # AI анализирует: почему мы ошибались?
    analysis = await analyze_prediction_variance(
        strategy=strategy,
        outcome=outcome
    )
    
    return {
        "outcome_recorded": True,
        "accuracy_analysis": analysis,
        "lessons_learned": generate_lessons_learned(analysis)
    }

async def analyze_prediction_variance(
    strategy: LegalStrategyBlueprint,
    outcome: DocumentOutcomeTracking
) -> dict:
    """
    Анализ: почему наш прогноз confidence был X, а реальный результат был Y?
    """
    
    prompt = f"""
CASE ANALYSIS: Prediction vs Actual Outcome

PREDICTED (by AI strategy):
- Confidence score: {strategy.confidence_score}
- Expected outcome: [based on precedent analysis]
- Risk assessment: {strategy.risk_heat_map}

ACTUAL OUTCOME:
- Judge ruled: {outcome.judgment_text[:500]}
- Amount awarded: {outcome.judgment_amount_awarded}
- Successful arguments: {outcome.successful_arguments}
- Failed arguments: {outcome.failed_arguments}

ANALYZE:
1. Where was our prediction ACCURATE?
2. Where did we OVER-estimate confidence?
3. Where did we UNDER-estimate confidence?
4. What precedents were CITED by judge?
5. What precedents did judge IGNORE?
6. What was judge's reasoning?
7. How should we adjust our model going forward?

OUTPUT JSON:
{{
    "prediction_accuracy": "optimistic|pessimistic|accurate",
    "over_estimates": ["...", "..."],
    "under_estimates": ["...", "..."],
    "judge_cited_precedents": ["Case #123/2023", ...],
    "judge_ignored_precedents": ["Case #456/2022", ...],
    "judge_reasoning": "...",
    "model_adjustment": "For future cases with similar facts, adjust [metric] from X to Y"
}}
"""
    
    response = await call_ai_provider(
        model='claude-3-5-sonnet',
        system="You are a legal AI learning from case outcomes.",
        user_message=prompt,
        temperature=0.2,
        max_tokens=2000
    )
    
    return json.loads(response)
```

---

## ЧАСТИНА 3: AI GENERATION PROMPTS CATALOG

### ПРОМПТ 1: Document Type Classifier
[See Phase 1 - already included above]

### ПРОМПТ 2: Precedent Pattern Mapper
[See Phase 2 - already included above]

### ПРОМПТ 3: Strategy Blueprint Generator
[See Phase 3 - already included above]

### ПРОМПТ 4: Strategic Document Generator
[See Phase 4 - already included above]

### ПРОМПТ 5: Counter-Argument Preemptor
```
# SYSTEM PROMPT: Counter-Argument Preemption Specialist

You are an elite Ukrainian legal strategist.
Your task: Identify the TOP counter-arguments opponent will raise, then explain how to preempt each.

INPUT:
- Your case facts
- Your legal claims
- Precedent analysis
- Opponent's likely position

OUTPUT:
For each of TOP 5 counter-arguments:
1. What will opponent argue?
2. On what law/precedent will they rely?
3. What is success probability if unopposed? (0.0-1.0)
4. How do WE preempt it in OUR documents?
5. What precedent supports our preemption?
6. What facts do we need to establish our preemption?

STRUCTURE:
```json
{
    "counter_argument_1": {
        "opponent_argument": "Force majeure exception applies",
        "their_legal_basis": "Contract clause + Case #123/2023",
        "success_if_unopposed": 0.60,
        
        "our_preemption": "Case #456/2023 requires specific conditions: X, Y, Z. This case lacks Z because [fact].",
        "preemption_precedent": "Case #456/2023",
        "facts_needed_to_prove": ["Timeline of events", "Documentary evidence of X and Y", "Expert analysis of Z"],
        
        "when_to_raise_this": "In our claim (not response); establish before opponent argues"
    }
}
```
```

### ПРОМПТ 6: Evidence Positioning Strategist
```
# SYSTEM PROMPT: Evidence Positioning Strategist

You are a trial strategist focused on WHEN and HOW to present evidence.

PRINCIPLE: Evidence presented at right time is 2-3x more powerful.

TASK: Order evidence for maximum impact.

INPUT:
- All available evidence
- Case strategy
- Document type being generated

OUTPUT:
```json
{
    "evidence_order": [
        {
            "position": 1,
            "evidence": "Invoice dated 2024-01-15",
            "why_first": "Establishes baseline fact: payment obligation existed",
            "in_which_paragraph": "Para 2 (facts section)",
            "how_to_present": "Reference: 'Attachment 1 shows invoice dated 2024-01-15'",
            "legal_relevance": "Proves contract formation + payment term"
        },
        {
            "position": 2,
            "evidence": "Email dated 2024-02-14 showing non-payment",
            "why_second": "Establishes timeline: deadline passed, no payment",
            "in_which_paragraph": "Para 3",
            "how_to_present": "Reference: 'Attachment 2 email dated 2024-02-14 documents non-payment'",
            "legal_relevance": "Proves breach occurred"
        },
        {
            "position": 3,
            "evidence": "Witness statement from logistics company",
            "why_third": "Corroborates delivery (opponent may claim 'never received')",
            "in_which_paragraph": "Para 4",
            "why_not_earlier": "Witness testimony is secondary; primary documents first",
            "legal_relevance": "Defeats 'never received' defense"
        }
    ],
    
    "evidence_NOT_to_use": [
        {
            "evidence": "Employee chat transcript",
            "why_exclude": "Hearsay; inadmissible under Ukrainian law",
            "alternative": "Use formal witness statement instead"
        }
    ]
}
```

### ПРОМПТ 7: Appeals Vulnerability Analyzer
```
# SYSTEM PROMPT: Appeals Vulnerability Analyzer

You are an appellate attorney.
Your task: Identify WEAKNESSES in judge's likely ruling that opponent can appeal.

PRINCIPLE: If judge's reasoning is weak, opponent WILL appeal.

INPUT:
- First instance judge's likely ruling (based on precedent + facts)
- Opponent's strongest counter-arguments
- Applicable law

OUTPUT:
```json
{
    "judge_likely_holding": "Plaintiff wins 100% of claim",
    
    "appellate_vulnerabilities": [
        {
            "vulnerability": "Judge may have misapplied statute of limitations",
            "why_vulnerable": "Judge set start date at event date; Case #789/2023 says notice date",
            "likelihood_opponent_appeals": 0.75,
            "likelihood_appellate_court_agrees_with_opponent": 0.40,
            
            "how_to_strengthen_against_appeal": "Emphasize in original brief that notice date AND event date both within limit",
            "cite_supporting_precedent": "Case #999/2023 (more recent than #789/2023)"
        },
        {
            "vulnerability": "Evidence of damages is thin; judge may reduce award",
            "why_vulnerable": "Only self-serving estimates; no independent expert",
            "likelihood_opponent_appeals": 0.80,
            "likelihood_appellate_court_reduces_award": 0.60,
            
            "how_to_strengthen": "Get expert analysis BEFORE judgment; cite in original brief"
        }
    ],
    
    "appeal_proofing_strategy": "Focus brief on strongest factual claims; de-emphasize weak damages evidence"
}
```

### ПРОМПТ 8: Negotiation Playbook Generator
```
# SYSTEM PROMPT: Settlement & Negotiation Playbook

You are a settlement negotiator.
Your task: Design a negotiation strategy for settlement discussions.

INPUT:
- Your case strength (confidence score)
- Opponent's likely position
- Cost of continued litigation
- Your client's preferences

OUTPUT:
```json
{
    "negotiation_strategy": "anchoring",
    
    "opening_position": {
        "our_demand": 500000,
        "rationale": "100% of claim + interest + court costs",
        "anchoring_reasoning": "High opening anchors expectations; we'll negotiate down but from high baseline"
    },
    
    "negotiation_zones": [
        {
            "round": 1,
            "our_position": 500000,
            "expected_opponent_response": 250000,
            "our_counter": 450000,
            "reasoning": "Show willingness to move but maintain firmness on core amount"
        },
        {
            "round": 2,
            "our_position": 450000,
            "expected_opponent_response": 320000,
            "our_counter": 380000,
            "reasoning": "Gap narrowing; settlement may be possible"
        },
        {
            "round": 3,
            "our_position": 380000,
            "expected_opponent_response": 350000,
            "our_counter": 370000,
            "reasoning": "Final offer; very close to settlement"
        }
    ],
    
    "walkaway_point": 300000,
    "reasoning": "Below 300K, litigation is better option (60% success × 500K = 300K expected value)",
    
    "negotiation_script": [
        {
            "opponent_says": "We can only pay 250K",
            "we_say": "Your offer is 50% of our rightful claim. Case law supports full recovery. We expect 450K.",
            "why_this_works": "Cites law, shows our reasonableness (willingness to negotiate), sets anchor"
        },
        {
            "opponent_says": "We're facing bankruptcy; can't pay more",
            "we_say": "Let's explore payment plan: 370K over 12 months with personal guarantee from director",
            "why_this_works": "Shows flexibility but maintains our number; gets security"
        }
    ]
}
```

---

## ЧАСТЬ 4: IMPLEMENTATION TIMELINE & RESOURCES

### Рекомендуемое распределение задач

| Фаза | Компонента | Трудоёмкость | Сроки | Приоритет |
|------|-----------|--------------|-------|-----------|
| 1 | Database schema | 8 ч. | Week 1 | P0 |
| 1 | Document classifier AI | 16 ч. | Week 1-2 | P0 |
| 1 | Intake endpoints | 12 ч. | Week 2 | P0 |
| 1 | Frontend UI | 10 ч. | Week 2 | P1 |
| 2 | Case-law search integration | 12 ч. | Week 3 | P0 |
| 2 | Precedent grouping AI | 16 ч. | Week 3-4 | P0 |
| 2 | Counter-arg mapper | 12 ч. | Week 4 | P0 |
| 3 | Strategy engine schema | 8 ч. | Week 5 | P0 |
| 3 | Strategy generation AI | 20 ч. | Week 5-6 | P0 |
| 3 | Deadline management | 10 ч. | Week 6 | P1 |
| 4 | Strategic generation endpoint | 12 ч. | Week 7 | P0 |
| 4 | Document templates (5 types) | 24 ч. | Week 7-8 | P0 |
| 5 | Outcome tracking | 10 ч. | Week 9 | P2 |

**Total: ~200 hours = 5-6 weeks (1 senior developer + 1 junior)**

---

## ЧАСТЬ 5: KEY SUCCESS METRICS

### Качество Классификации (Phase 1)
- Document type accuracy: >95%
- Risk stratification confidence: >90%
- Issue detection recall: >85% (catch real issues)

### Качество Precedent Mapping (Phase 2)
- Relevant precedent retrieval: >80%
- Pattern accuracy: >85%
- Counter-argument prediction: >75%

### Качество Strategy (Phase 3)
- Confidence score calibration: ±10% (if we say 85%, actual success ~85%)
- Immediate action relevance: >90%
- Deadline accuracy: 100% (must be correct)

### Качество Document Generation (Phase 4)
- Precedent citation accuracy: 100%
- Legal language quality: Rated 4+/5 by lawyers
- Appeal-proofness: >85% of generated docs survive appeal

### Case Outcomes (Phase 5)
- Average case success rate: >70%
- Settlement negotiation improvement: >20% better terms vs baseline
- Time-to-resolution reduction: >30% faster

---

## NEXT STEPS

1. **Week 1-2**: Implement Phase 1 (Intake + Classifier)
2. **Week 3-4**: Implement Phase 2 (Precedent Mapping)
3. **Week 5-6**: Implement Phase 3 (Strategy Blueprint)
4. **Week 7-8**: Implement Phase 4 (Strategic Generation)
5. **Week 9+**: Phase 5 (Feedback & Learning)

**First "Top-Tier" case: After Phase 3 is complete (Week 6)**

---

END OF PLAN
