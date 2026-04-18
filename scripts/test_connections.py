from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance


def test_neo4j():
    print("Testing Neo4j connection...")
    uri = "bolt://localhost:7687"
    try:
        driver = GraphDatabase.driver(uri, auth=("neo4j", "password123"))
        driver.verify_connectivity()
        print("✅ Neo4j: Connection Successful!")
        driver.close()
    except Exception as e:
        print(f"❌ Neo4j: Connection Failed! Error: {e}")


def test_qdrant():
    print("\nTesting Qdrant connection...")
    try:
        client = QdrantClient("localhost", port=6333)

        # Create a test collection
        collection_name = "test_collection"
        if not client.collection_exists(collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=4, distance=Distance.COSINE),
            )

        # Insert a dummy vector
        operation_info = client.upsert(
            collection_name=collection_name,
            wait=True,
            points=[
                PointStruct(
                    id=1, vector=[0.05, 0.61, 0.76, 0.74], payload={"test": "data"}
                )
            ],
        )
        print("✅ Qdrant: Connection & Data Insertion Successful!")
    except Exception as e:
        print(f"❌ Qdrant: Connection Failed! Error: {e}")


if __name__ == "__main__":
    test_neo4j()
    test_qdrant()
