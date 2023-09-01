import argparse
import asyncio
import os
import cv2
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from vidgear.gears import VideoGear

MONGO_HOST = os.environ.get('MONGO_HOST')
MONGO_PORT = os.environ.get('MONGO_PORT')


class ProcessVideo:
    def __init__(self, filename):
        self.raw_video = None
        self.processed_video = None
        self.filename = filename
        self.base_filename = None
        self.video_db = AsyncIOMotorClient(
            f'mongodb://{MONGO_HOST}:{MONGO_PORT}').video
        self.library = self.video_db.library
        self.fs = AsyncIOMotorGridFSBucket(self.video_db)

    async def download_video(self):
        cursor = self.fs.find(
            {'filename': self.filename}, no_cursor_timeout=True)
        while (await cursor.fetch_next):
            grid_out = cursor.next_object()
            self.raw_video = await grid_out.read()
            with open('video.mp4', 'wb') as f:
                f.write(self.raw_video)

    def _stream_to_file(self):
        self.base_filename = os.path.splitext(self.filename)[0]
        output_filename = f"{self.base_filename}_stabilized.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        # Open the VideoWriter
        output_writer = None
        frame_size = None

        while True:
            frame = self.processed_video.read()
            if frame is None:
                break

            if output_writer is None:
                frame_size = (frame.shape[1], frame.shape[0])
                output_writer = cv2.VideoWriter(
                    output_filename, fourcc, 30.0, frame_size)

            output_writer.write(frame)

        if output_writer is not None:
            output_writer.release()
            print(f"Processed frames saved to {output_filename}")
        else:
            print("No frames were processed.")

    def process_video(self):
        self.processed_video = \
            VideoGear(source='video.mp4', stabilize=True).start()
        self._stream_to_file()

    async def upload_video(self):
        filename = f"{self.base_filename}_stabilized.mp4"
        grid_in = self.fs.open_upload_stream(
            filename, metadata={'contentType': 'video/mp4'})
        with open(filename, 'rb') as file:
            data = file.read()
        await grid_in.write(data)
        await grid_in.close()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--filename', dest='filename', type=str, required=True)
    _args = parser.parse_args()
    return _args


async def main(filename):
    pv = ProcessVideo(filename=filename)
    await pv.download_video()
    pv.process_video()
    await pv.upload_video()


if __name__ == '__main__':
    args = parse_args()
    asyncio.run(main(args.filename))
