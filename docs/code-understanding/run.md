
# `spa-booking-api/run.py`

## 1. Purpose

This file is the main executable entry point for the entire backend Flask API. Its sole purpose is to load environment variables, create an instance of the Flask application using the `create_app` factory function, and then run the development server. This is a standard pattern in Flask applications to separate the application's creation from its execution.

## 2. Where it fits

This is the top-level file that starts the backend server.

```text
Developer runs `python run.py` in the terminal
    ↓
`load_dotenv()` loads variables from a `.env` file
    ↓
`create_app()` function from `app/__init__.py` is called
    ↓
A fully configured Flask `app` object is returned
    ↓
`app.run()` starts the development web server
    ↓
Server begins listening for HTTP requests
```

## 3. Inputs

This script doesn't take direct arguments, but it is configured by:

*   **Environment Variables**: The `load_dotenv()` function reads a `.env` file in the project root. This file is expected to contain configuration secrets and settings, such as `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, and `FLASK_ENV`. The `FLASK_ENV` variable is particularly important as it determines whether the app runs in 'development' or 'production' mode, which affects the configuration loaded by `create_app`.

## 4. Outputs

*   **A running process**: The primary output is a running web server process that listens for incoming network requests on `0.0.0.0:5000`.
*   **Debug information**: Because `debug=True` is set, the server will provide detailed error pages and automatically reload when code changes are detected.

## 5. Important functions/classes

```text
(script execution block)
if __name__ == '__main__':
    ↓
Purpose
    ↓
    To ensure the server only runs when the script is executed directly (i.e., `python run.py`), not when it's imported by another module.
    ↓
Input
    ↓
    The `app` object created by `create_app()`.
    ↓
What it does
    ↓
    Calls `app.run()` with specific parameters:
    - `host='0.0.0.0'`: Makes the server accessible from other machines on the network, not just `localhost`.
    - `port=5000`: Sets the server to listen on port 5000.
    - `debug=True`: Enables Flask's debug mode.
    ↓
Output
    ↓
    A running development web server.
```

The most important function is actually imported:

```text
create_app() (from `app/__init__.py`)
    ↓
Purpose
    ↓
    This is an application factory. It creates and configures the entire Flask application object, including initializing extensions and registering API blueprints (routes).
    ↓
Input
    ↓
    - `config_name`: (Optional) A string like 'development' or 'production' to specify which configuration to use. Defaults to the `FLASK_ENV` environment variable.
    ↓
What it does
    ↓
    1.  Creates a `Flask` instance.
    2.  Loads configuration from `app.config`.
    3.  Initializes all Flask extensions (like the database `db`, `jwt` for authentication, `cors`, `socketio`, etc.) by binding them to the app instance.
    4.  Imports all the API blueprint objects (e.g., `admin_bp`, `auth_bp`).
    5.  Registers each blueprint with a URL prefix (e.g., `auth_bp` is registered at `/api/auth`). This is how all the API routes are added to the application.
    6.  Registers custom error handlers.
    7.  Adds a simple `/api/health` check endpoint.
    ↓
Output
    ↓
    A fully configured and ready-to-run Flask `app` object.
```

## 6. Execution flow

1.  The developer runs `python run.py` from the command line.
2.  `dotenv.load_dotenv()` is called, loading environment variables from the `.env` file into the process's environment.
3.  The `create_app()` function is imported and called.
4.  Inside `create_app()`, a Flask app is instantiated. It reads the `FLASK_ENV` variable to select the correct configuration object (e.g., `DevelopmentConfig`).
5.  All extensions are initialized, and all API blueprints are registered, populating the app with its routes.
6.  `create_app()` returns the fully built `app` object.
7.  The `if __name__ == '__main__':` block executes.
8.  `app.run(host='0.0.0.0', port=5000, debug=True)` is called, which starts the Flask development server.
9.  The server process starts and begins listening on port 5000 for HTTP requests.

## 7. Dependencies

```text
dotenv (specifically `load_dotenv`)
    ↓
    A Python library used to load environment variables from a `.env` file into the application's environment. This is the first step, ensuring all configuration is available before the app is created.

app (from `app`)
    ↓
    This is the main application package. Specifically, the `create_app` factory function is imported from its `__init__.py` file. This is the most important dependency, as it contains the entire application assembly logic.
```

## 8. Relationship with other files

```text
This file (run.py)
 ├── imports and calls → app/__init__.py (to get the `create_app` factory)
 └── is configured by → .env (for environment variables)
```

## 9. Important state/data

This file is stateless. Its sole purpose is to initialize and run the application. The application object `app` is the most important piece of data, but it is passed directly to the `run` method and not manipulated further in this file.

## 10. What I should understand

1.  **This is Only the "Ignition Switch":** This file's only job is to start the server. All the complex setup logic is deliberately placed inside the `create_app` factory in `app/__init__.py`.
2.  **It's for Development:** The use of `app.run(debug=True)` indicates this script is intended for running the local development server. In a production environment, a proper WSGI server like Gunicorn or uWSGI would be used instead of Flask's built-in server.
3.  **Configuration Happens First:** The call to `load_dotenv()` is critically placed at the very top. This ensures that all necessary environment variables are loaded and available before any part of the application code, which relies on that configuration, is imported or executed.
4.  **The Application Factory Pattern is Key:** The use of `create_app()` is a standard Flask best practice. It avoids circular imports and makes the application easier to test and configure for different environments.

## 11. Potential confusing parts

*   **Where are the routes?**: Someone reading this file will not see any `@app.route` decorators. This is because all the routes are defined in separate "blueprint" files (e.g., `app/blueprints/auth.py`) and are registered with the application inside the `create_app` function. This file is kept clean of any actual application logic.
*   **`debug=True`**: It's important to understand this is for development only. Running a Flask app with `debug=True` in production is a major security risk, as it can expose sensitive information in error pages.

## 12. One-paragraph mental model

If I remember only one thing about this file, it should be that **it is the starter motor for the backend API.** It does not contain any engine parts itself; its only job is to perform the pre-start check of loading environment variables, then turn the key by calling the `create_app` factory to build the entire application engine, and finally, press the start button (`app.run`) to get the development server running.
