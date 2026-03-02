import yt_dlp

def download_vtuber_video(url, output_path='input_video.mp4'):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# 例：宝鐘マリンの公式チャンネル動画など
download_vtuber_video('https://www.youtube.com/watch?v=MYo9RmjXsmY', output_path='./videos/lunlun.mp4')