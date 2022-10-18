from app import create_app


def CreateIndex():
    app = create_app("dev")
    with app.app_context():
        from app.elasticsearch7  import ESCreateIndex
        ESCreateIndex()
    print("created index")
    
if __name__ == "__main__":
    CreateIndex()