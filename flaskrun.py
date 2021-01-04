from FanstiBgs import create_app
# from FanstiBgs.extensions.register_ext import celery

app = create_app()

if __name__ == '__main__':
    app.run(port=8002)
