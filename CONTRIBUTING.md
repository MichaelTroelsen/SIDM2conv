# Contributing Guidelines

Thank you for your interest in contributing to the SID to SF2 Converter project!

## Code of Conduct

- Be respectful and constructive
- Focus on technical accuracy
- Help maintain code quality

## Development Workflow

### 1. Setup

```bash
# Clone repository
git clone <repository-url>
cd SIDM2

# Verify Python version (3.8+ required, 3.7+ may work)
python --version

# Run tests to verify setup
python -m unittest test_converter -v
```

### 2. Making Changes

1. Create a feature branch
2. Make your changes
3. Update tests
4. Update documentation
5. Run all tests
6. Commit with descriptive message

## Documentation Rules

### When to Update Documentation

**ALWAYS update README.md when:**

- Adding new features or functionality
- Changing command-line interface or usage
- Modifying file formats or data structures
- Adding new dependencies
- Changing installation/setup process
- Fixing significant bugs that affect usage
- Adding new analysis or output capabilities

**ALWAYS update inline code comments when:**

- Adding new functions or classes
- Modifying existing function behavior
- Adding complex algorithms
- Changing data structures

### Documentation Standards

1. **README.md**: Keep format descriptions accurate and up-to-date
2. **Code docstrings**: Use clear, concise descriptions
3. **Comments**: Explain "why" not "what"
4. **Examples**: Provide working examples for new features

### Documentation Template for New Features

```markdown
## Feature Name

Brief description of what it does.

### Usage

```bash
command example
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| name | type | what it does |

### Example

```python
# Code example
```
```

## Testing Rules

### When to Add/Update Tests

**ALWAYS add tests when:**

- Adding new functions or methods
- Adding new classes
- Adding new command-line options
- Adding new file format support
- Adding new analysis capabilities

**ALWAYS update tests when:**

- Changing function signatures
- Changing return values or data structures
- Fixing bugs (add regression test)
- Changing validation logic

### Test Requirements

1. **Minimum coverage**: Every public function must have at least one test
2. **Edge cases**: Test boundary conditions and error cases
3. **Real data**: Include integration tests with actual SID files
4. **Descriptive names**: Test names should describe what they test

### Test Structure

```python
class TestFeatureName(unittest.TestCase):
    """Tests for feature description"""

    def setUp(self):
        """Set up test fixtures"""
        pass

    def tearDown(self):
        """Clean up after tests"""
        pass

    def test_normal_case(self):
        """Test description of normal behavior"""
        # Arrange
        input_data = ...

        # Act
        result = function(input_data)

        # Assert
        self.assertEqual(result, expected)

    def test_edge_case(self):
        """Test description of edge case"""
        pass

    def test_error_case(self):
        """Test that errors are handled correctly"""
        with self.assertRaises(ExpectedException):
            function(invalid_input)
```

### Running Tests

```bash
# Run all tests with verbose output
python -m unittest test_converter -v

# Run specific test class
python -m unittest test_converter.TestSIDParser -v

# Run specific test method
python -m unittest test_converter.TestSIDParser.test_parse_header_magic -v
```

### Test Naming Convention

- `test_<function>_<scenario>_<expected_result>`
- Example: `test_parse_header_invalid_magic_raises_error`

## Code Standards

### Python Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Maximum line length: 100 characters
- Use descriptive variable names

### Function Documentation

```python
def function_name(param1: Type1, param2: Type2) -> ReturnType:
    """
    Brief description of function.

    Detailed description if needed.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ExceptionType: When this happens
    """
    pass
```

### Class Documentation

```python
class ClassName:
    """
    Brief description of class.

    Detailed description of purpose and usage.

    Attributes:
        attr1: Description
        attr2: Description
    """
    pass
```

## Error Handling Guidelines

The SIDM2 project uses a structured error handling system to provide clear, actionable error messages to users. All code should use the custom error classes from `sidm2.errors` instead of generic exceptions.

### Available Error Classes

The `sidm2.errors` module provides 6 specialized error classes:

| Error Class | Use For | Example |
|-------------|---------|---------|
| `FileNotFoundError` | Missing files/directories | Input SID file not found |
| `InvalidInputError` | Invalid/corrupted data | Corrupted SID file format |
| `MissingDependencyError` | Missing modules/tools | Laxity converter not installed |
| `PermissionError` | Access denied issues | Cannot write output file |
| `ConfigurationError` | Invalid settings | Unknown driver type |
| `ConversionError` | Conversion failures | Table extraction failed |

### When to Use Custom Errors

**ALWAYS use custom error classes when:**

- File operations fail (reading, writing, access)
- Input data is invalid or corrupted
- Required dependencies are missing
- Configuration values are invalid
- Conversion or processing fails
- Permission errors occur

**DON'T use generic exceptions:**

```python
# ❌ Bad - Generic exceptions
raise Exception("File not found")
raise ValueError("Invalid input")
raise RuntimeError("Conversion failed")

# ✅ Good - Specific error classes
raise errors.FileNotFoundError(path=filepath, context="SID file")
raise errors.InvalidInputError(input_type="SID file", value=filepath)
raise errors.ConversionError(stage="conversion", reason="...")
```

### Basic Usage

```python
from sidm2 import errors

# File not found
if not os.path.exists(input_path):
    raise errors.FileNotFoundError(
        path=input_path,
        context="input SID file",
        suggestions=[
            "Check the file path: python scripts/sid_to_sf2.py --help",
            "Use absolute path instead of relative",
            "List files: ls SID/"
        ],
        docs_link="guides/TROUBLESHOOTING.md#1-file-not-found-issues"
    )

# Invalid input
if not validate_format(data):
    raise errors.InvalidInputError(
        input_type="SID file",
        value=filepath,
        expected="PSID or RSID format",
        got=f"Unknown magic bytes: {magic_bytes.hex()}",
        suggestions=[
            "Verify file is a valid SID file",
            "Re-download from HVSC or csdb.dk"
        ]
    )

# Missing dependency
if not module_available:
    raise errors.MissingDependencyError(
        dependency="sidm2.laxity_converter",
        install_command="pip install -e .",
        alternatives=["Use standard drivers instead"]
    )

# Configuration error
if driver not in available_drivers:
    raise errors.ConfigurationError(
        setting="driver",
        value=driver,
        valid_options=available_drivers,
        example="python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity"
    )

# Conversion error
try:
    extract_tables(sid_data)
except Exception as e:
    raise errors.ConversionError(
        stage="table extraction",
        reason=str(e),
        input_file=input_path,
        suggestions=[
            "Check player type: tools/player-id.exe input.sid",
            "Try different driver: --driver driver11"
        ]
    )
```

### Error Message Structure

All error messages follow a standard structure:

```
ERROR: [Clear Error Title]

What happened:
  [Brief explanation of what went wrong]

Why this happened:
  • [Common cause 1]
  • [Common cause 2]
  • [Common cause 3]

How to fix:
  1. [Primary solution with specific command]
  2. [Alternative solution]
  3. [Fallback solution]

Need help?
  * Documentation: [link to specific guide section]
  * Issues: https://github.com/MichaelTroelsen/SIDM2conv/issues
```

### Best Practices

1. **Use Specific Error Classes**: Choose the most appropriate error type for the situation
2. **Provide Context**: Include the problematic value/path in error messages
3. **Actionable Solutions**: Give 2-4 specific steps with actual commands
4. **Platform Awareness**: Provide platform-specific guidance when needed
5. **Documentation Links**: Link to specific troubleshooting guide sections
6. **Progressive Disclosure**: Start simple, provide details in "Technical details" section

### Testing Requirements

**When adding new error handling:**

1. Add test cases to `scripts/test_error_messages.py`
2. Verify error structure (contains all required sections)
3. Test that error can be raised and caught properly
4. Verify suggestions are helpful and accurate
5. Ensure documentation links are valid

```python
class TestMyNewError(unittest.TestCase):
    def test_my_error_structure(self):
        """Test MyNewError has proper structure."""
        error = errors.MyNewError(param="value")
        msg = str(error)

        # Verify structure
        self.assertIn("ERROR:", msg)
        self.assertIn("What happened:", msg)
        self.assertIn("How to fix:", msg)
        self.assertIn("Need help?", msg)
```

### Complete Documentation

For complete error handling guidelines, see:

- **Style Guide**: `docs/guides/ERROR_MESSAGE_STYLE_GUIDE.md` - Complete contributor guidelines
- **Troubleshooting Guide**: `docs/guides/TROUBLESHOOTING.md` - User-facing documentation
- **Error Module**: `sidm2/errors.py` - Implementation details
- **Test Suite**: `scripts/test_error_messages.py` - 34 tests, 100% coverage

### Checklist for Error Handling

When implementing error handling:

- [ ] Used appropriate error class from `sidm2.errors`
- [ ] Provided clear "What happened" description
- [ ] Listed 3-5 common causes in "Why this happened"
- [ ] Included 2-4 specific, actionable fixes with commands
- [ ] Added alternatives if applicable
- [ ] Linked to specific troubleshooting guide section
- [ ] Included technical details for debugging
- [ ] Added test case to `test_error_messages.py`
- [ ] Verified error can be raised and caught
- [ ] Tested on actual failure scenarios

## Git Workflow

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `test/description` - Test additions/fixes
- `refactor/description` - Code refactoring

### Commit Messages

Follow conventional commits format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `test`: Tests
- `refactor`: Code refactoring
- `style`: Formatting
- `chore`: Maintenance

Examples:
```
feat(parser): add support for RSID format
fix(analyzer): correct sequence detection for edge case
docs(readme): update SF2 format description
test(writer): add tests for template injection
```

### Pull Request Process

1. Ensure all tests pass
2. Update documentation
3. Write clear PR description
4. Reference related issues
5. Request review

## Adding New File Format Support

When adding support for a new player format:

1. **Research phase**
   - Document the format structure
   - Identify data locations
   - Create analysis tool

2. **Implementation phase**
   - Create parser class
   - Add extraction methods
   - Implement conversion logic

3. **Testing phase**
   - Add unit tests
   - Add integration tests with real files
   - Test edge cases

4. **Documentation phase**
   - Update README with format description
   - Add usage examples
   - Document limitations

## Checklist for Pull Requests

- [ ] Code follows project style guidelines
- [ ] All tests pass (`python -m unittest test_converter -v`)
- [ ] New tests added for new functionality
- [ ] Documentation updated (README.md)
- [ ] Commit messages follow convention
- [ ] No debug code or print statements left in
- [ ] Error handling is appropriate
- [ ] Code is readable and well-commented

## Reporting Issues

When reporting issues, include:

1. Python version
2. Operating system
3. Input file (or description)
4. Expected behavior
5. Actual behavior
6. Error messages (if any)
7. Steps to reproduce

## Questions?

If you have questions about contributing:

1. Check existing documentation
2. Look at existing code for patterns
3. Open an issue for discussion

Thank you for contributing!
