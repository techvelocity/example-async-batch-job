import logging
import os
from fastapi import FastAPI, BackgroundTasks, UploadFile, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from kubernetes import config

from base_api import CreateProcessVideoJob

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

PROTOCOL = os.environ.get('PROTOCOL')
HOST = os.environ.get('HOST')
MONGO_HOST = os.environ.get('MONGO_HOST')
MONGO_PORT = os.environ.get('MONGO_PORT')

config.load_incluster_config()


@app.on_event('startup')
async def get_mongo():
    video_db = AsyncIOMotorClient(f'mongodb://{MONGO_HOST}:{MONGO_PORT}').video
    app.fs = AsyncIOMotorGridFSBucket(video_db)


async def _get_videos():
    videos = app.fs.find()
    docs = await videos.to_list(None)
    video_urls = ''
    for i in docs:
        filename = i['filename']
        v = f'<a href="{PROTOCOL}://{HOST}/app/stream/{filename}" target="_blank">http://{HOST}/stream/{filename}</a>'
        video_urls = video_urls + '<br>' + v
    return video_urls


async def _process_video(filename):
    create_batch_job = CreateProcessVideoJob(filename)
    create_batch_job.create_job_object()
    create_batch_job.create_job()


@app.get('/api/check-for-filename/{filename}')
async def check_for_filename(filename: str):
    cursor = app.fs.find(
        {'filename': filename}, no_cursor_timeout=True)
    while (await cursor.fetch_next):
        f = cursor.next_object()
        if f:
            return {'error': 'filename already exists'}
    return ''


@app.post('/api/upload')
async def upload(file: UploadFile, background_tasks: BackgroundTasks):
    if file.filename:
        grid_in = app.fs.open_upload_stream(
            file.filename, metadata={'contentType': 'video/mp4'})
        data = await file.read()
        await grid_in.write(data)
        await grid_in.close()

        background_tasks.add_task(_process_video, file.filename)
        videos = await _get_videos()
        return videos
    return ''


@app.get('/api/stream/{filename}')
async def stream(filename: str):
    grid_out = await app.fs.open_download_stream_by_name(filename)

    async def read():
        while grid_out.tell() < grid_out.length:
            yield await grid_out.readchunk()

    return StreamingResponse(
        read(), media_type='video/mp4', headers={
            'Content-Length': str(grid_out.length)})
