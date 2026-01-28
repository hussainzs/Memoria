"""
Run python -m src.tests.reasoningbank_retriever_test
"""

import asyncio
from src.subquery_gen.reasoningbank_retriever import ReasoningBankRetriever


async def test_reasoningbank_retriever():
    """
    Simple test to verify ReasoningBankRetriever connections and functionality.
    """
    print("Initializing ReasoningBankRetriever...")
    
    # Initialize retriever with example weights
    # bm25_weight=0.7 for keyword matching, dense_weight=0.3 for semantic search
    retriever = ReasoningBankRetriever(bm25_weight=0.7, dense_weight=0.3)
    
    # Test query
    user_query = "give me the cheapest suppliers with best service levels and low price"
    
    try:
        # Retrieve results
        results = await retriever.retrieve(
            user_query=user_query,
            limit=5,
        )
        
        print(f"Retrieved {len(results)} results:\n")
        print("=" * 80)
        print(results)
        print("=" * 80)
        
    except Exception as e:
        print(f"Error during retrieval: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_reasoningbank_retriever())
