"""
NEUROTWIN OS — Code Review Graph Microservice
Analyzes git commits and changes using Neo4j graph relationships.
Tracks file co-change patterns, code quality over time, and architectural hotspots.
Exposes REST API on port 8004.
"""

import json
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import git
from fastapi import FastAPI, HTTPException
from neo4j import AsyncGraphDatabase
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse

from services.common.logging_utils import setup_logging
from services.common.fastapi_middleware import TraceMiddleware

setup_logging(service_name="neurotwin.codereview")
logger = logging.getLogger("neurotwin.codereview")

# ── Configuration ─────────────────────────────────────────────────────────────

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neurotwin-neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neurotwin_password")
REPO_PATH = os.getenv("REPO_PATH", "/app/repo")  # Path to repository to analyze

# ── Schemas ───────────────────────────────────────────────────────────────────

class FileNode(BaseModel):
    path: str
    language: Optional[str] = None
    is_test: bool = False
    total_changes: int = 0
    last_modified: Optional[float] = None


class CommitNode(BaseModel):
    hash: str
    author: str
    email: str
    timestamp: float
    message: str
    insertions: int = 0
    deletions: int = 0
    files_changed: List[str] = []


class CoChangeRelationship(BaseModel):
    file_a: str
    file_b: str
    strength: float  # 0-1, frequency of co-change
    shared_commits: int


class QualityMetric(BaseModel):
    file_path: str
    churn_score: float  # total lines added+deleted normalized
    complexity_score: float  # proxy: diff size or cyclomatic complexity if available
    bug_prone_score: float  # based on churn + co-change with buggy files
    last_updated: float
    trend: Optional[str] = None  # "improving", "degrading", "stable"


class AnalysisReport(BaseModel):
    total_commits: int
    total_files: int
    top_cochange_pairs: List[Dict]
    highest_churn_files: List[Dict]
    complex_files: List[Dict]
    generated_at: datetime


# ── Code Review Graph Engine ──────────────────────────────────────────────────

class CodeReviewGraph:
    """
    Core engine for analyzing code repositories and building graph relationships in Neo4j.
    """

    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self._driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self._uri = neo4j_uri
        self._repo: Optional[git.Repo] = None

    async def close(self):
        if self._driver:
            await self._driver.close()
            logger.info("Neo4j driver closed")

    def load_repository(self, repo_path: str) -> bool:
        """Initialize git repository for analysis."""
        try:
            self._repo = git.Repo(repo_path)
            logger.info(f"Loaded repository at {repo_path} with {self._repo.head.commit.hexsha[:8]}")
            return True
        except Exception as e:
            logger.error(f"Failed to load repository: {e}")
            return False

    # ── Schema Management ────────────────────────────────────────────────────

    async def ensure_schema(self):
        """Create Neo4j constraints and indexes."""
        queries = [
            # Constraints
            "CREATE CONSTRAINT file_path_unique IF NOT EXISTS FOR (f:CodeFile) REQUIRE f.path IS UNIQUE",
            "CREATE CONSTRAINT commit_hash_unique IF NOT EXISTS FOR (c:Commit) REQUIRE c.hash IS UNIQUE",
            "CREATE CONSTRAINT author_email_unique IF NOT EXISTS FOR (a:Author) REQUIRE a.email IS UNIQUE",

            # Indexes for query performance
            "CREATE INDEX file_language_idx IF NOT EXISTS FOR (f:CodeFile) ON (f.language)",
            "CREATE INDEX commit_timestamp_idx IF NOT EXISTS FOR (c:Commit) ON (c.timestamp)",
            "CREATE INDEX cochange_strength_idx IF NOT EXISTS FOR ()-[r:COCHANGES_WITH]-() ON (r.strength)",
        ]
        async with self._driver.session() as session:
            for query in queries:
                try:
                    await session.run(query)
                    logger.debug(f"Schema query executed: {query[:50]}...")
                except Exception as e:
                    logger.warning(f"Schema query skipped (may already exist): {e}")
        logger.info("Neo4j schema ensured")

    # ── Analysis Pipeline ─────────────────────────────────────────────────────

    async def analyze_repository(self, max_commits: int = 1000) -> Dict:
        """
        Main analysis pipeline: scan commits and build graph.
        Returns summary statistics.
        """
        if not self._repo:
            raise ValueError("No repository loaded")

        await self.ensure_schema()
        stats = {"commits_processed": 0, "files_encountered": set(), "cochange_pairs": {}}

        # Process commits in reverse chronological order
        commits = list(self._repo.iter_commits("--all", max_count=max_commits))
        logger.info(f"Analyzing {len(commits)} commits")

        for commit in commits:
            await self._process_commit(commit, stats)
            stats["commits_processed"] += 1

            if stats["commits_processed"] % 100 == 0:
                logger.info(f"Processed {stats['commits_processed']} commits")

        # Compute co-change relationships after all commits
        await self._compute_cochange_relationships()
        await self._compute_quality_metrics()

        logger.info(f"Analysis complete: {stats['commits_processed']} commits, {len(stats['files_encountered'])} files")
        return {
            "commits_processed": stats["commits_processed"],
            "unique_files": len(stats["files_encountered"]),
            "cochange_relationships": len(stats["cochange_pairs"]),
        }

    async def _process_commit(self, commit: git.Commit, stats: Dict):
        """Process a single commit and create graph nodes/relationships."""
        author_name = commit.author.name
        author_email = commit.author.email
        commit_hash = commit.hexsha
        timestamp = commit.committed_date
        message = commit.message.strip()

        # Track file changes
        files_changed = []
        insertions = 0
        deletions = 0

        try:
            # Get stats for the commit
            if commit.parents:
                diff = commit.parents[0].diff(commit)
            else:
                diff = commit.diff(git.NULL_TREE)

            for diff_item in diff:
                file_path = diff_item.a_path or diff_item.b_path
                if file_path:
                    files_changed.append(file_path)
                    stats["files_encountered"].add(file_path)

                    # Count insertions/deletions
                    if diff_item.diff:
                        diff_text = diff_item.diff.decode("utf-8", errors="ignore") if isinstance(diff_item.diff, bytes) else str(diff_item.diff)
                        insertions += diff_text.count("\n+")
                        deletions += diff_text.count("\n-")

        except Exception as e:
            logger.warning(f"Error processing diff for {commit_hash[:8]}: {e}")

        # Create nodes and relationships in Neo4j
        async with self._driver.session() as session:
            # Merge author
            await session.run(
                """
                MERGE (a:Author {email: $email})
                SET a.name = $name
                """,
                {"email": author_email, "name": author_name}
            )

            # Merge commit
            await session.run(
                """
                MERGE (c:Commit {hash: $hash})
                SET c.author_email = $email,
                    c.author_name = $name,
                    c.timestamp = $timestamp,
                    c.message = $message,
                    c.insertions = $insertions,
                    c.deletions = $deletions
                """,
                {
                    "hash": commit_hash,
                    "email": author_email,
                    "name": author_name,
                    "timestamp": timestamp,
                    "message": message[:500],
                    "insertions": insertions,
                    "deletions": deletions,
                }
            )

            # Link commit to author
            await session.run(
                """
                MATCH (c:Commit {hash: $hash})
                MATCH (a:Author {email: $email})
                MERGE (a)-[:AUTHORED]->(c)
                """,
                {"hash": commit_hash, "email": author_email}
            )

            # Process each file
            for file_path in files_changed:
                # Determine language from extension
                ext = Path(file_path).suffix.lower()
                language_map = {
                    ".py": "python", ".js": "javascript", ".ts": "typescript",
                    ".tsx": "typescript", ".java": "java", ".cpp": "cpp",
                    ".c": "c", ".go": "go", ".rs": "rust", ".rb": "ruby",
                    ".php": "php", ".swift": "swift", ".kt": "kotlin",
                    ".scala": "scala", ".html": "html", ".css": "css",
                    ".scss": "scss", ".sql": "sql", ".md": "markdown",
                    ".json": "json", ".yaml": "yaml", ".yml": "yaml",
                    ".toml": "toml", ".xml": "xml", ".sh": "bash",
                    ".ps1": "powershell", ".dockerfile": "dockerfile",
                }
                language = language_map.get(ext, "unknown")
                is_test = any(pat in file_path.lower() for pat in ["test", "spec", "__tests__", "test_"])

                # Merge file node
                await session.run(
                    """
                    MERGE (f:CodeFile {path: $path})
                    SET f.language = $language,
                        f.is_test = $is_test,
                        f.last_modified = $timestamp,
                        f.total_changes = coalesce(f.total_changes, 0) + 1
                    """,
                    {
                        "path": file_path,
                        "language": language,
                        "is_test": is_test,
                        "timestamp": timestamp,
                    }
                )

                # Link commit to file with change metadata
                await session.run(
                    """
                    MATCH (c:Commit {hash: $hash})
                    MATCH (f:CodeFile {path: $path})
                    MERGE (c)-[r:CHANGED]->(f)
                    SET r.insertions = $insertions,
                        r.deletions = $deletions
                    """,
                    {
                        "hash": commit_hash,
                        "path": file_path,
                        "insertions": insertions // max(len(files_changed), 1),  # rough estimate per file
                        "deletions": deletions // max(len(files_changed), 1),
                    }
                )

    async def _compute_cochange_relationships(self):
        """
        Compute co-change relationships: which files tend to change together.
        Creates COCHANGES_WITH relationships weighted by frequency.
        """
        logger.info("Computing co-change relationships...")
        async with self._driver.session() as session:
            # Find file pairs that appear together in commits
            result = await session.run(
                """
                MATCH (c:Commit)-[:CHANGED]->(f1:CodeFile),
                      (c)-[:CHANGED]->(f2:CodeFile)
                WHERE f1.path < f2.path  // avoid duplicates and self
                WITH f1, f2, count(c) as shared_commits
                WHERE shared_commits >= 2  // at least 2 co-changes to be significant
                MERGE (f1)-[r:COCHANGES_WITH]->(f2)
                SET r.strength = shared_commits * 1.0,
                    r.shared_commits = shared_commits
                RETURN count(r) as relationships_created
                """
            )
            record = await result.single()
            logger.info(f"Created {record['relationships_created']} co-change relationships")

    async def _compute_quality_metrics(self):
        """
        Compute quality metrics for each file based on churn and co-change patterns.
        Creates or updates QualityMetric nodes linked to files.
        """
        logger.info("Computing quality metrics...")
        async with self._driver.session() as session:
            # Compute churn score (total lines changed)
            await session.run(
                """
                MATCH (f:CodeFile)<-[:CHANGED]-(c:Commit)
                WITH f, sum(c.insertions + c.deletions) as total_changes
                SET f.churn_score = total_changes
                """
            )

            # Identify bug-prone files (high co-change count with many others)
            await session.run(
                """
                MATCH (f:CodeFile)-[:COCHANGES_WITH]-(other)
                WITH f, count(other) as cochange_count,
                     sum(r.strength) as total_strength
                SET f.cochange_count = cochange_count,
                    f.total_cochange_strength = total_strength
                """
            )

            # Create QualityMetric nodes
            await session.run(
                """
                MATCH (f:CodeFile)
                SET f.quality_score = CASE
                    WHEN f.churn_score IS NULL THEN 0.5
                    WHEN f.churn_score > 10000 THEN 0.2
                    WHEN f.churn_score > 5000 THEN 0.4
                    WHEN f.churn_score > 1000 THEN 0.6
                    ELSE 0.8
                END
                CREATE (qm:QualityMetric {
                    file_path: f.path,
                    churn_score: coalesce(f.churn_score, 0),
                    complexity_score: coalesce(f.complexity_score, 0.5),
                    bug_prone_score: coalesce(f.cochange_count * 0.1, 0),
                    last_updated: timestamp(),
                    overall_quality: f.quality_score
                })
                MERGE (f)-[:HAS_METRIC]->(qm)
                """,
            )
        logger.info("Quality metrics computed")

    # ── Query Methods ──────────────────────────────────────────────────────────

    async def get_cochange_partners(self, file_path: str, min_strength: float = 2.0) -> List[Dict]:
        """Get files that frequently change together with the given file."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (f:CodeFile {path: $path})-[r:COCHANGES_WITH]-(partner:CodeFile)
                WHERE r.strength >= $min_strength
                RETURN partner.path as file_path,
                       partner.language as language,
                       r.strength as strength,
                       r.shared_commits as shared_commits
                ORDER BY r.strength DESC
                LIMIT 20
                """,
                {"path": file_path, "min_strength": min_strength}
            )
            return [dict(record) async for record in result]

    async def get_architectural_hotspots(self, limit: int = 20) -> List[Dict]:
        """
        Find architectural hotspots: files with high co-change count
        (indicates tight coupling / potential for refactoring).
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (f:CodeFile)-[:COCHANGES_WITH]-(other)
                WITH f, count(DISTINCT other) as distinct_cochanges,
                     sum(r.strength) as total_strength
                WHERE distinct_cochanges >= 3
                RETURN f.path as file_path,
                       f.language as language,
                       distinct_cochanges as coupling_count,
                       total_strength as coupling_strength
                ORDER BY distinct_cochanges DESC, total_strength DESC
                LIMIT $limit
                """,
                {"limit": limit}
            )
            return [dict(record) async for record in result]

    async def get_top_churn_files(self, limit: int = 20) -> List[Dict]:
        """Get files with highest code churn (total lines changed)."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (f:CodeFile)
                WHERE f.churn_score IS NOT NULL
                RETURN f.path as file_path,
                       f.language as language,
                       f.churn_score as churn_score,
                       f.total_changes as change_count
                ORDER BY f.churn_score DESC
                LIMIT $limit
                """
            )
            return [dict(record) async for record in result]

    async def get_quality_report(self) -> Dict:
        """Aggregate quality metrics across the entire codebase."""
        async with self._driver.session() as session:
            # Average quality
            avg_result = await session.run(
                "MATCH (f:CodeFile) WHERE f.quality_score IS NOT NULL RETURN avg(f.quality_score) as avg_quality"
            )
            avg_rec = await avg_result.single()

            # Count by quality tier
            tier_result = await session.run(
                """
                MATCH (f:CodeFile)
                WITH f.quality_score as qs,
                     CASE
                         WHEN qs >= 0.8 THEN 'high'
                         WHEN qs >= 0.5 THEN 'medium'
                         ELSE 'low'
                     END as tier
                RETURN tier, count(*) as count
                ORDER BY tier
                """
            )
            tiers = {rec["tier"]: rec["count"] async for rec in tier_result}

            # Top problematic files (low quality, high churn)
            problems_result = await session.run(
                """
                MATCH (f:CodeFile)
                WHERE f.quality_score < 0.5 AND coalesce(f.churn_score, 0) > 1000
                RETURN f.path as file_path,
                       f.quality_score as quality,
                       f.churn_score as churn,
                       coalesce(f.cochange_count, 0) as coupling
                ORDER BY f.quality_score ASC, f.churn_score DESC
                LIMIT 10
                """
            )
            problematic = [dict(rec) async for rec in problems_result]

            return {
                "average_quality": round(avg_rec["avg_quality"], 3) if avg_rec["avg_quality"] else None,
                "quality_distribution": tiers,
                "problematic_files": problematic,
                "total_files_analyzed": sum(tiers.values()),
            }

    async def find_coupling_path(self, file_a: str, file_b: str, max_depth: int = 3) -> Optional[List[Dict]]:
        """
        Find coupling path between two files through co-change relationships.
        Helps understand architectural dependencies.
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH path = shortestPath(
                    (f1:CodeFile {path: $file_a})-[:COCHANGES_WITH*1..$max_depth]-(f2:CodeFile {path: $file_b})
                )
                RETURN nodes(path) as path_nodes, relationships(path) as path_rels
                """,
                {"file_a": file_a, "file_b": file_b, "max_depth": max_depth}
            )
            record = await result.single()
            if record:
                nodes = record["path_nodes"]
                rels = record["path_rels"]
                path = []
                for i, node in enumerate(nodes):
                    path.append({"type": "file", "path": node["path"], "language": node.get("language")})
                    if i < len(rels):
                        path.append({"type": "cochange", "strength": rels[i].get("strength", 1)})
                return path
            return None


# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="NEUROTWIN Code Review Graph",
    description="Analyzes code commits and tracks quality patterns using Neo4j graph relationships",
    version="1.0.0",
)
app.add_middleware(TraceMiddleware)

codereview = CodeReviewGraph(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)


@app.get("/health")
async def health_check():
    try:
        async with codereview._driver.session() as session:
            await session.run("RETURN 1")
        neo4j_ok = True
    except Exception:
        neo4j_ok = False

    return {
        "status": "ok" if neo4j_ok else "degraded",
        "service": "codereview",
        "version": "1.0.0",
        "neo4j_connected": neo4j_ok,
        "repo_loaded": codereview._repo is not None,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/v1/analyze")
async def analyze_repository(max_commits: int = 1000):
    """
    Trigger analysis of the repository.
    Scans git history and builds/updates the graph.
    """
    try:
        if not codereview._repo:
            # Try to load from REPO_PATH
            if not codereview.load_repository(REPO_PATH):
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not load repository at {REPO_PATH}. Check REPO_PATH environment variable."
                )

        start_time = time.time()
        result = await codereview.analyze_repository(max_commits=max_commits)
        elapsed = time.time() - start_time

        return {
            "success": True,
            "elapsed_seconds": round(elapsed, 2),
            "analysis": result,
            "message": f"Analyzed {result['commits_processed']} commits across {result['unique_files']} files"
        }
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/files/{file_path:path}/cochange")
async def get_cochange_partners(file_path: str, min_strength: float = 2.0):
    """
    Get files that frequently change together with the given file.
    Useful for understanding coupling and impact of changes.
    """
    try:
        partners = await codereview.get_cochange_partners(file_path, min_strength)
        return {
            "file": file_path,
            "cochange_partners": partners,
            "partner_count": len(partners)
        }
    except Exception as e:
        logger.error(f"Cochange query failed for {file_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/files/{file_path:path}/quality")
async def get_file_quality(file_path: str):
    """Get quality metrics for a specific file."""
    async with codereview._driver.session() as session:
        result = await session.run(
            """
            MATCH (f:CodeFile {path: $path})
            OPTIONAL MATCH (f)-[:HAS_METRIC]->(qm:QualityMetric)
            RETURN f.path as file_path,
                   f.language as language,
                   f.churn_score as churn_score,
                   f.cochange_count as coupling_count,
                   qm.overall_quality as quality_score
            """,
            {"path": file_path}
        )
        record = await result.single()
        if not record:
            raise HTTPException(status_code=404, detail="File not found in analysis graph")

        return dict(record)


@app.get("/v1/report/architectural-hotspots")
async def get_architectural_hotspots(limit: int = 20):
    """
    Get list of files with high coupling (change with many other files).
    These are architectural hotspots that may benefit from refactoring.
    """
    try:
        hotspots = await codereview.get_architectural_hotspots(limit)
        return {
            "hotspots": hotspots,
            "count": len(hotspots),
            "note": "High co-change count indicates tight coupling"
        }
    except Exception as e:
        logger.error(f"Hotspots query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/report/churn")
async def get_churn_report(limit: int = 20):
    """Get top files by code churn (lines added + deleted)."""
    try:
        churn_files = await codereview.get_top_churn_files(limit)
        return {
            "high_churn_files": churn_files,
            "count": len(churn_files),
            "note": "High churn often indicates unstable or buggy code"
        }
    except Exception as e:
        logger.error(f"Churn report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/report/quality")
async def get_quality_report():
    """Get overall quality metrics summary."""
    try:
        report = await codereview.get_quality_report()
        return report
    except Exception as e:
        logger.error(f"Quality report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/graph/coupling-path")
async def get_coupling_path(file_a: str, file_b: str, max_depth: int = 3):
    """
    Find shortest coupling path between two files through co-change relationships.
    Useful for understanding ripple effects of changes.
    """
    try:
        path = await codereview.find_coupling_path(file_a, file_b, max_depth)
        if path:
            return {
                "file_a": file_a,
                "file_b": file_b,
                "path": path,
                "path_length": len(path) // 2  # number of hops
            }
        else:
            return {
                "file_a": file_a,
                "file_b": file_b,
                "path": None,
                "message": "No coupling path found"
            }
    except Exception as e:
        logger.error(f"Coupling path query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/graph/stats")
async def get_graph_statistics():
    """Get overall graph statistics."""
    async with codereview._driver.session() as session:
        stats_result = await session.run(
            """
            MATCH (n)
            WITH labels(n) as labels, count(*) as count
            RETURN labels[0] as node_type, count
            UNION
            MATCH ()-[r]->()
            RETURN type(r) as node_type, count(*) as count
            """
        )
        stats = {}
        async for record in stats_result:
            stats[record["node_type"]] = record["count"]

        return {
            "graph_statistics": stats,
            "generated_at": datetime.utcnow().isoformat()
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8004, reload=True)
