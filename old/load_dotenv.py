def load_dotenv(dotenv_path='.env'):
    """
    Load environment variables from .env file

    Args:
        dotenv_path: Path to .env file (default: '.env')

    Returns:
        dict: Loaded environment variables
    """
    import os
    import re

    # Dictionary to store loaded environment variables
    loaded_env = {}

    try:
        with open(dotenv_path) as f:
            for line in f:
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                # Split by first equals sign
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove quotes if present
                    if value and (value[0] == value[-1] == '"' or value[0] == value[-1] == "'"):
                        value = value[1:-1]

                    # Expand variables in the value ${VAR}
                    if '${' in value:
                        for match in re.finditer(r'\${([^}]+)}', value):
                            var_name = match.group(1)
                            # Try to get from already loaded vars, then from os.environ, or empty string
                            var_value = loaded_env.get(var_name) or os.environ.get(var_name) or ''
                            value = value.replace(match.group(0), var_value)

                    # Set environment variable
                    os.environ[key] = value
                    loaded_env[key] = value

        return loaded_env
    except FileNotFoundError:
        # If file doesn't exist, return empty dict but don't raise an error
        return {}
