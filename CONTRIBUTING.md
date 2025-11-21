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

# Verify Python version (3.7+)
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
