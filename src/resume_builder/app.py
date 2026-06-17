"""Uvicorn entry point for the Resume Builder API."""

from resume_builder.api.main import create_app

app = create_app()


def main():
    import uvicorn

    uvicorn.run("resume_builder.app:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
