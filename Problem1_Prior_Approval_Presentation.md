# Problem 1: ESB AI / Prior Approval — AI-Assisted Warranty Claim Validation

## Selected Problem: Problem 1 — Prior Approval (Pre-Repair Validation)

---

## SLIDE 1 — Business Case

### The Problem
During Ford's Prior Approval (Pre-Repair) process, technicians submit warranty claims containing:
- A text narrative (customer concern, diagnosis, planned repair)
- A list of requested parts for authorization

Currently, human assessors must manually validate whether requested parts are logically justified by the technician's story. This is slow, inconsistent, and expensive at scale.

**Examples of anomalies:**
- Requesting spark plugs for an alternator repair
- Requesting an alarm/keyless lock system kit for a wiper motor concern
- Requesting unrelated parts that inflate claim costs

### Why It Matters to Ford
- **Volume**: Ford processes millions of warranty claims annually (~$3.5B+ in warranty costs)
- **Fraud/Waste**: Even 1-2% unjustified parts = tens of millions in unnecessary payouts
- **Speed**: Manual review creates bottlenecks — vehicles sit idle, customer satisfaction drops
- **Consistency**: Human assessors vary in accuracy and domain expertise

### Expected Business Value
| Metric | Impact |
|--------|--------|
| Claim processing time | 70-80% reduction (minutes → seconds) |
| Unjustified part detection | 15-25% improvement in catch rate |
| Assessor productivity | 3-5x throughput increase (AI handles routine, humans handle edge cases) |
| Annual cost savings | Estimated $50-150M reduction in unjustified payouts |
| Customer experience | Faster approvals → reduced vehicle downtime |

### Assumptions
- The system augments (not replaces) human assessors — AI flags/scores, humans make final decisions on edge cases
- Ford has access to historical approved/rejected claims for training and retrieval
- Part catalogs and vehicle service manuals are available as reference knowledge

---

## SLIDE 2 — Architecture / System Diagram

### Overall Solution Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         AI PRIOR APPROVAL SYSTEM                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────┐    ┌──────────────────────────────────────────────────┐       │
│  │  CLAIM       │    │          AGENTIC ORCHESTRATOR                     │       │
│  │  INGESTION   │───▶│  (LangGraph / CrewAI / Custom Agent Framework)   │       │
│  │  API         │    │                                                   │       │
│  └──────────────┘    │  ┌─────────┐ ┌──────────┐ ┌───────────────┐     │       │
│                       │  │ Claim   │ │ Parts    │ │ Reasoning     │     │       │
│                       │  │ Parser  │ │ Validator│ │ & Scoring     │     │       │
│                       │  │ Agent   │ │ Agent    │ │ Agent         │     │       │
│                       │  └────┬────┘ └────┬─────┘ └──────┬────────┘     │       │
│                       └───────┼───────────┼──────────────┼──────────────┘       │
│                               │           │              │                       │
│                               ▼           ▼              ▼                       │
│  ┌────────────────────────────────────────────────────────────────────┐          │
│  │                    RAG RETRIEVAL LAYER                              │          │
│  │                                                                    │          │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐     │          │
│  │  │ Vector DB    │  │ Parts        │  │ Historical Claims   │     │          │
│  │  │ (Pinecone/   │  │ Catalog      │  │ Knowledge Base      │     │          │
│  │  │  OpenSearch) │  │ Index        │  │ (approved/rejected) │     │          │
│  │  └──────────────┘  └──────────────┘  └─────────────────────┘     │          │
│  └────────────────────────────────────────────────────────────────────┘          │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────┐          │
│  │                    FOUNDATION MODELS                                │          │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐    │          │
│  │  │ Amazon Bedrock   │  │ Embedding Model │  │ Classification │    │          │
│  │  │ (Claude/Titan)   │  │ (Titan/Cohere)  │  │ Model (Fine-   │    │          │
│  │  │ for Reasoning    │  │ for Retrieval   │  │ tuned)         │    │          │
│  │  └─────────────────┘  └─────────────────┘  └────────────────┘    │          │
│  └────────────────────────────────────────────────────────────────────┘          │
│                                                                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│  CLOUD SERVICES (AWS)                                                            │
│  • API Gateway + Lambda (Ingestion)    • S3 (Document Store)                    │
│  • SageMaker (Model Hosting)           • OpenSearch (Vector Search)             │
│  • Step Functions (Orchestration)      • DynamoDB (Claim State)                 │
│  • CloudWatch (Monitoring)             • Bedrock (LLM Access)                   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Claim Ingestion | API Gateway + Lambda | Receive and normalize claim data |
| Agentic Orchestrator | LangGraph on ECS/Lambda | Multi-agent coordination |
| Claim Parser Agent | LLM (Claude 3.5) | Extract structured entities from narratives |
| Parts Validator Agent | RAG + LLM | Cross-reference parts against diagnosis |
| Reasoning Agent | LLM (Claude 3.5) | Generate human-readable justification |
| Vector Store | Amazon OpenSearch Serverless | Semantic search over parts catalog + historical claims |
| Embedding Model | Amazon Titan Embeddings | Convert text to vectors for retrieval |
| Decision Store | DynamoDB | Track claim decisions and audit trail |

---

## SLIDE 3 — Flow Diagram

### End-to-End Process Flow

```
┌─────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│Technician│────▶│ Claim    │────▶│ STEP 1:      │────▶│ STEP 2:      │────▶│ STEP 3:     │
│ Submits  │     │ Ingestion│     │ Parse &      │     │ RAG          │     │ Validate    │
│ Claim    │     │ API      │     │ Extract      │     │ Retrieval    │     │ Parts       │
└─────────┘     └──────────┘     └──────────────┘     └──────────────┘     └─────────────┘
                                        │                     │                     │
                                        ▼                     ▼                     ▼
                                  ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
                                  │ Entities:    │     │ Retrieved:   │     │ For each    │
                                  │ • Symptom    │     │ • Similar    │     │ part:       │
                                  │ • Diagnosis  │     │   claims     │     │ • Relevant? │
                                  │ • System     │     │ • Part-system│     │ • Score     │
                                  │ • Parts List │     │   mappings   │     │ • Reason    │
                                  └──────────────┘     │ • Repair     │     └──────┬──────┘
                                                       │   manuals    │            │
                                                       └──────────────┘            │
                                                                                   ▼
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────┐
│ OUTPUT:     │◀────│ STEP 5:      │◀────│ STEP 4:      │◀────│ STEP 3 Result:           │
│ Decision    │     │ Human-in-    │     │ Aggregate    │     │ Per-Part Scores          │
│ Delivered   │     │ Loop (Edge   │     │ & Score      │     │ ┌────────┬───────┬─────┐ │
│ to System   │     │ Cases Only)  │     │ Claim        │     │ │ Part   │ Score │Valid│ │
└─────────────┘     └──────────────┘     └──────────────┘     │ ├────────┼───────┼─────┤ │
                                                               │ │Seal    │ 0.95  │ ✓  │ │
                                                               │ │Oil     │ 0.92  │ ✓  │ │
                                                               │ │Nut     │ 0.88  │ ✓  │ │
                                                               │ │SpkPlug │ 0.12  │ ✗  │ │
                                                               │ └────────┴───────┴─────┘ │
                                                               └──────────────────────────┘
```

### Detailed Step Descriptions

**Step 1 — Parse & Extract (Claim Parser Agent)**
- Input: Raw claim (customer concern, tech findings, recommended repair, parts list)
- Process: LLM extracts structured entities — vehicle system (e.g., "rear differential"), symptom ("oil leak"), diagnosis ("pinion seal failure"), repair action ("replace seal")
- Output: Structured claim context

**Step 2 — RAG Retrieval**
- Query vector DB with: diagnosis + vehicle system + repair action
- Retrieve: Top-K similar historical approved claims, part-to-system mappings from catalog, relevant repair manual sections
- Purpose: Provide grounding evidence for validation

**Step 3 — Parts Validation (Parts Validator Agent)**
- For EACH requested part:
  - Check: Does part description relate to the diagnosed system?
  - Check: Was this part used in similar historical repairs?
  - Check: Does the repair manual suggest this part for this failure mode?
  - Score: 0.0 (completely unjustified) to 1.0 (perfectly justified)
  - Reason: Natural language explanation

**Step 4 — Aggregate & Score**
- Combine per-part scores into overall claim confidence
- Flag claims with any part below threshold (e.g., <0.5)
- Categorize: AUTO-APPROVE (all parts >0.8) / REVIEW (mixed) / FLAG (any part <0.3)

**Step 5 — Human-in-Loop (Edge Cases)**
- Claims in REVIEW/FLAG category routed to human assessor
- AI provides reasoning and evidence to accelerate human review
- Human decision feeds back into training data

---

## SLIDE 4 — Risks, Bottlenecks & Scaling

### Key Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **LLM Hallucination** — AI fabricates justification for invalid parts | High | RAG grounding + confidence thresholds + mandatory retrieval evidence |
| **False Rejections** — Valid claims incorrectly flagged | High | Conservative thresholds (bias toward approval) + human review for borderline |
| **Data Quality** — Inconsistent technician narratives | Medium | Robust parsing with few-shot examples + fallback to keyword matching |
| **Part Catalog Gaps** — New/unlisted parts not in knowledge base | Medium | Graceful degradation — unknown parts flagged for human review, not auto-rejected |
| **Adversarial Gaming** — Technicians crafting narratives to fool AI | Low | Anomaly detection on narrative patterns + periodic model retraining |

### Bottlenecks

| Bottleneck | Impact | Solution |
|-----------|--------|----------|
| **LLM Latency** — Multi-step reasoning takes 5-15s per claim | Processing speed | Parallel agent execution + caching of part-system mappings |
| **Vector DB Cold Start** — Initial embedding of millions of historical claims | Deployment time | Batch pre-processing + incremental indexing for new claims |
| **Human Review Queue** — Too many edge cases overflow assessor capacity | Throughput | Adaptive thresholds + active learning to reduce review volume over time |
| **Token Costs** — Large narratives × multiple LLM calls per claim | Operating cost | Summarization pre-step + tiered model usage (small model for parsing, large for reasoning) |

### Scaling Strategy

```
                    SCALING DIMENSIONS
    ┌─────────────────────────────────────────┐
    │                                         │
    │  HORIZONTAL                             │
    │  • Lambda auto-scaling for ingestion    │
    │  • ECS task scaling for agent workers   │
    │  • OpenSearch replica shards            │
    │                                         │
    │  THROUGHPUT                              │
    │  • Async processing via SQS queues      │
    │  • Batch mode for non-urgent claims     │
    │  • Result caching for repeat patterns   │
    │                                         │
    │  DATA                                   │
    │  • Partitioned vector indices by        │
    │    vehicle system / model year           │
    │  • Tiered storage (hot/warm/cold)       │
    │  • Incremental re-indexing pipeline     │
    │                                         │
    │  MODEL                                  │
    │  • Fine-tuned smaller models for        │
    │    high-volume simple validations        │
    │  • Large models reserved for complex    │
    │    multi-system repairs                  │
    │  • Model versioning + A/B testing       │
    │                                         │
    └─────────────────────────────────────────┘
```

---

## SLIDE 5 — Measuring Value

### KPIs and Metrics

#### Primary Business KPIs

| KPI | Baseline (Manual) | Target (AI-Assisted) | Measurement Method |
|-----|-------------------|---------------------|-------------------|
| **Avg. Claim Processing Time** | 2-4 hours | <5 minutes (auto) / 30 min (review) | Timestamp delta: submission → decision |
| **Unjustified Part Detection Rate** | ~60-70% (human) | >90% | Precision/Recall vs. audited ground truth |
| **False Rejection Rate** | N/A | <2% | Post-hoc audit of AI rejections |
| **Assessor Throughput** | 40-60 claims/day | 150-200 claims/day (AI-assisted) | Claims processed per assessor per shift |
| **Annual Cost Avoidance** | Baseline | $50-150M | Sum of flagged unjustified part costs |

#### AI/ML Performance Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| **Part Validation Accuracy** | >92% | % of parts correctly classified as justified/unjustified |
| **Precision (Flagging)** | >85% | Of parts flagged as unjustified, % actually unjustified |
| **Recall (Flagging)** | >90% | Of all unjustified parts, % caught by AI |
| **RAG Retrieval Relevance** | >80% MRR@5 | Mean Reciprocal Rank of relevant retrieved documents |
| **Reasoning Quality** | >4.0/5.0 | Human rating of AI-generated explanations |
| **Latency P95** | <10 seconds | 95th percentile end-to-end processing time |

#### Operational Health Metrics

| Metric | Target | Purpose |
|--------|--------|---------|
| **Auto-Approval Rate** | 60-70% of claims | Measures AI confidence / assessor workload reduction |
| **Human Override Rate** | <10% of AI decisions | Tracks AI alignment with human judgment |
| **Feedback Loop Velocity** | Weekly model refresh | Time from new data → model improvement |
| **System Uptime** | 99.9% | Availability SLA |
| **Cost per Claim** | <$0.50 | Total AI infrastructure cost / claims processed |

#### Continuous Improvement Loop

```
  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │ AI Decision  │────▶│ Human Review │────▶│ Feedback     │
  │ + Reasoning  │     │ (Override?)  │     │ Captured     │
  └──────────────┘     └──────────────┘     └──────┬───────┘
                                                    │
         ┌──────────────────────────────────────────┘
         ▼
  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │ Retrain /    │────▶│ A/B Test     │────▶│ Deploy       │
  │ Fine-tune    │     │ New vs Old   │     │ Improved     │
  └──────────────┘     └──────────────┘     └──────────────┘
```

**Measurement Cadence:**
- Real-time: Latency, throughput, error rates (CloudWatch dashboards)
- Daily: Accuracy metrics, auto-approval rates, override rates
- Weekly: Cost analysis, model drift detection
- Monthly: Business KPI review, ROI calculation
- Quarterly: Full model retraining assessment, strategy review
