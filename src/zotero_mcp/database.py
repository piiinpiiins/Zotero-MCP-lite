import sqlite3
import shutil
import os
import tempfile
import pymupdf
from contextlib import contextmanager
from typing import List, Dict, Any, Optional

class ZoteroDB:
    # Exclude non-bibliographic item types by name (not hardcoded IDs).
    # itemTypeIDs differ between Zotero 5/6 and Zotero 7.
    EXCLUDED_TYPE_NAMES = ('annotation', 'attachment', 'note')

    def __init__(self, db_path: str):
        self.original_db_path = db_path
        self.temp_db_path = os.path.join(tempfile.gettempdir(), "zotero_temp.sqlite")
        self.storage_dir = os.path.join(os.path.dirname(db_path), "storage")
        self._excluded_type_ids: tuple = ()

    def initialize(self):
        """Creates a temporary copy of the database to work with."""
        if not os.path.exists(self.original_db_path):
            raise FileNotFoundError(f"Zotero database not found at {self.original_db_path}")

        try:
            shutil.copy2(self.original_db_path, self.temp_db_path)
            print(f"Created temporary database copy at {self.temp_db_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to copy database: {e}")

        self._resolve_excluded_type_ids()

    def _resolve_excluded_type_ids(self):
        """Resolve excluded type names to IDs from the actual DB (version-safe)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ','.join('?' * len(self.EXCLUDED_TYPE_NAMES))
            cursor.execute(
                f"SELECT itemTypeID FROM itemTypes WHERE typeName IN ({placeholders})",
                self.EXCLUDED_TYPE_NAMES,
            )
            self._excluded_type_ids = tuple(row[0] for row in cursor.fetchall())
            if not self._excluded_type_ids:
                self._excluded_type_ids = (0,)  # fallback to exclude nothing valid

    @property
    def _excluded_ids_placeholder(self) -> str:
        """Return comma-separated placeholders for excluded IDs."""
        return ','.join('?' * len(self._excluded_type_ids))

    @contextmanager
    def get_connection(self):
        """Yields a database connection to the temporary file."""
        if not os.path.exists(self.temp_db_path):
            self.initialize()

        conn = sqlite3.connect(self.temp_db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def cleanup(self):
        """Removes the temporary database file."""
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    # Query methods
    def count_items(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            ph = self._excluded_ids_placeholder
            cursor.execute(
                f"SELECT count(*) FROM items WHERE itemTypeID NOT IN ({ph})",
                self._excluded_type_ids,
            )
            return cursor.fetchone()[0]

    def get_library_stats(self) -> Dict[str, Any]:
        """Get comprehensive library statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Total items (excluding notes and attachments)
            ph = self._excluded_ids_placeholder
            cursor.execute(
                f"SELECT count(*) FROM items WHERE itemTypeID NOT IN ({ph})",
                self._excluded_type_ids,
            )
            total_items = cursor.fetchone()[0]

            # Count by type
            cursor.execute(f"""
                SELECT it.typeName, count(*) as cnt
                FROM items i
                JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
                WHERE i.itemTypeID NOT IN ({ph})
                GROUP BY it.typeName
                ORDER BY cnt DESC
            """, self._excluded_type_ids)
            type_counts = {row['typeName']: row['cnt'] for row in cursor.fetchall()}

            # Collection count
            cursor.execute("SELECT count(*) FROM collections")
            collection_count = cursor.fetchone()[0]

            # Tag count
            cursor.execute("SELECT count(*) FROM tags")
            tag_count = cursor.fetchone()[0]

            # Creator count
            cursor.execute("SELECT count(DISTINCT creatorID) FROM itemCreators")
            creator_count = cursor.fetchone()[0]

            return {
                'total_items': total_items,
                'type_counts': type_counts,
                'collection_count': collection_count,
                'tag_count': tag_count,
                'creator_count': creator_count,
            }

    def get_recent_items(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the most recently added items, ordered by dateAdded DESC."""
        ph = self._excluded_ids_placeholder
        sql = f"""
            SELECT
                i.itemID,
                i.key,
                it.typeName,
                i.dateAdded,
                (
                    SELECT idv.value
                    FROM itemDataValues idv
                    JOIN itemData id ON id.valueID = idv.valueID
                    JOIN fields f ON id.fieldID = f.fieldID
                    WHERE id.itemID = i.itemID AND f.fieldName = 'title'
                ) as title
            FROM items i
            JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
            WHERE i.itemTypeID NOT IN ({ph})
            ORDER BY i.dateAdded DESC
            LIMIT ?
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (*self._excluded_type_ids, limit))
            return [dict(row) for row in cursor.fetchall()]

    def search_items(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for items by title or creator.
        Returns a list of simplified item dicts.
        """
        ph = self._excluded_ids_placeholder
        sql = f"""
            SELECT DISTINCT
                i.itemID,
                i.key,
                it.typeName,
                (
                    SELECT idv.value
                    FROM itemDataValues idv
                    JOIN itemData id ON id.valueID = idv.valueID
                    JOIN fields f ON id.fieldID = f.fieldID
                    WHERE id.itemID = i.itemID AND f.fieldName = 'title'
                ) as title,
                (
                    SELECT idv.value
                    FROM itemDataValues idv
                    JOIN itemData id ON id.valueID = idv.valueID
                    JOIN fields f ON id.fieldID = f.fieldID
                    WHERE id.itemID = i.itemID AND f.fieldName = 'date'
                ) as date
            FROM items i
            JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
            WHERE i.itemTypeID NOT IN ({ph})
            AND (
                title LIKE ?
                OR EXISTS (
                    SELECT 1 FROM itemCreators ic
                    JOIN creators c ON ic.creatorID = c.creatorID
                    WHERE ic.itemID = i.itemID
                    AND (c.lastName LIKE ? OR c.firstName LIKE ?)
                )
            )
            ORDER BY i.dateAdded DESC
            LIMIT ?
        """
        wildcard_query = f"%{query}%"
        params = (*self._excluded_type_ids, wildcard_query, wildcard_query, wildcard_query, limit)

        results = []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            for row in cursor.fetchall():
                results.append(dict(row))
        return results

    def get_item_details(self, item_id: int = None, item_key: str = None) -> Dict[str, Any]:
        """
        Get full details for a specific item by ID or Key.
        """
        if item_id is None and item_key is None:
            raise ValueError("Must provide either item_id or item_key")

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Build query based on available identifier
            if item_id:
                query = "SELECT i.itemID, i.key, it.typeName, i.dateAdded, i.dateModified FROM items i JOIN itemTypes it ON i.itemTypeID = it.itemTypeID WHERE i.itemID = ?"
                param = (item_id,)
            else:
                query = "SELECT i.itemID, i.key, it.typeName, i.dateAdded, i.dateModified FROM items i JOIN itemTypes it ON i.itemTypeID = it.itemTypeID WHERE i.key = ?"
                param = (item_key,)

            cursor.execute(query, param)
            item_row = cursor.fetchone()
            if not item_row:
                return None

            item = dict(item_row)
            # Ensure we have the ID for subsequent queries
            item_id = item['itemID']

            # Get all fields
            cursor.execute("""
                SELECT f.fieldName, idv.value
                FROM itemData id
                JOIN fields f ON id.fieldID = f.fieldID
                JOIN itemDataValues idv ON id.valueID = idv.valueID
                WHERE id.itemID = ?
            """, (item_id,))

            item['fields'] = {row['fieldName']: row['value'] for row in cursor.fetchall()}

            # Get creators
            cursor.execute("""
                SELECT c.firstName, c.lastName, c.fieldMode, ic.orderIndex
                FROM itemCreators ic
                JOIN creators c ON ic.creatorID = c.creatorID
                WHERE ic.itemID = ?
                ORDER BY ic.orderIndex
            """, (item_id,))

            creators = []
            for row in cursor.fetchall():
                if row['fieldMode'] == 1: # Single field mode (e.g. institution)
                    name = row['lastName']
                else:
                    name = f"{row['firstName']} {row['lastName']}".strip()
                creators.append(name)

            item['creators'] = creators

            return item

    # --- Related Papers ---

    SIMILARITY_WEIGHTS = {
        'collections': 0.30,
        'tags': 0.25,
        'text': 0.25,
        'creators': 0.10,
        'venue': 0.10,
    }

    def find_related_papers(self, item_id: int = None, item_key: str = None,
                            limit: int = 10) -> Dict[str, Any]:
        """
        Find papers most related to the given paper using composite similarity.
        Returns source item info and a ranked list of related papers with
        scores and explanations.
        """
        if item_id is None and item_key is None:
            raise ValueError("Must provide either item_id or item_key")

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Resolve item_key -> item_id and get source metadata
            if item_key and not item_id:
                cursor.execute(
                    "SELECT itemID FROM items WHERE key = ?", (item_key,))
                row = cursor.fetchone()
                if not row:
                    return None
                item_id = row['itemID']

            # Get source item metadata
            cursor.execute("""
                SELECT i.itemID, i.key, it.typeName,
                    (SELECT idv.value FROM itemDataValues idv
                     JOIN itemData id ON id.valueID = idv.valueID
                     JOIN fields f ON id.fieldID = f.fieldID
                     WHERE id.itemID = i.itemID AND f.fieldName = 'title'
                    ) as title
                FROM items i
                JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
                WHERE i.itemID = ?
            """, (item_id,))
            source = cursor.fetchone()
            if not source:
                return None
            source_info = dict(source)

            # Compute similarity scores across all dimensions
            raw_scores = self._compute_similarity_scores(cursor, item_id)

            if not raw_scores:
                return {
                    'source': source_info,
                    'related': [],
                }

            # Compute weighted composite and rank
            ranked = []
            for cid, dim_scores in raw_scores.items():
                composite = sum(
                    self.SIMILARITY_WEIGHTS[dim] * dim_scores.get(dim, 0.0)
                    for dim in self.SIMILARITY_WEIGHTS
                )
                ranked.append((cid, composite, dim_scores))
            ranked.sort(key=lambda x: x[1], reverse=True)
            top = ranked[:limit]

            # Get metadata and explanations for top results
            top_ids = [cid for cid, _, _ in top]
            metadata = self._get_items_metadata_batch(cursor, top_ids)
            explanations = self._get_relationship_explanations(
                cursor, item_id, top_ids)

            related = []
            for cid, composite, dim_scores in top:
                meta = metadata.get(cid, {})
                expl = explanations.get(cid, {})
                related.append({
                    'itemID': cid,
                    'key': meta.get('key', ''),
                    'title': meta.get('title', 'Untitled'),
                    'typeName': meta.get('typeName', ''),
                    'score': round(composite, 3),
                    'signal_scores': {k: round(v, 3) for k, v in dim_scores.items()},
                    'explanation': expl,
                })

            return {
                'source': source_info,
                'related': related,
            }

    def _compute_similarity_scores(self, cursor, source_item_id: int) -> Dict[int, Dict[str, float]]:
        """Compute per-dimension similarity scores for all candidate items."""
        scores: Dict[int, Dict[str, float]] = {}

        # 1. Shared Collections (Jaccard)
        cursor.execute("""
            WITH source_coll AS (
                SELECT collectionID FROM collectionItems WHERE itemID = ?
            ),
            source_cnt AS (
                SELECT count(*) as cnt FROM source_coll
            )
            SELECT
                ci2.itemID as candidateID,
                1.0 * count(*) / (
                    (SELECT cnt FROM source_cnt) +
                    (SELECT count(*) FROM collectionItems WHERE itemID = ci2.itemID) -
                    count(*)
                ) as score
            FROM collectionItems ci1
            JOIN collectionItems ci2 ON ci1.collectionID = ci2.collectionID
                AND ci2.itemID != ?
            WHERE ci1.itemID = ?
            GROUP BY ci2.itemID
        """, (source_item_id, source_item_id, source_item_id))
        for row in cursor.fetchall():
            scores.setdefault(row['candidateID'], {})['collections'] = row['score']

        # 2. Shared Tags (Jaccard)
        cursor.execute("""
            WITH source_tags AS (
                SELECT tagID FROM itemTags WHERE itemID = ?
            ),
            source_cnt AS (
                SELECT count(*) as cnt FROM source_tags
            )
            SELECT
                it2.itemID as candidateID,
                1.0 * count(*) / (
                    (SELECT cnt FROM source_cnt) +
                    (SELECT count(*) FROM itemTags WHERE itemID = it2.itemID) -
                    count(*)
                ) as score
            FROM itemTags it1
            JOIN itemTags it2 ON it1.tagID = it2.tagID AND it2.itemID != ?
            WHERE it1.itemID = ?
            GROUP BY it2.itemID
        """, (source_item_id, source_item_id, source_item_id))
        for row in cursor.fetchall():
            scores.setdefault(row['candidateID'], {})['tags'] = row['score']

        # 3. Shared Creators (Jaccard)
        cursor.execute("""
            WITH source_creators AS (
                SELECT creatorID FROM itemCreators WHERE itemID = ?
            ),
            source_cnt AS (
                SELECT count(*) as cnt FROM source_creators
            )
            SELECT
                ic2.itemID as candidateID,
                1.0 * count(*) / (
                    (SELECT cnt FROM source_cnt) +
                    (SELECT count(*) FROM itemCreators WHERE itemID = ic2.itemID) -
                    count(*)
                ) as score
            FROM itemCreators ic1
            JOIN itemCreators ic2 ON ic1.creatorID = ic2.creatorID
                AND ic2.itemID != ?
            WHERE ic1.itemID = ?
            GROUP BY ic2.itemID
        """, (source_item_id, source_item_id, source_item_id))
        for row in cursor.fetchall():
            scores.setdefault(row['candidateID'], {})['creators'] = row['score']

        # 4. Shared Venue (binary match on publicationTitle)
        cursor.execute("""
            SELECT
                id2.itemID as candidateID,
                1.0 as score
            FROM itemData id1
            JOIN itemData id2 ON id1.valueID = id2.valueID AND id2.itemID != ?
            WHERE id1.itemID = ?
              AND id1.fieldID = (SELECT fieldID FROM fields WHERE fieldName = 'publicationTitle')
              AND id2.fieldID = id1.fieldID
        """, (source_item_id, source_item_id))
        for row in cursor.fetchall():
            scores.setdefault(row['candidateID'], {})['venue'] = row['score']

        # 5. Fulltext Word Overlap (IDF-filtered rare words)
        cursor.execute("""
            WITH
            source_attachments AS (
                SELECT itemID FROM itemAttachments WHERE parentItemID = ?
            ),
            total_docs AS (
                SELECT count(DISTINCT itemID) as total FROM fulltextItemWords
            ),
            rare_words AS (
                SELECT wordID
                FROM fulltextItemWords
                GROUP BY wordID
                HAVING count(DISTINCT itemID) < (SELECT total / 2 FROM total_docs)
            ),
            source_rare AS (
                SELECT DISTINCT fiw.wordID
                FROM fulltextItemWords fiw
                JOIN source_attachments sa ON fiw.itemID = sa.itemID
                JOIN rare_words rw ON fiw.wordID = rw.wordID
            ),
            source_rare_cnt AS (
                SELECT count(*) as cnt FROM source_rare
            ),
            overlap AS (
                SELECT
                    ia.parentItemID as candidateID,
                    count(DISTINCT fiw.wordID) as shared_rare
                FROM fulltextItemWords fiw
                JOIN source_rare sr ON fiw.wordID = sr.wordID
                JOIN itemAttachments ia ON fiw.itemID = ia.itemID
                WHERE ia.parentItemID IS NOT NULL
                  AND ia.parentItemID != ?
                GROUP BY ia.parentItemID
            ),
            candidate_rare AS (
                SELECT
                    ia.parentItemID as candidateID,
                    count(DISTINCT fiw.wordID) as rare_count
                FROM fulltextItemWords fiw
                JOIN rare_words rw ON fiw.wordID = rw.wordID
                JOIN itemAttachments ia ON fiw.itemID = ia.itemID
                WHERE ia.parentItemID IS NOT NULL
                  AND ia.parentItemID != ?
                GROUP BY ia.parentItemID
            )
            SELECT
                o.candidateID,
                1.0 * o.shared_rare / max(src.cnt, cr.rare_count) as score
            FROM overlap o
            JOIN candidate_rare cr ON o.candidateID = cr.candidateID
            CROSS JOIN source_rare_cnt src
            WHERE src.cnt > 0
        """, (source_item_id, source_item_id, source_item_id))
        for row in cursor.fetchall():
            scores.setdefault(row['candidateID'], {})['text'] = row['score']

        # Filter: only keep candidates that are real bibliographic items
        valid_candidates = set()
        if scores:
            id_ph = ','.join('?' * len(scores))
            ex_ph = self._excluded_ids_placeholder
            cursor.execute(
                f"SELECT itemID FROM items WHERE itemID IN ({id_ph}) "
                f"AND itemTypeID NOT IN ({ex_ph})",
                list(scores.keys()) + list(self._excluded_type_ids))
            valid_candidates = {row['itemID'] for row in cursor.fetchall()}

        return {cid: s for cid, s in scores.items() if cid in valid_candidates}

    def _get_relationship_explanations(self, cursor, source_item_id: int,
                                        candidate_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Get human-readable explanations for why each candidate is related."""
        explanations: Dict[int, Dict[str, Any]] = {}
        if not candidate_ids:
            return explanations

        for cid in candidate_ids:
            expl: Dict[str, Any] = {}

            # Shared collection names
            cursor.execute("""
                SELECT c.collectionName
                FROM collectionItems ci1
                JOIN collectionItems ci2 ON ci1.collectionID = ci2.collectionID
                JOIN collections c ON ci1.collectionID = c.collectionID
                WHERE ci1.itemID = ? AND ci2.itemID = ?
            """, (source_item_id, cid))
            colls = [row['collectionName'] for row in cursor.fetchall()]
            if colls:
                expl['shared_collections'] = colls

            # Shared tag names
            cursor.execute("""
                SELECT t.name
                FROM itemTags it1
                JOIN itemTags it2 ON it1.tagID = it2.tagID
                JOIN tags t ON it1.tagID = t.tagID
                WHERE it1.itemID = ? AND it2.itemID = ?
            """, (source_item_id, cid))
            tags = [row['name'] for row in cursor.fetchall()]
            if tags:
                expl['shared_tags'] = tags

            # Shared creator names
            cursor.execute("""
                SELECT c.firstName, c.lastName, c.fieldMode
                FROM itemCreators ic1
                JOIN itemCreators ic2 ON ic1.creatorID = ic2.creatorID
                JOIN creators c ON ic1.creatorID = c.creatorID
                WHERE ic1.itemID = ? AND ic2.itemID = ?
            """, (source_item_id, cid))
            creators = []
            for row in cursor.fetchall():
                if row['fieldMode'] == 1:
                    creators.append(row['lastName'])
                else:
                    creators.append(f"{row['firstName']} {row['lastName']}".strip())
            if creators:
                expl['shared_creators'] = creators

            # Shared venue
            cursor.execute("""
                SELECT idv.value
                FROM itemData id1
                JOIN itemData id2 ON id1.valueID = id2.valueID
                JOIN itemDataValues idv ON id1.valueID = idv.valueID
                WHERE id1.itemID = ? AND id2.itemID = ?
                  AND id1.fieldID = (SELECT fieldID FROM fields WHERE fieldName = 'publicationTitle')
                  AND id2.fieldID = id1.fieldID
            """, (source_item_id, cid))
            row = cursor.fetchone()
            if row:
                expl['shared_venue'] = row['value']

            explanations[cid] = expl

        return explanations

    def _get_items_metadata_batch(self, cursor, item_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Batch-fetch title, key, typeName for a list of item IDs."""
        if not item_ids:
            return {}
        placeholders = ','.join('?' * len(item_ids))
        cursor.execute(f"""
            SELECT i.itemID, i.key, it.typeName,
                (SELECT idv.value FROM itemDataValues idv
                 JOIN itemData id ON id.valueID = idv.valueID
                 JOIN fields f ON id.fieldID = f.fieldID
                 WHERE id.itemID = i.itemID AND f.fieldName = 'title'
                ) as title
            FROM items i
            JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
            WHERE i.itemID IN ({placeholders})
        """, item_ids)
        return {row['itemID']: dict(row) for row in cursor.fetchall()}

    # --- Collections ---

    def list_collections(self, parent_collection_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List collections. If parent_collection_id is given, list its sub-collections.
        If None, list top-level collections. Each entry includes child count and item count.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if parent_collection_id is None:
                cursor.execute("""
                    SELECT c.collectionID, c.collectionName, c.key,
                        (SELECT count(*) FROM collections c2 WHERE c2.parentCollectionID = c.collectionID) as child_count,
                        (SELECT count(*) FROM collectionItems ci WHERE ci.collectionID = c.collectionID) as item_count
                    FROM collections c
                    WHERE c.parentCollectionID IS NULL
                    ORDER BY c.collectionName
                """)
            else:
                cursor.execute("""
                    SELECT c.collectionID, c.collectionName, c.key,
                        (SELECT count(*) FROM collections c2 WHERE c2.parentCollectionID = c.collectionID) as child_count,
                        (SELECT count(*) FROM collectionItems ci WHERE ci.collectionID = c.collectionID) as item_count
                    FROM collections c
                    WHERE c.parentCollectionID = ?
                    ORDER BY c.collectionName
                """, (parent_collection_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_collection_items(self, collection_key: str) -> List[Dict[str, Any]]:
        """Get all items in a specific collection by collection key.
        Includes standalone attachments (PDFs added directly without a parent item).
        """
        ph = self._excluded_ids_placeholder
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT
                    i.itemID, i.key, it.typeName, i.dateAdded,
                    COALESCE(
                        (SELECT idv.value FROM itemDataValues idv
                         JOIN itemData id ON id.valueID = idv.valueID
                         JOIN fields f ON id.fieldID = f.fieldID
                         WHERE id.itemID = i.itemID AND f.fieldName = 'title'),
                        ia.path
                    ) as title
                FROM collectionItems ci
                JOIN collections c ON ci.collectionID = c.collectionID
                JOIN items i ON ci.itemID = i.itemID
                JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
                LEFT JOIN itemAttachments ia ON ia.itemID = i.itemID
                WHERE c.key = ?
                  AND (
                    i.itemTypeID NOT IN ({ph})
                    OR (it.typeName = 'attachment' AND ia.parentItemID IS NULL)
                  )
                ORDER BY i.dateAdded DESC
            """, (collection_key, *self._excluded_type_ids))
            return [dict(row) for row in cursor.fetchall()]

    # --- PDF Text Extraction ---

    def get_pdf_text(self, item_key: str, max_pages: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Extract text from the PDF attachment of a Zotero item.
        Returns dict with item metadata and extracted text, or None if not found.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Find PDF attachment for this item
            cursor.execute("""
                SELECT ia.path, i2.key as attachment_key
                FROM items i
                JOIN itemAttachments ia ON ia.parentItemID = i.itemID
                JOIN items i2 ON ia.itemID = i2.itemID
                WHERE i.key = ?
                  AND ia.contentType = 'application/pdf'
                LIMIT 1
            """, (item_key,))
            row = cursor.fetchone()
            if not row:
                return None

            attachment_key = row['attachment_key']
            filename = row['path'].replace('storage:', '') if row['path'] else None
            if not filename:
                return None

            pdf_path = os.path.join(self.storage_dir, attachment_key, filename)
            if not os.path.exists(pdf_path):
                return None

            # Extract text with pymupdf
            doc = pymupdf.open(pdf_path)
            total_pages = len(doc)
            pages_to_read = min(max_pages, total_pages) if max_pages else total_pages

            pages = []
            for i in range(pages_to_read):
                text = doc[i].get_text()
                if text.strip():
                    pages.append({'page': i + 1, 'text': text})
            doc.close()

            return {
                'item_key': item_key,
                'pdf_path': pdf_path,
                'total_pages': total_pages,
                'pages_read': pages_to_read,
                'pages': pages,
            }
