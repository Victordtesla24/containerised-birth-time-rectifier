---
description: Detailed Development Protocols of building new features, modifying current features and new capabilities
globs:
alwaysApply: true
---
### Development Protocol (Fail Fast & Iterative)
**Pre and Post requisite**: This protocol pre and post requisite has a strict pre-requisite of mandatory and strict adherance with every single other protocols [my-code-optimisation-protocols.mdc](mdc:.cursor/rules/my-code-optimisation-protocols.mdc), [my-directory-management-protocols.mdc](mdc:.cursor/rules/my-directory-management-protocols.mdc), [my-error-fixing-protocols.mdc](mdc:.cursor/rules/my-error-fixing-protocols.mdc), [my-memory-manager.mdc](mdc:.cursor/rules/my-memory-manager.mdc) meticulously.

1. **Strict Enforcement:**
   - Follow Directory Management([my-directory-management-protocols.mdc](mdc:.cursor/rules/my-directory-management-protocols.mdc)), Code Modification & Replacement, and Error Handling Protocols ([my-error-fixing-protocols.mdc](mdc:.cursor/rules/my-error-fixing-protocols.mdc)) rigorously.
   - **Do Not Overcomplicate:** Only modify precisely what is required for a **new feature** or **error fix**.
   - **No Unnecessary Changes:** Do not introduce placeholder text (e.g., `# ... [rest of the existing methods remain unchanged]`) or modify entire files.
   - **Targeted Changes Only:** Update only specific sections that relate to the current task or fix.
   - **File Integrity Verification:** After every change, verify the file's integrity (no extraneous comments or modifications).
   - **Cross-Protocol Calls:** If any issues with directory structure or import errors arise during development, **invoke the Directory Management Protocol** [my-directory-management-protocols.mdc](mdc:.cursor/rules/my-directory-management-protocols.mdc) and/or the **Error Handling Protocol** [my-error-fixing-protocols.mdc](mdc:.cursor/rules/my-error-fixing-protocols.mdc) to resolve them.
   - **Metrics-Driven Development:** Implement New Relic's FAIL framework (Feedback, Analytics, Iteration, Learning) for quantitative validation.
   - **Stakeholder Integration:** Establish regular feedback loops with stakeholders at key development milestones.
   - **Technical Debt Management:** Monitor and maintain Code Health Index throughout development lifecycle.

2. **Fail Fast & Iterative Approach:**
   - Implement small, incremental changes.
   - If a change **fails** or introduces new issues, **roll back immediately** and refine the approach in the next iteration.
   - Prioritize **quick detection** of issues and **focused** solutions.
   - **Call to Error Management & Directory Management Protocols:** Whenever new errors surface (especially those involving imports or structure), seamlessly link to the relevant protocols for a minimal fix [my-error-fixing-protocols.mdc](mdc:.cursor/rules/my-error-fixing-protocols.mdc) [my-directory-management-protocols.mdc](mdc:.cursor/rules/my-directory-management-protocols.mdc).

3. **Directory Structure & Modularity:**
   - Adhere to deployment guidelines (e.g., **VERCEL**).
   - Reuse existing files and consolidate duplicates where possible.
   - **Refactor large files (>600 lines)** into smaller, modular files following industry-standard architecture and **Directory Management Protocols** [my-directory-management-protocols.mdc](mdc:.cursor/rules/my-directory-management-protocols.mdc) .
   - **Invoke Error Handling Protocols** if any directory modifications break existing imports call **Error Handling Protocols** [my-error-fixing-protocols.mdc](mdc:.cursor/rules/my-error-fixing-protocols.mdc).

4. **Hybrid Planning Model:**
   - Follow IBM's Strategic Fail-Fast Framework:
     1. Conduct 2-week traditional planning sprints with stakeholder alignment
     2. Define MVP with Code Health Index baseline and quantitative success metrics
     3. Execute fail-fast iterations with FAIL metrics tracking:
        - Feedback: Gather user metrics and stakeholder input
        - Analytics: Calculate impact scores and performance metrics
        - Iteration: Apply learnings from analytics
        - Learning: Document insights and optimize next cycle
     4. Perform quarterly strategic scaling reviews with metric-based decisions
   - Balance upfront architectural planning with agile execution
   - Maintain technical debt metrics throughout development
   - Track iteration velocity and error resolution efficiency

---

## During Development

- **Strict Requirement:** Do not lose, add, or remove functionality beyond the **targeted** change.
- **Tool Usage Tag:** Begin every tool invocation with `[MEMORY BANK: ACTIVE]`.
- **Documentation:** Update the Memory Bank only after the task/change is **fully completed**.
- **Protocol Integration:** During development, if any error arises, call the **Error Handling Protocol ([my-error-fixing-protocols.mdc](mdc:.cursor/rules/my-error-fixing-protocols.mdc))**. If that error involves file structure or imports, also invoke the **Directory Management Protocol ([my-directory-management-protocols.mdc](mdc:.cursor/rules/my-directory-management-protocols.mdc))** and the **Recursive Import Error Fixing Algorithm** from [.cursorrules](mdc:.cursorrules).

---
