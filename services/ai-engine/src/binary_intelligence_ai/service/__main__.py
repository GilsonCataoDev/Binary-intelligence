import logging

from binary_intelligence_ai.service.app import build_server, load_engine_configuration


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    configuration = load_engine_configuration()
    server = build_server(configuration)
    logging.getLogger(__name__).info("engine listening on http://%s:%d (simulation only)", configuration.host, configuration.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
