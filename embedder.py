"""
Embedding generator for AGN Health Q&A data.
Creates vector embeddings and sets up MongoDB Atlas vector search index.
"""
import logging
from typing import List, Dict
import torch
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient
from pymongo.operations import UpdateOne
import numpy as np

import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/embedder.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class QAEmbedder:
    """Generates embeddings for Q&A documents and creates vector search index."""

    def __init__(self):
        """Initialize the embedder with MongoDB connection and embedding model."""
        self.mongo_client = None
        self.db = None
        self.collection = None
        self.embedding_model = None
        self._setup_mongodb()
        self._setup_embedding_model()

    def _setup_mongodb(self):
        """Set up MongoDB connection."""
        try:
            self.mongo_client = MongoClient(config.MONGODB_URL)
            self.db = self.mongo_client[config.MONGODB_DATABASE]
            self.collection = self.db[config.MONGODB_COLLECTION]
            logger.info("MongoDB connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def _setup_embedding_model(self):
        """Load the embedding model."""
        try:
            logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
            self.embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)

            # Verify embedding dimension
            test_embedding = self.embedding_model.encode("test", convert_to_numpy=True)
            actual_dim = len(test_embedding)

            if actual_dim != config.EMBEDDING_DIMENSION:
                logger.warning(
                    f"Model dimension ({actual_dim}) doesn't match configured dimension ({config.EMBEDDING_DIMENSION}). "
                    f"Using actual dimension: {actual_dim}"
                )
                # Update the dimension to match actual
                config.EMBEDDING_DIMENSION = actual_dim

            logger.info(f"Embedding model loaded successfully with dimension: {actual_dim}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def create_combined_text(self, document: Dict) -> str:
        """
        Combine topic and question into a single text for embedding.

        Args:
            document: MongoDB document containing topic and question

        Returns:
            Combined text string
        """
        topic = document.get('topic', '').strip()
        question = document.get('question', '').strip()

        parts = []
        if topic:
            parts.append(f"หัวข้อ: {topic}")
        if question:
            parts.append(f"คำถาม: {question}")

        return "\n".join(parts) if parts else ""

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for the given text.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector
        """
        if not text:
            # Return zero vector for empty text
            return [0.0] * config.EMBEDDING_DIMENSION

        try:
            embedding = self.embedding_model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return [0.0] * config.EMBEDDING_DIMENSION

    def embed_documents(self, batch_size: int = 32):
        """
        Generate embeddings for all documents in the collection.

        Args:
            batch_size: Number of documents to process in each batch
        """
        try:
            # Count total documents
            total_docs = self.collection.count_documents({})
            logger.info(f"Found {total_docs} documents to process")

            if total_docs == 0:
                logger.warning("No documents found in collection. Run scraper first.")
                return

            # Count documents without embeddings
            docs_without_embeddings = self.collection.count_documents({
                "contentVector": {"$exists": False}
            })
            logger.info(f"Documents without embeddings: {docs_without_embeddings}")

            # Process documents in batches
            processed = 0
            skipped = 0
            updated = 0

            # Get all documents without embeddings
            cursor = self.collection.find({"contentVector": {"$exists": False}})

            batch_docs = []
            batch_texts = []
            batch_ids = []

            for doc in cursor:
                combined_text = self.create_combined_text(doc)

                if not combined_text:
                    logger.warning(f"Document {doc['thread_id']}: Empty text, skipping")
                    skipped += 1
                    continue

                batch_docs.append(doc)
                batch_texts.append(combined_text)
                batch_ids.append(doc['_id'])

                # Process batch when it reaches batch_size
                if len(batch_texts) >= batch_size:
                    updated += self._process_batch(batch_ids, batch_texts)
                    processed += len(batch_texts)
                    logger.info(f"Progress: {processed}/{docs_without_embeddings} documents processed")

                    # Clear batch
                    batch_docs = []
                    batch_texts = []
                    batch_ids = []

            # Process remaining documents
            if batch_texts:
                updated += self._process_batch(batch_ids, batch_texts)
                processed += len(batch_texts)

            logger.info(f"Embedding completed! Processed: {processed}, Updated: {updated}, Skipped: {skipped}")

        except Exception as e:
            logger.error(f"Error during embedding process: {e}")
            raise

    def _process_batch(self, doc_ids: List, texts: List[str]) -> int:
        """
        Process a batch of documents and update with embeddings.

        Args:
            doc_ids: List of document IDs
            texts: List of texts to embed

        Returns:
            Number of documents updated
        """
        try:
            # Generate embeddings for the batch
            embeddings = self.embedding_model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                batch_size=len(texts)
            )

            # Prepare bulk update operations
            operations = []
            for doc_id, embedding in zip(doc_ids, embeddings):
                operations.append(
                    UpdateOne(
                        {"_id": doc_id},
                        {"$set": {"contentVector": embedding.tolist()}}
                    )
                )

            # Execute bulk update
            result = self.collection.bulk_write(operations)
            return result.modified_count

        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            return 0

    def create_vector_index(self):
        """
        Create MongoDB Atlas vector search index.

        Note: This requires MongoDB Atlas M10+ cluster with Vector Search capability.
        The index creation is done via the MongoDB Atlas API or UI.
        """
        index_name = config.VECTOR_INDEX_NAME

        try:
            # Check if index already exists
            existing_indexes = list(self.collection.list_search_indexes())
            index_exists = any(idx.get('name') == index_name for idx in existing_indexes)

            if index_exists:
                logger.info(f"Vector search index '{index_name}' already exists")
                return

            # Create the vector search index
            index_definition = {
                "name": index_name,
                "definition": {
                    "mappings": {
                        "dynamic": True,
                        "fields": {
                            "contentVector": {
                                "type": "knnVector",
                                "dimensions": config.EMBEDDING_DIMENSION,
                                "similarity": "cosine"
                            }
                        }
                    }
                }
            }

            logger.info(f"Creating vector search index '{index_name}'...")
            self.collection.create_search_index(index_definition)
            logger.info(f"Vector search index '{index_name}' created successfully!")
            logger.info("Note: Index creation may take a few minutes to complete in Atlas.")

        except AttributeError:
            # Fallback for older PyMongo versions or non-Atlas deployments
            logger.warning("Vector search index creation not supported. Please create manually in MongoDB Atlas:")
            logger.warning(f"""
Index Configuration:
- Index Name: {index_name}
- Collection: {config.MONGODB_DATABASE}.{config.MONGODB_COLLECTION}
- Field: contentVector
- Type: knnVector
- Dimensions: {config.EMBEDDING_DIMENSION}
- Similarity: cosine

JSON Definition:
{{
  "fields": [
    {{
      "type": "vector",
      "path": "contentVector",
      "numDimensions": {config.EMBEDDING_DIMENSION},
      "similarity": "cosine"
    }}
  ]
}}
            """)
        except Exception as e:
            logger.error(f"Error creating vector search index: {e}")
            logger.warning("You may need to create the index manually in MongoDB Atlas UI")
            logger.warning(f"Index name: {index_name}, Field: contentVector, Dimensions: {config.EMBEDDING_DIMENSION}, Similarity: cosine")

    def verify_embeddings(self):
        """Verify that embeddings were created successfully."""
        try:
            total_docs = self.collection.count_documents({})
            docs_with_embeddings = self.collection.count_documents({
                "contentVector": {"$exists": True}
            })

            logger.info(f"Verification: {docs_with_embeddings}/{total_docs} documents have embeddings")

            if docs_with_embeddings > 0:
                # Check a sample document
                sample = self.collection.find_one({"contentVector": {"$exists": True}})
                if sample:
                    vector_length = len(sample['contentVector'])
                    logger.info(f"Sample embedding dimension: {vector_length}")

            return docs_with_embeddings == total_docs

        except Exception as e:
            logger.error(f"Error during verification: {e}")
            return False

    def close(self):
        """Clean up resources."""
        if self.mongo_client:
            self.mongo_client.close()
            logger.info("MongoDB connection closed")


def main():
    """Main function to run the embedder."""
    embedder = None
    try:
        embedder = QAEmbedder()

        # Generate embeddings
        logger.info("Starting embedding generation...")
        embedder.embed_documents(batch_size=32)

        # Verify embeddings
        logger.info("Verifying embeddings...")
        success = embedder.verify_embeddings()

        if success:
            logger.info("All documents have embeddings!")
        else:
            logger.warning("Some documents are missing embeddings")

        # Create vector search index
        logger.info("Creating vector search index...")
        embedder.create_vector_index()

        logger.info("Embedder process completed successfully!")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        if embedder:
            embedder.close()


if __name__ == "__main__":
    main()
