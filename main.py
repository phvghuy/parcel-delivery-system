import sys
import uvicorn


def run_api() -> None:
    uvicorn.run(
        "smart_delivery_routing.interface.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "api"

    if mode == "api":
        run_api()
    else:
        print("Usage: python main.py api")
        sys.exit(1)
