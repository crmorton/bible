from bible_api.api import create_app

app = create_app()

if __name__ == '__main__':
    import uvicorn
    from bible_api.config import DEFAULT_PORT

    uvicorn.run('bible_api.api:create_app()', host='0.0.0.0', port=DEFAULT_PORT)
