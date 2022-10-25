from app.module_3.a import hello_world


def process_greeting(name: str) -> None:
    print(hello_world() + name)

