"""
Script kiểm tra kết nối tích hợp — Neo4j và Qdrant.

Chạy: python src/utils/connection_check.py
Yêu cầu: File .env đã được điền đủ giá trị tại thư mục gốc project.

Script thực hiện smoke test cho cả hai database:
- Neo4j: tạo, đọc, xóa TestNode, kiểm tra cleanup
- Qdrant: tạo, upsert, search, xóa collection smoke_test, kiểm tra cleanup

Exit code 0 nếu cả hai PASS, 1 nếu bất kỳ test nào FAIL.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Tìm .env từ root project
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)


def test_neo4j() -> bool:
    """
    Kiểm tra kết nối Neo4j với các bước:
    1. verify_connectivity
    2. Tạo TestNode
    3. Đọc lại TestNode
    4. Xóa TestNode
    5. Kiểm tra cleanup (count = 0)

    Trả về True nếu tất cả bước thành công, False nếu thất bại.
    """
    print("Checking Neo4j connection...")

    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")

    if not all([uri, user, password]):
        print("  ❌ Neo4j: FAIL — Thiếu biến môi trường (NEO4J_URI, NEO4J_USER, hoặc NEO4J_PASSWORD) trong .env")
        return False

    driver = None
    try:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(uri, auth=(user, password))

        # Bước 1: Kiểm tra kết nối cơ bản
        driver.verify_connectivity()
        print("  → verify_connectivity: OK")

        # Bước 2: Tạo TestNode
        with driver.session() as session:
            session.run('CREATE (t:TestNode {name: "smoke_test"}) RETURN t')
        print("  → Create TestNode: OK")

        # Bước 3: Đọc lại TestNode
        with driver.session() as session:
            result = session.run('MATCH (t:TestNode {name: "smoke_test"}) RETURN t')
            record = result.single()
            if record is None:
                print("  ❌ Neo4j: FAIL — Không đọc được TestNode sau khi tạo")
                return False
        print("  → Read TestNode: OK")

        # Bước 4: Xóa TestNode
        try:
            with driver.session() as session:
                session.run('MATCH (t:TestNode {name: "smoke_test"}) DELETE t')
            print("  → Delete TestNode: OK")
        except Exception as e:
            print(f"  ❌ Neo4j: FAIL — Lỗi khi xóa TestNode: {e}")
            return False

        # Bước 5: Kiểm tra cleanup
        with driver.session() as session:
            result = session.run(
                'MATCH (t:TestNode {name: "smoke_test"}) RETURN count(t) AS count'
            )
            count = result.single()["count"]
            if count != 0:
                print(f"  ❌ Neo4j: FAIL — Cleanup không thành công, còn {count} TestNode")
                return False
        print("  → Verify cleanup: OK")

        print("✅ Neo4j: PASS")
        return True

    except Exception as e:
        print(f"  ❌ Neo4j: FAIL — {e}")
        return False
    finally:
        # Luôn cố gắng cleanup dù đã thất bại ở bước nào
        if driver is not None:
            try:
                with driver.session() as session:
                    session.run('MATCH (t:TestNode {name: "smoke_test"}) DELETE t')
            except Exception:
                pass  # Bỏ qua lỗi cleanup — có thể node chưa được tạo
            try:
                driver.close()
            except Exception:
                pass


def test_qdrant() -> bool:
    """
    Kiểm tra kết nối Qdrant với các bước:
    1. Tạo collection smoke_test
    2. Upsert 1 vector
    3. Search vector
    4. Xóa collection
    5. Kiểm tra cleanup (collection không còn tồn tại)

    Trả về True nếu tất cả bước thành công, False nếu thất bại.
    """
    print("Checking Qdrant connection...")

    host = os.getenv("QDRANT_HOST")
    port = os.getenv("QDRANT_PORT")

    if not all([host, port]):
        print("  ❌ Qdrant: FAIL — Thiếu biến môi trường (QDRANT_HOST hoặc QDRANT_PORT) trong .env")
        return False

    collection_name = "smoke_test"
    client = None
    collection_created = False

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, PointStruct, VectorParams

        client = QdrantClient(host=host, port=int(port))

        # Bước 1: Tạo collection smoke_test
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=4, distance=Distance.COSINE),
        )
        collection_created = True
        print(f"  → Create collection {collection_name}: OK")

        # Bước 2: Upsert 1 vector
        client.upsert(
            collection_name=collection_name,
            wait=True,
            points=[
                PointStruct(
                    id=1,
                    vector=[0.1, 0.2, 0.3, 0.4],
                    payload={"test": True},
                )
            ],
        )
        print("  → Upsert vector: OK")

        # Bước 3: Search vector
        search_results = client.search(
            collection_name=collection_name,
            query_vector=[0.1, 0.2, 0.3, 0.4],
            limit=1,
        )
        if len(search_results) != 1:
            print(f"  ❌ Qdrant: FAIL — Search trả về {len(search_results)} kết quả, mong đợi 1")
            return False
        print("  → Search vector: OK")

        # Bước 4: Xóa collection
        try:
            client.delete_collection(collection_name=collection_name)
            collection_created = False
            print(f"  → Delete collection: OK")
        except Exception as e:
            print(f"  ❌ Qdrant: FAIL — Lỗi khi xóa collection: {e}")
            return False

        # Bước 5: Kiểm tra cleanup
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]
        if collection_name in collection_names:
            print(f"  ❌ Qdrant: FAIL — Collection {collection_name} vẫn còn tồn tại sau khi xóa")
            return False
        print("  → Verify cleanup: OK")

        print("✅ Qdrant: PASS")
        return True

    except Exception as e:
        print(f"  ❌ Qdrant: FAIL — {e}")
        return False
    finally:
        # Luôn cố gắng cleanup collection nếu đã tạo
        if client is not None and collection_created:
            try:
                client.delete_collection(collection_name=collection_name)
            except Exception:
                pass  # Bỏ qua lỗi cleanup


if __name__ == "__main__":
    print("=== Integration Verification ===")

    neo4j_pass = test_neo4j()
    print()
    qdrant_pass = test_qdrant()

    passed = sum([neo4j_pass, qdrant_pass])
    print(f"\n=== Result: {passed}/2 PASSED ===")

    sys.exit(0 if passed == 2 else 1)
