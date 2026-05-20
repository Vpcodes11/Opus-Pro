import unittest
from unittest.mock import patch
from app.core.downloader import get_video_info_url

class TestDownloader(unittest.TestCase):
    @patch('yt_dlp.YoutubeDL')
    def test_get_video_info_url_exception(self, mock_ytdl):
        # Setup mock to raise an exception when extract_info is called
        mock_instance = mock_ytdl.return_value.__enter__.return_value
        mock_instance.extract_info.side_effect = Exception("Mocked download error")

        result = get_video_info_url("https://www.youtube.com/watch?v=invalid")

        self.assertEqual(result, {'title': 'Unknown', 'duration': 0})

if __name__ == '__main__':
    unittest.main()
