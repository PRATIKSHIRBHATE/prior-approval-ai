"""Knowledge base backed by ChromaDB for RAG retrieval.

Stores three document categories:
  1. Historical claims (approved / rejected)
  2. Part-to-vehicle-system mappings
  3. Repair reference entries
"""

from __future__ import annotations

import chromadb
from chromadb.config import Settings


# ---------------------------------------------------------------------------
# ChromaDB client (in-memory for demo; swap to persistent path for prod)
# ---------------------------------------------------------------------------

_client: chromadb.ClientAPI | None = None


def get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.Client(Settings(anonymized_telemetry=False))
    return _client


def get_collection(name: str = "claims_kb") -> chromadb.Collection:
    client = get_client()
    return client.get_or_create_collection(name=name)


# ---------------------------------------------------------------------------
# Seed data — representative sample for the demo
# ---------------------------------------------------------------------------

SEED_HISTORICAL_CLAIMS = [
    {
        "id": "hc-001",
        "text": "Vehicle system: rear differential. Symptom: oil leak at pinion seal. "
                "Diagnosis: pinion seal failure. Repair: replace pinion seal. "
                "Parts used: pinion seal, differential oil, crush sleeve. Outcome: approved.",
        "metadata": {"category": "historical_claim", "outcome": "approved", "vehicle_system": "rear differential"},
    },
    {
        "id": "hc-002",
        "text": "Vehicle system: engine. Symptom: rough idle and misfires. "
                "Diagnosis: worn spark plugs. Repair: replace spark plugs. "
                "Parts used: spark plug set, ignition coil. Outcome: approved.",
        "metadata": {"category": "historical_claim", "outcome": "approved", "vehicle_system": "engine"},
    },
    {
        "id": "hc-003",
        "text": "Vehicle system: alternator. Symptom: battery not charging. "
                "Diagnosis: alternator failure. Repair: replace alternator. "
                "Parts used: alternator, serpentine belt. Outcome: approved.",
        "metadata": {"category": "historical_claim", "outcome": "approved", "vehicle_system": "alternator"},
    },
    {
        "id": "hc-004",
        "text": "Vehicle system: alternator. Symptom: battery not charging. "
                "Diagnosis: alternator failure. Repair: replace alternator. "
                "Parts requested: alternator, spark plug set. Outcome: rejected. "
                "Reason: spark plug set unrelated to alternator repair.",
        "metadata": {"category": "historical_claim", "outcome": "rejected", "vehicle_system": "alternator"},
    },
    {
        "id": "hc-005",
        "text": "Vehicle system: braking system. Symptom: squealing brakes. "
                "Diagnosis: worn brake pads. Repair: replace brake pads and rotors. "
                "Parts used: brake pad set, brake rotor pair. Outcome: approved.",
        "metadata": {"category": "historical_claim", "outcome": "approved", "vehicle_system": "braking system"},
    },
    {
        "id": "hc-006",
        "text": "Vehicle system: wiper system. Symptom: wipers not working. "
                "Diagnosis: wiper motor failure. Repair: replace wiper motor. "
                "Parts requested: wiper motor, alarm/keyless lock system kit. Outcome: rejected. "
                "Reason: alarm/keyless lock system kit unrelated to wiper motor concern.",
        "metadata": {"category": "historical_claim", "outcome": "rejected", "vehicle_system": "wiper system"},
    },
    {
        "id": "hc-007",
        "text": "Vehicle system: transmission. Symptom: harsh shifting. "
                "Diagnosis: transmission fluid degradation. Repair: flush and refill transmission fluid. "
                "Parts used: transmission fluid, transmission filter, pan gasket. Outcome: approved.",
        "metadata": {"category": "historical_claim", "outcome": "approved", "vehicle_system": "transmission"},
    },
    {
        "id": "hc-008",
        "text": "Vehicle system: cooling system. Symptom: engine overheating. "
                "Diagnosis: thermostat stuck closed. Repair: replace thermostat. "
                "Parts used: thermostat, coolant, thermostat gasket. Outcome: approved.",
        "metadata": {"category": "historical_claim", "outcome": "approved", "vehicle_system": "cooling system"},
    },
]

SEED_PART_MAPPINGS = [
    {
        "id": "pm-001",
        "text": "Part: pinion seal. Compatible vehicle systems: rear differential, front differential, transfer case.",
        "metadata": {"category": "part_mapping", "part_name": "pinion seal"},
    },
    {
        "id": "pm-002",
        "text": "Part: spark plug set. Compatible vehicle systems: engine, ignition system.",
        "metadata": {"category": "part_mapping", "part_name": "spark plug set"},
    },
    {
        "id": "pm-003",
        "text": "Part: alternator. Compatible vehicle systems: alternator, charging system, electrical system.",
        "metadata": {"category": "part_mapping", "part_name": "alternator"},
    },
    {
        "id": "pm-004",
        "text": "Part: brake pad set. Compatible vehicle systems: braking system, front brakes, rear brakes.",
        "metadata": {"category": "part_mapping", "part_name": "brake pad set"},
    },
    {
        "id": "pm-005",
        "text": "Part: wiper motor. Compatible vehicle systems: wiper system, windshield system.",
        "metadata": {"category": "part_mapping", "part_name": "wiper motor"},
    },
    {
        "id": "pm-006",
        "text": "Part: serpentine belt. Compatible vehicle systems: alternator, engine, power steering, AC compressor.",
        "metadata": {"category": "part_mapping", "part_name": "serpentine belt"},
    },
    {
        "id": "pm-007",
        "text": "Part: thermostat. Compatible vehicle systems: cooling system, engine.",
        "metadata": {"category": "part_mapping", "part_name": "thermostat"},
    },
    {
        "id": "pm-008",
        "text": "Part: transmission filter. Compatible vehicle systems: transmission, drivetrain.",
        "metadata": {"category": "part_mapping", "part_name": "transmission filter"},
    },
]

SEED_REPAIR_REFERENCES = [
    {
        "id": "rr-001",
        "text": "Failure mode: pinion seal failure in rear differential. "
                "Recommended parts: pinion seal, differential oil, crush sleeve. "
                "Procedure: Remove driveshaft, remove pinion nut, extract old seal, install new seal.",
        "metadata": {"category": "repair_reference", "vehicle_system": "rear differential", "failure_mode": "pinion seal failure"},
    },
    {
        "id": "rr-002",
        "text": "Failure mode: alternator failure in charging system. "
                "Recommended parts: alternator, serpentine belt. "
                "Procedure: Disconnect battery, remove serpentine belt, unbolt alternator, install replacement.",
        "metadata": {"category": "repair_reference", "vehicle_system": "alternator", "failure_mode": "alternator failure"},
    },
    {
        "id": "rr-003",
        "text": "Failure mode: worn brake pads in braking system. "
                "Recommended parts: brake pad set, brake rotor pair, brake caliper hardware kit. "
                "Procedure: Remove wheel, remove caliper, replace pads and rotors, reassemble.",
        "metadata": {"category": "repair_reference", "vehicle_system": "braking system", "failure_mode": "worn brake pads"},
    },
    {
        "id": "rr-004",
        "text": "Failure mode: wiper motor failure. "
                "Recommended parts: wiper motor, wiper transmission linkage. "
                "Procedure: Remove cowl panel, disconnect wiper motor, install replacement motor.",
        "metadata": {"category": "repair_reference", "vehicle_system": "wiper system", "failure_mode": "wiper motor failure"},
    },
]


# ---------------------------------------------------------------------------
# Loading & querying
# ---------------------------------------------------------------------------

def load_seed_data(collection_name: str = "claims_kb") -> chromadb.Collection:
    """Load all seed documents into ChromaDB and return the collection."""
    collection = get_collection(collection_name)

    all_docs = SEED_HISTORICAL_CLAIMS + SEED_PART_MAPPINGS + SEED_REPAIR_REFERENCES

    # Avoid re-inserting if already loaded
    existing = collection.count()
    if existing >= len(all_docs):
        return collection

    ids = [doc["id"] for doc in all_docs]
    documents = [doc["text"] for doc in all_docs]
    metadatas = [doc["metadata"] for doc in all_docs]

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return collection


def query_knowledge_base(
    diagnosis: str,
    vehicle_system: str,
    repair_action: str,
    top_k: int = 5,
    collection_name: str = "claims_kb",
) -> list[dict]:
    """Query the vector store and return the top-K most relevant documents.

    Parameters
    ----------
    diagnosis : str
        The diagnosed failure (e.g. "pinion seal failure").
    vehicle_system : str
        The vehicle system involved (e.g. "rear differential").
    repair_action : str
        The planned repair action (e.g. "replace pinion seal").
    top_k : int
        Maximum number of documents to retrieve.

    Returns
    -------
    list[dict]
        Each dict has keys: id, document, metadata, distance.
    """
    collection = get_collection(collection_name)

    # If collection is empty, return empty
    if collection.count() == 0:
        return []

    query_text = f"{diagnosis} {vehicle_system} {repair_action}"

    results = collection.query(
        query_texts=[query_text],
        n_results=min(top_k, collection.count()),
    )

    documents = []
    if results and results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            documents.append({
                "id": doc_id,
                "document": results["documents"][0][i] if results["documents"] else "",
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else 0.0,
            })

    return documents
