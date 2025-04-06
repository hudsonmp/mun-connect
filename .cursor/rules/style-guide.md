# Coding Style Guide

This document outlines the coding standards and practices for the Model UN Assistant platform. Following these guidelines will ensure code consistency, maintainability, and a lean codebase focused on delivering core functionality.

## Guiding Principles

1. **Simplicity Over Complexity**: Choose the simplest solution that meets requirements.
2. **Minimize Dependencies**: Only add external packages when absolutely necessary.
3. **Clear Intent**: Code should be self-documenting with descriptive names.
4. **Lean Implementation**: Avoid premature optimization and bloated features.
5. **Focus on Core Value**: Every line of code should directly support key user stories.

## Python (Backend) Style Guide

### Code Formatting

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Use 4 spaces for indentation (not tabs)
- Maximum line length: 88 characters (compatible with Black formatter)
- Use Black for automatic formatting
- Use isort to organize imports

```python
# Example of properly formatted Python code
import json
import os
from typing import Dict, List, Optional

import openai
from flask import Flask, jsonify, request
from werkzeug.exceptions import BadRequest

app = Flask(__name__)

def generate_position_paper(
    committee: str,
    country: str,
    topic: str,
    reference_materials: Optional[List[str]] = None
) -> Dict:
    """
    Generate a position paper based on provided parameters.
    
    Args:
        committee: Name of the committee
        country: Country being represented
        topic: Topic of the paper
        reference_materials: List of reference material IDs
        
    Returns:
        Dictionary containing generated document and metadata
    """
    # Implementation
    response = {
        "document_id": "unique-id",
        "title": f"Position Paper: {country} on {topic}",
        "content": "<h1>Position Paper</h1>..."
    }
    return response
```

### Project Structure

```
/backend
├── app.py                  # Main application entry point
├── requirements.txt        # Dependencies
├── routes/                 # API route definitions
│   ├── __init__.py
│   ├── auth.py             # Authentication routes
│   ├── documents.py        # Document generation/management routes
│   └── references.py       # Reference materials routes
├── services/               # Business logic
│   ├── __init__.py
│   ├── document_service.py # Document generation logic
│   ├── openai_service.py   # OpenAI API interaction
│   └── storage_service.py  # Supabase storage interaction
├── utils/                  # Utility functions
│   ├── __init__.py
│   ├── error_handling.py   # Error handling utilities
│   └── validators.py       # Input validation
└── config.py               # Configuration (using environment variables)
```

### Naming Conventions

- **Files**: Lowercase with underscores (snake_case)
- **Classes**: CamelCase (e.g., `DocumentGenerator`)
- **Functions/Methods**: snake_case (e.g., `generate_document`)
- **Variables**: snake_case (e.g., `user_id`)
- **Constants**: UPPERCASE_WITH_UNDERSCORES (e.g., `MAX_FILE_SIZE`)

### Documentation

- Every function should have a docstring explaining purpose, parameters, and return values
- Complex logic should have inline comments explaining "why" not "what"
- Use type hints for function parameters and return types
- README.md should include setup instructions and API overview

### Error Handling

- Use specific exception types
- Catch exceptions at the appropriate level
- Provide helpful error messages
- Log errors with context information

```python
try:
    document = document_service.generate(committee, country, topic)
    return jsonify(document)
except ValidationError as e:
    # Client error, return 400
    return jsonify({"error": str(e), "code": "VALIDATION_ERROR"}), 400
except OpenAIServiceError as e:
    # External service error, return 503
    return jsonify({"error": "Document generation failed", "code": "SERVICE_UNAVAILABLE"}), 503
except Exception as e:
    # Unexpected error, log and return 500
    logger.error(f"Unexpected error generating document: {str(e)}", exc_info=True)
    return jsonify({"error": "An unexpected error occurred", "code": "SERVER_ERROR"}), 500
```

### Testing

- Write tests for critical paths first
- Use pytest for test framework
- Group tests by functionality
- Mock external dependencies

## JavaScript/TypeScript (Frontend) Style Guide

### Code Formatting

- Use ESLint with Airbnb preset (modified for simplicity)
- Use Prettier for auto-formatting
- 2 spaces for indentation

```javascript
// Example of properly formatted React component
import React, { useState } from 'react';

function DocumentEditor({ initialContent, onSave }) {
  const [content, setContent] = useState(initialContent);
  
  const handleChange = (newContent) => {
    setContent(newContent);
  };
  
  const handleSave = () => {
    onSave(content);
  };
  
  return (
    <div className="editor-container">
      <TinyMCE
        value={content}
        onChange={handleChange}
        init={{
          height: 500,
          menubar: false,
          plugins: [
            'advlist', 'autolink', 'lists', 'link', 'charmap', 'preview',
            'searchreplace', 'table', 'wordcount'
          ],
          toolbar: 'bold italic | bullist numlist | link | removeformat'
        }}
      />
      <button
        className="save-button"
        onClick={handleSave}
      >
        Save Document
      </button>
    </div>
  );
}

export default DocumentEditor;
```

### Project Structure

```
/frontend
├── public/
│   ├── index.html          # HTML template
│   └── favicon.ico         # Site favicon
├── src/
│   ├── components/         # Reusable UI components
│   │   ├── DocumentEditor.jsx
│   │   ├── UploadForm.jsx
│   │   └── common/         # Shared components like buttons, inputs
│   ├── pages/              # Page components
│   │   ├── Home.jsx        # Landing page
│   │   ├── Generator.jsx   # Document generation page
│   │   └── Documents.jsx   # Document management page
│   ├── services/           # API interaction
│   │   ├── api.js          # Base API setup
│   │   ├── documents.js    # Document-related API calls
│   │   └── auth.js         # Authentication API calls
│   ├── utils/              # Utility functions
│   │   ├── formatting.js   # Text/date formatting helpers
│   │   └── validation.js   # Form validation
│   ├── App.jsx             # Main application component
│   ├── index.jsx           # Application entry point
│   └── styles/             # Global styles
│       └── globals.css     # Global CSS
├── package.json            # Dependencies
└── next.config.js          # Next.js configuration
```

### Naming Conventions

- **Files**: Component files use PascalCase (e.g., `DocumentEditor.jsx`)
- **Utility files**: Use camelCase (e.g., `apiUtils.js`)
- **Components**: PascalCase (e.g., `<DocumentEditor />`)
- **Functions**: camelCase (e.g., `generateDocument()`)
- **Variables**: camelCase (e.g., `userId`)
- **Constants**: UPPERCASE_WITH_UNDERSCORES (e.g., `MAX_FILE_SIZE`)

### Component Structure

- One component per file
- Functional components with hooks preferred over class components
- Props destructuring at the top
- Group related state variables
- Keep JSX clean and readable

### CSS/Styling

- Use a minimal approach - no complex CSS frameworks
- Use CSS modules for component-specific styles
- Minimal inline styles, only for dynamic values
- Follow a consistent naming convention for classes

### State Management

- Use React Context for global state when necessary
- Keep state as local as possible
- Avoid unnecessary state - derive values when possible

### Code Quality

- Avoid console.logs in production code
- Minimize component re-renders
- Clean up effects that create subscriptions
- Keep functions pure when possible

## API Design Principles

1. **Consistency**: Use consistent patterns across all endpoints
2. **Simplicity**: Keep API surface area minimal
3. **Validation**: Validate all inputs server-side
4. **Error Handling**: Provide clear error responses
5. **Rate Limiting**: Implement rate limiting on all endpoints

## Database Guidelines

1. **Normalization**: Keep schema normalized but not overengineered
2. **Indexed Fields**: Index fields used in WHERE clauses
3. **Field Sizes**: Use appropriate field size constraints
4. **Timestamps**: Include created_at and updated_at fields on all tables

## Version Control

1. **Commit Messages**: Use clear, descriptive commit messages
2. **Branch Names**: Use descriptive branch names (e.g., `feature/document-generation`)
3. **Pull Requests**: Keep PRs focused on a single feature or bug fix
4. **Code Review**: All code should be reviewed before merging

## Documentation

1. **API Documentation**: Document all endpoints with examples
2. **Setup Instructions**: Clear instructions for local development
3. **Architecture Overview**: Document high-level system design
4. **Deployment Process**: Document the deployment workflow

## Performance Guidelines

1. **Bundle Size**: Keep JavaScript bundle size under 300KB
2. **API Response Times**: Target < 200ms for non-generation APIs
3. **Page Load Time**: Initial page load under 2 seconds
4. **Memory Usage**: Keep server memory usage moderate

By following these guidelines, we'll create a codebase that is focused, maintainable, and delivers the core functionality efficiently.
