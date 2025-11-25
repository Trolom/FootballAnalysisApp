import shutil
import tempfile
from django.test import override_settings
from rest_framework.test import APITestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock
from rest_framework import status
from api.models import VideoJob

# Create a temporary directory for media files during tests
MEDIA_ROOT = tempfile.mkdtemp()

@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class JobEndpointTests(APITestCase):

    @classmethod
    def tearDownClass(cls):
        # Clean up the temporary media directory after tests run
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
        # Setup the video mock to pass the "duration" check
        # The view uses: with VideoFileClip(...) as clip:
        # I need the context manager to return a mock with .duration
        mock_clip_instance = MagicMock()
        mock_clip_instance.duration = 10.0  # Less than MAX_SECONDS (30)
        mock_video_clip.return_value.__enter__.return_value = mock_clip_instance

        # Creating a fake video file
        video_content = b"fake_video_content"
        video_file = SimpleUploadedFile(
            "test_video.mp4", 
            video_content, 
            content_type="video/mp4"
        )

        payload = {"file": video_file}
        
        # Execute POST
        response = self.client.post(self.list_url, payload, format='multipart')

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(VideoJob.objects.count(), 2)
        
        new_job = VideoJob.objects.latest('created_at')
        self.assertEqual(new_job.status, "processing")
        
        # Verify Celery was called
        mock_task.assert_called_once()

    def test_upload_video_missing_file(self):
        payload = {}
        response = self.client.post(self.list_url, payload, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # The view returns {"detail": "file required"}
        self.assertIn('detail', response.data)
        self.assertEqual(response.data['detail'], "file required")

    def test_list_jobs(self):
        """
        Ensure we can list jobs.
        """
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertTrue(len(data) >= 1)

    def test_retrieve_job(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.job.id)