# Commands

## Poetry

    ```bash
    # Activate or create a virtual environment
    poetry shell

    # Install main dependencies
    poetry install
    # Or install with optional dependency groups (suitable for development, documentation, etc. Not accessible for end-users)
    poetry install --with docs
    # Or install with extra module dependencies (suitable for optional features available to end-users)
    poetry install --extras ui
    poetry install --all-extras

    # Add a new dependency
    poetry add <package>
    # Or add a new dev dependency
    poetry add <package> --group dev
    # Or add a new extra dependency
    poetry add --extras "ui" <package>
    ```
