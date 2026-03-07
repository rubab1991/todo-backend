from typing import List, Dict, Any
import numpy as np
from ..config import settings
import cohere


class CohereEmbeddingAgent:
    def __init__(self):
        self.co = cohere.Client(settings.cohere_api_key)
        self.model = "embed-multilingual-v2.0"  # Using a Cohere embedding model

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate semantic embeddings for the given texts
        """
        try:
            response = self.co.embed(
                texts=texts,
                model=self.model
            )

            return [embedding for embedding in response.embeddings]
        except Exception as e:
            raise e

    async def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts using embeddings
        """
        embeddings = await self.generate_embeddings([text1, text2])

        # Calculate cosine similarity
        emb1 = np.array(embeddings[0])
        emb2 = np.array(embeddings[1])

        # Cosine similarity formula
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return float(similarity)

    async def find_similar_tasks(self, query: str, task_list: List[Dict[str, Any]], threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Find tasks similar to the query using semantic embeddings
        """
        if not task_list:
            return []

        # Extract task titles/descriptions to compare
        task_texts = []
        for task in task_list:
            text = task.get('title', '') + ' ' + (task.get('description', '') or '')
            task_texts.append(text)

        # Add the query to the list
        all_texts = [query] + task_texts

        # Generate embeddings
        embeddings = await self.generate_embeddings(all_texts)

        # Compare query embedding with task embeddings
        query_embedding = embeddings[0]
        similarities = []

        for i, task_embedding in enumerate(embeddings[1:]):
            # Calculate cosine similarity
            emb1 = np.array(query_embedding)
            emb2 = np.array(task_embedding)

            dot_product = np.dot(emb1, emb2)
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)

            if norm1 == 0 or norm2 == 0:
                similarity = 0.0
            else:
                similarity = dot_product / (norm1 * norm2)

            if similarity >= threshold:
                similarities.append({
                    'task': task_list[i],
                    'similarity_score': float(similarity)
                })

        # Sort by similarity score
        similarities.sort(key=lambda x: x['similarity_score'], reverse=True)

        return [item['task'] for item in similarities]


# Global instance
embedding_agent = CohereEmbeddingAgent()


async def generate_embeddings_for_text(text: str) -> List[float]:
    """
    Generate embeddings for a single text
    """
    return await embedding_agent.generate_embeddings([text])


async def find_similar_tasks(query: str, task_list: List[Dict[str, Any]], threshold: float = 0.7) -> List[Dict[str, Any]]:
    """
    Find tasks similar to the query
    """
    return await embedding_agent.find_similar_tasks(query, task_list, threshold)