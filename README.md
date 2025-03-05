# HTTP Reply Test Server

A Python-based server for testing HTTP clients by serving specially crafted HTTP responses.

## Overview

This server allows you to test HTTP clients by serving predefined test cases as HTTP responses. It's particularly useful for:

- Security testing of HTTP clients
- Testing how clients handle malformed HTTP responses
- Fuzzing HTTP client implementations
- Reproducing HTTP-related vulnerabilities

## Project Background

This project is inspired by the PROTOS test suite (c05-http-reply), which was originally developed by the University of Oulu Secure Programming Group (OUSPG) for testing HTTP implementations. The original PROTOS suite is licensed under GNU General Public License (GPL) version 2.

For more information on the original PROTOS test suite:
http://www.ee.oulu.fi/research/ouspg/protos/testing/c05/http-reply
(Note: This link is no longer active as of 2025)

## Features

- Serves test cases from individual files or a zip archive
- Supports sequential injection of multiple test cases
- Configurable port and connection behavior
- Detailed logging of client requests and server actions
- Simple command-line interface

## Requirements

- Python 3.6 or higher

## Installation

1. Simply download the `HTTP-reply-test-server.py` script
2. Make it executable:
   ```
   chmod +x HTTP-reply-test-server.py
   ```

## Usage

To start the server, run the script with any desired options:
```
python HTTP-reply-test-server.py [options]
```
Note: By default, the server uses `testcases.zip` or the `testcases` folder unless a custom zip or folder is specified.

### Command-line Options

- `-p`, `--port`: Specify the port number (default: 8080)
- `-d`, `--directory`: Specify the directory containing test cases
- `-z`, `--zipfile`: Specify a zip file containing test cases
- `-l`, `--logfile`: Specify a file to log server actions
- `-h`, `--help`: Show the help message and exit

### Examples

Start the server on port 8080 with test cases in the `testcases` directory:
```
python HTTP-reply-test-server.py -p 8080 -d testcases
```

Start the server with test cases from a zip file:
```
python HTTP-reply-test-server.py -z testcases.zip
```

Log server actions to a file:
```
python HTTP-reply-test-server.py -l server.log
```

