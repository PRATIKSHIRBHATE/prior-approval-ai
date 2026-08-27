"""LangGraph multi-agent backend for warranty claim validation.

Mirrors the reference travel-planner project structure:
  StateGraph  →  sequential agent nodes  →  PostgresSaver checkpointer
"""

import os
import json
import certifi
from dotenv import load_dotenv

load_dotenv()

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

from typing import TypedDict, Annotated, List
import operator
import uuid

import psycopg
from psycopg.rows import dict_row

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import (
    AnyMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
)
from langchain_groq import ChatGroq

from models import ParsedClaim, PartResult, ClaimDecision
from decision import categorize_claim
from knowledge_base import load_seed_data, query_knowledge_base


# ===========================================================================
# Configuration
# ===========================================================================

def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError(
            "DATABASE_URL is missing. Please add your PostgreSQL URL to .env"
        )
    if "sslmode=" not in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{separator}sslmode=require"
    return database_url


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing. Please add it to your .env file.")


# ===========================================================================
# LLM
# ===========================================================================

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=GROQ_API_KEY,
)


# ===========================================================================
# State
# ===========================================================================

class ClaimValidationState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    narrative: str
    parts: list[str]
    parsed_claim: str       # JSON string of ParsedClaim
    retrieval_context: str  # Formatted retrieved documents
    part_scores: str        # JSON string of list[PartResult]
    explanation: str        # Human-readable summary
    decision: str           # AUTO_APPROVE | REVIEW | FLAG
    overall_score: float
    llm_calls: int


# ===========================================================================
# Agent 1: Claim Parser
# ===========================================================================

def claim_parser_agent(state: ClaimValidationState) -> dict:
    """Extract structured entities from the technician's narrative."""

    narrative = state["narrative"]

    prompt = f"""You are an automotive warranty claim parser. Extract structured information from the following technician narrative.

Return ONLY a valid JSON object with these exact keys:
- "vehicle_system": the vehicle system being repaired (e.g., "rear differential", "engine", "braking system")
- "symptom": the reported symptom (e.g., "oil leak", "rough idle")
- "diagnosis": the diagnosed problem (e.g., "pinion seal failure", "worn spark plugs")
- "repair_action": the planned repair (e.g., "replace pinion seal", "replace spark plugs")
- "confidence": a float between 0.0 and 1.0 indicating how confident you are in the extraction

If any field cannot be determined, use "unknown" as the value and lower the confidence.

Technician Narrative:
{narrative}

JSON Output:"""

    response = llm.invoke([
        SystemMessage(content="You are an expert automotive warranty claim parser. Return only valid JSON."),
        HumanMessage(content=prompt),
    ])

    # Try to parse LLM output as JSON
    try:
        raw = response.content.strip()
        # Handle markdown code blocks
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            raw = raw.rsplit("```", 1)[0]
        parsed = json.loads(raw)
        claim = ParsedClaim(
            vehicle_system=parsed.get("vehicle_system", "unknown"),
            symptom=parsed.get("symptom", "unknown"),
            diagnosis=parsed.get("diagnosis", "unknown"),
            repair_action=parsed.get("repair_action", "unknown"),
            confidence=float(parsed.get("confidence", 0.5)),
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        claim = ParsedClaim(
            vehicle_system="unknown",
            symptom="unknown",
            diagnosis="unknown",
            repair_action="unknown",
            confidence=0.1,
        )

    return {
        "parsed_claim": claim.to_json(),
        "messages": [AIMessage(content="Claim parsed successfully.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


# ===========================================================================
# Agent 2: RAG Retrieval
# ===========================================================================

def rag_retrieval(state: ClaimValidationState) -> dict:
    """Query the vector store for relevant evidence."""

    parsed = ParsedClaim.from_json(state["parsed_claim"])

    # Ensure seed data is loaded
    load_seed_data()

    docs = query_knowledge_base(
        diagnosis=parsed.diagnosis,
        vehicle_system=parsed.vehicle_system,
        repair_action=parsed.repair_action,
        top_k=5,
    )

    if not docs:
        context = "No relevant documents found in the knowledge base. This claim should be reviewed by a human assessor."
    else:
        lines = []
        for i, doc in enumerate(docs, 1):
            lines.append(f"--- Document {i} (distance: {doc['distance']:.3f}) ---")
            lines.append(doc["document"])
            lines.append(f"Category: {doc['metadata'].get('category', 'unknown')}")
            lines.append("")
        context = "\n".join(lines)

    return {
        "retrieval_context": context,
        "messages": [AIMessage(content="RAG retrieval completed.")],
        "llm_calls": state.get("llm_calls", 0),
    }


# ===========================================================================
# Agent 3: Parts Validator
# ===========================================================================

def parts_validator_agent(state: ClaimValidationState) -> dict:
    """Evaluate each requested part against the diagnosis and evidence."""

    parsed = ParsedClaim.from_json(state["parsed_claim"])
    parts = state["parts"]
    context = state["retrieval_context"]

    prompt = f"""You are an automotive warranty parts validation expert. For each requested part, determine if it is justified by the diagnosis and evidence.

Claim Context:
- Vehicle System: {parsed.vehicle_system}
- Symptom: {parsed.symptom}
- Diagnosis: {parsed.diagnosis}
- Repair Action: {parsed.repair_action}

Retrieved Evidence:
{context}

Requested Parts: {json.dumps(parts)}

For EACH part, provide:
- "part_name": the part name exactly as listed
- "relevance_score": float 0.0 (completely unjustified) to 1.0 (perfectly justified)
- "reason": a brief explanation of why this score was assigned
- "evidence_refs": list of evidence document references that support your assessment

Return ONLY a valid JSON array of objects. Example:
[
  {{"part_name": "pinion seal", "relevance_score": 0.95, "reason": "Directly related to diagnosed pinion seal failure", "evidence_refs": ["Document 1"]}},
  {{"part_name": "spark plug set", "relevance_score": 0.1, "reason": "Unrelated to rear differential repair", "evidence_refs": []}}
]

JSON Array Output:"""

    response = llm.invoke([
        SystemMessage(content="You are an expert automotive warranty parts validator. Return only valid JSON."),
        HumanMessage(content=prompt),
    ])

    try:
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            raw = raw.rsplit("```", 1)[0]
        parsed_results = json.loads(raw)
        part_results = []
        for pr in parsed_results:
            part_results.append(PartResult(
                part_name=pr.get("part_name", "unknown"),
                relevance_score=float(pr.get("relevance_score", 0.5)),
                reason=pr.get("reason", "No reason provided"),
                evidence_refs=pr.get("evidence_refs", []),
            ))
    except (json.JSONDecodeError, KeyError, TypeError):
        # Fallback: score all parts as needing review
        part_results = [
            PartResult(
                part_name=p,
                relevance_score=0.5,
                reason="Unable to parse LLM response; flagged for manual review.",
                evidence_refs=[],
            )
            for p in parts
        ]

    # Ensure all submitted parts have a result
    scored_names = {pr.part_name.lower() for pr in part_results}
    for p in parts:
        if p.lower() not in scored_names:
            part_results.append(PartResult(
                part_name=p,
                relevance_score=0.5,
                reason="Part not evaluated by LLM; flagged for manual review.",
                evidence_refs=[],
            ))

    scores_json = json.dumps([pr.to_dict() for pr in part_results])

    return {
        "part_scores": scores_json,
        "messages": [AIMessage(content="Parts validation completed.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


# ===========================================================================
# Agent 4: Reasoning
# ===========================================================================

def reasoning_agent(state: ClaimValidationState) -> dict:
    """Generate a human-readable explanation of the validation decision."""

    parsed = ParsedClaim.from_json(state["parsed_claim"])
    part_results = [PartResult.from_dict(pr) for pr in json.loads(state["part_scores"])]
    context = state["retrieval_context"]

    parts_summary = "\n".join(
        f"  - {pr.part_name}: score={pr.relevance_score:.2f} — {pr.reason}"
        for pr in part_results
    )

    prompt = f"""You are a warranty claim review assistant. Generate a clear, concise explanation of the validation results for this claim.

Claim Summary:
- Vehicle System: {parsed.vehicle_system}
- Symptom: {parsed.symptom}
- Diagnosis: {parsed.diagnosis}
- Repair Action: {parsed.repair_action}

Per-Part Validation Results:
{parts_summary}

Retrieved Evidence Summary:
{context[:1500]}

Write a 2-4 paragraph explanation that:
1. Summarizes the claim and diagnosis
2. Explains which parts are justified and which are not, referencing the evidence
3. Provides an overall assessment

Explanation:"""

    response = llm.invoke([
        SystemMessage(content="You are a professional warranty claim review assistant. Write clear, evidence-based explanations."),
        HumanMessage(content=prompt),
    ])

    return {
        "explanation": response.content.strip(),
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


# ===========================================================================
# Agent 5: Aggregation
# ===========================================================================

def aggregation_agent(state: ClaimValidationState) -> dict:
    """Compute the final decision category from per-part scores."""

    part_results = [PartResult.from_dict(pr) for pr in json.loads(state["part_scores"])]
    scores = [pr.relevance_score for pr in part_results]

    decision, overall_score = categorize_claim(scores)

    return {
        "decision": decision,
        "overall_score": overall_score,
        "messages": [AIMessage(content=f"Claim categorized as {decision} (score: {overall_score:.2f}).")],
        "llm_calls": state.get("llm_calls", 0),
    }


# ===========================================================================
# Build Graph
# ===========================================================================

graph = StateGraph(ClaimValidationState)

graph.add_node("claim_parser_agent", claim_parser_agent)
graph.add_node("rag_retrieval", rag_retrieval)
graph.add_node("parts_validator_agent", parts_validator_agent)
graph.add_node("reasoning_agent", reasoning_agent)
graph.add_node("aggregation_agent", aggregation_agent)

graph.add_edge(START, "claim_parser_agent")
graph.add_edge("claim_parser_agent", "rag_retrieval")
graph.add_edge("rag_retrieval", "parts_validator_agent")
graph.add_edge("parts_validator_agent", "reasoning_agent")
graph.add_edge("reasoning_agent", "aggregation_agent")
graph.add_edge("aggregation_agent", END)


# ===========================================================================
# PostgreSQL Checkpointer
# ===========================================================================

DATABASE_URL = get_database_url()

_conn = psycopg.connect(
    DATABASE_URL,
    autocommit=True,
    row_factory=dict_row,
)

checkpointer = PostgresSaver(_conn)
checkpointer.setup()

claim_graph = graph.compile(checkpointer=checkpointer)


# ===========================================================================
# Public API for FastAPI
# ===========================================================================

def run_claim_validator(
    narrative: str,
    parts: list[str],
    thread_id: str | None = None,
) -> dict:
    """Run the full claim validation workflow.

    Returns a dict with: thread_id, decision, overall_score, part_results,
    explanation, parsed_claim, llm_calls.
    """
    if not thread_id:
        thread_id = f"claim_{uuid.uuid4().hex}"

    config = {"configurable": {"thread_id": thread_id}}

    result = claim_graph.invoke(
        {
            "messages": [HumanMessage(content=narrative)],
            "narrative": narrative,
            "parts": parts,
            "parsed_claim": "",
            "retrieval_context": "",
            "part_scores": "[]",
            "explanation": "",
            "decision": "",
            "overall_score": 0.0,
            "llm_calls": 0,
        },
        config=config,
    )

    part_results_raw = json.loads(result.get("part_scores", "[]"))

    return {
        "thread_id": thread_id,
        "decision": result.get("decision", "REVIEW"),
        "overall_score": result.get("overall_score", 0.0),
        "part_results": part_results_raw,
        "explanation": result.get("explanation", ""),
        "parsed_claim": result.get("parsed_claim", "{}"),
        "llm_calls": result.get("llm_calls", 0),
    }
