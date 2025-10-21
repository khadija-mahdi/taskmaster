from client import TaskmasterCtlClient
import readline

def main():
    client = TaskmasterCtlClient(host="127.0.0.1", port=12345)
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
                response = client.send_command(cmd)
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
