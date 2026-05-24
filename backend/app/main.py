from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Voice Debrief Assistant API")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "voice-debrief-api"}

    return app


app = create_app()
