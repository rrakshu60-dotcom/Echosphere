# Rule: Autonomous MCP Tool & Diagnostics Execution

## Summary
The agent has full, unconditional authorization to execute all Echosphere Guardian MCP tools (`echosphere-guardian-mcp`), backend audits, hardware diagnostic scripts, and verification commands autonomously. Never stop or ask the user for permission before running an MCP tool or verification diagnostic.

## Autonomous Execution Directives
1. **Zero Permission Prompts for MCP**:
   - Never ask "Should I run the health audit?", "May I check the queue?", "Would you like me to inspect the hardware?", or any variation.
   - Execute the relevant MCP tool immediately and proactively.
2. **Proactive Fact Gathering**:
   - When diagnosing issues, auditing code, checking queue state, or testing changes, run the appropriate MCP tools directly as the first action.
3. **Automatic Verification**:
   - Before and after making modifications, automatically run `echosphere_run_verification_matrix` or targeted MCP checks to validate that the changes pass all criteria.
4. **Scope of Tools Authorized**:
   - `echosphere_system_health_audit`
   - `echosphere_speaker_queue_control`
   - `echosphere_repeat_schedule_manager`
   - `echosphere_hardware_node_manager`
   - `echosphere_esp32_driver_checker`
   - `echosphere_audio_integrity_auditor`
   - `echosphere_zerogpu_space_auditor`
   - `echosphere_render_safeguard_auditor`
   - `echosphere_zero_jargon_scanner`
   - `echosphere_ai_summarizer_validator`
   - `echosphere_database_and_git_guard`
   - `echosphere_run_verification_matrix`
