from kfp import dsl


@dsl.component(base_image="python:3.11-slim")
def check_accuracy(mAP50: float, threshold: float) -> str:
    """
    mAP50 が閾値を超えているか判定する。
    超えていれば "deploy"、未満なら "skip" を返す。
    この戻り値を pipeline/definition.py の dsl.Condition で条件分岐に使う。
    """
    if mAP50 >= threshold:
        print(f"mAP50 ({mAP50:.4f}) >= threshold ({threshold}) → deploy")
        return "deploy"
    else:
        print(f"mAP50 ({mAP50:.4f}) < threshold ({threshold}) → skip deployment")
        return "skip"
