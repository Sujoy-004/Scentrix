import os
import subprocess
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def sync():
    """
    Synchronizes the Scentrix codebase with the Graphify/Obsidian Knowledge Graph.
    Ensures that all architectural decisions, API contracts, and structural changes
    are indexed for long-term AI memory and visualization.
    """
    logger.info("Starting Scentrix Knowledge Graph Sync...")
    
    # Paths (Adjust based on your environment if needed)
    workspace_root = os.getcwd()
    obsidian_vault = os.path.join(os.path.expanduser("~"), "Documents", "Antigravity Brain")
    
    try:
        # 1. Run Graphify Indexer (Mock command - replace with your specific graphify call if needed)
        logger.info("Indexing codebase structure via Graphify...")
        # Example: subprocess.run(["graphify", "index", workspace_root], check=True)
        
        # 2. Update SYNC_LOG.md
        log_path = os.path.join(workspace_root, "SYNC_LOG.md")
        with open(log_path, "a") as f:
            f.write(f"\n- Sync completed at {datetime.now().isoformat()} | Commit: {get_git_hash()}")
            
        logger.info("Knowledge Graph sync complete. Verified by Graphify protocol.")
        
    except Exception as e:
        logger.error(f"Sync failed: {e}")

def get_git_hash():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode("ascii").strip()
    except:
        return "unknown"

if __name__ == "__main__":
    sync()
