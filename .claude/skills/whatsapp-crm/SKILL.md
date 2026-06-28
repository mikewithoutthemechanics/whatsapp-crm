```markdown
# whatsapp-crm Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches best practices and patterns for contributing to the `whatsapp-crm` Python codebase. The repository is a Customer Relationship Management (CRM) tool built around WhatsApp, with a focus on clear code organization, consistent naming, and testable components. No specific framework is enforced, so conventions are especially important for maintainability.

## Coding Conventions

### File Naming
- Use **camelCase** for file names.
  - Example: `userManager.py`, `messageHandler.py`

### Imports
- Use **relative imports** within the project.
  - Example:
    ```python
    from .userManager import UserManager
    from .utils import sendMessage
    ```

### Exports
- Use **named exports** (i.e., define and import specific classes/functions, not `*`).
  - Example:
    ```python
    # In userManager.py
    class UserManager:
        pass

    # In another module
    from .userManager import UserManager
    ```

### Commit Messages
- Use the `fix` prefix for bug fixes.
- Keep commit messages concise (average 41 characters).
  - Example: `fix: handle empty message case`

## Workflows

### Adding a New Feature
**Trigger:** When implementing a new capability.
**Command:** `/add-feature`

1. Create a new Python file using camelCase (e.g., `featureName.py`).
2. Use relative imports to include dependencies.
3. Export new classes or functions using named exports.
4. Write or update tests in a corresponding `*.test.*` file.
5. Commit changes with a descriptive message.

### Fixing a Bug
**Trigger:** When resolving a defect or issue.
**Command:** `/fix-bug`

1. Identify and isolate the bug in the codebase.
2. Make code changes following the coding conventions.
3. Add or update relevant tests to cover the fix.
4. Commit with a `fix:` prefix (e.g., `fix: correct user lookup`).

### Writing Tests
**Trigger:** When adding or updating tests.
**Command:** `/write-test`

1. Create or update a test file matching the pattern `*.test.*` (e.g., `userManager.test.py`).
2. Write test cases for new or changed functionality.
3. Use the same import/export conventions as production code.
4. Run tests to ensure correctness.

## Testing Patterns

- Test files follow the `*.test.*` naming convention (e.g., `messageHandler.test.py`).
- The specific testing framework is not enforced; choose one that fits the project (e.g., `unittest`, `pytest`).
- Tests should import modules using relative imports and named exports.
- Example test structure:
  ```python
  # userManager.test.py
  from .userManager import UserManager

  def test_create_user():
      manager = UserManager()
      assert manager.create_user('Alice') is not None
  ```

## Commands
| Command      | Purpose                                 |
|--------------|-----------------------------------------|
| /add-feature | Start workflow for adding a new feature |
| /fix-bug     | Start workflow for fixing a bug         |
| /write-test  | Start workflow for writing tests        |
```
