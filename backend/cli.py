import argparse
import logging
import sys
from pathlib import Path
from backend.engine import AnyRAG

def main():
    logging.basicConfig(level=logging.INFO, format="[AnyRAG] %(message)s")
    parser = argparse.ArgumentParser(
        description="AnyRAG - Universal Document Ingestion, Retrieval & Comparison Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py ingest doc/anyrag_session_log.md
  python main.py list
  python main.py ask anyrag_session_log.md "What models were discussed?"
  python main.py compare doc1.pdf doc2.pdf
  python main.py diff doc1.pdf doc2.pdf
  python main.py purge anyrag_session_log.md
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest and index a document")
    ingest_parser.add_argument("file_path", help="Path to file (PDF, DOCX, PPTX, MD, TXT, etc.)")

    # List command
    subparsers.add_parser("list", help="List all currently indexed documents")

    # Ask command
    ask_parser = subparsers.add_parser("ask", help="Ask a question to a document's grounded persona ('Doc Jarvis')")
    ask_parser.add_argument("doc", help="Document name or doc_id")
    ask_parser.add_argument("query", help="Question to ask")
    ask_parser.add_argument("--top_k", type=int, default=4, help="Number of chunks to retrieve")

    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare two documents using semantic RAG")
    compare_parser.add_argument("doc1", help="First document name or doc_id")
    compare_parser.add_argument("doc2", help="Second document name or doc_id")
    compare_parser.add_argument("--query", default=None, help="Specific focus for comparison")

    # Diff command
    diff_parser = subparsers.add_parser("diff", help="Perform chunk-level semantic diff between two documents")
    diff_parser.add_argument("doc1", help="First document name or doc_id")
    diff_parser.add_argument("doc2", help="Second document name or doc_id")

    # Search command
    search_parser = subparsers.add_parser("search", help="Global semantic search across all indexed documents")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--top_k", type=int, default=5, help="Number of results")

    # Purge command
    purge_parser = subparsers.add_parser("purge", help="Cascade delete a document and all its vector embeddings")
    purge_parser.add_argument("doc", help="Document name, file path, or doc_id")

    # Clear command
    subparsers.add_parser("clear", help="Clear all indexed documents and vectors")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    rag = AnyRAG()

    if args.command == "ingest":
        res = rag.ingest(args.file_path)
        print("\n--- Ingest Summary ---")
        print(f"File: {res.get('file_name')}")
        print(f"Document ID: {res.get('doc_id')}")
        print(f"Chunks Indexed: {res.get('chunk_count')}")

    elif args.command == "list":
        docs = rag.list_documents()
        print("\n--- Indexed Documents ---")
        if not docs:
            print("No documents currently indexed. Run 'ingest' to add files.")
        else:
            for d in docs:
                size_kb = d['file_size'] / 1024
                print(f"- [{d['doc_id']}] {d['file_name']} ({d['file_type']}, {d['chunk_count']} chunks, {size_kb:.1f} KB)")
                print(f"  Path: {d['file_path']}")
                print(f"  Indexed: {d['indexed_at']}\n")

    elif args.command == "ask":
        result = rag.ask(args.doc, args.query, top_k=args.top_k)
        print(f"\n[{result['persona_name']} for '{result['document']}']:")
        print("=" * 60)
        print(result["answer"])
        print("=" * 60)
        print(f"(Retrieved {len(result['retrieved_chunks'])} grounded context chunks)")

    elif args.command == "compare":
        res = rag.compare(args.doc1, args.doc2, query=args.query)
        print(f"\n--- Cross-Document Comparison: {res['doc1_name']} vs {res['doc2_name']} ---")
        print("=" * 60)
        print(res["comparison"])
        print("=" * 60)

    elif args.command == "diff":
        res = rag.semantic_diff(args.doc1, args.doc2)
        if "error" in res:
            print(f"Diff Error: {res['error']}")
            return

        print(f"\n--- Semantic Diff: {res['doc1_name']} vs {res['doc2_name']} ---")
        print(f"Overall Semantic Similarity: {res['overall_semantic_similarity']:.2f}")
        print(f"Common/Overlapping Topics: {res['common_topics_count']}")
        print(f"Unique Topics in {res['doc1_name']}: {res['unique_doc1_count']}")
        print(f"Unique Topics in {res['doc2_name']}: {res['unique_doc2_count']}")

        if res["common_samples"]:
            print("\n[Sample Overlapping Sections]:")
            for item in res["common_samples"]:
                print(f"  - Sim {item['similarity']}: '{item['doc1_section']}' <=> '{item['doc2_section']}'")

        if res["unique_doc1_samples"]:
            print(f"\n[Unique in {res['doc1_name']}]:")
            for item in res["unique_doc1_samples"]:
                print(f"  - {item['section']}: {item['content'][:120]}...")

        if res["unique_doc2_samples"]:
            print(f"\n[Unique in {res['doc2_name']}]:")
            for item in res["unique_doc2_samples"]:
                print(f"  - {item['section']}: {item['content'][:120]}...")

    elif args.command == "search":
        results = rag.search_all(args.query, top_k=args.top_k)
        print(f"\n--- Semantic Search Results for '{args.query}' ---")
        for i, r in enumerate(results, 1):
            print(f"{i}. [Score {r['score']:.3f}] Doc: {r['doc_id']} | Section: {r.get('section_title') or 'N/A'}")
            print(f"   {r['content'][:180]}...\n")

    elif args.command == "purge":
        count = rag.purge(args.doc)
        if count > 0:
            print(f"Document and {count} associated chunk embeddings purged successfully.")
        else:
            print(f"Document '{args.doc}' not found.")

    elif args.command == "clear":
        rag.clear()
        print("All documents and vectors purged.")

if __name__ == "__main__":
    main()
