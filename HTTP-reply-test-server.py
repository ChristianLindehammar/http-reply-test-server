#!/usr/bin/env python3

import argparse
import os
import socket
import sys
import time
import datetime
import signal
import zipfile
from pathlib import Path

# Add signal handler for clean exit on Ctrl+C
def signal_handler(sig, frame):
    print('\nServer shutting down...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def print_usage():
    """Print information about all available command-line options"""
    print("=" * 80)
    print("HTTP Reply Test Server - Available Options:")
    print("=" * 80)
    print("-port       : Port number to listen on (default: 8000)")
    print("-closedelay : Delay in milliseconds before closing socket (default: 0)")
    print("-single     : Inject single test case with specified index")
    print("-start      : Start test case index (default: 0)")
    print("-stop       : Stop test case index (default: max int)")
    print("-file       : Send single file instead of test cases")
    print("-testdir    : Directory containing test cases (default: testcases)")
    print("-zip        : Path to zip file containing test cases")
    print("-h, --help  : Show this help message and exit")
    print("=" * 80)
    print("Test Case Lookup Order:")
    print("1. If -file is specified, that single file will be used")
    print("2. If -zip is specified, test cases will be loaded from that zip file")
    print("3. Otherwise, the server will look for a file named '<testdir>.zip' (default: testcases.zip)")
    print("4. If zip file is not found, the server will look in the directory specified by -testdir")
    print("5. Test case files must have numeric filenames matching the -start and -stop range")
    print("=" * 80)
    print("")

class HTTPReplyTestServer:
    def __init__(self):
        self.port = 8000
        self.close_delay = 0
        self.start_index = 0
        self.stop_index = sys.maxsize
        self.test_case_dir = "testcases"
        self.single_file = None
        self.server_socket = None
        self.zip_file = None

    def prepare(self):
        """Open server socket to accept connections"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Set a timeout so we can handle keyboard interrupts
            self.server_socket.settimeout(1.0)
            self.server_socket.bind(('0.0.0.0', self.port))
            self.server_socket.listen(1)
            print(f"Server started on port {self.port}")
        except Exception as e:
            print(f"Error: {str(e)}")
            sys.exit(-1)

    def inject(self, index, data):
        """Inject a test case as HTTP response"""
        print("Waiting for connect...", end='', flush=True)
        
        # Set a short timeout to make Ctrl+C more responsive
        self.server_socket.settimeout(0.5)
        
        try:
            dot_counter = 0
            while True:
                try:
                    client_socket, addr = self.server_socket.accept()
                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"\n[{now}] Connection from [{addr[0]}:{addr[1]}]")
                    
                    # Read and log the request
                    try:
                        request = client_socket.recv(1024)
                        if request:
                            request_text = request.decode('utf-8', errors='replace').strip()
                            first_line = request_text.split('\n')[0] if '\n' in request_text else request_text
                            print(f"Received request: {first_line}")
                    except Exception as io:
                        print(f"Error reading request: {str(io)}")
                        client_socket.close()
                        continue
                        
                    print(f"Injecting testcase #{index}, data {len(data)} bytes")
                    
                    try:
                        client_socket.sendall(data)
                    except Exception as io:
                        print(f"Error: {str(io)}")
                    
                    # Delay before closing if specified
                    if self.close_delay > 0:
                        time.sleep(self.close_delay / 1000)  # Convert ms to seconds
                        
                    try:
                        client_socket.close()
                    except Exception as s:
                        print(f"Error: {str(s)}")
                        
                    # Return after successful injection
                    return
                    
                except socket.timeout:
                    # Print a dot every second to show we're alive
                    dot_counter += 1
                    if dot_counter % 2 == 0:  # With 0.5s timeout, this is ~1 second
                        print(".", end="", flush=True)
                    continue
                except KeyboardInterrupt:
                    print("\nOperation canceled by user.")
                    sys.exit(0)  # Exit immediately on Ctrl+C
                except Exception as se:
                    print(f"\nError: {str(se)}")
                    return
        except KeyboardInterrupt:
            print("\nOperation canceled by user.")
            sys.exit(0)  # Exit immediately on Ctrl+C

    def parse_single_file(self):
        """Parse test case from a single file"""
        print(f"Reading data from file: {self.single_file}")
        
        try:
            with open(self.single_file, 'rb') as file:
                data = file.read()
                self.inject(0, data)
        except Exception as e:
            print(f"Error: {str(e)}")

    def parse_zip_test_cases(self):
        """Parse test cases from a zip file"""
        print(f"Reading test cases from zip file: {self.zip_file}")
        
        try:
            with zipfile.ZipFile(self.zip_file, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                
                # Filter and sort test cases
                test_cases = []
                for file_name in file_list:
                    # Extract just the filename without directories
                    base_name = os.path.basename(file_name)
                    if base_name:  # Skip directories
                        try:
                            index = int(base_name)
                            if self.start_index <= index <= self.stop_index:
                                test_cases.append((index, file_name))
                        except ValueError:
                            # Skip files that don't have numeric names
                            pass
                
                test_cases.sort()  # Sort by index
                
                if not test_cases:
                    print(f"No valid test cases found in zip file in range {self.start_index}-{self.stop_index}")
                    return
                
                print(f"Found {len(test_cases)} test cases in zip file")
                
                # Process each test case
                for index, file_path in test_cases:
                    try:
                        with zip_ref.open(file_path) as file:
                            data = file.read()
                            self.inject(index, data)
                    except KeyboardInterrupt:
                        print("\nTest case injection aborted by user.")
                        return
                    except Exception as e:
                        print(f"Error processing {file_path}: {str(e)}")
                        
        except zipfile.BadZipFile:
            print(f"Error: {self.zip_file} is not a valid zip file")
        except Exception as e:
            print(f"Error reading zip file: {str(e)}")

    def parse_test_cases(self):
        """Parse test cases from directory or zip file"""
        if self.single_file:
            self.parse_single_file()
            return
            
        # First check for explicitly set zip file
        zip_path = None
        if self.zip_file:
            zip_path = self.zip_file
        else:
            # Check if a zip file with the same base name as test_case_dir exists
            auto_zip_path = f"{self.test_case_dir}.zip"
            if Path(auto_zip_path).exists():
                print(f"Found zip file {auto_zip_path}, using it instead of directory")
                zip_path = auto_zip_path
        
        # If we have a zip path, use it
        if zip_path:
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    file_list = zip_ref.namelist()
                    
                    # Filter and sort test cases
                    test_cases = []
                    for file_name in file_list:
                        # Extract just the filename without directories
                        base_name = os.path.basename(file_name)
                        if base_name:  # Skip directories
                            try:
                                index = int(base_name)
                                if self.start_index <= index <= self.stop_index:
                                    test_cases.append((index, file_name))
                            except ValueError:
                                # Skip files that don't have numeric names
                                pass
                    
                    test_cases.sort()  # Sort by index
                    
                    if not test_cases:
                        print(f"No valid test cases found in zip file in range {self.start_index}-{self.stop_index}")
                        return
                    
                    print(f"Found {len(test_cases)} test cases in zip file")
                    
                    # Process each test case
                    for index, file_path in test_cases:
                        try:
                            with zip_ref.open(file_path) as file:
                                data = file.read()
                                self.inject(index, data)
                        except KeyboardInterrupt:
                            print("\nTest case injection aborted by user.")
                            return
                        except Exception as e:
                            print(f"Error processing {file_path}: {str(e)}")
                    
                    return  # Successfully processed zip file, don't check directory
                    
            except zipfile.BadZipFile:
                print(f"Warning: {zip_path} exists but is not a valid zip file")
                # Fall back to directory-based loading
            except Exception as e:
                print(f"Error reading zip file: {str(e)}")
                # Fall back to directory-based loading
            
        # If no zip file or zip file failed, try directory
        test_cases = []
        test_case_path = Path(self.test_case_dir)
        
        if not test_case_path.exists():
            print(f"Warning: Test case directory '{self.test_case_dir}' not found")
            print("Server will start but no test cases will be available unless provided by '-file'")
            return
        
        # Continue with directory-based test case loading
        for file in sorted(test_case_path.iterdir()):
            try:
                index = int(file.name)
                if self.start_index <= index <= self.stop_index:
                    test_cases.append((index, file))
            except ValueError:
                # Skip files that don't have numeric names
                pass
                
        try:
            for index, file_path in test_cases:
                try:
                    with open(file_path, 'rb') as file:
                        data = file.read()
                        self.inject(index, data)
                except KeyboardInterrupt:
                    print("\nTest case injection aborted by user.")
                    return
                except Exception as e:
                    print(f"Error: {str(e)}")
        except KeyboardInterrupt:
            print("\nTest case injection aborted by user.")
            return

    def finish(self):
        """Clean up server socket"""
        if self.server_socket:
            self.server_socket.close()

    def serve_forever(self):
        """Keep server running to handle incoming connections"""
        print("Server waiting for connections. Press Ctrl+C to exit.")
        request_count = 0
        
        # Set a short timeout to make Ctrl+C more responsive
        self.server_socket.settimeout(0.5)
        
        try:
            while True:
                try:
                    client_socket, addr = self.server_socket.accept()
                    request_count += 1
                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"\n[{now}] Connection #{request_count} from [{addr[0]}:{addr[1]}]")
                    
                    # Read and log the request
                    try:
                        request = client_socket.recv(1024)
                        if request:
                            request_text = request.decode('utf-8', errors='replace').strip()
                            first_line = request_text.split('\n')[0] if '\n' in request_text else request_text
                            print(f"Received request: {first_line}")
                    except Exception as io:
                        print(f"Error reading request: {str(io)}")
                        continue
                    
                    # Send a basic HTTP response if no test case is specified
                    response = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 13\r\n\r\nHello, World!"
                    try:
                        client_socket.sendall(response)
                        print(f"Sent response: HTTP/1.1 200 OK (13 bytes)")
                    except Exception as io:
                        print(f"Error sending response: {str(io)}")
                    
                    try:
                        client_socket.close()
                    except Exception as s:
                        print(f"Error closing socket: {str(s)}")
                
                except socket.timeout:
                    # This is expected, continue the loop to allow for keyboard interrupt
                    continue
                except KeyboardInterrupt:
                    print("\nServer shutting down...")
                    sys.exit(0)  # Exit immediately
                except Exception as e:
                    print(f"Error: {str(e)}")
        except KeyboardInterrupt:
            print("\nServer shutting down...")
            sys.exit(0)  # Exit immediately

    def run(self):
        try:
            self.prepare()
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now}] Server listening for connections on port {self.port}...")
            
            # Parse and inject test cases if available
            has_test_cases = False
            
            try:
                if self.single_file:
                    has_test_cases = True
                    self.parse_single_file()
                else:
                    # Check for explicit zip file or auto-detected zip file
                    zip_path = self.zip_file or f"{self.test_case_dir}.zip"
                    zip_exists = Path(zip_path).exists()
                    
                    if zip_exists:
                        try:
                            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                                for file_name in zip_ref.namelist():
                                    base_name = os.path.basename(file_name)
                                    if base_name:  # Skip directories
                                        try:
                                            index = int(base_name)
                                            if self.start_index <= index <= self.stop_index:
                                                has_test_cases = True
                                                break
                                        except ValueError:
                                            pass
                        except Exception:
                            pass  # If zip file check fails, we'll fall back to directory check
                    
                    # If no test cases found in zip, check directory
                    if not has_test_cases and Path(self.test_case_dir).exists():
                        test_case_path = Path(self.test_case_dir)
                        for file in sorted(test_case_path.iterdir()):
                            try:
                                index = int(file.name)
                                if self.start_index <= index <= self.stop_index:
                                    has_test_cases = True
                                    break
                            except ValueError:
                                pass
                    
                    # Parse test cases if found
                    if has_test_cases:
                        self.parse_test_cases()
                    else:
                        print(f"No test cases found in range {self.start_index}-{self.stop_index}")
                        if not zip_exists and not Path(self.test_case_dir).exists():
                            print(f"Neither {zip_path} nor directory {self.test_case_dir} found")
                
            except KeyboardInterrupt:
                print("\nServer operation interrupted by user.")
                return
            
            # Keep server running if no test cases were injected or if finished injecting
            if not has_test_cases or not self.single_file:
                self.serve_forever()
                
        except KeyboardInterrupt:
            print("\nServer shutting down...")
        finally:
            self.finish()

def main():
    # Print usage information at startup
    print_usage()
    
    parser = argparse.ArgumentParser(description='HTTP Reply Test Server')
    parser.add_argument('-port', type=int, default=8000, 
                      help='Port number to listen on (default: 8000)')
    parser.add_argument('-closedelay', type=int, default=0,
                      help='Delay in milliseconds before closing socket (default: 0)')
    parser.add_argument('-single', type=int,
                      help='Inject single test case with specified index')
    parser.add_argument('-start', type=int, default=0,
                      help='Start test case index (default: 0)')
    parser.add_argument('-stop', type=int, default=sys.maxsize,
                      help='Stop test case index (default: max int)')
    parser.add_argument('-file', type=str,
                      help='Send single file instead of test cases')
    parser.add_argument('-testdir', type=str, default='testcases',
                      help='Directory containing test cases (default: testcases)')
    parser.add_argument('-zip', type=str,
                      help='Path to zip file containing test cases')

    args = parser.parse_args()
    
    server = HTTPReplyTestServer()
    server.port = args.port
    server.close_delay = args.closedelay
    
    # Handle single index option
    if args.single is not None:
        server.start_index = args.single
        server.stop_index = args.single
    else:
        server.start_index = args.start
        server.stop_index = args.stop
        
    server.test_case_dir = args.testdir
    server.single_file = args.file
    server.zip_file = args.zip
    
    server.run()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nServer shutting down...")
        sys.exit(0)