"""
test_upload_video_success:
Action: Upload a valid 10-second video.
Expect: Success (201), Job saved in DB, and AI worker started.

test_upload_video_too_long:
Action: Upload a 40-second video (Limit is 30s).
Expect: Rejection (400 Error) and NO data saved to DB.

test_upload_video_missing_file:
Action: Send an upload request without attaching a file.
Expect: Rejection (400 Error) saying "file required".

test_list_and_retrieve:
Action: Request the list of jobs and a specific job ID.
Expect: The server returns the correct data (200 OK).
"""

import shutil
import tempfile
from django.test import override_settings
from rest_framework.test import APITestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock
from rest_framework import status
from api.models import VideoJob

MEDIA_ROOT = tempfile.mkdtemp()

@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class JobEndpointTests(APITestCase):

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.job = VideoJob.objects.create(
            status="pending",
            original="videos/test_existing.mp4"
        )
        self.list_url = reverse('jobs-list')
        self.detail_url = reverse('jobs-detail', args=[self.job.id])

    @patch("api.views.VideoFileClip")
    @patch("api.views.process_video_task.delay")
    def test_upload_video_success(self, mock_task, mock_video_clip):
        mock_clip_instance = MagicMock()
        mock_clip_instance.duration = 10.0
        mock_video_clip.return_value.__enter__.return_value = mock_clip_instance

        video_content = b"fake_video_content"
        video_file = SimpleUploadedFile(
            "test_video.mp4", 
            video_content, 
            content_type="video/mp4"
        )

        payload = {"file": video_file}
        
        response = self.client.post(self.list_url, payload, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(VideoJob.objects.count(), 2)
        
        new_job = VideoJob.objects.latest('created_at')
        self.assertEqual(new_job.status, "processing")
        
        mock_task.assert_called_once()
        args, _ = mock_task.call_args
        self.assertEqual(args[0], new_job.id)

    @patch("api.views.VideoFileClip")
    def test_upload_video_too_long(self, mock_video_clip):
        mock_clip_instance = MagicMock()
        mock_clip_instance.duration = 40.0
        mock_video_clip.return_value.__enter__.return_value = mock_clip_instance

        video_file = SimpleUploadedFile("long_video.mp4", b"content", content_type="video/mp4")
        payload = {"file": video_file}

        response = self.client.post(self.list_url, payload, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], "video longer than 30 seconds")
        self.assertEqual(VideoJob.objects.count(), 1)

    def test_upload_video_missing_file(self):
        payload = {}
        response = self.client.post(self.list_url, payload, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], "file required")

    def test_list_jobs(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertTrue(len(data) >= 1)

    def test_retrieve_job(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.job.id)