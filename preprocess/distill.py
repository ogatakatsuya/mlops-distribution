from autodistill.detection import CaptionOntology
from autodistill_grounding_dino import GroundingDINO

# 1. オントロジー（何をどう呼ぶか）の定義
# VLMへの指示語 : YOLOのクラス名
ontology = CaptionOntology({
    "anime girl with red marine captain hat": "houshou_marine",
    "anime girl with rabbit ears": "usada_pekora"
})

# 2. 教師モデル（VLM）の初期化
base_model = GroundingDINO(ontology=ontology)

# 3. 自動ラベリングの実行
# ./raw_images 内の画像を解析し、./dataset にYOLO形式で保存
dataset = base_model.label(
    input_folder="./raw_images",
    output_folder="./vtuber_dataset"
)

# 4. 生徒モデル（YOLO）の学習
# これだけで、VLMが作ったラベルを元にYOLOの訓練が始まります
# target_model = YOLOv8("yolo26n.pt") # 2026年最新のNanoモデルを想定
# target_model.train(data="./vtuber_dataset/data.yaml", epochs=50)