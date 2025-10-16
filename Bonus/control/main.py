from client import TaskmasterCtlClient

def main():
    client = TaskmasterCtlClient(host="127.0.0.1", port=12345)
    client.connect()
    print("Connected to Taskmaster server.")
    try:
        while True:
            cmd = input("taskmasterctl> ").strip()
            if cmd.lower() == "exit":
                break
            response = client.send_command(cmd)
            print("Server:", response)
    except Exception as e:
        print("An error occurred:", e)
    finally:
        client.close()

if __name__ == "__main__":
    main()
