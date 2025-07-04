import logging
import json
from openai import OpenAI
from src.storage import Storage
from src.embeddings import LocalEmbeddings
from src.entity_resolver import EntityResolver
from src.processor_v2 import EnhancedMeetingProcessor
from src.query_engine_v2 import QueryEngineV2
from src.config import settings
from src.models import ExtractionResult
from src.eml_parser import EMLParser

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main function to run the verification test."""
    logger.info("Starting verification of refactored LLM calls...")

    # --- 1. Initialization ---
    logger.info("Initializing components...")
    storage = Storage()
    embeddings = LocalEmbeddings()
    llm_client = OpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
    )
    entity_resolver = EntityResolver(storage, embeddings, llm_client)
    processor = EnhancedMeetingProcessor(storage, entity_resolver, embeddings)
    query_engine = QueryEngineV2(storage, llm_client, entity_resolver)

    # --- 2. Data Selection and Parsing ---
    eml_file_path = "data/BRV Readiness Planning And Hypercare Strategy.eml"
    logger.info(f"Parsing EML file: {eml_file_path}")
    parser = EMLParser(eml_file_path)
    email_body = parser.get_body()
    meeting_id = parser.get_message_id()

    # --- 3. Simulate Extraction (Simplified) ---
    # In a real scenario, an extractor LLM call would produce this.
    # We will create a simplified version to test the processor.
    logger.info("Simulating extraction result...")
    extraction = ExtractionResult(
        entities=[
            {"name": "BRV Readiness", "type": "Project", "description": "The overall project for BRV readiness."},
            {"name": "Hypercare Strategy", "type": "Plan", "description": "The plan for post-launch support."},
            {"name": "UAT Coordination", "type": "Task", "description": "Coordination of User Acceptance Testing."}
        ],
        relationships=[],
        states=[
            {"entity": "BRV Readiness", "to_state": {"status": "in_progress", "progress": "50%"}},
            {"entity": "Hypercare Strategy", "to_state": {"status": "planned"}},
        ],
        memories=[],
        meeting_metadata={
            "title": "BRV Readiness Planning And Hypercare Strategy",
            "summary": "The team discussed the progress of the BRV readiness project, which is now 50% complete. The hypercare strategy is still in the planning phase. UAT coordination was also discussed as a key task.",
            "transcript_context": email_body
        }
    )

    # --- 4. Process the Meeting ---
    logger.info(f"Processing meeting with ID: {meeting_id}")
    try:
        processing_result = processor.process_meeting_with_context(extraction, meeting_id)
        logger.info("Meeting processing completed.")
        logger.info(f"Processing Validation Metrics: {json.dumps(processing_result['validation'], indent=2)}")
        logger.info("Generated State Changes:")
        for transition in processing_result.get("state_changes", []):
            logger.info(json.dumps(transition.to_dict(), indent=2))
    except Exception as e:
        logger.error(f"An error occurred during meeting processing: {e}", exc_info=True)
        return

    # --- 5. Query the System ---
    logger.info("--- Querying System --- ")
    queries = [
        "What is the status of BRV Readiness?",
        "Give me a timeline for the Hypercare Strategy.",
        "Are there any blockers for UAT Coordination?"
    ]

    for query in queries:
        logger.info(f"\nExecuting query: '{query}'")
        try:
            query_response = query_engine.query(query)
            logger.info(f"Query Response:\n{query_response}")
        except Exception as e:
            logger.error(f"An error occurred during query execution: {e}", exc_info=True)

    logger.info("\nVerification script finished.")

if __name__ == "__main__":
    main()
