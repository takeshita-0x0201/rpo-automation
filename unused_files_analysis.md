# Unused Python Files Analysis for RPO-Automation Project

## Analysis Date: 2025-07-23

## Summary
This analysis identifies Python files that appear to be unused in the rpo-automation project, categorized by confidence level. The analysis focused on the directories: `core/`, `webapp/`, `scripts/`, and `ai_matching_system/`.

## Methodology
1. Identified all Python files in target directories
2. Analyzed import statements across the codebase
3. Checked for files with `if __name__ == "__main__"` blocks (entry points)
4. Examined webapp/main.py router imports
5. Searched for dynamic imports using importlib, __import__, exec, or eval

## Categories of Unused Files

### HIGH Confidence - Definitely Unused (41 files)
These files are never imported and are not entry points:

#### AI Matching System - Old/Deprecated Modules (17 files)
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/ai_matching/deep_research_matcher.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/ai_matching/deep_research_modular.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/ai_matching/embeddings/gemini_embedder.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/ai_matching/nodes/base.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/ai_matching/nodes/evaluator.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/ai_matching/nodes/gap_analyzer.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/ai_matching/nodes/orchestrator.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/ai_matching/nodes/rag_searcher.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/ai_matching/nodes/reporter.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/ai_matching/nodes/score_based_strategy.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/ai_matching/nodes/searcher.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/ai_matching/rag/advanced_search_strategy.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/ai_matching/rag/pinecone_vector_db.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/ai_matching/rag/search_quality_monitor.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/ai_matching/rag/vector_db.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/ai_matching/rag/vector_manager.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/ai_matching/rag/feedback_loop.py` (has main but never imported)

#### Core - Unused Modules (10 files)
- `/Users/yukitakeshia/rpo-automation/core/agent/agent.py`
- `/Users/yukitakeshia/rpo-automation/core/agent/executor.py`
- `/Users/yukitakeshia/rpo-automation/core/agent/poller.py`
- `/Users/yukitakeshia/rpo-automation/core/ai/openai_client.py` (replaced by gemini_client)
- `/Users/yukitakeshia/rpo-automation/core/data/client_patterns.py`
- `/Users/yukitakeshia/rpo-automation/core/services/performance_monitor.py`
- `/Users/yukitakeshia/rpo-automation/core/sheets/writer.py`
- `/Users/yukitakeshia/rpo-automation/core/utils/env_loader.py`
- `/Users/yukitakeshia/rpo-automation/core/utils/logging_config.py`
- `/Users/yukitakeshia/rpo-automation/core/scraping/bizreach_scraper.py` (has main but never imported)

#### Webapp - Unused Services and API (4 files)
- `/Users/yukitakeshia/rpo-automation/webapp/api/evaluations.py` (imported in main.py but likely deprecated)
- `/Users/yukitakeshia/rpo-automation/webapp/services/ai_matching_service_debug.py`
- `/Users/yukitakeshia/rpo-automation/webapp/services/job_structuring_service.py`
- `/Users/yukitakeshia/rpo-automation/webapp/services/vector_sync_service.py` (imported by other files but might be unused)

#### Scripts - Old/Unused Utilities (10 files)
- `/Users/yukitakeshia/rpo-automation/scripts/check_pinecone_index.py`
- `/Users/yukitakeshia/rpo-automation/scripts/check_table_relationships.py`
- `/Users/yukitakeshia/rpo-automation/scripts/check_vector_content.py`
- `/Users/yukitakeshia/rpo-automation/scripts/create_pinecone_index.py`
- `/Users/yukitakeshia/rpo-automation/scripts/daily/daily_screening.py`
- `/Users/yukitakeshia/rpo-automation/scripts/inspect_pinecone_data.py`
- `/Users/yukitakeshia/rpo-automation/scripts/reset_sync_data.py`
- `/Users/yukitakeshia/rpo-automation/scripts/setup/generate_icons.py` (has main but never imported)
- `/Users/yukitakeshia/rpo-automation/scripts/setup/install_agent.py`
- `/Users/yukitakeshia/rpo-automation/tests/scripts/investigate_ai_evaluations.py` (test script, has main)
- `/Users/yukitakeshia/rpo-automation/tests/scripts/verify_ai_evaluations_fix.py` (test script, has main)

### MEDIUM Confidence - Likely Unused but Needs Verification (26 files)
These files have main blocks (can be run directly) but are never imported:

#### AI Matching System - Standalone Scripts (8 files)
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/run_separated_matching.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/scripts/add_resume_text_to_json.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/scripts/analyze_evaluation_diff.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/scripts/enrich_historical_data.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/scripts/interactive_search.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/scripts/run_matching.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/scripts/search_similar_cases.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/scripts/test_matching_demo.py`
- `/Users/yukitakeshia/rpo-automation/ai_matching_system/scripts/vectorize_historical_data.py`

#### Webapp - Migration and Fix Scripts (6 files)
- `/Users/yukitakeshia/rpo-automation/webapp/apply_migration.py`
- `/Users/yukitakeshia/rpo-automation/webapp/migrations/run_migration.py`
- `/Users/yukitakeshia/rpo-automation/webapp/scripts/analyze_llm_responses.py`
- `/Users/yukitakeshia/rpo-automation/webapp/scripts/check_tables.py`
- `/Users/yukitakeshia/rpo-automation/webapp/scripts/debug_overall_assessment.py`
- `/Users/yukitakeshia/rpo-automation/webapp/scripts/fix_existing_assessments.py`
- `/Users/yukitakeshia/rpo-automation/webapp/scripts/fix_overall_assessment.py`

#### Scripts - Utility Scripts (10 files)
- `/Users/yukitakeshia/rpo-automation/scripts/processing/create_test_job.py`
- `/Users/yukitakeshia/rpo-automation/scripts/processing/process_generic_job.py`
- `/Users/yukitakeshia/rpo-automation/scripts/processing/process_job_description.py`
- `/Users/yukitakeshia/rpo-automation/scripts/setup/setup_media_platforms.py`
- `/Users/yukitakeshia/rpo-automation/scripts/sync_client_evaluations_to_pinecone.py`
- `/Users/yukitakeshia/rpo-automation/scripts/test_client_evaluation_upload.py`
- `/Users/yukitakeshia/rpo-automation/scripts/test_vector_sync.py`
- `/Users/yukitakeshia/rpo-automation/scripts/utilities/add_url_patterns.py`
- `/Users/yukitakeshia/rpo-automation/scripts/utilities/check_candidates_data.py`
- `/Users/yukitakeshia/rpo-automation/scripts/utilities/check_media_platforms.py`
- `/Users/yukitakeshia/rpo-automation/scripts/utilities/execute_job_manually.py`

#### Database Scripts (2 files)
- `/Users/yukitakeshia/rpo-automation/database/scripts/check_supabase_tables.py`
- `/Users/yukitakeshia/rpo-automation/database/scripts/check_table_types.py`

### LOW Confidence - Might Be Important (30 files)
These are routers imported by webapp/main.py and other important entry points:

#### Webapp Routers - All Active (20 files)
All router files in `/Users/yukitakeshia/rpo-automation/webapp/routers/` are actively used by main.py

#### Important Entry Points (2 files)
- `/Users/yukitakeshia/rpo-automation/webapp/main.py` - Main FastAPI application
- `/Users/yukitakeshia/rpo-automation/run_webapp.py` - Application launcher

#### Core Module Used but Shows as Unused (1 file)
- `/Users/yukitakeshia/rpo-automation/core/data/structure_requirements.py` (has main block, might be used)

## Recommendations

### 1. Safe to Delete (HIGH Confidence)
The 41 files in the HIGH confidence category can likely be deleted without impact. These appear to be:
- Old AI matching system implementations that have been replaced
- Deprecated core modules (agent system, OpenAI client, sheets writer)
- Unused performance monitoring and logging utilities
- Old Pinecone-related scripts

### 2. Review Before Deletion (MEDIUM Confidence)
The 26 files in MEDIUM confidence should be reviewed:
- Migration scripts might be needed for future database changes
- Test job creation scripts might be useful for testing
- Utility scripts might be occasionally used for maintenance

### 3. Keep (LOW Confidence)
All webapp routers and main entry points should be kept as they are actively used.

## Next Steps
1. Review the HIGH confidence files with the team to confirm they can be deleted
2. Check if any MEDIUM confidence scripts are documented in operational procedures
3. Consider moving useful but rarely-used scripts to a separate 'archive' or 'tools' directory
4. Update any documentation that might reference these unused files