"""Print the API's OpenAPI schema as JSON (used to generate the client's TypeScript types)."""

import json

from app.main import create_app

if __name__ == "__main__":
    print(json.dumps(create_app().openapi(), indent=2))
