import os
from app.github.client import GitHubClient
from app.rag.ingestion import RepositoryIngestor

def run():
    client = GitHubClient()
    ingestor = RepositoryIngestor(client)
    
    owner = "octocat"
    repo = "Hello-World"
    
    print(f"Ingesting {owner}/{repo}...")
    docs = ingestor.ingest_repository(owner, repo)
    
    print(f"Total documents ingested: {len(docs)}")
    for doc in docs:
        print(f"Path: {doc['file_path']}")
        print(f"Language: {doc['language']}")
        print(f"Content Length: {len(doc['content'])}")
        print(f"Content Preview: {doc['content'][:100]}...\n")

if __name__ == "__main__":
    run()
