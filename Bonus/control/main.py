from client import TaskmasterCtlClient
import readline
import sys

def main():
    client = TaskmasterCtlClient(host="127.0.0.1", port=12345)
    # Check if attach command was provided as argument
    if len(sys.argv) > 2 and sys.argv[1] == "attach":
        try:
            client.connect()
            print("Connected to Taskmaster server.")
            client.attach(sys.argv[2])
        except Exception as e:
            print("Error:", e)
        finally:
            client.close()
        return

    # Interactive mode
    try:
        client.connect()
        print("Connected to Taskmaster server.")
    except Exception as e:
        print("Initial connect failed, will retry on demand:", e)

    try:
        while True:
            cmd = input("taskmasterctl> ").strip()
            readline.add_history(cmd)
            if cmd.lower() == "exit":
                break

            try:
                cmd_parts = cmd.split()
                if not cmd_parts:
                    continue
                    
                if cmd_parts[0] == "attach" and len(cmd_parts) > 1:
                    # Handle attach command specially
                    client.attach(cmd_parts[1])
                else:
                    # Handle other commands normally
                    response = client.send_command(cmd)
                    print(response)
            except (BrokenPipeError, ConnectionResetError, OSError, ConnectionError) as conn_err:
                print("Connection error:", conn_err, "- attempting to reconnect...")
                try:
                    client.connect()
                    print("Reconnected.")
                    try:
                        response = client.send_command(cmd)
                    except Exception as send_err:
                        print("Failed to send after reconnect:", send_err)
                        continue  
                except Exception as reconnect_err:
                    print("Reconnect failed:", reconnect_err)
                    continue 
            except Exception as e:
                print("Error sending command:", e)
                continue

    except Exception as e:
        print("An error occurred:", e)
    finally:
        try:
            client.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
