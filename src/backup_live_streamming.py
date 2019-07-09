from pysony import SonyAPI
def liveview(filename=None):
    camera = SonyAPI()

    f = camera.liveview()
    with open(filename, 'wb') as backup:
        while True:
            data = f.read(100)
            backup.write(data)

if __name__ == "__main__":
    liveview('backup_data.txt')
