import cv2
import os

def extract_frames(video_path, output_dir, interval_sec=2):
  if not os.path.exists(output_dir):
      os.makedirs(output_dir)

  cap = cv2.VideoCapture(video_path)
  # 修正箇所: cv2.get ではなく cap.get を使用
  fps = cap.get(cv2.CAP_PROP_FPS) 
  if fps == 0: fps = 30 # 万が一取得できない場合のデフォルト
  
  interval_frames = int(fps * interval_sec)
  count = 0
  saved_count = 0

  print(f"Extracting frames every {interval_sec} seconds...")
  while cap.isOpened():
      ret, frame = cap.read()
      if not ret:
          break
      if count % interval_frames == 0:
          cv2.imwrite(os.path.join(output_dir, f"debidebi_frame_{saved_count:04d}.jpg"), frame)
          saved_count += 1
      count += 1

  cap.release()
#   os.remove(video_path) # 一時ファイルを削除
  print(f"Success: {saved_count} images saved to {output_dir}")

extract_frames('videos/debidebi.mp4', './frames', interval_sec=15)