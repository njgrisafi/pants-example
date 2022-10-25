from app.module_3.b import process_greeting, hello_world


def message_greeter(name: str) -> None:
    print(name)
    process_greeting()