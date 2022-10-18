from app import create_app

app = create_app("dev")
app.secret_key = "123456"

if __name__ == "__main__":
    app.run(host="127.0.0.1", port = 8000, debug = True)
    
