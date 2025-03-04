import fire

from sahi_onnx.predict import predict


def main():
    fire.Fire(predict)


if __name__ == "__main__":
    main()
