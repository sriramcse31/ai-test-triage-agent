"""
RAG Memory System - Stores and retrieves historical failures using embeddings
Save as: agent/memory.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
from typing import List, Optional
import numpy as np

from llama_index.core import VectorStoreIndex, Document, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.lancedb import LanceDBVectorStore
import lancedb

# Add sentence-transformers as fallback
try:
    from sentence_transformers import SentenceTransformer
    USE_SENTENCE_TRANSFORMERS = True
except ImportError:
    USE_SENTENCE_TRANSFORMERS = False

from agent.models import HistoricalFailure, Resolution


class FailureMemory:
    """RAG-based memory for storing and retrieving historical failures"""
    
    def __init__(self, db_path: str = "data/failures_db"):
        """Initialize vector store and embedding model"""
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Use local embedding model
        print("🔧 Loading embedding model...")
        
        Settings.embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-small-en-v1.5",
            cache_folder=None,  # Use default cache location
            embed_batch_size=10,
            device=None  # Auto-detect CPU/GPU
        )
        
        # Initialize LanceDB
        self.db = lancedb.connect(str(self.db_path))
        
        # Create or load vector store
        try:
            self.table = self.db.open_table("failures")
            print("✓ Loaded existing failure database")
        except:
            self.table = None
            print("✓ Will create new database on first insert")
        
        self.index: Optional[VectorStoreIndex] = None
        self._load_index()
    
    def _load_index(self):
        """Load existing index if available"""
        if self.table is not None:
            vector_store = LanceDBVectorStore(
                uri=str(self.db_path),
                table_name="failures"
            )
            self.index = VectorStoreIndex.from_vector_store(vector_store)
    
    def add_failure(self, failure: HistoricalFailure) -> str:
        """Add a failure to memory"""
        # Convert failure to embedding text
        text = failure.to_embedding_text()
        
        # Create document with metadata
        doc = Document(
            text=text,
            metadata={
                "test_name": failure.test_name,
                "error_type": failure.error_type or "unknown",
                "timestamp": failure.timestamp.isoformat(),
                "flaky_score": failure.flaky_score,
                "has_resolution": failure.resolution is not None,
                "raw_data": json.dumps(failure.to_dict())
            }
        )
        
        # Initialize index if needed
        if self.index is None:
            vector_store = LanceDBVectorStore(
                uri=str(self.db_path),
                table_name="failures"
            )
            self.index = VectorStoreIndex.from_documents(
                [doc], 
                vector_store=vector_store
            )
            self.table = self.db.open_table("failures")
        else:
            self.index.insert(doc)
        
        return f"Added: {failure.test_name}"
    
    def add_failures_bulk(self, failures: List[HistoricalFailure]):
        """Add multiple failures efficiently"""
        documents = []
        for failure in failures:
            text = failure.to_embedding_text()
            doc = Document(
                text=text,
                metadata={
                    "test_name": failure.test_name,
                    "error_type": failure.error_type or "unknown",
                    "timestamp": failure.timestamp.isoformat(),
                    "flaky_score": failure.flaky_score,
                    "has_resolution": failure.resolution is not None,
                    "raw_data": json.dumps(failure.to_dict())
                }
            )
            documents.append(doc)
        
        vector_store = LanceDBVectorStore(
            uri=str(self.db_path),
            table_name="failures"
        )
        self.index = VectorStoreIndex.from_documents(
            documents,
            vector_store=vector_store
        )
        
        # Now try to open the table after it's created
        try:
            self.table = self.db.open_table("failures")
        except Exception as e:
            print(f"⚠️  Note: {e}")
            # Table will be accessible through the index
        
        print(f"✓ Added {len(failures)} failures to memory")
    
    def search_similar(
        self, 
        query_failure: HistoricalFailure,
        top_k: int = 5
    ) -> List[HistoricalFailure]:
        """Find similar past failures"""
        if self.index is None:
            return []
        
        query_text = query_failure.to_embedding_text()
        
        # Use retriever instead of query_engine (no LLM needed)
        retriever = self.index.as_retriever(similarity_top_k=top_k)
        nodes = retriever.retrieve(query_text)
        
        # Extract failures from results
        similar_failures = []
        for node in nodes:
            try:
                raw_data = json.loads(node.metadata['raw_data'])
                failure = HistoricalFailure.from_dict(raw_data)
                similar_failures.append(failure)
            except Exception as e:
                print(f"⚠️  Error parsing result: {e}")
                continue
        
        return similar_failures
    
    def get_flaky_tests(self, threshold: float = 0.6) -> List[HistoricalFailure]:
        """Get tests with high flaky scores"""
        if self.table is None:
            return []
        
        results = self.table.search().where(
            f"flaky_score >= {threshold}"
        ).limit(10).to_list()
        
        failures = []
        for result in results:
            try:
                raw_data = json.loads(result['metadata']['raw_data'])
                failures.append(HistoricalFailure.from_dict(raw_data))
            except:
                continue
        
        return failures
    
    def get_by_test_name(self, test_name: str) -> List[HistoricalFailure]:
        """Get all failures for a specific test"""
        if self.table is None:
            return []
        
        results = self.table.search().where(
            f"test_name = '{test_name}'"
        ).limit(20).to_list()
        
        failures = []
        for result in results:
            try:
                raw_data = json.loads(result['metadata']['raw_data'])
                failures.append(HistoricalFailure.from_dict(raw_data))
            except:
                continue
        
        return failures
    
    def get_stats(self) -> dict:
        """Get memory statistics"""
        if self.table is None:
            return {"total_failures": 0}
        
        total = self.table.count_rows()
        
        return {
            "total_failures": total,
            "db_path": str(self.db_path)
        }


def load_sample_data_to_memory():
    """Load sample historical failures into memory"""
    from agent.models import SAMPLE_HISTORICAL_FAILURES
    
    # Convert sample data to HistoricalFailure objects
    failures = []
    for data in SAMPLE_HISTORICAL_FAILURES:
        # Make a copy to avoid modifying the original
        data_copy = data.copy()
        
        # Convert resolution if it exists and is a dict
        if 'resolution' in data_copy and data_copy['resolution']:
            if isinstance(data_copy['resolution'], dict):
                data_copy['resolution'] = Resolution.from_dict(data_copy['resolution'])
        
        failure = HistoricalFailure.from_dict(data_copy)
        failures.append(failure)
    
    # Initialize memory and add failures
    memory = FailureMemory()
    memory.add_failures_bulk(failures)
    
    print(f"\n✅ Loaded {len(failures)} sample failures")
    print(f"📊 Stats: {memory.get_stats()}")
    
    return memory


if __name__ == "__main__":
    # Test the memory system
    print("🧪 Testing RAG Memory System\n")
    
    memory = load_sample_data_to_memory()
    
    # Test similarity search
    from agent.models import HistoricalFailure
    from datetime import datetime
    
    test_failure = HistoricalFailure(
        test_name="test_checkout_flow",
        error_message="TimeoutError: selector '#payment-form' not visible",
        error_type="TimeoutError",
        log_snippet="Element is hidden, waiting timed out after 30s",
        timestamp=datetime.now(),
        duration_seconds=31.0,
        retry_count=0,
        artifacts=[],
        resolution=None,
        flaky_score=0.0
    )
    
    print("\n🔍 Searching for similar failures...")
    similar = memory.search_similar(test_failure, top_k=3)
    
    print(f"\nFound {len(similar)} similar failures:")
    for i, failure in enumerate(similar, 1):
        print(f"\n{i}. {failure.test_name}")
        print(f"   Error: {failure.error_message}")
        if failure.resolution:
            print(f"   Fix: {failure.resolution.fix_applied}")