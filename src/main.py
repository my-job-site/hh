from threading import Thread

from loader import Loader

if __name__ == "__main__":
    loader = Loader()
    thread = Thread(target=loader.run)

    try:
        thread.start()
    except KeyboardInterrupt:
        thread.join()
