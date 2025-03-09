---
description: Detailed Code Optimization Protocol that describes how to optimise existing code
globs:
alwaysApply: false
---
### Code Optimization Protocol
**Pre and Post requisite**: This protocol pre and post requisite has a strict pre-requisite of mandatory and strict adherance with every single other protocols [my-development-protocols.mdc](mdc:.cursor/rules/my-development-protocols.mdc), [my-error-fixing-protocols.mdc](mdc:.cursor/rules/my-error-fixing-protocols.mdc), [my-directory-management-protocols.mdc](mdc:.cursor/rules/my-directory-management-protocols.mdc), & [my-memory-manager.mdc](mdc:.cursor/rules/my-memory-manager.mdc) meticulously.

- **Only generate or replace code** when absolutely necessary.
- Keep solutions **minimal and simple** ("**less code is better**").
- Apply **atomic changes** and remain **focused** on the specific request.
- **Refactor large files (>600 lines)** into smaller modules for better maintainability and performance.
- **Technical Debt Quantification:**
  ```
  CHI = (Cyclomatic Complexity × Code Duplication) / Test Coverage
  ```
- Monitor and maintain Code Health Index thresholds:
  ```python
  def calculate_health_index():
      return {
          'complexity_score': measure_cyclomatic_complexity(),
          'duplication_rate': detect_code_duplication(),
          'test_coverage': calculate_test_coverage(),
          'cognitive_load': assess_cognitive_complexity(),
          'maintainability_index': calculate_maintainability()
      }
  ```
- Implement threshold-based refactoring triggers:
  - CHI > 0.7: Immediate refactoring required
  - CHI > 0.5: Plan refactoring in next sprint
  - CHI > 0.3: Monitor for degradation
- Track and optimize cyclomatic complexity
- Implement Mad Devs' Composition Refactoring:
  - Extract complex handlers into microservices
  - Apply red-green-refactor pattern
  - Enforce DRY principle strictly

### AI-Powered Refactoring

- **GitHub Copilot Integration:**
  - Automated code smell detection with severity classification
  - Context-aware method extraction based on cognitive load metrics
  - Test-driven refactor suggestions with coverage analysis
  - Real-time complexity assessment
- **DRY Compliance:**
  - Use AI to identify and consolidate duplicate code
  - Extract common patterns into reusable methods
  - Generate comprehensive test coverage
  - Track duplication metrics over time
- **Continuous Improvement:**
  - Regular AI-assisted code reviews with quantitative scoring
  - Automated complexity reduction suggestions prioritized by impact
  - Smart test generation pre-refactor with coverage goals
  - Integration with Code Health Index monitoring
- **Performance Optimization:**
  - AI-driven performance bottleneck detection
  - Automated optimization suggestions based on runtime metrics
  - Resource utilization analysis and recommendations

---
