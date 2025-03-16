"""This module provides functions to retrieve related context."""
import database
from langchain_core.documents import Document


def _combine(texts: list[str]) -> str:
    return "\n\n".join(texts)


def get_context(
        client_id: str,
        context_name: str,
        query: str,
        num_retrieve: int = 30,
        score_threshold: float = 0.3,
    ) -> tuple[str, str]:
    """Get related context from the database."""
    collection = database.Collection(client_id, context_name)
    texts = collection.content.get()['documents']
    
    if len(texts) > num_retrieve:
        return retrieve_database(
            collection, query, num_retrieve, score_threshold)
    
    metamsg = f"Too many requested. {len(texts)} returned."
    return _combine(texts), metamsg


def retrieve_database(
        collection: database.Collection,
        query: str,
        num_retrieve: int,
        score_threshold: float,
    ) -> tuple[str, str]:
    """Retrieve related context from the database."""

    retriever = collection.content.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "k": num_retrieve,
            "score_threshold": score_threshold,
        },
    )
    chunks = retriever.invoke(query)
    texts = [chunk.page_content for chunk in chunks]
    metamsg = f"{num_retrieve} requested, {len(chunks)} retrieved."
    return _combine(texts), metamsg
