#!/usr/bin/env python
# -*- coding: utf-8 -*-




from __future__ import print_function
import sys
import logging
import json
import socket


def sigint_handler(signal, frame):
    # 负责linux kernel信号处理
    """
    handle keyboard interrupts (CTRL-C)
    """

    # cli_output
    print()
    logging.info("CTRL-C received, exiting")
    sys.exit(0)


def send_message(connection, message):
    # 发送消息
    try:
        connection.sendall(message)
    except socket.error:
        logging.error("error, send_message")
        sys.exit(-1)

    logging.info("message sent: " + message)


def json_load(json_file):
    # 载入json格式的文件，并将其解码
    with open(json_file, "rb") as file_:
        json_ = json.load(file_)

    return json_


def json_save(json_file, json_):
    # 使用简单的json.dumps方法对简单数据类型进行编码，并将编码后的json保存到文件中
    # save json structrure into json file,and make easy readable
    with open(json_file, "wb+") as file_:
        json.dump(json_, file_, sort_keys=True, indent=4, separators=(",", ": "))


if __name__ == "__main__":
    print("This file is meant to be imported, not run.")
