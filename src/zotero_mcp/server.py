from mcp.server.fastmcp import FastMCP
from .database import ZoteroDB
# from .semantic_scholar import SemanticScholarClient, SemanticScholarError, format_paper_md  # Disabled: external search
import os

# Initialize the MCP server
mcp = FastMCP("Zotero")

# Initialize DB — path from environment variable or default
DB_PATH = os.environ.get("ZOTERO_DB_PATH", os.path.expanduser("~/Zotero/zotero.sqlite"))
db = ZoteroDB(DB_PATH)
# s2 = SemanticScholarClient()  # Disabled: external search

@mcp.resource("zotero://library/info")
def get_library_info() -> str:
    """Get basic information about the Zotero library."""
    try:
        stats = db.get_library_stats()
        md = "# Zotero Library Statistics\n\n"
        md += f"- **Total Items:** {stats['total_items']}\n"
        md += f"- **Collections:** {stats['collection_count']}\n"
        md += f"- **Tags:** {stats['tag_count']}\n"
        md += f"- **Creators:** {stats['creator_count']}\n"
        md += "\n## Items by Type\n\n"
        for type_name, count in stats['type_counts'].items():
            md += f"- {type_name}: {count}\n"
        return md
    except Exception as e:
        return f"Error accessing library: {str(e)}"

@mcp.resource("zotero://library/items")
def list_recent_items() -> str:
    """List the 50 most recent items in the library."""
    try:
        items = db.get_recent_items(limit=50)
        md = "# Recent Items\n\n"
        for item in items:
            title = item['title'] or 'Untitled'
            date_added = item['dateAdded'][:10] if item.get('dateAdded') else ''
            md += f"- **[{item['key']}]** {title} ({item['typeName']}) _{date_added}_\n"
        return md
    except Exception as e:
        return f"Error listing items: {str(e)}"

@mcp.resource("zotero://items/{item_key}")
def get_item_resource(item_key: str) -> str:
    """Get full details of a specific item by its key."""
    try:
        item = db.get_item_details(item_key=item_key)
        if not item:
            return f"Item {item_key} not found."

        md = f"# {item['fields'].get('title', 'Untitled')}\n\n"
        md += f"**Key:** {item['key']}\n"
        md += f"**Type:** {item['typeName']}\n"
        md += f"**Date:** {item['fields'].get('date', 'N/A')}\n\n"

        md += "## Creators\n"
        for creator in item.get('creators', []):
            md += f"- {creator}\n"

        md += "\n## Fields\n"
        for k, v in item.get('fields', {}).items():
            if k not in ['title', 'date']:
                md += f"- **{k}:** {v}\n"

        return md
    except Exception as e:
        return f"Error retrieving item {item_key}: {str(e)}"

@mcp.tool()
def search_items(query: str) -> str:
    """
    Search for items in the Zotero library by title or creator.
    Returns a list of items with their Keys and basic info.
    """
    try:
        items = db.search_items(query, limit=20)
        if not items:
            return "No items found."

        md = f"Found {len(items)} items for '{query}':\n\n"
        for item in items:
            md += f"- Key: `{item['key']}` | Title: {item['title']} | Type: {item['typeName']}\n"
        return md
    except Exception as e:
        return f"Error searching: {str(e)}"

@mcp.tool()
def get_item_details(item_key: str) -> str:
    """
    Get full details for a specific item by its Key (e.g. 'ABCD1234').
    Useful for retrieving abstract, publication data, etc.
    """
    return get_item_resource(item_key)

@mcp.tool()
def find_related_papers(item_key: str, limit: int = 10) -> str:
    """
    Find papers in your Zotero library most related to the given paper.
    Uses shared collections, tags, authors, publication venue, and fulltext
    word overlap to compute a composite similarity score.

    Args:
        item_key: The Zotero item key (e.g. 'ABCD1234').
        limit: Maximum number of related papers to return (default: 10).
    """
    try:
        result = db.find_related_papers(item_key=item_key, limit=limit)
        if result is None:
            return f"Item {item_key} not found."

        source = result['source']
        related = result['related']
        source_title = source.get('title') or 'Untitled'

        md = "# Related Papers\n\n"
        md += f"**Source:** {source_title}\n"
        md += f"**Key:** {source.get('key', '')} | **Type:** {source.get('typeName', '')}\n\n"

        if not related:
            md += "_No related papers found. This item may lack collections, tags, or indexed fulltext._\n"
            return md

        md += f"Found {len(related)} related papers:\n\n"

        for i, paper in enumerate(related, 1):
            title = paper['title'] or 'Untitled'
            md += f"---\n\n### {i}. {title} (Score: {paper['score']})\n"
            md += f"**Key:** `{paper['key']}` | **Type:** {paper['typeName']}\n"

            expl = paper.get('explanation', {})
            reasons = []
            if expl.get('shared_collections'):
                reasons.append(f"- Same collection: {', '.join(expl['shared_collections'])}")
            if expl.get('shared_tags'):
                reasons.append(f"- Shared tags: {', '.join(expl['shared_tags'])}")
            if expl.get('shared_creators'):
                reasons.append(f"- Same authors: {', '.join(expl['shared_creators'])}")
            if expl.get('shared_venue'):
                reasons.append(f"- Same venue: {expl['shared_venue']}")
            text_score = paper.get('signal_scores', {}).get('text', 0)
            if text_score > 0:
                pct = int(text_score * 100)
                reasons.append(f"- Similar fulltext content ({pct}% word overlap)")

            if reasons:
                md += "**Why related:**\n"
                md += "\n".join(reasons) + "\n"
            md += "\n"

        md += "---\n\n"
        md += "_Similarity weights: collections (30%), tags (25%), fulltext (25%), creators (10%), venue (10%)_\n"
        return md
    except Exception as e:
        return f"Error finding related papers: {str(e)}"

@mcp.tool()
def list_collections(parent_collection_key: str = None) -> str:
    """
    List Zotero collections (folders). Shows the collection hierarchy.

    - Call with no arguments to see all top-level collections.
    - Call with a parent_collection_key to see its sub-collections.

    Each collection shows its key, name, number of sub-collections, and number of items.
    Use the collection key with get_collection_items() to list items in a collection.
    """
    try:
        # Resolve key to ID if provided
        parent_id = None
        parent_name = None
        if parent_collection_key:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT collectionID, collectionName FROM collections WHERE key = ?",
                    (parent_collection_key,))
                row = cursor.fetchone()
                if not row:
                    return f"Collection with key '{parent_collection_key}' not found."
                parent_id = row['collectionID']
                parent_name = row['collectionName']

        collections = db.list_collections(parent_collection_id=parent_id)
        if not collections:
            if parent_collection_key:
                return f"No sub-collections found in '{parent_name}'."
            return "No collections found."

        if parent_collection_key:
            md = f"# Sub-collections of: {parent_name}\n\n"
        else:
            md = "# Zotero Collections (Top-Level)\n\n"

        for c in collections:
            sub = f" ({c['child_count']} sub-collections)" if c['child_count'] > 0 else ""
            md += f"- **[{c['key']}]** {c['collectionName']} — {c['item_count']} items{sub}\n"

        return md
    except Exception as e:
        return f"Error listing collections: {str(e)}"

@mcp.tool()
def get_collection_items(collection_key: str) -> str:
    """
    List all items in a specific Zotero collection (folder) by its key.
    Use list_collections() first to find collection keys.

    Args:
        collection_key: The collection key (e.g. 'ABCD1234').
    """
    try:
        items = db.get_collection_items(collection_key)

        # Get collection name
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT collectionName FROM collections WHERE key = ?",
                (collection_key,))
            row = cursor.fetchone()
            name = row['collectionName'] if row else collection_key

        if not items:
            return f"No items found in collection '{name}'."

        md = f"# Items in: {name}\n\n"
        md += f"Total: {len(items)} items\n\n"
        for item in items:
            title = item['title'] or 'Untitled'
            date = item['dateAdded'][:10] if item.get('dateAdded') else ''
            md += f"- Key: `{item['key']}` | {title} ({item['typeName']}) _{date}_\n"
        return md
    except Exception as e:
        return f"Error listing collection items: {str(e)}"

@mcp.tool()
def get_pdf_text(item_key: str, max_pages: int = 20) -> str:
    """
    Extract text content from the PDF attachment of a Zotero item.

    Args:
        item_key: The Zotero item key (e.g. 'ABCD1234').
        max_pages: Maximum number of pages to extract (default: 20).
    """
    try:
        result = db.get_pdf_text(item_key=item_key, max_pages=max_pages)
        if result is None:
            return f"No PDF found for item {item_key}."

        md = f"# PDF Text: {item_key}\n\n"
        md += f"**Pages:** {result['pages_read']}/{result['total_pages']}"
        if result['pages_read'] < result['total_pages']:
            md += f" (use max_pages to read more)"
        md += "\n\n"

        for page in result['pages']:
            md += f"---\n### Page {page['page']}\n\n{page['text']}\n\n"

        return md
    except Exception as e:
        return f"Error extracting PDF text: {str(e)}"


# ── Helper: extract DOI from Zotero item ─────────────────────

def _get_doi_from_zotero(item_key: str) -> str:
    """Extract DOI from a Zotero item. Returns 'DOI:xxx' or None."""
    item = db.get_item_details(item_key=item_key)
    if not item:
        return None
    doi = item.get('fields', {}).get('DOI', '')
    if not doi:
        extra = item.get('fields', {}).get('extra', '')
        if 'DOI:' in extra:
            doi = extra.split('DOI:')[1].strip().split()[0]
    return f"DOI:{doi}" if doi else None


# ── Semantic Scholar Tools (DISABLED) ────────────────────────
# These tools require SEMANTIC_SCHOLAR_API_KEY and external API access.
# To re-enable, uncomment the tools below and the imports/init at the top.


def serve():
    """Entry point for running the server."""
    try:
        db.initialize()
        mcp.run()
    finally:
        db.cleanup()

if __name__ == "__main__":
    serve()
